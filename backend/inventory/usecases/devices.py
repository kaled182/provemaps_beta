# ruff: noqa: E501
# flake8: noqa

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypedDict,
    cast,
)

from django.core.cache import cache
from django.db.models import Prefetch, Q, QuerySet
from django.utils.text import slugify

from inventory.domain.optical import (
    fetch_port_optical_snapshot,
    fetch_ports_optical_snapshots,
)
from inventory.models import Device, FiberCable, Port, Site
from inventory.services.device_groups import sync_device_groups_for_device
from integrations.zabbix.zabbix_service import zabbix_request

ZABBIX_REQUEST = zabbix_request

logger = logging.getLogger(__name__)

OPTICAL_DISCOVERY_CACHE_TTL = 120  # seconds (2 minutes max)


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


def _resolve_host_inventory(host: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the host inventory record or an empty dict when absent."""

    inventory = host.get("inventory")
    if isinstance(inventory, dict):
        return cast(Dict[str, Any], inventory)
    return {}


def _coerce_dict_list(raw_items: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    result: List[Dict[str, Any]] = []
    entries = cast(Sequence[object], raw_items)
    for entry in entries:
        if isinstance(entry, dict):
            result.append(cast(Dict[str, Any], entry))
    return result


def _score_optical_candidate_local(item: Dict[str, Any], kind: str) -> int:
    text = " ".join(
        [
            (cast(str, item.get("key_", "")) or "").lower(),
            (cast(str, item.get("name", "")) or "").lower(),
        ]
    )
    units = (cast(str, item.get("units", "")) or "").lower()
    score = 0

    if "power" in text:
        score += 2
    if "optical" in text or "fiber" in text:
        score += 1
    if "dbm" in text or "dbm" in units:
        score += 3

    if kind == "rx":
        if any(token in text for token in ("rx", "receive", "input")):
            score += 2
        if "tx" in text:
            score -= 1
    else:
        if any(token in text for token in ("tx", "transmit", "output")):
            score += 2
        if "rx" in text:
            score -= 1

    if any(word in text for word in ("threshold", "alarm", "bias", "temperature", "fault")):
        score -= 3
    return score


def _preload_optical_discovery_cache(
    hostid: str,
    ports: Sequence[Port],
) -> Dict[Tuple[str, Optional[str]], Dict[str, Optional[str]]]:
    hostid_str = str(hostid).strip()
    if not hostid_str:
        return {}

    # Try to reuse cached discovery map when port set did not change recently
    try:
        signature_data: List[Dict[str, str]] = [
            {
                "id": str(getattr(port, "pk", getattr(port, "id", "")) or ""),
                "name": (getattr(cast(Any, port), "name", "") or "").strip(),
            }
            for port in ports
        ]
        signature_bytes = json.dumps(signature_data, sort_keys=True).encode("utf-8")
        signature_hash = hashlib.sha1(signature_bytes).hexdigest()
        cache_key_map = f"optical:discovery:{hostid_str}:{signature_hash}"
    except Exception:
        signature_hash = ""
        cache_key_map = f"optical:discovery:{hostid_str}:generic"

    cached_map: Optional[
        Dict[Tuple[str, Optional[str]], Dict[str, Optional[str]]]
    ] = None
    try:
        cached_value = cache.get(cache_key_map)
        if isinstance(cached_value, dict):
            cached_map = cast(
                Dict[Tuple[str, Optional[str]], Dict[str, Optional[str]]],
                cached_value,
            )
    except Exception:
        cached_map = None
    if cached_map:
        return cached_map

    port_entries: List[_PortEntry] = []
    for port in ports:
        name = (getattr(cast(Any, port), "name", "") or "").strip()
        if not name:
            continue
        lower = name.lower()
        trimmed = lower.replace(" ", "")
        normalized = _normalize_identifier(name)
        normalized_trimmed = _normalize_identifier(trimmed)
        port_entries.append(
            _PortEntry(
                port=port,
                record=PortRecord(port=port, created=False, defaults={}),
                lower=lower,
                normalized=normalized,
                trimmed=trimmed,
                normalized_trimmed=normalized_trimmed,
            )
        )

    if not port_entries:
        return {}

    default_cache: Dict[Tuple[str, Optional[str]], Dict[str, Optional[str]]] = {}
    for entry in port_entries:
        entry_name = cast(str, getattr(cast(Any, entry.port), "name", "")) or None
        default_cache[(hostid_str, entry_name)] = {"rx": None, "tx": None}

    base_params: Dict[str, Any] = {
        "output": ["itemid", "key_", "name", "units"],
        "hostids": [hostid_str],
        "filter": {"status": "0"},
        "limit": 5000,
    }

    search_variants: List[Dict[str, Any]] = [
        {"search": {"key_": "power"}, "searchByAny": True, "searchWildcardsEnabled": True},
        {"search": {"name": "optical"}, "searchByAny": True, "searchWildcardsEnabled": True},
        {"search": {"key_": "optical"}, "searchByAny": True, "searchWildcardsEnabled": True},
        {"search": {"name": "dbm"}, "searchByAny": True, "searchWildcardsEnabled": True},
        {"search": {"name": "power"}, "searchByAny": True, "searchWildcardsEnabled": True},
        {"search": {"key_": "laser"}, "searchByAny": True, "searchWildcardsEnabled": True},
        {"search": {"name": "laser"}, "searchByAny": True, "searchWildcardsEnabled": True},
    ]

    gathered: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()

    gathered_items_cache_key = f"optical:gathered:{hostid_str}"
    cache_hit_items = False
    try:
        cached_items = cache.get(gathered_items_cache_key)
        if isinstance(cached_items, list):
            gathered = _coerce_dict_list(cached_items)
            cache_hit_items = True
    except Exception:
        cache_hit_items = False

    if not cache_hit_items:
        for variant in search_variants:
            params = base_params.copy()
            params.update(variant)
            try:
                raw_items = ZABBIX_REQUEST("item.get", params)
            except Exception as exc:  # pragma: no cover - network failure fallback
                logger.debug(
                    "Failed preloading optical items for host %s with params %s: %s",
                    hostid_str,
                    variant,
                    exc,
                )
                continue
            items = _coerce_dict_list(raw_items)
            for item in items:
                itemid = cast(str, item.get("itemid"))
                if not itemid or itemid in seen_ids:
                    continue
                seen_ids.add(itemid)
                gathered.append(item)

        if not gathered:
            try:
                fallback_items = _coerce_dict_list(ZABBIX_REQUEST("item.get", base_params))
                for item in fallback_items:
                    itemid = cast(str, item.get("itemid"))
                    if not itemid or itemid in seen_ids:
                        continue
                    seen_ids.add(itemid)
                    gathered.append(item)
            except Exception as exc:  # pragma: no cover - network failure fallback
                logger.debug(
                    "Fallback optical preload failed for host %s: %s",
                    hostid_str,
                    exc,
                )

        if gathered:
            try:
                cache.set(
                    gathered_items_cache_key,
                    gathered,
                    OPTICAL_DISCOVERY_CACHE_TTL,
                )
            except Exception:
                pass

    if not gathered:
        logger.debug(
            "Optical preload returned no candidates for host %s; using default discovery cache",
            hostid_str,
        )
        return default_cache

    port_match_map: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}
    for item in gathered:
        key_value = cast(str, item.get("key_", ""))
        name_value = cast(str, item.get("name", ""))
        combined_text = f"{key_value.lower()} {name_value.lower()}".strip()
        if not combined_text:
            continue
        combined_normalized = _normalize_identifier(f"{key_value}{name_value}")
        tokens = _extract_key_tokens(key_value)
        rx_candidate_score = _score_optical_candidate_local(item, "rx")
        tx_candidate_score = _score_optical_candidate_local(item, "tx")

        for entry in port_entries:
            match_score = _score_port_match(entry, tokens, combined_text, combined_normalized)
            if match_score <= 0:
                continue

            entry_name = cast(str, getattr(cast(Any, entry.port), "name", "")) or None
            cache_key: Tuple[str, Optional[str]] = (hostid_str, entry_name)
            match_info = port_match_map.setdefault(
                cache_key,
                {"rx": None, "tx": None, "rx_score": float("-inf"), "tx_score": float("-inf")},
            )

            if rx_candidate_score > 0:
                rx_total = match_score + rx_candidate_score
                if rx_total > cast(float, match_info["rx_score"]):
                    match_info["rx_score"] = rx_total
                    match_info["rx"] = key_value or None

            if tx_candidate_score > 0:
                tx_total = match_score + tx_candidate_score
                if tx_total > cast(float, match_info["tx_score"]):
                    match_info["tx_score"] = tx_total
                    match_info["tx"] = key_value or None

    discovery_cache: Dict[Tuple[str, Optional[str]], Dict[str, Optional[str]]] = default_cache.copy()
    for entry in port_entries:
        entry_name = cast(str, getattr(cast(Any, entry.port), "name", "")) or None
        cache_key = (hostid_str, entry_name)
        match_info = port_match_map.get(cache_key)
        if match_info is None:
            continue
        discovery_cache[cache_key] = {
            "rx": cast(Optional[str], match_info.get("rx")),
            "tx": cast(Optional[str], match_info.get("tx")),
        }

    logger.debug(
        "Prefetched %d optical candidates for host %s (ports=%d, mapped=%d)",
        len(gathered),
        hostid_str,
        len(port_entries),
        len([entry for entry in discovery_cache.values() if entry.get("rx") or entry.get("tx")]),
    )

    try:
        cache.set(
            cache_key_map,
            discovery_cache,
            OPTICAL_DISCOVERY_CACHE_TTL,
        )
    except Exception:
        pass

    return discovery_cache


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
    start_time = time.perf_counter()
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

    ports_list: List[Port] = list(ports_qs)
    hostid = (getattr(cast(Any, device), "zabbix_hostid", "") or "").strip()
    discovery_cache: Dict[Any, Any] = {}
    if hostid:
        discovery_cache = _preload_optical_discovery_cache(hostid, ports_list)

    snapshots: Dict[int, Dict[str, Any]] = {}
    if hostid:
        snapshots = fetch_ports_optical_snapshots(
            ports_list,
            discovery_cache=discovery_cache,
            persist_keys=True,
            include_status_meta=False,
        )

    ports_with_optical: List[Dict[str, Any]] = []

    for port in ports_list:
        port_any = cast(Any, port)
        port_id = cast(int, getattr(port_any, "id", port_any.pk))
        cable = cable_origin_map.get(port_id) or cable_dest_map.get(port_id)
        optical_snapshot = snapshots.get(
            port_id,
            {
                "rx_dbm": None,
                "tx_dbm": None,
                "rx_raw": None,
                "tx_raw": None,
                "rx_key": None,
                "tx_key": None,
            },
        )
        cable_any = cast(Any, cable) if cable else None
        port_notes = cast(str, getattr(port_any, "notes", ""))
        ports_with_optical.append(
            {
                "id": port_id,
                "name": cast(str, getattr(port_any, "name", "")),
                "notes": port_notes,
                "cable_id": cast(
                    Optional[int],
                    getattr(cable_any, "id", None) if cable_any else None,
                ),
                "cable_name": cast(
                    Optional[str],
                    getattr(cable_any, "name", None) if cable_any else None,
                ),
                "optical": optical_snapshot,
            }
        )

    duration = time.perf_counter() - start_time
    logger.info(
        "get_device_ports_with_optical completed device=%s hostid=%s ports=%d duration=%.3fs",
        cast(Any, device).pk,
        hostid or "",
        len(ports_with_optical),
        duration,
    )

    # Fetch uptime and CPU values from Zabbix
    uptime_value = None
    cpu_value = None
    
    uptime_key = getattr(cast(Any, device), "uptime_item_key", "")
    cpu_key = getattr(cast(Any, device), "cpu_usage_item_key", "")
    
    if uptime_key or cpu_key:
        try:
            # Fetch item values from Zabbix
            items_to_fetch = []
            if uptime_key:
                items_to_fetch.append(uptime_key)
            if cpu_key:
                items_to_fetch.append(cpu_key)
            
            item_values = zabbix_request(
                "item.get",
                {
                    "output": ["key_", "lastvalue", "units"],
                    "hostids": [hostid],
                    "filter": {"key_": items_to_fetch},
                },
            )
            
            # Map values
            for item in item_values:
                key = item.get("key_", "")
                lastvalue = item.get("lastvalue", "")
                units = item.get("units", "")
                
                if key == uptime_key and lastvalue:
                    # Convert uptime from seconds to human readable format
                    try:
                        seconds = int(lastvalue)
                        days = seconds // 86400
                        hours = (seconds % 86400) // 3600
                        minutes = (seconds % 3600) // 60
                        
                        parts = []
                        if days > 0:
                            parts.append(f"{days}d")
                        if hours > 0:
                            parts.append(f"{hours}h")
                        if minutes > 0:
                            parts.append(f"{minutes}m")
                        
                        uptime_value = " ".join(parts) if parts else "< 1m"
                    except (ValueError, TypeError):
                        uptime_value = lastvalue
                
                elif key == cpu_key and lastvalue:
                    # Format CPU value
                    try:
                        cpu_float = float(lastvalue)
                        cpu_value = f"{cpu_float:.1f}%"
                    except (ValueError, TypeError):
                        cpu_value = f"{lastvalue}{units}" if units else lastvalue
        
        except Exception as e:
            logger.warning(f"Failed to fetch Zabbix values for device {device.id}: {e}")
    
    return {
        "device_id": cast(int, getattr(cast(Any, device), "id", device.pk)),
        "device_name": cast(str, getattr(cast(Any, device), "name", "")),
        "primary_ip": cast(Optional[str], getattr(cast(Any, device), "primary_ip", None)),
        "uptime_value": uptime_value,
        "cpu_value": cpu_value,
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
            "selectInventory": "extend",
        },
    )
    if not zabbix_data:
        raise InventoryNotFound("Host not found in Zabbix")

    host = zabbix_data[0]
    inventory = _resolve_host_inventory(host)

    def _clean(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    def _to_decimal(value: str) -> Optional[Decimal]:
        if not value:
            return None
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None

    site_display_name = (
        _clean(inventory.get("location"))
        or _clean(inventory.get("site_location"))
        or _clean(inventory.get("site_city"))
        or _clean(host.get("name"))
        or _clean(host.get("host"))
        or f"Zabbix Host {hostid}"
    )
    site_state = _clean(inventory.get("site_state"))
    site_country = _clean(inventory.get("site_country"))

    slug_source = "-".join(
        part for part in [site_display_name, site_state, site_country] if part
    )
    slug_candidate = slugify(slug_source) or slugify(site_display_name) or f"site-{hostid}"

    host_primary_name = _clean(host.get("host"))
    fallback_host_name = _clean(host.get("name"))
    desired_device_name = (
        host_primary_name
        or fallback_host_name
        or site_display_name
        or f"Zabbix Host {hostid}"
    )

    hostid_str = str(hostid)
    existing_device = (
        Device.objects.select_related("site")
        .filter(zabbix_hostid=hostid_str)
        .first()
    )

    address_payload = {
        "display_name": site_display_name,
        "address_line1": _clean(inventory.get("site_address_a")),
        "address_line2": _clean(inventory.get("site_address_b")),
        "address_line3": _clean(inventory.get("site_address_c")),
        "city": _clean(inventory.get("site_city")),
        "state": site_state,
        "postal_code": _clean(inventory.get("site_zip")),
        "country": site_country,
        "rack_location": _clean(inventory.get("site_location")),
    }

    lat_decimal = _to_decimal(_clean(inventory.get("location_lat")))
    lon_decimal = _to_decimal(_clean(inventory.get("location_lon")))

    # Find existing site based on what Zabbix returns
    # DO NOT use existing_device.site - we need to check if device should be moved to a different site
    site = None
    logger.info(f"Searching for site: '{site_display_name}'")
    
    # Strategy 1: Exact match (case-insensitive)
    site = Site.objects.filter(display_name__iexact=site_display_name).first()
    if site:
        logger.info(f"Found site by exact match: {site.display_name}")
    
    if site is None:
        # Strategy 2: Match by slug
        site = Site.objects.filter(slug=slug_candidate).first()
        if site:
            logger.info(f"Found site by slug '{slug_candidate}': {site.display_name}")
    
    if site is None:
        # Strategy 3: Normalize both sides and compare (remove accents)
        from unicodedata import normalize
        
        # Remove accents from search term
        normalized_search = normalize('NFKD', site_display_name).encode('ASCII', 'ignore').decode('ASCII').strip().lower()
        logger.info(f"Trying normalized search: '{normalized_search}'")
        
        # Check all sites with normalized comparison
        for existing_site in Site.objects.all():
            normalized_existing = normalize('NFKD', existing_site.display_name).encode('ASCII', 'ignore').decode('ASCII').strip().lower()
            if normalized_existing == normalized_search:
                site = existing_site
                logger.info(f"Found site by normalized match: {site.display_name}")
                break
    
    site_created = False
    if site is None:
        logger.warning(f"Site '{site_display_name}' not found in database. Creating new site.")
        
        # Last resort: Use get_or_create to avoid duplicate key violations
        # This ensures thread-safety when multiple devices are added simultaneously
        site_defaults = {**address_payload}
        site_defaults['slug'] = slug_candidate
        if lat_decimal is not None:
            site_defaults['latitude'] = lat_decimal
        if lon_decimal is not None:
            site_defaults['longitude'] = lon_decimal
        
        try:
            site, site_created = Site.objects.get_or_create(
                display_name=site_display_name,
                defaults=site_defaults
            )
            if site_created:
                logger.info(f"Created new site: {site.display_name}")
            else:
                logger.info(f"Site already exists (race condition avoided): {site.display_name}")
        except Exception as e:
            # If still fails due to unique constraint, try to find it one more time
            logger.error(f"Failed to create site '{site_display_name}': {e}")
            
            # Try exact match again (another process might have created it)
            site = Site.objects.filter(display_name__iexact=site_display_name).first()
            
            if site is None:
                # Try normalized match as last resort
                from unicodedata import normalize
                normalized_search = normalize('NFKD', site_display_name).encode('ASCII', 'ignore').decode('ASCII').strip().lower()
                
                for existing_site in Site.objects.all():
                    normalized_existing = normalize('NFKD', existing_site.display_name).encode('ASCII', 'ignore').decode('ASCII').strip().lower()
                    if normalized_existing == normalized_search:
                        site = existing_site
                        logger.info(f"Found site after error by normalized match: {site.display_name}")
                        break
            
            if site is None:
                # Absolute last resort: use normalized name
                logger.error(f"Could not find or create site '{site_display_name}'. Re-raising exception.")
                raise
    else:
        logger.info(f"Using existing site: {site.display_name}")
        
        # Update site fields if needed (but NEVER update display_name or slug - these are immutable)
        update_fields: List[str] = []
        for field, value in address_payload.items():
            # Skip immutable fields
            if field in ('display_name', 'slug'):
                continue
            if value and getattr(site, field) != value:
                setattr(site, field, value)
                update_fields.append(field)
        if lat_decimal is not None and site.latitude != lat_decimal:
            site.latitude = lat_decimal
            update_fields.append("latitude")
        if lon_decimal is not None and site.longitude != lon_decimal:
            site.longitude = lon_decimal
            update_fields.append("longitude")
        if update_fields:
            site.save(update_fields=update_fields)

    # Extrair IP primário das interfaces do Zabbix
    primary_ip = None
    interfaces = host.get("interfaces", [])
    if interfaces:
        # Preferir interface do tipo 1 (agent) ou 2 (SNMP), depois qualquer uma com IP
        for iface in interfaces:
            if iface.get("ip"):
                primary_ip = iface["ip"].strip()
                # Preferir interface do tipo 1 ou 2
                if iface.get("type") in ["1", "2", 1, 2]:
                    break

    # Buscar items do Zabbix primeiro para detectar uptime e CPU keys
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

    # Buscar item keys para uptime e CPU usage
    uptime_key = None
    cpu_key = None
    
    for item in host_items:
        key = item.get("key_") or ""
        key_lower = key.lower()
        name_lower = (item.get("name") or "").lower()
        
        # Identificar item key de uptime - aceita: sysUpTime, system.uptime
        # NÃO aceita: InterfaceUptime, ifLastChange, lastdowntime, etc
        if not uptime_key:
            # Verificar se é realmente uptime do SISTEMA (não interface, lastchange, etc)
            if "sysuptime" in key_lower:
                uptime_key = key
            elif "system.uptime" in key_lower:
                uptime_key = key
            elif "uptime" in key_lower:
                # Excluir falsos positivos: interface, lastchange, lastdown, iflast
                if not any(exclude in key_lower for exclude in ["interface", "lastchange", "lastdown", "iflast"]):
                    uptime_key = key
            elif "uptime" in name_lower and "system" in name_lower:
                uptime_key = key
        
        # Identificar item key de CPU usage - aceita: hwCpuDevDuty, cpu.util, system.cpu, etc
        if not cpu_key:
            if any(pattern in key_lower for pattern in ["hwcpudevduty", "cpu.util", "cpu.usage", "system.cpu"]):
                cpu_key = key
            elif "cpu" in key_lower and any(pattern in key_lower for pattern in ["duty", "load", "util", "usage"]):
                cpu_key = key
            elif "cpu" in name_lower and any(pattern in name_lower for pattern in ["uso", "usage", "util", "duty", "utiliza"]):
                cpu_key = key

    device_created = False
    if existing_device:
        device = existing_device
        update_fields: List[str] = []
        if device.site_id != getattr(site, "pk", None):
            device.site = site
            update_fields.append("site")
        if desired_device_name and device.name != desired_device_name:
            device.name = desired_device_name
            update_fields.append("name")
        if not device.zabbix_hostid or str(device.zabbix_hostid) != hostid_str:
            device.zabbix_hostid = hostid_str
            update_fields.append("zabbix_hostid")
        # Atualizar IP se mudou
        if primary_ip and device.primary_ip != primary_ip:
            device.primary_ip = primary_ip
            update_fields.append("primary_ip")
        # Atualizar uptime_item_key se mudou
        if uptime_key and device.uptime_item_key != uptime_key:
            device.uptime_item_key = uptime_key
            update_fields.append("uptime_item_key")
        # Atualizar cpu_usage_item_key se mudou
        if cpu_key and device.cpu_usage_item_key != cpu_key:
            device.cpu_usage_item_key = cpu_key
            update_fields.append("cpu_usage_item_key")
        if update_fields:
            device.save(update_fields=update_fields)
    else:
        device, device_created = Device.objects.get_or_create(
            site=site,
            name=desired_device_name,
            defaults={
                "vendor": "",
                "model": "",
                "zabbix_hostid": hostid_str,
                "primary_ip": primary_ip,
                "uptime_item_key": uptime_key or "",
                "cpu_usage_item_key": cpu_key or "",
            },
        )
        if (
            not device_created
            and (
                not device.zabbix_hostid
                or str(device.zabbix_hostid) != hostid_str
            )
        ):
            update_fields_list = ["zabbix_hostid"]
            device.zabbix_hostid = hostid_str
            if primary_ip and device.primary_ip != primary_ip:
                device.primary_ip = primary_ip
                update_fields_list.append("primary_ip")
            if uptime_key and device.uptime_item_key != uptime_key:
                device.uptime_item_key = uptime_key
                update_fields_list.append("uptime_item_key")
            if cpu_key and device.cpu_usage_item_key != cpu_key:
                device.cpu_usage_item_key = cpu_key
                update_fields_list.append("cpu_usage_item_key")
            device.save(update_fields=update_fields_list)

    # Sync device groups from Zabbix automatically
    try:
        sync_device_groups_for_device(device)
        logger.info(f"Auto-synced device groups for {device.name}")
    except Exception as e:
        logger.warning(f"Failed to auto-sync device groups for {device.name}: {e}")

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

    created_summary = {
        "sites": int(site_created),
        "devices": int(device_created),
        "ports": 0,
    }

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

    discovery_cache = _preload_optical_discovery_cache(
        str(device.zabbix_hostid or ""),
        [record.port for record in port_records],
    )
    bulk_snapshots = fetch_ports_optical_snapshots(
        [record.port for record in port_records],
        discovery_cache=discovery_cache,
        persist_keys=True,
        include_status_meta=False,
    )

    optical_snapshots: List[Dict[str, Any]] = []
    for record in port_records:
        port_like = cast(PortLike, record.port)
        snapshot = bulk_snapshots.get(
            port_like.id,
            {
                "rx_key": None,
                "tx_key": None,
                "rx_dbm": None,
                "tx_dbm": None,
            },
        )
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
        summary: Dict[str, Any] = {
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
            "site": site.display_name,
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
    site_map: Dict[str, Site] = {}
    device_map: Dict[tuple[str, str], Device] = {}

    def _register_site(site_obj: Site) -> None:
        keys = {site_obj.display_name, site_obj.slug}
        for key in keys:
            if key:
                site_map[str(key).strip()] = site_obj

    for existing_site in Site.objects.all():
        _register_site(existing_site)

    for site_data in sites_payload:
        raw_name = site_data.get("display_name") or site_data.get("name")
        if not raw_name:
            continue
        display_name = str(raw_name).strip()
        state_value = str(site_data.get("state") or "").strip()
        country_value = str(site_data.get("country") or "").strip()
        slug_source = "-".join(
            part for part in [display_name, state_value, country_value] if part
        )
        slug_candidate = slugify(slug_source) or slugify(display_name) or None

        site = Site.objects.filter(display_name__iexact=display_name).first()
        was_created = False
        if site is None:
            site = Site(
                display_name=display_name,
                address_line1=str(site_data.get("address_line1") or site_data.get("address") or "").strip(),
                address_line2=str(site_data.get("address_line2") or "").strip(),
                address_line3=str(site_data.get("address_line3") or "").strip(),
                city=str(site_data.get("city") or "").strip(),
                state=state_value,
                postal_code=str(site_data.get("postal_code") or site_data.get("zip") or "").strip(),
                country=country_value,
                rack_location=str(site_data.get("rack_location") or "").strip(),
                description=str(site_data.get("description") or "").strip(),
            )
            if slug_candidate:
                site.slug = slug_candidate

            lat_value = site_data.get("lat")
            lon_value = site_data.get("lng")
            try:
                if lat_value is not None:
                    site.latitude = Decimal(str(lat_value))
            except (InvalidOperation, ValueError):  # pragma: no cover - defensive
                pass
            try:
                if lon_value is not None:
                    site.longitude = Decimal(str(lon_value))
            except (InvalidOperation, ValueError):  # pragma: no cover
                pass
            site.save()
            was_created = True
        else:
            update_fields: List[str] = []
            field_mapping: Dict[str, Any] = {
                "address_line1": site_data.get("address_line1") or site_data.get("address") or "",
                "address_line2": site_data.get("address_line2") or "",
                "address_line3": site_data.get("address_line3") or "",
                "city": site_data.get("city") or "",
                "state": state_value,
                "postal_code": site_data.get("postal_code") or site_data.get("zip") or "",
                "country": country_value,
                "rack_location": site_data.get("rack_location") or "",
                "description": site_data.get("description") or site.description,
            }
            for field, raw in field_mapping.items():
                value = str(raw).strip()
                if value and getattr(site, field) != value:
                    setattr(site, field, value)
                    update_fields.append(field)
            if slug_candidate and site.slug != slug_candidate:
                site.slug = slug_candidate
                update_fields.append("slug")
            if update_fields:
                site.save(update_fields=update_fields)
        if was_created:
            created["sites"] += 1
        _register_site(site)

    for device_data in devices_payload:
        site_name = str(device_data.get("site") or "").strip()
        site = site_map.get(site_name)
        if not site:
            site = (
                Site.objects.filter(display_name__iexact=site_name).first()
                or Site.objects.filter(slug=slugify(site_name)).first()
            )
            if site:
                _register_site(site)
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
        for key in {site.display_name, site.slug}:
            if key:
                device_map[(str(key).strip(), device.name)] = device

    port_map: Dict[tuple[int, str], Port] = {}
    for port_data in ports_payload:
        site_name = str(port_data.get("site") or "").strip()
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
        origin_device_raw = device_map.get(
            (str(fiber_data.get("origin_site") or "").strip(), fiber_data.get("origin_device"))
        )
        dest_device_raw = device_map.get(
            (str(fiber_data.get("dest_site") or "").strip(), fiber_data.get("dest_device"))
        )

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


def list_device_select_options() -> List[Dict[str, Any]]:
    """Return device options suitable for select inputs in the UI."""

    device_rows = (
        Device.objects.select_related("site")
        .order_by("name")
        .values(
            "id",
            "name",
            "site_id",
            "site__display_name",
        )
    )

    options: List[Dict[str, Any]] = []

    for entry in device_rows:
        site_label = entry.get("site__display_name") or ""
        site_id = entry.get("site_id")

        option: Dict[str, Any] = {
            "id": int(entry["id"]),
            "name": entry["name"],
        }

        if site_label:
            option["site"] = site_label

        if site_id:
            option["site_id"] = int(site_id)

        options.append(option)

    return options


__all__ = [
    "InventoryUseCaseError",
    "InventoryValidationError",
    "InventoryNotFound",
    "get_device_ports",
    "get_device_ports_with_optical",
    "device_port_optical_status",
    "add_device_from_zabbix",
    "discover_zabbix_hosts",
    "bulk_create_inventory",
    "list_sites",
    "port_traffic_history",
    "list_device_select_options",
    "ZABBIX_REQUEST",
]
