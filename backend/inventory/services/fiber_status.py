"""Reusable helpers to retrieve and combine fiber status information."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, cast

from integrations.zabbix.zabbix_service import zabbix_request
from inventory.models import CableSegment

__all__ = [
    "fetch_interface_status_advanced",
    "combine_cable_status",
    "evaluate_cable_status_for_cable",
    "get_oper_status_from_zabbix",
    "get_oper_status_from_port",
]

UP_VALUES = {"1", 1}
DOWN_VALUES = {"2", 2, "0", 0}


def _request_list(method: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    return cast(List[Dict[str, Any]], zabbix_request(method, params) or [])


def _interpret_item_value(value: Any) -> str:
    if value in UP_VALUES:
        return "up"
    if value in DOWN_VALUES:
        return "down"
    return "unknown"


def fetch_interface_status_advanced(
    hostid: str | int | None,
    primary_item_key: str | None = None,
    interfaceid: str | int | None = None,
    rx_key: str | None = None,
    tx_key: str | None = None,
) -> Tuple[str, Dict[str, Any]]:
    if not hostid:
        return "unknown", {"error": "missing_hostid"}

    def _get_item(key: str | None) -> Dict[str, Any] | None:
        if not key:
            return None
        items = _request_list(
            "item.get",
            {
                "output": [
                    "itemid",
                    "key_",
                    "lastvalue",
                    "value_type",
                    "name",
                ],
                "hostids": hostid,
                "search": {"key_": key},
                "searchByAny": True,
                "limit": 1,
            },
        )
        return items[0] if items else None

    primary_item = _get_item(primary_item_key) if primary_item_key else None
    if primary_item:
        raw = primary_item.get("lastvalue")
        if raw is not None:
            interpreted = _interpret_item_value(raw)
            return (
                interpreted,
                {
                    "method": "primary_item",
                    "key": primary_item.get("key_"),
                    "raw": raw,
                },
            )
        history = _request_list(
            "history.get",
            {
                "itemids": primary_item["itemid"],
                "history": primary_item.get("value_type", 3),
                "sortfield": "clock",
                "sortorder": "DESC",
                "limit": 1,
            },
        )
        if history:
            raw = history[0].get("value")
            interpreted = _interpret_item_value(raw)
            return (
                interpreted,
                {
                    "method": "primary_item_history",
                    "key": primary_item.get("key_"),
                    "raw": raw,
                },
            )

    discovered: Dict[str, Any] = {}
    rx_item = _get_item(rx_key)
    tx_item = _get_item(tx_key)

    if (not rx_item and not tx_item) and interfaceid:
        candidate_items = _request_list(
            "item.get",
            {
                "output": [
                    "itemid",
                    "key_",
                    "lastvalue",
                    "value_type",
                    "name",
                ],
                "interfaceids": [interfaceid],
                "filter": {"status": "0"},
            },
        )
        rx_patterns = [
            "rxpower",
            "lanerxpower",
            "opticalrx",
            "rx low",
            "rx high",
        ]
        tx_patterns = [
            "txpower",
            "lanetxpower",
            "opticaltx",
            "tx low",
            "tx high",
        ]

        def match_any(text: str, patterns: List[str]) -> bool:
            lowered = text.lower()
            return any(pattern in lowered for pattern in patterns)

        for item in candidate_items:
            key_text = (item.get("key_") or "").lower()
            name_text = (item.get("name") or "").lower()
            combined = f"{key_text} {name_text}".strip()
            if (
                not rx_item
                and match_any(combined, rx_patterns)
                and "tx" not in combined
            ):
                rx_item = item
                discovered["rx_key"] = item.get("key_")
            elif (
                not tx_item
                and match_any(combined, tx_patterns)
                and "rx" not in combined
            ):
                tx_item = item
                discovered["tx_key"] = item.get("key_")
            if rx_item and tx_item:
                break
        if not rx_item and not tx_item:
            for item in candidate_items:
                key_lower = (item.get("key_") or "").lower()
                if not rx_item and "rx" in key_lower:
                    rx_item = item
                    discovered["rx_key_generic"] = item.get("key_")
                if not tx_item and "tx" in key_lower:
                    tx_item = item
                    discovered["tx_key_generic"] = item.get("key_")
                if rx_item and tx_item:
                    break
        if discovered:
            discovered["auto_discovered"] = True

    if not rx_item and not tx_item:
        reason: Dict[str, Any] = {"method": "no_items_found"}
        if interfaceid:
            reason["interfaceid"] = interfaceid
            reason["auto_discovery_attempt"] = True
        return "unknown", reason

    def _parse_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    rx_val = _parse_float(rx_item.get("lastvalue")) if rx_item else None
    tx_val = _parse_float(tx_item.get("lastvalue")) if tx_item else None

    threshold_down = -50
    if rx_val is not None or tx_val is not None:
        values = [v for v in (rx_val, tx_val) if v is not None]
        if values and all(v < threshold_down for v in values):
            meta = {
                "method": "optical_power",
                "rx": rx_val,
                "tx": tx_val,
                "threshold": threshold_down,
            }
            meta.update(discovered)
            return "down", meta
        meta = {
            "method": "optical_power",
            "rx": rx_val,
            "tx": tx_val,
            "threshold": threshold_down,
        }
        meta.update(discovered)
        return "up", meta

    meta = {"method": "optical_power_no_values"}
    meta.update(discovered)
    return "unknown", meta


def combine_cable_status(origin_status: str, dest_status: str) -> str:
    if origin_status == "up" and dest_status == "up":
        return "up"
    if origin_status == "down" and dest_status == "down":
        return "down"
    if (
        origin_status == "up" and dest_status == "down"
    ) or (
        origin_status == "down" and dest_status == "up"
    ):
        return "degraded"
    return "unknown"


def evaluate_cable_status_for_cable(cable: Any) -> Dict[str, Any]:
    # Verificação prioritária: segmentos físicos rompidos
    broken_segment = (
        cable.segments
        .filter(
            status__in=[
                CableSegment.STATUS_BROKEN,
                "broken",
                "BROKEN",
                "cut",
                "CUT",
                "rompeu",
                "ROMPEU",
            ]
        )
        .order_by('segment_number')
        .first()
    )

    if broken_segment is not None:
        origin_reason = {
            "method": "cable_segment_status",
            "segment_id": broken_segment.id,
            "segment_name": broken_segment.name,
            "segment_status": broken_segment.status,
        }
        dest_reason = dict(origin_reason)
        return {
            "origin_status": "down",
            "destination_status": "down",
            "origin_reason": origin_reason,
            "destination_reason": dest_reason,
            "combined_status": "down",
            "previous_status": cable.status,
            "changed": cable.status != "down",
        }

    origin_device = cable.origin_port.device
    dest_device = cable.destination_port.device
    origin_status, origin_reason = fetch_interface_status_advanced(
        origin_device.zabbix_hostid,
        primary_item_key=cable.origin_port.zabbix_item_key,
        interfaceid=cable.origin_port.zabbix_interfaceid,
        rx_key=cable.origin_port.rx_power_item_key,
        tx_key=cable.origin_port.tx_power_item_key,
    )
    dest_status, dest_reason = fetch_interface_status_advanced(
        dest_device.zabbix_hostid,
        primary_item_key=cable.destination_port.zabbix_item_key,
        interfaceid=cable.destination_port.zabbix_interfaceid,
        rx_key=cable.destination_port.rx_power_item_key,
        tx_key=cable.destination_port.tx_power_item_key,
    )
    combined = combine_cable_status(origin_status, dest_status)

    if (
        combined == "unknown"
        and origin_status == "unknown"
        and dest_status == "unknown"
    ):
        host_av_origin = _host_availability_status(origin_device.zabbix_hostid)
        host_av_dest = _host_availability_status(dest_device.zabbix_hostid)
        if host_av_origin != "unknown" or host_av_dest != "unknown":
            fallback = combine_cable_status(host_av_origin, host_av_dest)
            if fallback != "unknown":
                combined = fallback
                origin_reason = {
                    "method": "host_availability_fallback",
                    "host_available": host_av_origin,
                }
                dest_reason = {
                    "method": "host_availability_fallback",
                    "host_available": host_av_dest,
                }
                origin_status = host_av_origin
                dest_status = host_av_dest

    return {
        "origin_status": origin_status,
        "destination_status": dest_status,
        "origin_reason": origin_reason,
        "destination_reason": dest_reason,
        "combined_status": combined,
        "previous_status": cable.status,
        "changed": combined != cable.status,
    }


def _host_availability_status(hostid: Any) -> str:
    if not hostid:
        return "unknown"
    data = _request_list(
        "host.get",
        {
            "output": ["hostid", "available"],
            "hostids": hostid,
            "limit": 1,
        },
    )
    if not data:
        return "unknown"
    code = str(data[0].get("available", "0"))
    if code == "1":
        return "up"
    if code == "2":
        return "down"
    return "unknown"


def get_oper_status_from_zabbix(
    device: Any,
    port_name: str,
) -> Tuple[str, Any, Dict[str, str]]:
    item_key = f"ifOperStatus[{port_name}]"
    items = _request_list(
        "item.get",
        {
            "output": [
                "itemid",
                "key_",
                "lastvalue",
                "valuemapid",
                "value_type",
                "name",
            ],
            "hostids": device.zabbix_hostid,
            "search": {"key_": item_key},
            "searchByAny": True,
            "limit": 1,
        },
    )
    if not items:
        return "unknown", None, {}
    item = items[0]
    valuemapid = item.get("valuemapid")
    valuemap: Dict[str, str] | None = None
    if valuemapid:
        maps = _request_list(
            "valuemap.get",
            {"output": "extend", "valuemapids": [valuemapid]},
        )
        if maps:
            valuemap = {
                entry["value"]: entry["newvalue"]
                for entry in maps[0].get("mappings", [])
            }
    raw = item.get("lastvalue")
    if raw is None:
        history = _request_list(
            "history.get",
            {
                "itemids": item["itemid"],
                "history": item.get("value_type", 3),
                "sortfield": "clock",
                "sortorder": "DESC",
                "limit": 1,
            },
        )
        if history:
            raw = history[0].get("value")
    status = "unknown"
    if raw == "1":
        status = "up"
    elif raw == "2":
        status = "down"
    return status, raw, valuemap or {}


def get_oper_status_from_port(port: Any) -> Tuple[str, Any, Dict[str, Any]]:
    hostid = port.device.zabbix_hostid
    key = (port.zabbix_item_key or "").strip()
    itemid = (port.zabbix_itemid or "").strip()

    def _interpret(raw: Any) -> str:
        if raw in {"1", 1}:
            return "up"
        if raw in {"2", 2}:
            return "down"
        return "unknown"

    if key and hostid:
        items = _request_list(
            "item.get",
            {
                "output": [
                    "itemid",
                    "key_",
                    "lastvalue",
                    "value_type",
                    "name",
                ],
                "hostids": hostid,
                "search": {"key_": key},
                "searchByAny": True,
                "limit": 1,
            },
        )
        if items:
            item = items[0]
            raw = item.get("lastvalue")
            status = _interpret(raw)
            if status != "unknown":
                return status, raw, {
                    "method": "item_key",
                    "key": key,
                    "itemid": item.get("itemid"),
                }
            key_itemid = item.get("itemid")
            if not itemid and key_itemid:
                itemid = key_itemid

    if itemid:
        items = _request_list(
            "item.get",
            {
                "output": [
                    "itemid",
                    "key_",
                    "lastvalue",
                    "value_type",
                    "name",
                ],
                "itemids": [itemid],
                "limit": 1,
            },
        )
        if items:
            item = items[0]
            raw = item.get("lastvalue")
            status = _interpret(raw)
            return status, raw, {
                "method": "itemid",
                "itemid": itemid,
                "key": item.get("key_"),
            }

    return "unknown", None, {
        "method": "not_found_or_unknown",
        "key": key,
        "itemid": itemid,
    }
