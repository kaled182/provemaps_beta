from __future__ import annotations

# pyright: reportUnknownParameterType=false, reportUnknownArgumentType=false
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
# pyright: reportMissingParameterType=false, reportMissingTypeArgument=false
# pyright: reportPrivateUsage=false, reportAttributeAccessIssue=false

import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, cast

from integrations.zabbix.zabbix_service import (
    safe_cache_get,
    safe_cache_set,
    zabbix_request,
)

from inventory.cache.fibers import invalidate_fiber_cache
from inventory.domain.geometry import (
    calculate_path_length,
    sanitize_path_points,
)
from inventory.domain.optical import fetch_port_optical_snapshot
from inventory.models import FiberCable, FiberEvent, Port
from inventory.services.fiber_status import (
    combine_cable_status as combine_cable_status_service,
    evaluate_cable_status_for_cable,
    fetch_interface_status_advanced,
    get_oper_status_from_port,
)

logger = logging.getLogger(__name__)

LIVE_STATUS_CACHE_KEY_TEMPLATE = "inventory:fiber_live_status:{cable_id}"
LIVE_STATUS_CACHE_TIMEOUT = 45  # seconds


class FiberUseCaseError(Exception):
    """Generic business-rule error for fiber operations."""


class FiberValidationError(FiberUseCaseError):
    """Raised when incoming data fails validation."""


class FiberNotFound(FiberUseCaseError):
    """Raised when a fiber cable cannot be located."""


@dataclass
class FiberLiveStatus:
    origin_status: str
    destination_status: str
    origin_reason: Dict[str, object]
    destination_reason: Dict[str, object]
    combined_status: str
    changed: bool


def _port_payload(port: Port) -> Dict[str, object]:
    device = port.device
    site = getattr(device, "site", None)
    return {
        "id": port.id,
        "name": port.name,
        "device": device.name,
        "site": site.name if site else None,
    }


def _get_port(port_id: str | int, *, with_site: bool = True) -> Port:
    queryset = Port.objects.all()
    if with_site:
        queryset = queryset.select_related("device__site")
    try:
        return queryset.get(id=port_id)
    except Port.DoesNotExist as exc:
        raise FiberValidationError("Port not found") from exc


def get_fiber_cable(cable_id: int) -> FiberCable:
    try:
        return FiberCable.objects.select_related(
            "origin_port__device__site",
            "destination_port__device__site",
        ).get(id=cable_id)
    except FiberCable.DoesNotExist as exc:
        raise FiberNotFound("FiberCable not found") from exc


def parse_kml_coordinates(kml_file) -> List[Dict[str, float]]:
    try:
        tree = ET.parse(kml_file)
        root = tree.getroot()
    except Exception as exc:
        raise FiberValidationError(f"Failed to process KML: {exc}") from exc

    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    coords: List[Dict[str, float]] = []
    for linestring in root.findall(".//kml:LineString", ns):
        coord_text = linestring.find("kml:coordinates", ns)
        if coord_text is None:
            continue
        raw = (coord_text.text or "").strip().replace("\n", " ")
        for pair in raw.split():
            parts = pair.split(",")
            if len(parts) < 2:
                continue
            try:
                lng, lat = float(parts[0]), float(parts[1])
            except ValueError:
                continue
            if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
                coords.append({"lat": lat, "lng": lng})
    if not coords:
        raise FiberValidationError("No coordinates found in the KML payload")
    if len(coords) < 2:
        raise FiberValidationError("Path requires at least two valid points")
    return coords


def create_fiber_from_kml(
    name: str,
    origin_device_id: str,
    dest_device_id: str,
    origin_port_id: str,
    dest_port_id: str,
    kml_file: Any,
    single_port: bool = False,
) -> Dict[str, object]:
    if FiberCable.objects.filter(name__iexact=name).exists():
        raise FiberValidationError("A fiber with this name already exists")

    origin_port_id_value = cast(str | int, origin_port_id)
    origin_port = _get_port(origin_port_id_value)
    dest_port = _get_port(dest_port_id)

    if str(origin_port.device_id) != str(origin_device_id):
        raise FiberValidationError(
            "Origin port does not belong to the selected device"
        )
    if str(dest_port.device_id) != str(dest_device_id):
        raise FiberValidationError(
            "Destination port does not belong to the selected device"
        )
    
    # Only enforce distinct port checks when not in single-port mode
    if not single_port:
        if origin_port == dest_port:
            raise FiberValidationError(
                "Origin and destination ports must be different"
            )
        if origin_port.device_id == dest_port.device_id:
            raise FiberValidationError(
                "Origin and destination devices must be different"
            )

    coords = parse_kml_coordinates(kml_file)
    # Sanitiza e calcula comprimento em km
    sanitized = sanitize_path_points(coords, allow_empty=False)
    length_km = calculate_path_length(sanitized)

    fiber = FiberCable.objects.create(
        name=name,
        origin_port=origin_port,
        destination_port=dest_port,
        path_coordinates=sanitized,
        length_km=length_km,
        status=FiberCable.STATUS_UNKNOWN,
    )
    invalidate_fiber_cache()
    payload = fiber_to_payload(fiber, coords=sanitized)
    payload["length_km"] = length_km
    return payload


def fiber_to_payload(
    fiber: FiberCable,
    coords: Optional[Iterable[Dict[str, float]]] = None,
) -> Dict[str, object]:
    origin_port = fiber.origin_port
    dest_port = fiber.destination_port
    return {
        "fiber_id": fiber.id,
        "name": fiber.name,
        "points": (
            len(list(coords))
            if coords is not None
            else len(fiber.path_coordinates or [])
        ),
        "path_coordinates": (
            list(coords)
            if coords is not None
            else (fiber.path_coordinates or [])
        ),
        "origin_port": {
            "id": origin_port.id,
            "name": origin_port.name,
            "device": origin_port.device.name,
            "site": (
                origin_port.device.site.name
                if origin_port.device.site_id
                else None
            ),
        },
        "destination_port": {
            "id": dest_port.id,
            "name": dest_port.name,
            "device": dest_port.device.name,
            "site": (
                dest_port.device.site.name
                if dest_port.device.site_id
                else None
            ),
        },
    }


def cable_value_mapping_status(
    cable: FiberCable,
    item_key_origin: Optional[str],
    item_key_dest: Optional[str],
) -> Dict[str, object]:
    origin_key = item_key_origin or cable.origin_port.zabbix_item_key
    destination_key = (
        item_key_dest
        or cable.destination_port.zabbix_item_key
        or origin_key
    )

    def fetch_value(hostid, key):
        if not (hostid and key):
            return None
        items = zabbix_request(
            "item.get",
            {
                "output": ["itemid", "key_", "lastvalue", "value_type"],
                "hostids": hostid,
                "search": {"key_": key},
                "searchByAny": True,
                "limit": 1,
            },
        ) or []
        if not items:
            return None
        candidate = items[0]
        val = candidate.get("lastvalue")
        if val is None:
            hist = zabbix_request(
                "history.get",
                {
                    "itemids": candidate["itemid"],
                    "history": candidate.get("value_type", 3),
                    "sortfield": "clock",
                    "sortorder": "DESC",
                    "limit": 1,
                },
            ) or []
            if hist:
                val = hist[0].get("value")
        return str(val) if val is not None else None

    raw_origin = fetch_value(
        cable.origin_port.device.zabbix_hostid,
        origin_key,
    )
    raw_dest = fetch_value(
        cable.destination_port.device.zabbix_hostid,
        destination_key,
    )

    def interpret(raw):
        if raw == "1":
            return "up"
        if raw == "0":
            return "down"
        if raw is not None:
            return f"unknown ({raw})"
        return "unknown"

    origin_status = interpret(raw_origin)
    dest_status = interpret(raw_dest)
    combined = combine_cable_status_service(
        "up"
        if origin_status == "up"
        else ("down" if origin_status == "down" else "unknown"),
        "up"
        if dest_status == "up"
        else ("down" if dest_status == "down" else "unknown"),
    )
    return {
        "cable_id": cable.id,
        "origin_raw": raw_origin,
        "dest_raw": raw_dest,
        "origin_status": origin_status,
        "dest_status": dest_status,
        "combined_status": combined,
    }


def list_fiber_cables() -> List[Dict[str, object]]:
    cables = FiberCable.objects.select_related(
        "origin_port__device__site",
        "destination_port__device__site",
    )
    payload = []
    for cable in cables:
        origin_site = cable.origin_port.device.site
        dest_site = cable.destination_port.device.site
        payload.append(
            {
                "id": cable.id,
                "name": cable.name,
                "status": cable.status,
                "length_km": (
                    float(cable.length_km)
                    if cable.length_km is not None
                    else None
                ),
                # Campos enriquecidos (flat) para uso rápido no modal Vue
                "origin_port_id": cable.origin_port.id,
                "destination_port_id": cable.destination_port.id,
                "origin_port_name": cable.origin_port.name,
                "destination_port_name": cable.destination_port.name,
                "origin_device_id": cable.origin_port.device.id,
                "destination_device_id": cable.destination_port.device.id,
                "origin_device_name": cable.origin_port.device.name,
                "destination_device_name": cable.destination_port.device.name,
                "origin_site_id": origin_site.id if origin_site else None,
                "destination_site_id": dest_site.id if dest_site else None,
                "origin": {
                    "site": origin_site.name if origin_site else None,
                    "city": origin_site.city if origin_site else None,
                    "lat": (
                        float(origin_site.latitude)
                        if origin_site and origin_site.latitude is not None
                        else None
                    ),
                    "lng": (
                        float(origin_site.longitude)
                        if origin_site and origin_site.longitude is not None
                        else None
                    ),
                    "device": cable.origin_port.device.name,
                    "port": cable.origin_port.name,
                },
                "destination": {
                    "site": dest_site.name if dest_site else None,
                    "city": dest_site.city if dest_site else None,
                    "lat": (
                        float(dest_site.latitude)
                        if dest_site and dest_site.latitude is not None
                        else None
                    ),
                    "lng": (
                        float(dest_site.longitude)
                        if dest_site and dest_site.longitude is not None
                        else None
                    ),
                    "device": cable.destination_port.device.name,
                    "port": cable.destination_port.name,
                },
                "path": cable.path_coordinates or [],
            }
        )
    return payload


def fiber_detail_payload(cable: FiberCable) -> Dict[str, object]:
    origin_site = cable.origin_port.device.site
    dest_site = cable.destination_port.device.site
    return {
        "id": cable.id,
        "name": cable.name,
        "status": cable.status,
        "length_km": (
            float(cable.length_km) if cable.length_km is not None else None
        ),
        "origin": {
            "site": origin_site.name if origin_site else None,
            "lat": (
                float(origin_site.latitude)
                if origin_site and origin_site.latitude is not None
                else None
            ),
            "lng": (
                float(origin_site.longitude)
                if origin_site and origin_site.longitude is not None
                else None
            ),
            "device": cable.origin_port.device.name,
            "device_id": cable.origin_port.device.id,
            "port": cable.origin_port.name,
            "port_id": cable.origin_port.id,
        },
        "destination": {
            "site": dest_site.name if dest_site else None,
            "lat": (
                float(dest_site.latitude)
                if dest_site and dest_site.latitude is not None
                else None
            ),
            "lng": (
                float(dest_site.longitude)
                if dest_site and dest_site.longitude is not None
                else None
            ),
            "device": cable.destination_port.device.name,
            "device_id": cable.destination_port.device.id,
            "port": cable.destination_port.name,
            "port_id": cable.destination_port.id,
        },
        "path": cable.path_coordinates or [],
        "single_port": cable.origin_port == cable.destination_port,
    }


def update_fiber_path(cable: FiberCable, raw_path: Any) -> Dict[str, object]:
    allow_empty = True
    sanitized = sanitize_path_points(raw_path, allow_empty=allow_empty)
    if sanitized and len(sanitized) < 2:
        raise FiberValidationError("Path requires at least two valid points")

    length_km = calculate_path_length(sanitized)
    cable.path_coordinates = sanitized
    cable.length_km = length_km
    cable.save(update_fields=["path_coordinates", "length_km"])
    invalidate_fiber_cache()
    return {
        "status": "ok",
        "length_km": length_km,
        "points": len(sanitized),
        "path": sanitized,
    }


def update_fiber_metadata(
    cable: FiberCable,
    name: Optional[str] = None,
    origin_port_id: Optional[int] = None,
    dest_port_id: Optional[int] = None,
) -> Dict[str, object]:
    """Update fiber metadata such as name and endpoint ports."""
    updated_fields = []

    if name is not None:
        name = name.strip()
        if not name:
            raise FiberValidationError("Name cannot be empty")
        cable.name = name
        updated_fields.append("name")

    if origin_port_id is not None:
        try:
            origin_port = Port.objects.get(id=origin_port_id)
        except Port.DoesNotExist as exc:
            raise FiberValidationError(
                f"Origin port {origin_port_id} not found"
            ) from exc
        cable.origin_port = origin_port
        updated_fields.append("origin_port")

    if dest_port_id is not None:
        try:
            dest_port = Port.objects.get(id=dest_port_id)
        except Port.DoesNotExist as exc:
            raise FiberValidationError(
                f"Destination port {dest_port_id} not found"
            ) from exc
        cable.destination_port = dest_port
        updated_fields.append("destination_port")

    if updated_fields:
        cable.save(update_fields=updated_fields)
        invalidate_fiber_cache()

    return {
        "status": "ok",
        "updated_fields": updated_fields,
        "cable_id": cable.id,
        "name": cable.name,
    }


def delete_fiber(cable: FiberCable) -> None:
    cable.delete()
    invalidate_fiber_cache()


def _persist_discovered_optical_keys(
    port: Port,
    reason: Dict[str, Any],
) -> None:
    if not isinstance(reason, dict):
        return

    updates: Dict[str, str] = {}

    rx_candidate = reason.get("rx_key") or reason.get("rx_key_generic")
    if rx_candidate and not port.rx_power_item_key:
        updates["rx_power_item_key"] = str(rx_candidate)

    tx_candidate = reason.get("tx_key") or reason.get("tx_key_generic")
    if tx_candidate and not port.tx_power_item_key:
        updates["tx_power_item_key"] = str(tx_candidate)

    if not updates:
        return

    try:
        Port.objects.filter(pk=port.pk).update(**updates)
        for field, value in updates.items():
            setattr(port, field, value)
        logger.debug(
            "Persisted auto-discovered optical keys for port %s: %s",
            port.pk,
            updates,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(
            "Failed to persist optical keys for port %s: %s",
            port.pk,
            exc,
        )


def compute_live_status(
    cable: FiberCable,
    persist: bool,
    *,
    event_reason: str,
) -> FiberLiveStatus:
    cache_key = LIVE_STATUS_CACHE_KEY_TEMPLATE.format(cable_id=cable.id)

    if not persist:
        cached_entry = safe_cache_get(cache_key)
        if isinstance(cached_entry, dict):
            cached_payload = cached_entry.get("live_status")
            if isinstance(cached_payload, dict):
                cached_data = dict(cached_payload)
                cached_data["changed"] = (
                    cached_data.get("combined_status") != cable.status
                )
                try:
                    return FiberLiveStatus(**cached_data)
                except TypeError:
                    logger.debug(
                        "Discarded malformed live status cache for cable %s",
                        cable.id,
                    )

    origin_dev = cable.origin_port.device
    dest_dev = cable.destination_port.device

    origin_status, origin_reason = fetch_interface_status_advanced(
        origin_dev.zabbix_hostid,
        primary_item_key=cable.origin_port.zabbix_item_key,
        interfaceid=cable.origin_port.zabbix_interfaceid,
        rx_key=cable.origin_port.rx_power_item_key,
        tx_key=cable.origin_port.tx_power_item_key,
    )
    dest_status, dest_reason = fetch_interface_status_advanced(
        dest_dev.zabbix_hostid,
        primary_item_key=cable.destination_port.zabbix_item_key,
        interfaceid=cable.destination_port.zabbix_interfaceid,
        rx_key=cable.destination_port.rx_power_item_key,
        tx_key=cable.destination_port.tx_power_item_key,
    )

    _persist_discovered_optical_keys(cable.origin_port, origin_reason)
    _persist_discovered_optical_keys(cable.destination_port, dest_reason)
    combined = combine_cable_status_service(origin_status, dest_status)
    changed = combined != cable.status
    if persist and changed:
        previous = cable.status
        cable.update_status(combined)
        FiberEvent.objects.create(
            fiber=cable,
            previous_status=previous,
            new_status=combined,
            detected_reason=event_reason,
        )

    status = FiberLiveStatus(
        origin_status=origin_status,
        destination_status=dest_status,
        origin_reason=origin_reason,
        destination_reason=dest_reason,
        combined_status=combined,
        changed=changed,
    )

    cache_payload = {
        "live_status": asdict(status),
        "computed_at": time.time(),
        "cable_status": cable.status,
    }
    safe_cache_set(cache_key, cache_payload, LIVE_STATUS_CACHE_TIMEOUT)

    return status


def live_status_payload(
    cable: FiberCable,
    status: FiberLiveStatus,
    persist: bool,
) -> Dict[str, object]:
    return {
        "cable_id": cable.id,
        "name": cable.name,
        "origin_status": status.origin_status,
        "destination_status": status.destination_status,
        "origin_reason": status.origin_reason,
        "destination_reason": status.destination_reason,
        "combined_status": status.combined_status,
        "stored_status": cable.status,
        "changed": status.changed,
        "persisted": persist and status.changed,
    }


def bulk_live_status(
    cables: Iterable[FiberCable],
    persist: bool,
) -> Tuple[List[Dict[str, object]], int]:
    results = []
    changed_any = 0
    for cable in cables:
        status = compute_live_status(
            cable,
            persist=persist,
            event_reason="live-endpoint-bulk",
        )
        if persist and status.changed:
            changed_any += 1
        results.append(
            {
                "cable_id": cable.id,
                "name": cable.name,
                "origin_status": status.origin_status,
                "destination_status": status.destination_status,
                "origin_reason": status.origin_reason,
                "destination_reason": status.destination_reason,
                "combined_status": status.combined_status,
                "stored_status": cable.status,
                "changed": status.changed,
                "will_persist": persist,
            }
        )
    if persist and changed_any:
        invalidate_fiber_cache()
    return results, changed_any


def refresh_fibers_status(cables: Iterable[FiberCable]) -> Dict[str, object]:
    updated = 0
    results = []
    for cable in cables:
        eval_data = evaluate_cable_status_for_cable(cable)
        if eval_data["changed"]:
            previous = cable.status
            cable.update_status(eval_data["combined_status"])
            FiberEvent.objects.create(
                fiber=cable,
                previous_status=previous,
                new_status=eval_data["combined_status"],
                detected_reason="api-refresh",
            )
            updated += 1
        results.append(
            {
                "cable_id": cable.id,
                "name": cable.name,
                "old_status": eval_data["previous_status"],
                "new_status": eval_data["combined_status"],
                "changed": eval_data["changed"],
            }
        )
    if updated:
        invalidate_fiber_cache()
    return {"updated": updated, "total": len(results), "results": results}


def create_manual_fiber(data: Dict[str, object]) -> Dict[str, object]:
    name = (data.get("name") or "").strip()
    origin_device_id = data.get("origin_device_id")
    origin_port_id = data.get("origin_port_id")
    dest_device_id = data.get("dest_device_id")
    dest_port_id = data.get("dest_port_id")
    single_port_flag = str(data.get("single_port", "")).lower()
    single_port = single_port_flag in ("1", "true", "on", "yes")

    if single_port:
        dest_device_id = origin_device_id
        dest_port_id = dest_port_id or origin_port_id

    if not (name and origin_device_id and origin_port_id and dest_port_id):
        raise FiberValidationError("Required fields are missing")

    origin_port_id_value = cast(str | int, origin_port_id)
    origin_port = _get_port(origin_port_id_value)
    if single_port:
        dest_port = origin_port
    else:
        dest_port_id_value = cast(str | int, dest_port_id)
        dest_port = _get_port(dest_port_id_value)
        if str(dest_port.device_id) != str(dest_device_id):
            raise FiberValidationError(
                "Destination port does not belong to the selected device"
            )
        if origin_port == dest_port:
            raise FiberValidationError(
                "Origin and destination ports must be different"
            )

    if str(origin_port.device_id) != str(origin_device_id):
        raise FiberValidationError(
            "Origin port does not belong to the selected device"
        )

    raw_path = data.get("path") or []
    sanitized = sanitize_path_points(raw_path, allow_empty=False)
    length_km = calculate_path_length(sanitized)

    fiber = FiberCable.objects.create(
        name=name,
        origin_port=origin_port,
        destination_port=dest_port,
        path_coordinates=sanitized,
        length_km=length_km,
        status=FiberCable.STATUS_UNKNOWN,
        notes="single-port-monitoring" if single_port else "",
    )
    invalidate_fiber_cache()
    return {
        "fiber": fiber,
        "payload": {
            "fiber_id": fiber.id,
            "name": fiber.name,
            "points": len(sanitized),
            "length_km": length_km,
            "origin_port": _port_payload(origin_port),
            "destination_port": _port_payload(dest_port),
            "single_port": single_port,
        },
    }


def update_cable_oper_status(cable_id: int) -> Dict[str, Any]:
    """
    Return operational status metadata for a cable (Phase 9.1 optimized).
    
    OPTIMIZATION: Uses Port.last_rx_power and last_tx_power fields
    (populated by update_all_port_optical_levels Celery task) instead
    of calling fetch_port_optical_snapshot() synchronously.
    
    This eliminates Zabbix API calls during web requests, relying on
    database-cached optical values.
    """
    try:
        cable = FiberCable.objects.select_related(
            "origin_port__device", "destination_port__device"
        ).get(id=cable_id)
    except FiberCable.DoesNotExist as exc:
        raise FiberNotFound("FiberCable not found") from exc

    origin_port = cable.origin_port
    dest_port = cable.destination_port

    status_origin, raw_origin, meta_origin = get_oper_status_from_port(
        origin_port
    )
    status_dest, raw_dest, meta_dest = get_oper_status_from_port(
        dest_port
    )

    meta_origin["port_id"] = origin_port.id
    meta_origin["port_name"] = origin_port.name
    meta_origin["device_name"] = origin_port.device.name

    meta_dest["port_id"] = dest_port.id
    meta_dest["port_name"] = dest_port.name
    meta_dest["device_name"] = dest_port.device.name

    # PHASE 9.1: Use cached optical values from Port model
    # (populated asynchronously by update_all_port_optical_levels task)
    # instead of calling fetch_port_optical_snapshot() which hits Zabbix
    origin_optical = {
        "rx_dbm": origin_port.last_rx_power,
        "tx_dbm": origin_port.last_tx_power,
        "last_check": origin_port.last_optical_check,
        "source": "cached",  # Indicate this is from DB cache
    }
    dest_optical = {
        "rx_dbm": dest_port.last_rx_power,
        "tx_dbm": dest_port.last_tx_power,
        "last_check": dest_port.last_optical_check,
        "source": "cached",
    }

    status = combine_cable_status_service(status_origin, status_dest)
    previous_status = cable.status

    if status != previous_status:
        cable.update_status(status)
        FiberEvent.objects.create(
            fiber=cable,
            previous_status=previous_status,
            new_status=status,
            detected_reason=(
                f"zabbix-oper-status:origin={meta_origin.get('method')},"
                f"dest={meta_dest.get('method')}"
            ),
        )

    return {
        "cable_id": cable.id,
        "status": status,
        "origin_status": status_origin,
        "origin_raw": raw_origin,
        "origin_meta": meta_origin,
        "origin_optical": origin_optical,
        "destination_status": status_dest,
        "destination_raw": raw_dest,
        "destination_meta": meta_dest,
        "destination_optical": dest_optical,
        "updated": status != previous_status,
        "previous_status": previous_status,
    }


__all__ = [
    "FiberUseCaseError",
    "FiberValidationError",
    "FiberNotFound",
    "FiberLiveStatus",
    "get_fiber_cable",
    "parse_kml_coordinates",
    "create_fiber_from_kml",
    "fiber_to_payload",
    "cable_value_mapping_status",
    "list_fiber_cables",
    "fiber_detail_payload",
    "update_fiber_path",
    "update_fiber_metadata",
    "delete_fiber",
    "compute_live_status",
    "live_status_payload",
    "bulk_live_status",
    "refresh_fibers_status",
    "create_manual_fiber",
    "update_cable_oper_status",
]
