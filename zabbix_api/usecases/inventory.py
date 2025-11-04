# ruff: noqa: E501
# flake8: noqa

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Set, TypedDict, cast

from django.db.models import Prefetch, Q, QuerySet

from inventory.models import Device, FiberCable, Port, Site

from ..domain.optical import fetch_port_optical_snapshot
from ..services.zabbix_service import zabbix_request

ZABBIX_REQUEST = zabbix_request

logger = logging.getLogger(__name__)


class InventoryUseCaseError(Exception):
    """Generic error raised by inventory use cases."""


class InventoryValidationError(InventoryUseCaseError):
    """Input validation error."""


class InventoryNotFound(InventoryUseCaseError):
    """Requested resource not found."""


class HostItem(TypedDict, total=False):
    itemid: str
    key_: str
    name: str
    interfaceid: str
    lastvalue: str
    units: str
    snmpindex: str
    value_type: str
    _role: Optional[str]


HostItemList = List[HostItem]


class TrafficPoint(TypedDict):
    timestamp: int
    value: float


class TrafficChannel(TypedDict):
    history: List[TrafficPoint]
    unit: str
    configured: bool


TrafficData = TypedDict(
    "TrafficData",
    {
        "port_id": int,
        "port_name": str,
        "device_name": str,
        "in": TrafficChannel,
        "out": TrafficChannel,
        "period": str,
        "period_seconds": int,
        "since": Optional[int],
        "incremental": bool,
        "generated_at": int,
        "time_from": int,
        "history_limit": int,
    },
    total=False,
)


def _new_str_set() -> Set[str]:
    return set()


@dataclass
class PortRecord:
    port: Port
    created: bool
    defaults: Dict[str, str]
    updated_fields: Set[str] = field(default_factory=_new_str_set)
    optical_snapshot: Optional[Dict[str, Any]] = None


@dataclass
class _PortEntry:
    port: Port
    record: PortRecord
    lower: str
    normalized: str
    trimmed: str
    normalized_trimmed: str


class PortLike(Protocol):
    id: int
    name: str
    device_id: int
    device: Device
    zabbix_item_key: Optional[str]
    zabbix_itemid: Optional[str]
    zabbix_interfaceid: Optional[str]
    zabbix_item_id_traffic_in: Optional[str]
    zabbix_item_id_traffic_out: Optional[str]
    rx_power_item_key: Optional[str]
    tx_power_item_key: Optional[str]
    notes: str

    def refresh_from_db(self) -> None:
        ...


class DeviceLike(Protocol):
    id: int
    name: str
    zabbix_hostid: Optional[str]
    site: Site
    device_icon: Any

    def save(self, *, update_fields: Iterable[str]) -> None:
        ...


class SiteLike(Protocol):
    id: int
    name: str
    city: str
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]
    devices: Any


def _port_map_key(port: Port) -> tuple[int, str]:
    """Return the (device_id, lower_port_name) tuple for mapping operations."""
    port_like = cast(PortLike, port)
    return port_like.device_id, port_like.name.lower()



def _coerce_host_items(raw_items: Any) -> HostItemList:
    if not isinstance(raw_items, list):
        return []
    result: HostItemList = []
    entries = cast(Sequence[object], raw_items)
    for entry_obj in entries:
        if isinstance(entry_obj, dict):
            result.append(cast(HostItem, entry_obj))
    return result


def _coerce_dict_list(raw_items: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    result: List[Dict[str, Any]] = []
    entries = cast(Sequence[object], raw_items)
    for entry in entries:
        if isinstance(entry, dict):
            result.append(cast(Dict[str, Any], entry))
    return result


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

    return None


def _score_port_match(entry: _PortEntry, tokens: Iterable[str], combined_text: str, combined_normalized: str) -> int:
    score = 0
    port_lower = entry.lower
    normalized = entry.normalized
    trimmed = entry.trimmed
    normalized_trimmed = entry.normalized_trimmed

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
        device: Device = Device.objects.get(id=device_id)
    except Device.DoesNotExist as exc:
        raise InventoryNotFound("Device not found") from exc

    ports_qs: QuerySet[Port] = Port.objects.filter(device=device).select_related("device")
    ports_data: List[Dict[str, Any]] = []

    for port in ports_qs:
        cable_as_origin = FiberCable.objects.filter(origin_port=port).first()
        cable_as_dest = FiberCable.objects.filter(destination_port=port).first()
        fiber_cable = cable_as_origin or cable_as_dest

        port_any = cast(Any, port)
        fiber_any = cast(Any, fiber_cable) if fiber_cable else None

        port_id = cast(int, getattr(port_any, "id", port_any.pk))
        device_name = cast(str, getattr(getattr(port_any, "device", None), "name", ""))
        fiber_cable_id = cast(Optional[int], getattr(fiber_any, "id", None) if fiber_any else None)
        ports_data.append(
            {
                "id": port_id,
                "name": cast(str, getattr(port_any, "name", "")),
                "device": device_name,
                "fiber_cable_id": fiber_cable_id,
                "zabbix_item_key": getattr(port_any, "zabbix_item_key", None),
                "notes": getattr(port_any, "notes", None),
            }
        )

    return {"ports": ports_data}


def get_device_ports_with_optical(device_id: int) -> Dict[str, Any]:
    try:
        device: Device = Device.objects.select_related("site").get(id=device_id)
    except Device.DoesNotExist as exc:
        raise InventoryNotFound("Device not found") from exc

    ports_qs: QuerySet[Port] = Port.objects.filter(device=device).select_related("device")
    cables_qs: QuerySet[FiberCable] = (
        FiberCable.objects.filter(Q(origin_port__device=device) | Q(destination_port__device=device))
        .select_related("origin_port", "destination_port")
    )

    cable_origin_map: Dict[int, FiberCable] = {}
    cable_dest_map: Dict[int, FiberCable] = {}
    for cable in cables_qs:
        cable_any = cast(Any, cable)
        origin_id = cast(Optional[int], getattr(cable_any, "origin_port_id", None))
        if origin_id is not None:
            cable_origin_map.setdefault(origin_id, cable)
        dest_id = cast(Optional[int], getattr(cable_any, "destination_port_id", None))
        if dest_id is not None:
            cable_dest_map.setdefault(dest_id, cable)

    discovery_cache: Dict[Any, Any] = {}
    ports_with_optical: List[Dict[str, Any]] = []

    for port in ports_qs:
        port_any = cast(Any, port)
        port_id = cast(int, getattr(port_any, "id", port_any.pk))
        cable = cable_origin_map.get(port_id) or cable_dest_map.get(port_id)
        optical_snapshot = fetch_port_optical_snapshot(port, discovery_cache=discovery_cache)
        cable_any = cast(Any, cable) if cable else None
        ports_with_optical.append(
            {
                "id": port_id,
                "name": cast(str, getattr(port_any, "name", "")),
                "cable_id": cast(Optional[int], getattr(cable_any, "id", None) if cable_any else None),
                "cable_name": cast(Optional[str], getattr(cable_any, "name", None) if cable_any else None),
                "optical": optical_snapshot,
            }
        )

    return {
        "device_id": cast(int, getattr(cast(Any, device), "id", device.pk)),
        "device_name": cast(str, getattr(cast(Any, device), "name", "")),
        "ports": ports_with_optical,
    }


def device_port_optical_status(port_id: int) -> Dict[str, Any]:
    try:
        port = Port.objects.select_related("device").get(id=port_id)
    except Port.DoesNotExist as exc:
        raise InventoryNotFound("Port not found") from exc

    hostid = (port.device.zabbix_hostid or "").strip()
    if not hostid:
        raise InventoryValidationError("Device missing Zabbix Host ID")

    optical_snapshot = fetch_port_optical_snapshot(port)
    return {
        "port_id": port.pk,
        "port_name": port.name,
        "optical": optical_snapshot,
    }


def add_device_from_zabbix(payload: Mapping[str, Any]) -> Dict[str, Any]:
    hostid = payload.get("hostid") or payload.get("device_name")
    if not hostid:
        raise InventoryValidationError("hostid is required")

    zabbix_data = ZABBIX_REQUEST(
        "host.get",
        {
            "output": ["hostid", "name", "host"],
            "hostids": hostid,
            "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type"],
        },
    )
    if not zabbix_data:
        raise InventoryNotFound("Host not found in Zabbix")

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
            site.latitude = Decimal(lat)
            update_fields.append("latitude")
        except (InvalidOperation, ValueError):
            pass
    if lon:
        try:
            site.longitude = Decimal(lon)
            update_fields.append("longitude")
        except (InvalidOperation, ValueError):
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

    raw_host_items = ZABBIX_REQUEST(
        "item.get",
        {
            "output": ["itemid", "key_", "name", "interfaceid", "lastvalue", "units", "snmpindex"],
            "hostids": hostid,
            "filter": {"status": "0"},
            "limit": 2000,
        },
    )
    host_items: HostItemList = _coerce_host_items(raw_host_items)

    port_records: List[PortRecord] = []
    primary_items: HostItemList = []
    legacy_primary_items: HostItemList = []

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

    creation_candidates: HostItemList = primary_items if primary_items else legacy_primary_items
    if not creation_candidates:
        creation_candidates = [
            item
            for item in host_items
            if (item.get("key_") or "").lower().startswith(("ifoperstatus[", "lastdowntime["))
        ]

    port_record_map: Dict[tuple[int, str], PortRecord] = {}

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

        record = PortRecord(port=port, created=port_created, defaults=defaults)
        port_records.append(record)
        port_record_map[_port_map_key(port)] = record

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
            record = PortRecord(port=port, created=False, defaults={})
            port_records.append(record)
            port_record_map[_port_map_key(port)] = record

    created_summary = {"sites": int(site_created), "devices": int(created), "ports": 0}

    port_entries: List[_PortEntry] = []
    for record in port_records:
        port = record.port
        lower = port.name.lower()
        normalized = _normalize_identifier(lower)
        trimmed = lower[1:] if lower.startswith("x") else lower
        normalized_trimmed = normalized[1:] if normalized.startswith("x") else normalized
        port_entries.append(
            _PortEntry(
                port=port,
                record=record,
                lower=lower,
                normalized=normalized,
                trimmed=trimmed,
                normalized_trimmed=normalized_trimmed,
            )
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

        best_entry: Optional[_PortEntry] = None
        best_score = 0
        for entry in port_entries:
            score = _score_port_match(entry, tokens, combined_text, combined_normalized)
            if score > best_score:
                best_score = score
                best_entry = entry
        if not best_entry or best_score < 45:
            continue

        port = best_entry.port
        record = best_entry.record
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
                updates["zabbix_item_id_traffic_in"] = item_id
        elif role == "traffic_out":
            if item_id and not port.zabbix_item_id_traffic_out:
                updates["zabbix_item_id_traffic_out"] = item_id
        elif role == "optical_rx":
            if key and port.rx_power_item_key != key:
                updates["rx_power_item_key"] = key
        elif role == "optical_tx":
            if key and port.tx_power_item_key != key:
                updates["tx_power_item_key"] = key

        _apply_port_updates(port, updates, record.updated_fields)

    discovery_cache: Dict[Any, Any] = {}
    optical_snapshots: List[Dict[str, Any]] = []
    for record in port_records:
        port_like = cast(PortLike, record.port)
        snapshot = fetch_port_optical_snapshot(record.port, discovery_cache=discovery_cache)
        record.optical_snapshot = snapshot
        optical_snapshots.append(
            {
                "port_id": port_like.id,
                "rx_key": snapshot.get("rx_key"),
                "tx_key": snapshot.get("tx_key"),
                "rx_dbm": snapshot.get("rx_dbm"),
                "tx_dbm": snapshot.get("tx_dbm"),
            }
        )

    ports_created_payload: List[Dict[str, Any]] = []
    ports_updated_payload: List[Dict[str, Any]] = []
    for record in port_records:
        port = record.port
        port_like = cast(PortLike, port)
        port.refresh_from_db()
        summary = {
            "id": port_like.id,
            "name": port_like.name,
            "zabbix_item_key": port_like.zabbix_item_key,
            "zabbix_itemid": port_like.zabbix_itemid,
            "zabbix_interfaceid": port_like.zabbix_interfaceid,
            "zabbix_item_id_traffic_in": port_like.zabbix_item_id_traffic_in,
            "zabbix_item_id_traffic_out": port_like.zabbix_item_id_traffic_out,
            "rx_power_item_key": port_like.rx_power_item_key,
            "tx_power_item_key": port_like.tx_power_item_key,
            "updated_fields": sorted(record.updated_fields) if record.updated_fields else [],
            "optical_snapshot": record.optical_snapshot,
        }
        if record.created:
            ports_created_payload.append(summary)
        elif summary["updated_fields"]:
            ports_updated_payload.append(summary)

    created_summary["ports"] = len(ports_created_payload)

    device_like = cast(DeviceLike, device)

    return {
        "created": created_summary,
        "device": {
            "id": device_like.id,
            "name": device_like.name,
            "site": site.name,
            "zabbix_hostid": device_like.zabbix_hostid,
        },
        "ports_created": ports_created_payload,
        "ports_updated": ports_updated_payload,
        "total_ports_detected": len(port_records),
        "optical_snapshots": optical_snapshots,
    }


def discover_zabbix_hosts() -> Dict[str, Any]:
    raw_hosts = ZABBIX_REQUEST(
        "host.get",
        {
            "output": ["hostid", "host", "name"],
            "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type"],
        },
    )
    hosts = _coerce_dict_list(raw_hosts)
    results: List[Dict[str, Any]] = []
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
        device_like = cast(DeviceLike, device)
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
        port_like = cast(PortLike, port)
        port_map[(device_like.id, port_like.name)] = port

    for fiber_data in fibers_payload:
        origin_device_raw = device_map.get((fiber_data.get("origin_site"), fiber_data.get("origin_device")))
        dest_device_raw = device_map.get((fiber_data.get("dest_site"), fiber_data.get("dest_device")))

        origin_device = cast(Optional[DeviceLike], origin_device_raw) if origin_device_raw else None
        dest_device = cast(Optional[DeviceLike], dest_device_raw) if dest_device_raw else None

        origin_port_name = fiber_data.get("origin_port")
        dest_port_name = fiber_data.get("dest_port")

        origin_port = (
            port_map.get((origin_device.id, origin_port_name))
            if origin_device and isinstance(origin_port_name, str)
            else None
        )
        dest_port = (
            port_map.get((dest_device.id, dest_port_name))
            if dest_device and isinstance(dest_port_name, str)
            else None
        )
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
    data: List[Dict[str, Any]] = []
    for site_obj in sites_qs:
        site_like = cast(SiteLike, site_obj)
        devices_payload: List[Dict[str, Any]] = []
        device_iterable = cast(Iterable[Device], site_like.devices.all())
        for device_obj in device_iterable:
            device_like = cast(DeviceLike, device_obj)
            icon_url: Optional[str]
            try:
                icon_url = cast(Optional[str], getattr(device_like.device_icon, "url", None)) if device_like.device_icon else None
            except Exception:
                icon_url = None

            devices_payload.append(
                {
                    "id": device_like.id,
                    "name": device_like.name,
                    "zabbix_hostid": device_like.zabbix_hostid,
                    "lat": float(site_like.latitude) if site_like.latitude else None,
                    "lng": float(site_like.longitude) if site_like.longitude else None,
                    "icon_url": icon_url,
                }
            )
        data.append(
            {
                "id": site_like.id,
                "name": site_like.name,
                "city": site_like.city,
                "lat": float(site_like.latitude) if site_like.latitude else None,
                "lng": float(site_like.longitude) if site_like.longitude else None,
                "devices": devices_payload,
            }
        )
    return {"sites": data}


def port_traffic_history(port_id: int, params: Mapping[str, str]) -> TrafficData:
    try:
        port = Port.objects.select_related("device").get(id=port_id)
    except Port.DoesNotExist as exc:
        raise InventoryNotFound("Port not found") from exc

    if not port.device.zabbix_hostid:
        raise InventoryValidationError("Device missing Zabbix Host ID configuration")

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

    limit_override: Optional[int] = None
    limit_raw = params.get("limit")
    if limit_raw:
        try:
            limit_override = int(limit_raw)
        except ValueError:
            limit_override = None
    if limit_override and 50 <= limit_override <= 10000:
        default_limit = limit_override
    history_limit = default_limit

    port_like = cast(PortLike, port)
    device_like = cast(DeviceLike, port_like.device)

    traffic_in_channel: TrafficChannel = {
        "history": [],
        "unit": "bps",
        "configured": bool(port_like.zabbix_item_id_traffic_in),
    }
    traffic_out_channel: TrafficChannel = {
        "history": [],
        "unit": "bps",
        "configured": bool(port_like.zabbix_item_id_traffic_out),
    }

    traffic_data: TrafficData = {
        "port_id": port_like.id,
        "port_name": port_like.name,
        "device_name": device_like.name,
        "in": traffic_in_channel,
        "out": traffic_out_channel,
    }

    if port.zabbix_item_id_traffic_in:
        try:
            item_info_raw = ZABBIX_REQUEST(
                "item.get",
                {
                    "output": ["itemid", "value_type", "units"],
                    "itemids": port.zabbix_item_id_traffic_in,
                },
            )
            item_info = _coerce_dict_list(item_info_raw)
            if item_info:
                value_type = item_info[0].get("value_type", "3")
                traffic_in_channel["unit"] = str(item_info[0].get("units", "bps"))
                history_in_raw = ZABBIX_REQUEST(
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
                history_in = _coerce_dict_list(history_in_raw)
                if history_in:
                    for point in history_in:
                        try:
                            ts = int(point["clock"])
                            if since and ts <= since:
                                continue
                            traffic_in_channel["history"].append(
                                {"timestamp": ts, "value": float(point["value"])}
                            )
                        except (ValueError, KeyError):
                            continue
        except Exception as exc:
            logger.error("Failed to retrieve traffic IN history: %s", exc)

    if port.zabbix_item_id_traffic_out:
        try:
            item_info_raw = ZABBIX_REQUEST(
                "item.get",
                {
                    "output": ["itemid", "value_type", "units"],
                    "itemids": port.zabbix_item_id_traffic_out,
                },
            )
            item_info = _coerce_dict_list(item_info_raw)
            if item_info:
                value_type = item_info[0].get("value_type", "3")
                traffic_out_channel["unit"] = str(item_info[0].get("units", "bps"))
                history_out_raw = ZABBIX_REQUEST(
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
                history_out = _coerce_dict_list(history_out_raw)
                if history_out:
                    for point in history_out:
                        try:
                            ts = int(point["clock"])
                            if since and ts <= since:
                                continue
                            traffic_out_channel["history"].append(
                                {"timestamp": ts, "value": float(point["value"])}
                            )
                        except (ValueError, KeyError):
                            continue
        except Exception as exc:
            logger.error("Failed to retrieve traffic OUT history: %s", exc)

    traffic_data["period"] = raw_period
    traffic_data["period_seconds"] = seconds
    traffic_data["since"] = since if since_applied else None
    traffic_data["incremental"] = since_applied
    traffic_data["generated_at"] = now_ts
    traffic_data["time_from"] = time_from
    traffic_data["history_limit"] = history_limit

    return traffic_data
