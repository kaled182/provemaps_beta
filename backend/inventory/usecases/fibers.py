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
from inventory.spatial import coords_to_linestring, linestring_to_coords
# NOTE: fetch_port_optical_snapshot no longer used directly here
from inventory.models import FiberCable, FiberCableAuditLog, FiberEvent, Port
from inventory.services.fiber_status import (
    combine_cable_status as combine_cable_status_service,
    evaluate_cable_status_for_cable,
    fetch_interface_status_advanced,
    get_oper_status_from_port,
)
from inventory.spatial import coords_to_linestring
from django.db.models import Q
from django.conf import settings
from setup_app.services import runtime_settings

logger = logging.getLogger(__name__)

LIVE_STATUS_CACHE_KEY_TEMPLATE = "inventory:fiber_live_status:{cable_id}"
LIVE_STATUS_CACHE_TIMEOUT = 45  # seconds

OPTICAL_STATUS_SEVERITY = {
    "critical": 3,
    "warning": 2,
    "offline": 3,
    "online": 1,
    "unknown": 0,
}


def _log_audit(
    cable: FiberCable | None,
    cable_name: str,
    action: str,
    user=None,
    changes: dict | None = None,
) -> None:
    """Create a FiberCableAuditLog entry. Silently swallows errors to avoid
    breaking the main operation if audit logging fails."""
    try:
        FiberCableAuditLog.objects.create(
            cable=cable,
            cable_name=cable_name,
            user=user,
            username=getattr(user, "username", "") or "",
            action=action,
            changes=changes or {},
        )
    except Exception:
        logger.exception("[audit] Failed to write audit log for cable '%s'", cable_name)


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_port_thresholds(port: Optional[Port]) -> dict[str, float | None]:
    runtime_config = runtime_settings.get_runtime_config()
    warning_default = _float_or_none(
        getattr(runtime_config, "optical_rx_warning_threshold", None)
    )
    if warning_default is None:
        warning_default = _float_or_none(
            getattr(settings, "OPTICAL_RX_WARNING_THRESHOLD", -24.0)
        )

    critical_default = _float_or_none(
        getattr(runtime_config, "optical_rx_critical_threshold", None)
    )
    if critical_default is None:
        critical_default = _float_or_none(
            getattr(settings, "OPTICAL_RX_CRITICAL_THRESHOLD", -27.0)
        )

    warning = warning_default
    critical = critical_default

    if port and getattr(port, "alarm_enabled", False):
        custom_warning = _float_or_none(port.alarm_warning_threshold)
        custom_critical = _float_or_none(port.alarm_critical_threshold)
        if custom_warning is not None:
            warning = custom_warning
        if custom_critical is not None:
            critical = custom_critical
        if custom_warning is None and custom_critical is not None:
            warning = custom_critical + 2.0

    if warning is not None and critical is not None and warning < critical:
        warning, critical = critical, warning

    return {"warning": warning, "critical": critical}


def _classify_optical_thresholds(
    rx_value: float | None, thresholds: dict[str, float | None]
) -> str:
    if rx_value is None:
        return "unknown"

    critical = thresholds.get("critical")
    warning = thresholds.get("warning")

    if critical is not None and rx_value <= critical:
        return "critical"
    if warning is not None and rx_value <= warning:
        return "warning"
    return "online"


def _classify_optical_heuristic(
    rx_value: float | None, thresholds: dict[str, float | None]
) -> str:
    if rx_value is None:
        return "unknown"

    # When thresholds are configured, rely on them instead of fallback heuristics.
    warning = thresholds.get("warning")
    critical = thresholds.get("critical")
    if warning is not None or critical is not None:
        return "unknown"

    if rx_value >= -20:
        return "online"
    if rx_value >= -28:
        return "warning"
    return "critical"


def _port_optical_snapshot(port: Optional[Port]) -> dict[str, Any]:
    if not port:
        return {
            "status": "unknown",
            "rx": None,
            "tx": None,
            "last_check": None,
            "warning_threshold": None,
            "critical_threshold": None,
            "port_id": None,
            "port_name": None,
            "device_name": None,
            "alarm_enabled": False,
        }

    thresholds = _resolve_port_thresholds(port)
    rx_value = _float_or_none(port.last_rx_power)
    tx_value = _float_or_none(port.last_tx_power)
    status_thresholds = _classify_optical_thresholds(rx_value, thresholds)
    status_heuristic = _classify_optical_heuristic(rx_value, thresholds)
    status = _aggregate_optical_status(status_thresholds, status_heuristic)

    return {
        "status": status,
        "status_sources": {
            "thresholds": status_thresholds,
            "heuristic": status_heuristic,
        },
        "rx": rx_value,
        "tx": tx_value,
        "last_check": (
            port.last_optical_check.isoformat()
            if port.last_optical_check
            else None
        ),
        "warning_threshold": thresholds["warning"],
        "critical_threshold": thresholds["critical"],
        "port_id": port.id,
        "port_name": port.name,
        "device_name": port.device.name if port.device else None,
        "alarm_enabled": bool(port.alarm_enabled),
    }


def _aggregate_optical_status(*statuses: str) -> str:
    best_status = "unknown"
    best_score = OPTICAL_STATUS_SEVERITY.get(best_status, 0)
    for status in statuses:
        score = OPTICAL_STATUS_SEVERITY.get(status, 0)
        if score > best_score:
            best_status = status
            best_score = score
    return best_status


def build_optical_summary(cable: FiberCable) -> dict[str, Any]:
    origin = _port_optical_snapshot(getattr(cable, "origin_port", None))
    destination = _port_optical_snapshot(
        getattr(cable, "destination_port", None)
    )
    status = _aggregate_optical_status(
        origin.get("status", "unknown"),
        destination.get("status", "unknown"),
    )
    return {
        "status": status,
        "origin": origin,
        "destination": destination,
    }


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
    cable_group_id: Optional[int] = None,
    responsible_user_id: Optional[int] = None,
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
    
    # CRITICAL: Gerar path PostGIS para permitir operações de infraestrutura
    path_geom = coords_to_linestring(sanitized)

    from inventory.models import CableGroup  # local import to avoid circular
    group = None
    if cable_group_id:
        try:
            group = CableGroup.objects.get(id=cable_group_id)
        except CableGroup.DoesNotExist:
            pass
    responsible_user = None
    if responsible_user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            responsible_user = User.objects.get(id=responsible_user_id)
        except User.DoesNotExist:
            pass

    fiber = FiberCable.objects.create(
        name=name,
        origin_port=origin_port,
        destination_port=dest_port,
        path=path_geom,  # PostGIS LineString
        length_km=length_km,
        status=FiberCable.STATUS_UNKNOWN,
        cable_group=group,
        responsible_user=responsible_user,
    )
    invalidate_fiber_cache()
    payload = fiber_to_payload(fiber, coords=sanitized)
    payload["length_km"] = length_km
    return payload


def fiber_to_payload(
    fiber: FiberCable,
    coords: Optional[Iterable[Dict[str, float]]] = None,
) -> Dict[str, object]:
    """Convert FiberCable to API payload with coordinates from PostGIS path."""
    from inventory.spatial import linestring_to_coords
    
    origin_port = fiber.origin_port
    dest_port = fiber.destination_port
    
    # Get coordinates from provided param or extract from PostGIS path
    if coords is not None:
        path_coords = list(coords)
    else:
        path_coords = linestring_to_coords(fiber.path) if fiber.path else []
    
    return {
        "fiber_id": fiber.id,
        "name": fiber.name,
        "points": len(path_coords),
        "path_coordinates": path_coords,
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
        "cable_group",
        "folder",
    )
    payload = []
    for cable in cables:
        origin_site = cable.origin_port.device.site
        dest_site = cable.destination_port.device.site
        optical_summary = build_optical_summary(cable)
        payload.append(
            {
                "id": cable.id,
                "name": cable.name,
                "status": cable.status,
                "optical_status": optical_summary["status"],
                "optical_summary": optical_summary,
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
                "parent_cable_id": cable.parent_cable_id,
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
                "path": (
                    linestring_to_coords(cable.path) if cable.path else []
                ),
                "cable_group": (
                    {"id": cable.cable_group.id, "name": cable.cable_group.name}
                    if cable.cable_group_id
                    else None
                ),
                "folder": (
                    {"id": cable.folder.id, "name": cable.folder.name}
                    if cable.folder_id
                    else None
                ),
                "cable_type": (
                    {"id": cable.cable_type.id, "name": cable.cable_type.name}
                    if cable.cable_type_id
                    else None
                ),
            }
        )
    return payload


def fiber_detail_payload(cable: FiberCable) -> Dict[str, object]:
    origin_site = cable.origin_port.device.site
    dest_site = cable.destination_port.device.site
    
    # Buscar pontos de infraestrutura
    infrastructure_points = []
    for p in cable.infrastructure_points.all():
        loc = None
        try:
            loc = {
                "type": "Point",
                "coordinates": [p.location.x, p.location.y],
            }
        except Exception:
            loc = None
        infrastructure_points.append({
            "id": p.id,
            "type": p.type,
            "type_display": p.get_type_display(),
            "name": p.name,
            "location": loc,
            "distance_from_origin": p.distance_from_origin,
            "metadata": p.metadata,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    
    return {
        "id": cable.id,
        "name": cable.name,
        "status": cable.status,
        "cable_type": (
            {"id": cable.cable_type.id, "name": cable.cable_type.name}
            if cable.cable_type_id
            else None
        ),
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
        "path": linestring_to_coords(cable.path) if cable.path else [],
        "path_length_km": (
            float(cable.length_km) if cable.length_km is not None else None
        ),
        "infrastructure_points": infrastructure_points,
        "single_port": cable.origin_port == cable.destination_port,
        "cable_group": (
            {
                "id": cable.cable_group.id,
                "name": cable.cable_group.name,
                "attenuation_db_per_km": (
                    float(cable.cable_group.attenuation_db_per_km)
                    if cable.cable_group.attenuation_db_per_km is not None
                    else None
                ),
            }
            if cable.cable_group_id
            else None
        ),
        "responsible": (
            {
                "id": cable.responsible.id,
                "name": cable.responsible.name,
                "type": cable.responsible.type,
            }
            if cable.responsible_id
            else None
        ),
        "responsible_user": (
            {
                "id": cable.responsible_user.id,
                "username": cable.responsible_user.username,
                "full_name": cable.responsible_user.get_full_name() or cable.responsible_user.username,
            }
            if cable.responsible_user_id
            else None
        ),
        "folder": (
            {"id": cable.folder.id, "name": cable.folder.name}
            if cable.folder_id
            else None
        ),
    }


def update_fiber_path(cable: FiberCable, raw_path: Any) -> Dict[str, object]:
    """
    Update cable path from coordinates and store in PostGIS geometry.
    
    CRITICAL: Converts coordinate list to PostGIS LineString for spatial operations.
    """
    from inventory.spatial import coords_to_linestring
    
    allow_empty = True
    sanitized = sanitize_path_points(raw_path, allow_empty=allow_empty)
    if sanitized and len(sanitized) < 2:
        raise FiberValidationError("Path requires at least two valid points")

    length_km = calculate_path_length(sanitized)
    cable.path = coords_to_linestring(sanitized)
    cable.length_km = length_km
    
    cable.save(update_fields=["path", "length_km"])
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
    cable_group_id: Optional[int] = None,
    responsible_id: Optional[int] = None,
    responsible_user_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    cable_type: Optional[str] = None,
    user=None,
) -> Dict[str, object]:
    """Update fiber metadata such as name and endpoint ports."""
    updated_fields = []
    changes: dict = {}

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

    if cable_group_id is not None:
        from inventory.models import CableGroup
        if cable_group_id == 0:
            cable.cable_group = None
        else:
            try:
                cable.cable_group = CableGroup.objects.get(id=cable_group_id)
            except CableGroup.DoesNotExist:
                pass
        updated_fields.append("cable_group")

    if responsible_id is not None:
        from inventory.models import Responsible
        if responsible_id == 0:
            cable.responsible = None
        else:
            try:
                cable.responsible = Responsible.objects.get(id=responsible_id)
            except Responsible.DoesNotExist:
                pass
        updated_fields.append("responsible")

    if responsible_user_id is not None:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if responsible_user_id == 0:
            cable.responsible_user = None
        else:
            try:
                cable.responsible_user = User.objects.get(id=responsible_user_id)
            except User.DoesNotExist:
                pass
        updated_fields.append("responsible_user")

    if folder_id is not None:
        from inventory.models import CableFolder
        if folder_id == 0:
            cable.folder = None
        else:
            try:
                cable.folder = CableFolder.objects.get(id=folder_id)
            except CableFolder.DoesNotExist:
                pass
        updated_fields.append("folder")

    if cable_type is not None:
        from inventory.models import CableType
        if cable_type == 0 or cable_type == "0":
            cable.cable_type = None
        else:
            try:
                cable.cable_type = CableType.objects.get(id=int(cable_type))
            except (CableType.DoesNotExist, ValueError, TypeError):
                cable.cable_type = None
        updated_fields.append("cable_type")

    if updated_fields:
        cable.save(update_fields=updated_fields)
        invalidate_fiber_cache()
        _log_audit(cable, cable.name, FiberCableAuditLog.Action.UPDATED, user=user, changes=changes)

    return {
        "status": "ok",
        "updated_fields": updated_fields,
        "cable_id": cable.id,
        "name": cable.name,
    }


def delete_fiber(cable: FiberCable, user=None) -> None:
    cable_name = cable.name
    _log_audit(cable, cable_name, FiberCableAuditLog.Action.DELETED, user=user)
    cable.delete()
    invalidate_fiber_cache()


def get_delete_blockers(cable: FiberCable) -> Dict[str, object]:
    """Identify objects that would block deleting the given cable.

    Currently detects CableSegments from other cables that reference
    this cable's infrastructures via PROTECT foreign keys.
    """
    # local import to avoid cycles
    from .models import FiberInfrastructure, CableSegment

    infra_ids = list(
        FiberInfrastructure.objects.filter(cable=cable).values_list(
            "id", flat=True
        )
    )

    external_segments_qs = (
        CableSegment.objects.filter(
            Q(start_infrastructure_id__in=infra_ids)
            | Q(end_infrastructure_id__in=infra_ids)
        )
        .exclude(cable_id=cable.id)
    )

    external_segments: list[dict[str, object]] = []
    for seg in external_segments_qs.select_related("cable"):
        external_segments.append(
            {
                "segment_id": seg.id,
                "segment_number": seg.segment_number,
                "cable_id": seg.cable_id,
                "cable_name": getattr(seg.cable, "name", None),
                "start_infrastructure_id": seg.start_infrastructure_id,
                "end_infrastructure_id": seg.end_infrastructure_id,
            }
        )

    return {
        "infrastructure_ids": infra_ids,
        "external_segments_count": len(external_segments),
        "external_segments": external_segments,
    }


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


def create_manual_fiber(data: Dict[str, object], user=None) -> Dict[str, object]:
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
    
    # CRITICAL: Gerar path PostGIS para permitir operações de infraestrutura
    path_geom = coords_to_linestring(sanitized)

    cable_group_id = data.get("cable_group_id") or None
    cable_group = None
    if cable_group_id:
        from inventory.models import CableGroup  # local import avoids circular
        try:
            cable_group = CableGroup.objects.get(id=cable_group_id)
        except CableGroup.DoesNotExist:
            pass

    responsible_user_id = data.get("responsible_user_id") or None
    responsible_user = None
    if responsible_user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            responsible_user = User.objects.get(id=responsible_user_id)
        except User.DoesNotExist:
            pass

    folder_id = data.get("folder_id") or None
    folder = None
    if folder_id:
        from inventory.models import CableFolder
        try:
            folder = CableFolder.objects.get(id=folder_id)
        except CableFolder.DoesNotExist:
            pass

    cable_type_id = data.get("cable_type_id") or None
    cable_type_obj = None
    if cable_type_id:
        from inventory.models import CableType
        try:
            cable_type_obj = CableType.objects.get(id=cable_type_id)
        except CableType.DoesNotExist:
            pass

    fiber = FiberCable.objects.create(
        name=name,
        origin_port=origin_port,
        destination_port=dest_port,
        path=path_geom,  # PostGIS LineString
        length_km=length_km,
        status=FiberCable.STATUS_UNKNOWN,
        notes="single-port-monitoring" if single_port else "",
        cable_group=cable_group,
        responsible_user=responsible_user,
        folder=folder,
        cable_type=cable_type_obj,
    )
    invalidate_fiber_cache()
    _log_audit(fiber, fiber.name, FiberCableAuditLog.Action.CREATED, user=user)
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
    "get_delete_blockers",
    "compute_live_status",
    "live_status_payload",
    "bulk_live_status",
    "refresh_fibers_status",
    "create_manual_fiber",
    "update_cable_oper_status",
]


def delete_fibers_bulk(
    ids: Optional[Iterable[int]] = None,
    delete_all: bool = False,
) -> Dict[str, object]:
    """Delete multiple FiberCable entries.

    - If `delete_all` is True, ignores `ids` and deletes all cables.
    - Otherwise, deletes cables whose IDs are provided in `ids`.
    Returns a summary with deleted and missing IDs.
    """
    deleted_ids: list[int] = []
    missing_ids: list[int] = []

    target_ids: list[int]
    if delete_all:
        target_ids = list(FiberCable.objects.values_list("id", flat=True))
    else:
        raw_ids = list(ids or [])
        # Normalize and validate integers
        target_ids = []
        for raw in raw_ids:
            try:
                target_ids.append(int(raw))
            except Exception:
                continue

    for cid in target_ids:
        try:
            cable = FiberCable.objects.get(id=cid)
        except FiberCable.DoesNotExist:
            missing_ids.append(cid)
            continue
        delete_fiber(cable)
        deleted_ids.append(cid)

    # invalidate_fiber_cache() is already called per delete_fiber;
    # no extra call is strictly necessary, but harmless if added.
    return {
        "deleted_count": len(deleted_ids),
        "deleted_ids": deleted_ids,
        "missing_ids": missing_ids,
    }
