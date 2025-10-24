from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

from django.db.models import Prefetch, Q

from ..domain.optical import _fetch_port_optical_snapshot
from ..models import Device, FiberCable, Port, Site
from ..services.zabbix_service import zabbix_request

ZABBIX_REQUEST = zabbix_request

logger = logging.getLogger(__name__)


class InventoryUseCaseError(Exception):
    """Erro genérico para casos de uso de inventário."""


class InventoryValidationError(InventoryUseCaseError):
    """Erro de validação de entrada."""


class InventoryNotFound(InventoryUseCaseError):
    """Recurso solicitado não encontrado."""


def _normalize_identifier(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _extract_key_tokens(key: str | None) -> List[str]:
    if not key or "[" not in key or "]" not in key:
        return []
    try:
        start = key.index("[") + 1
        end = key.rindex("]")
    except ValueError:
        return []
    inside = key[start:end]
    tokens: List[str] = []
    for part in inside.split(","):
        token = part.strip().strip('"').strip("'")
        if token:
            tokens.append(token)
    return tokens


def _identify_item_role(key_lower: str, name_lower: str) -> str | None:
    if not key_lower:
        return None

    if "ifoperstatus" in key_lower:
        return "primary_oper"
    if "lastdowntime" in key_lower:
        return "legacy_lastdown"

    traffic_in_markers = ("net.if.in", "ifhcin", "ifinoctets")
    traffic_out_markers = ("net.if.out", "ifhcout", "ifoutoctets")
    if any(marker in key_lower for marker in traffic_in_markers):
        return "traffic_in"
    if any(marker in key_lower for marker in traffic_out_markers):
        return "traffic_out"

    is_threshold = any(word in key_lower for word in ("threshold", "warn", "alarm", "limit"))

    rx_markers = (
        "hwentityopticallanerxpower",
        "rxpower",
        "opticalrx",
        "opticrx",
        "rx_dbm",
    )
    tx_markers = (
        "hwentityopticallanetxpower",
        "txpower",
        "opticaltx",
        "optictx",
        "tx_dbm",
    )

    if not is_threshold:
        if any(marker in key_lower for marker in tx_markers) or (
            "power" in key_lower and "tx" in key_lower and "rx" not in key_lower
        ):
            return "optical_tx"
        if any(marker in key_lower for marker in rx_markers) or (
            "power" in key_lower and "rx" in key_lower and "tx" not in key_lower
        ):
            return "optical_rx"

        if name_lower:
            if any(marker in name_lower for marker in tx_markers):
                return "optical_tx"
            if any(marker in name_lower for marker in rx_markers):
                return "optical_rx"

    return None


def _score_port_match(entry: Dict[str, Any], tokens: Iterable[str], combined_text: str, combined_normalized: str) -> int:
    score = 0
    port_lower = entry["lower"]
    normalized = entry["normalized"]
    trimmed = entry["trimmed"]
    normalized_trimmed = entry["normalized_trimmed"]

    if port_lower and port_lower in combined_text:
        score = max(score, len(port_lower) + 60)
    if trimmed and trimmed in combined_text:
        score = max(score, len(trimmed) + 55)
    if normalized and normalized in combined_normalized:
        score = max(score, len(normalized) + 50)
    if normalized_trimmed and normalized_trimmed in combined_normalized:
        score = max(score, len(normalized_trimmed) + 45)

    for token in tokens:
        token_lower = token.lower()
        token_norm = _normalize_identifier(token)
        if token_lower == port_lower:
            score = max(score, len(token_lower) + 120)
        if trimmed and token_lower == trimmed:
            score = max(score, len(token_lower) + 100)
        if token_norm and token_norm == normalized:
            score = max(score, len(token_norm) + 90)
        if normalized_trimmed and token_norm == normalized_trimmed:
            score = max(score, len(token_norm) + 85)
    return score


def _apply_port_updates(port: Port, updates: Dict[str, Any], updated_fields: set[str]) -> None:
    if not updates:
        return
    Port.objects.filter(pk=port.pk).update(**updates)
    for field, value in updates.items():
        setattr(port, field, value)
        updated_fields.add(field)


def get_device_ports(device_id: int) -> Dict[str, Any]:
    try:
        device = Device.objects.get(id=device_id)
    except Device.DoesNotExist as exc:
        raise InventoryNotFound("Device nao encontrado") from exc

    ports = Port.objects.filter(device=device).select_related("device")
    ports_data: List[Dict[str, Any]] = []

    for port in ports:
        cable_as_origin = FiberCable.objects.filter(origin_port=port).first()
        cable_as_dest = FiberCable.objects.filter(destination_port=port).first()
        cable = cable_as_origin or cable_as_dest

        ports_data.append(
            {
                "id": port.id,
                "name": port.name,
                "device": port.device.name,
                "fiber_cable_id": cable.id if cable else None,
                "zabbix_item_key": port.zabbix_item_key,
                "notes": port.notes,
            }
        )

    return {"ports": ports_data}


def get_device_ports_with_optical(device_id: int) -> Dict[str, Any]:
    try:
        device = Device.objects.select_related("site").get(id=device_id)
    except Device.DoesNotExist as exc:
        raise InventoryNotFound("Device nao encontrado") from exc

    ports = Port.objects.filter(device=device).select_related("device")
    cables = (
        FiberCable.objects.filter(Q(origin_port__device=device) | Q(destination_port__device=device))
        .select_related("origin_port", "destination_port")
    )

    cable_origin_map: Dict[int, FiberCable] = {}
    cable_dest_map: Dict[int, FiberCable] = {}
    for cable in cables:
        cable_origin_map.setdefault(cable.origin_port_id, cable)
        cable_dest_map.setdefault(cable.destination_port_id, cable)

    discovery_cache: Dict[Any, Any] = {}
    ports_with_optical: List[Dict[str, Any]] = []

    for port in ports:
        cable = cable_origin_map.get(port.id) or cable_dest_map.get(port.id)
        optical_snapshot = _fetch_port_optical_snapshot(port, discovery_cache=discovery_cache)
        ports_with_optical.append(
            {
                "id": port.id,
                "name": port.name,
                "cable_id": cable.id if cable else None,
                "cable_name": cable.name if cable else None,
                "optical": optical_snapshot,
            }
        )

    return {
        "device_id": device.id,
        "device_name": device.name,
        "ports": ports_with_optical,
    }


def device_port_optical_status(port_id: int) -> Dict[str, Any]:
    try:
        port = Port.objects.select_related("device").get(id=port_id)
    except Port.DoesNotExist as exc:
        raise InventoryNotFound("Porta nao encontrada") from exc

    hostid = (port.device.zabbix_hostid or "").strip()
    if not hostid:
        raise InventoryValidationError("Device sem Zabbix Host ID")

    optical_snapshot = _fetch_port_optical_snapshot(port)
    return {
        "port_id": port.id,
        "port_name": port.name,
        "optical": optical_snapshot,
    }


def add_device_from_zabbix(payload: Mapping[str, Any]) -> Dict[str, Any]:
    hostid = payload.get("hostid") or payload.get("device_name")
    if not hostid:
        raise InventoryValidationError("hostid obrigatorio")

    zabbix_data = ZABBIX_REQUEST(
        "host.get",
        {
            "output": ["hostid", "name", "host"],
            "hostids": hostid,
            "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type"],
        },
    )
    if not zabbix_data:
        raise InventoryNotFound("Host nao encontrado no Zabbix")

    host = zabbix_data[0]
    site_name = host.get("name") or host.get("host")

    lat: Optional[str] = None
    lon: Optional[str] = None
    address: Optional[str] = None

    if "inventory" in host:
        inv = host["inventory"]
        lat = inv.get("location_lat")
        lon = inv.get("location_lon")
        address = inv.get("site_address") or inv.get("location")
    else:
        inv_data = ZABBIX_REQUEST(
            "host.get",
            {"output": ["hostid"], "hostids": hostid, "selectInventory": "extend"},
        )
        if inv_data and "inventory" in inv_data[0]:
            inv = inv_data[0]["inventory"]
            lat = inv.get("location_lat")
            lon = inv.get("location_lon")
            address = inv.get("site_address") or inv.get("location")

    site, site_created = Site.objects.get_or_create(name=site_name)
    update_fields: List[str] = []
    if lat:
        try:
            site.latitude = float(lat)
            update_fields.append("latitude")
        except Exception:
            pass
    if lon:
        try:
            site.longitude = float(lon)
            update_fields.append("longitude")
        except Exception:
            pass
    if address:
        site.city = address
        update_fields.append("city")
    if update_fields:
        site.save(update_fields=update_fields)

    device, created = Device.objects.get_or_create(
        site=site,
        name=host.get("host"),
        defaults={
            "vendor": "",
            "model": "",
            "zabbix_hostid": hostid,
        },
    )
    if not created and (not device.zabbix_hostid or str(device.zabbix_hostid) != str(hostid)):
        device.zabbix_hostid = str(hostid)
        device.save(update_fields=["zabbix_hostid"])

    host_items = ZABBIX_REQUEST(
        "item.get",
        {
            "output": ["itemid", "key_", "name", "interfaceid", "lastvalue", "units", "snmpindex"],
            "hostids": hostid,
            "filter": {"status": "0"},
            "limit": 2000,
        },
    ) or []

    port_records: List[Dict[str, Any]] = []
    primary_items: List[Dict[str, Any]] = []
    legacy_primary_items: List[Dict[str, Any]] = []

    for item in host_items:
        key = item.get("key_") or ""
        key_lower = key.lower()
        name_lower = (item.get("name") or "").lower()
        role = _identify_item_role(key_lower, name_lower)
        item["_role"] = role
        if role == "primary_oper":
            primary_items.append(item)
        elif role == "legacy_lastdown":
            legacy_primary_items.append(item)

    creation_candidates = primary_items if primary_items else legacy_primary_items
    if not creation_candidates:
        creation_candidates = [
            item
            for item in host_items
            if (item.get("key_") or "").lower().startswith(("ifoperstatus[", "lastdowntime["))
        ]

    port_record_map: Dict[str, Dict[str, Any]] = {}

    for item in creation_candidates:
        key = item.get("key_") or ""
        tokens = _extract_key_tokens(key)
        if not tokens:
            continue
        port_name = tokens[0].strip()
        if not port_name:
            continue

        defaults = {
            "zabbix_item_key": key,
            "zabbix_interfaceid": str(item.get("interfaceid") or ""),
            "zabbix_itemid": str(item.get("itemid") or ""),
            "notes": item.get("name", ""),
        }

        port, port_created = Port.objects.get_or_create(
            device=device,
            name=port_name,
            defaults=defaults,
        )

        record = {
            "port": port,
            "created": port_created,
            "updated_fields": set(),
            "defaults": defaults,
        }
        port_records.append(record)
        port_record_map[(port.device_id, port.name.lower())] = record

    if not port_records:
        for item in host_items:
            key = item.get("key_") or ""
            tokens = _extract_key_tokens(key)
            if not tokens:
                continue
            port_name = tokens[0].strip()
            if not port_name:
                continue
            port, _ = Port.objects.get_or_create(
                device=device,
                name=port_name,
                defaults={
                    "zabbix_item_key": key,
                    "zabbix_interfaceid": str(item.get("interfaceid") or ""),
                    "notes": item.get("name", ""),
                },
            )
            record = {
                "port": port,
                "created": False,
                "updated_fields": set(),
                "defaults": {},
            }
            port_records.append(record)
            port_record_map[(port.device_id, port.name.lower())] = record

    created_summary = {"sites": int(site_created), "devices": int(created), "ports": 0}

    port_entries: List[Dict[str, Any]] = []
    for record in port_records:
        port = record["port"]
        lower = port.name.lower()
        normalized = _normalize_identifier(lower)
        trimmed = lower[1:] if lower.startswith("x") else lower
        normalized_trimmed = normalized[1:] if normalized.startswith("x") else normalized
        port_entries.append(
            {
                "port": port,
                "record": record,
                "lower": lower,
                "normalized": normalized,
                "trimmed": trimmed,
                "normalized_trimmed": normalized_trimmed,
            }
        )

    for item in host_items:
        key = item.get("key_") or ""
        key_lower = key.lower()
        name_lower = (item.get("name") or "").lower()
        role = item.get("_role") or _identify_item_role(key_lower, name_lower)
        if not role:
            continue

        tokens = _extract_key_tokens(key)
        combined_text = f"{key_lower} {name_lower}"
        combined_normalized = _normalize_identifier(combined_text)

        best_entry = None
        best_score = 0
        for entry in port_entries:
            score = _score_port_match(entry, tokens, combined_text, combined_normalized)
            if score > best_score:
                best_score = score
                best_entry = entry
        if not best_entry or best_score < 45:
            continue

        port = best_entry["port"]
        record = best_entry["record"]
        updates: Dict[str, Any] = {}
        iface_id = str(item.get("interfaceid") or "")
        if iface_id and iface_id != "0" and port.zabbix_interfaceid != iface_id:
            updates["zabbix_interfaceid"] = iface_id

        item_id = str(item.get("itemid") or "")
        if role in ("primary_oper", "legacy_lastdown"):
            should_override = role == "primary_oper" or not port.zabbix_item_key
            if key and should_override and port.zabbix_item_key != key:
                updates["zabbix_item_key"] = key
            if item_id:
                if should_override and port.zabbix_itemid != item_id:
                    updates["zabbix_itemid"] = item_id
                elif role == "legacy_lastdown" and not port.zabbix_itemid:
                    updates["zabbix_itemid"] = item_id
            note = item.get("name", "")
            if note and should_override and port.notes != note:
                updates["notes"] = note
        elif role == "traffic_in":
            if item_id and not port.zabbix_item_id_traffic_in:
                updates["zabbix_item_id_trafego_in"] = item_id
        elif role == "traffic_out":
            if item_id and not port.zabbix_item_id_traffic_out:
                updates["zabbix_item_id_trafego_out"] = item_id
        elif role == "optical_rx":
            if key and port.rx_power_item_key != key:
                updates["rx_power_item_key"] = key
        elif role == "optical_tx":
            if key and port.tx_power_item_key != key:
                updates["tx_power_item_key"] = key

        _apply_port_updates(port, updates, record["updated_fields"])

    discovery_cache: Dict[Any, Any] = {}
    optical_snapshots: List[Dict[str, Any]] = []
    for record in port_records:
        snapshot = _fetch_port_optical_snapshot(record["port"], discovery_cache=discovery_cache)
        record["optical_snapshot"] = snapshot
        optical_snapshots.append(
            {
                "port_id": record["port"].id,
                "rx_key": snapshot.get("rx_key"),
                "tx_key": snapshot.get("tx_key"),
                "rx_dbm": snapshot.get("rx_dbm"),
                "tx_dbm": snapshot.get("tx_dbm"),
            }
        )

    ports_created_payload: List[Dict[str, Any]] = []
    ports_updated_payload: List[Dict[str, Any]] = []
    for record in port_records:
        port = record["port"]
        port.refresh_from_db()
        summary = {
            "id": port.id,
            "name": port.name,
            "zabbix_item_key": port.zabbix_item_key,
            "zabbix_itemid": port.zabbix_itemid,
            "zabbix_interfaceid": port.zabbix_interfaceid,
            "zabbix_item_id_traffic_in": port.zabbix_item_id_traffic_in,
            "zabbix_item_id_traffic_out": port.zabbix_item_id_traffic_out,
            "rx_power_item_key": port.rx_power_item_key,
            "tx_power_item_key": port.tx_power_item_key,
            "updated_fields": sorted(record["updated_fields"]) if record["updated_fields"] else [],
            "optical_snapshot": record.get("optical_snapshot"),
        }
        if record["created"]:
            ports_created_payload.append(summary)
        elif summary["updated_fields"]:
            ports_updated_payload.append(summary)

    created_summary["ports"] = len(ports_created_payload)

    return {
        "created": created_summary,
        "device": {
            "id": device.id,
            "name": device.name,
            "site": site.name,
            "zabbix_hostid": device.zabbix_hostid,
        },
        "ports_created": ports_created_payload,
        "ports_updated": ports_updated_payload,
        "total_ports_detected": len(port_records),
        "optical_snapshots": optical_snapshots,
    }


def discover_zabbix_hosts() -> Dict[str, Any]:
    hosts = ZABBIX_REQUEST(
        "host.get",
        {
            "output": ["hostid", "host", "name"],
            "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type"],
        },
    ) or []
    results = []
    for host in hosts:
        interfaces = host.get("interfaces", [])
        results.append(
            {
                "hostid": host.get("hostid"),
                "name": host.get("name") or host.get("host"),
                "interfaces": interfaces,
            }
        )
    return {"hosts": results}


def bulk_create_inventory(payload: Mapping[str, Any]) -> Dict[str, Any]:
    sites_payload = payload.get("sites", [])
    devices_payload = payload.get("devices", [])
    ports_payload = payload.get("ports", [])
    fibers_payload = payload.get("fibers", [])

    created = {"sites": 0, "devices": 0, "ports": 0, "fibers": 0}
    site_map = {s.name: s for s in Site.objects.all()}
    device_map: Dict[tuple[str, str], Device] = {}

    for site_data in sites_payload:
        name = site_data.get("name")
        if not name:
            continue
        site, was_created = Site.objects.get_or_create(
            name=name,
            defaults={
                "city": site_data.get("city", ""),
                "latitude": site_data.get("lat"),
                "longitude": site_data.get("lng"),
                "description": site_data.get("description", ""),
            },
        )
        if was_created:
            created["sites"] += 1
        site_map[site.name] = site

    for device_data in devices_payload:
        site_name = device_data.get("site")
        site = site_map.get(site_name)
        if not site:
            continue
        device, was_created = Device.objects.get_or_create(
            site=site,
            name=device_data.get("name"),
            defaults={
                "vendor": device_data.get("vendor", ""),
                "model": device_data.get("model", ""),
                "zabbix_hostid": device_data.get("zabbix_hostid", ""),
            },
        )
        if was_created:
            created["devices"] += 1
        device_map[(site.name, device.name)] = device

    port_map: Dict[tuple[int, str], Port] = {}
    for port_data in ports_payload:
        site_name = port_data.get("site")
        device_name = port_data.get("device")
        device = device_map.get((site_name, device_name))
        if not device:
            continue
        port, was_created = Port.objects.get_or_create(
            device=device,
            name=port_data.get("name"),
            defaults={
                "zabbix_item_key": port_data.get("zabbix_item_key", ""),
                "zabbix_interfaceid": port_data.get("zabbix_interfaceid", ""),
                "notes": port_data.get("notes", ""),
            },
        )
        if was_created:
            created["ports"] += 1
        port_map[(device.id, port.name)] = port

    for fiber_data in fibers_payload:
        origin_device = device_map.get((fiber_data.get("origin_site"), fiber_data.get("origin_device")))
        dest_device = device_map.get((fiber_data.get("dest_site"), fiber_data.get("dest_device")))
        origin_port = port_map.get((origin_device.id, fiber_data.get("origin_port"))) if origin_device else None
        dest_port = port_map.get((dest_device.id, fiber_data.get("dest_port"))) if dest_device else None
        if not origin_port or not dest_port:
            continue
        _, was_created = FiberCable.objects.get_or_create(
            name=fiber_data.get("name"),
            defaults={
                "origin_port": origin_port,
                "destination_port": dest_port,
                "length_km": fiber_data.get("length_km"),
                "path_coordinates": fiber_data.get("path"),
                "status": FiberCable.STATUS_UNKNOWN,
            },
        )
        if was_created:
            created["fibers"] += 1

    return {"created": created}


def list_sites() -> Dict[str, Any]:
    sites_qs = Site.objects.prefetch_related(
        Prefetch("devices", queryset=Device.objects.only("id", "name", "zabbix_hostid", "site", "device_icon"))
    )
    data = []
    for site in sites_qs:
        devices_payload = []
        for device in site.devices.all():
            try:
                icon_url = device.device_icon.url if device.device_icon else None
            except Exception:
                icon_url = None

            devices_payload.append(
                {
                    "id": device.id,
                    "name": device.name,
                    "zabbix_hostid": device.zabbix_hostid,
                    "lat": float(site.latitude) if site.latitude else None,
                    "lng": float(site.longitude) if site.longitude else None,
                    "icon_url": icon_url,
                }
            )
        data.append(
            {
                "id": site.id,
                "name": site.name,
                "city": site.city,
                "lat": float(site.latitude) if site.latitude else None,
                "lng": float(site.longitude) if site.longitude else None,
                "devices": devices_payload,
            }
        )
    return {"sites": data}


def port_traffic_history(port_id: int, params: Mapping[str, str]) -> Dict[str, Any]:
    try:
        port = Port.objects.select_related("device").get(id=port_id)
    except Port.DoesNotExist as exc:
        raise InventoryNotFound("Porta nao encontrada") from exc

    if not port.device.zabbix_hostid:
        raise InventoryValidationError("Device sem Zabbix Host ID configurado")

    if not port.zabbix_item_id_traffic_in and not port.zabbix_item_id_traffic_out:
        raise InventoryValidationError(
            'Port missing traffic items configured in Zabbix',
        )

    raw_period = (params.get("period") or "24h").lower().strip()
    seconds = None
    predefined = {
        "1h": 3600,
        "6h": 6 * 3600,
        "12h": 12 * 3600,
        "24h": 24 * 3600,
        "7d": 7 * 24 * 3600,
        "30d": 30 * 24 * 3600,
    }
    if raw_period in predefined:
        seconds = predefined[raw_period]
    else:
        match = re.match(r"^(\d+)([hdm])$", raw_period)
        if match:
            val = int(match.group(1))
            unit = match.group(2)
            if unit == "h":
                seconds = val * 3600
            elif unit == "d":
                seconds = val * 24 * 3600
            elif unit == "m":
                seconds = val * 60
    if not seconds:
        seconds = predefined["24h"]
        raw_period = "24h"
    max_seconds = predefined["30d"]
    if seconds > max_seconds:
        seconds = max_seconds
        raw_period = "30d"

    now_ts = int(datetime.now().timestamp())
    time_from = now_ts - seconds

    since_raw = params.get("since")
    since = None
    since_applied = False
    if since_raw:
        try:
            since_val = int(since_raw)
            if since_val > time_from and since_val < now_ts:
                since = since_val
                since_applied = True
        except ValueError:
            pass

    if seconds <= 24 * 3600:
        default_limit = min(1500, max(300, int(seconds / 60) + 50))
    else:
        default_limit = min(5000, max(1000, int(seconds / 120) + 100))
    try:
        limit_override = int(params.get("limit")) if params.get("limit") else None
        if limit_override and 50 <= limit_override <= 10000:
            default_limit = limit_override
    except ValueError:
        pass
    history_limit = default_limit

    traffic_data = {
        "port_id": port.id,
        "port_name": port.name,
        "device_name": port.device.name,
        "in": {"history": [], "unit": "bps", "configured": bool(port.zabbix_item_id_traffic_in)},
        "out": {"history": [], "unit": "bps", "configured": bool(port.zabbix_item_id_traffic_out)},
    }

    if port.zabbix_item_id_traffic_in:
        try:
            item_info = ZABBIX_REQUEST(
                "item.get",
                {
                    "output": ["itemid", "value_type", "units"],
                    "itemids": port.zabbix_item_id_traffic_in,
                },
            )
            if item_info:
                value_type = item_info[0].get("value_type", "3")
                traffic_data["in"]["unit"] = item_info[0].get("units", "bps")
                history_in = ZABBIX_REQUEST(
                    "history.get",
                    {
                        "itemids": port.zabbix_item_id_traffic_in,
                        "history": value_type,
                        "time_from": time_from,
                        "sortfield": "clock",
                        "sortorder": "ASC",
                        "limit": history_limit,
                    },
                )
                if history_in:
                    for point in history_in:
                        try:
                            ts = int(point["clock"])
                            if since and ts <= since:
                                continue
                            traffic_data["in"]["history"].append(
                                {"timestamp": ts, "value": float(point["value"])}
                            )
                        except (ValueError, KeyError):
                            continue
        except Exception as exc:
            logger.error("Erro ao buscar traffic IN: %s", exc)

    if port.zabbix_item_id_traffic_out:
        try:
            item_info = ZABBIX_REQUEST(
                "item.get",
                {
                    "output": ["itemid", "value_type", "units"],
                    "itemids": port.zabbix_item_id_traffic_out,
                },
            )
            if item_info:
                value_type = item_info[0].get("value_type", "3")
                traffic_data["out"]["unit"] = item_info[0].get("units", "bps")
                history_out = ZABBIX_REQUEST(
                    "history.get",
                    {
                        "itemids": port.zabbix_item_id_traffic_out,
                        "history": value_type,
                        "time_from": time_from,
                        "sortfield": "clock",
                        "sortorder": "ASC",
                        "limit": history_limit,
                    },
                )
                if history_out:
                    for point in history_out:
                        try:
                            ts = int(point["clock"])
                            if since and ts <= since:
                                continue
                            traffic_data["out"]["history"].append(
                                {"timestamp": ts, "value": float(point["value"])}
                            )
                        except (ValueError, KeyError):
                            continue
        except Exception as exc:
            logger.error("Erro ao buscar traffic OUT: %s", exc)

    traffic_data.update(
        {
            "period": raw_period,
            "period_seconds": seconds,
            "since": since if since_applied else None,
            "incremental": since_applied,
            "generated_at": now_ts,
            "time_from": time_from,
            "history_limit": history_limit,
        }
    )

    return traffic_data
