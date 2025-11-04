# zabbix_api/services/zabbix_service.py
# Zabbix integration service (JSON-RPC) plus lookup helpers (phase 1)
# Preserves behaviour while adding short-lived host/port cache lookups.
# pyright: reportUnknownParameterType=false, reportUnknownArgumentType=false
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
# pyright: reportMissingParameterType=false, reportMissingTypeArgument=false
# pyright: reportUnusedFunction=false

from __future__ import annotations

import hashlib
import logging
import platform
import re
import subprocess
import time

import requests

from typing import Any, Mapping, Sequence, cast

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse

from .zabbix_client import (
    READ_ONLY_SAFE_METHODS,
    clear_token_cache,
    get_current_config as _client_current_config,
    normalize_zabbix_url as _normalize_zabbix_url,
    zabbix_login,
    zabbix_request,
)

logger = logging.getLogger(__name__)

JsonDict = dict[str, Any]
JsonList = list[JsonDict]

__all__ = [
    "READ_ONLY_SAFE_METHODS",
    "clear_token_cache",
    "_normalize_zabbix_url",
    "zabbix_login",
    "zabbix_request",
]


# Safe cache utility for local development
# -----------------------------------------------------------------------------
def safe_cache_get(key: str, default: Any | None = None) -> Any | None:
    """Return cache value while ignoring Redis connectivity failures."""
    try:
        return cache.get(key, default=default)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis unavailable); using default: %s",
            exc.__class__.__name__,
        )
        return default


def safe_cache_set(key: str, value: Any, timeout: int | None = None) -> None:
    """Store value while ignoring Redis connectivity failures."""
    try:
        cache.set(key, value, timeout=timeout)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis unavailable); store skipped: %s",
            exc.__class__.__name__,
        )


def safe_cache_delete(key: str) -> None:
    """Delete value while ignoring Redis connectivity failures."""
    try:
        cache.delete(key)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis unavailable); delete skipped: %s",
            exc.__class__.__name__,
        )


def _current_zabbix_config():
    """Compatibility wrapper used by legacy tests and call sites."""
    return _client_current_config()

# Utility helpers / reports (kept for compatibility)
# -----------------------------------------------------------------------------


def get_host_performance_metrics(hostid: str) -> JsonList | None:
    """Return basic host performance metrics gathered from related items.

    Optimized to avoid N+1 requests by batching ``history.get`` calls per
    item ``value_type``.

    Notes
    -----
    Zabbix ``search`` does not accept lists, so we perform multiple lookups
    by well-known prefixes and merge the results.
    """
    terms = [
        "system.cpu",
        "vm.memory",
        "vfs.fs",
        "net.if",
        "disk",
        "memory",
        "cpu",
    ]
    seen: set[str] = set()
    items: JsonList = []

    # Step 1: collect candidate items (multiple searches required)
    for term in terms:
        res: JsonList = cast(
            JsonList,
            zabbix_request(
                "item.get",
                {
                    "output": [
                        "itemid",
                        "name",
                        "key_",
                        "units",
                        "value_type",
                    ],
                    "hostids": hostid,
                    "search": {"key_": term},
                    "searchWildcardsEnabled": True,
                    "filter": {"status": 0},
                    "limit": 200,
                },
            )
            or [],
        )
        for it in res:
            iid = it.get("itemid")
            if iid and iid not in seen:
                seen.add(iid)
                items.append(it)

    if not items:
        return None

    # Step 2: collect all ``itemids`` and perform a single ``history.get``
    # call per ``value_type`` to reduce API chatter
    items_by_type: dict[str, JsonList] = {}
    for it in items:
        value_type = it["value_type"]
        if value_type not in items_by_type:
            items_by_type[value_type] = []
        items_by_type[value_type].append(it)

    # Step 3: run ``history.get`` by ``value_type`` (far fewer calls)
    history_map: dict[str, JsonDict] = {}
    for value_type, typed_items in items_by_type.items():
        itemids = [str(it["itemid"]) for it in typed_items]

        hist_results: JsonList = cast(
            JsonList,
            zabbix_request(
                "history.get",
                {
                    "itemids": itemids,
                    "history": value_type,
                    "sortfield": "clock",
                    "sortorder": "DESC",
                    "limit": len(itemids),
                },
            )
            or [],
        )

        # Build a map itemid -> most recent value
        for hist in hist_results:
            itemid = hist.get("itemid")
            if itemid and itemid not in history_map:
                history_map[itemid] = {
                    "value": hist.get("value"),
                    "clock": hist.get("clock"),
                }

    # Step 4: enrich original items with historical values
    latest: JsonList = []
    for it in items:
        hist_data = history_map.get(it["itemid"])
        if hist_data:
            it["latest_value"] = hist_data["value"]
            it["latest_timestamp"] = hist_data["clock"]
        latest.append(it)

    return latest


def get_host_problems(hostid: str) -> JsonList | None:
    """Return recent problems for a given host."""
    return cast(
        JsonList | None,
        zabbix_request(
            "problem.get",
            {
                "output": [
                    "eventid",
                    "objectid",
                    "name",
                    "severity",
                    "clock",
                    "acknowledged",
                ],
                "hostids": hostid,
                "recent": True,
                "sortfield": ["eventid"],
                "sortorder": "DESC",
            },
        ),
    )


def format_host_data(
    host_data: Sequence[Mapping[str, Any]] | None,
) -> JsonList | None:
    """Return human-friendly host data payload."""
    if not host_data:
        return None

    status_map = {"0": "Monitored", "1": "Not monitored"}
    available_map = {"0": "Unknown", "1": "Available", "2": "Unavailable"}

    formatted: JsonList = []
    for h in host_data:
        formatted.append(
            {
                "hostid": h.get("hostid"),
                "host": h.get("host"),
                "name": h.get("name", h.get("host")),
                "status": {
                    "code": h.get("status", "0"),
                    "description": status_map.get(
                        h.get("status", "0"),
                        "Unknown",
                    ),
                },
                "available": {
                    "code": h.get("available", "0"),
                    "description": available_map.get(
                        h.get("available", "0"),
                        "Unknown",
                    ),
                },
                "error": h.get("error", ""),
                "groups": h.get("groups", []),
                "interfaces": h.get("interfaces", []),
                "items_count": len(h.get("items", [])),
                "triggers_count": len(h.get("triggers", [])),
            }
        )
    return formatted


def get_host_network_details(hostid: str) -> dict[str, Any] | None:
    """Return network info, recent values, and problems for the host.

    Optimized to batch ``history.get`` calls per ``value_type`` to avoid N+1
    patterns and reduce API chatter.
    """
    try:
        host_info = cast(
            JsonList | None,
            zabbix_request(
                "host.get",
                {
                    "output": [
                        "hostid",
                        "host",
                        "name",
                        "status",
                        "available",
                    ],
                    "hostids": hostid,
                    "selectInterfaces": "extend",
                    "selectInventory": "extend",
                    "selectMacros": ["macro", "value"],
                },
            ),
        )
        if not host_info:
            return None

        host = host_info[0]

        # Step 1: collect common network items using multiple safe lookups
        terms = [
            "net.if",
            "agent.ping",
            "icmpping",
            "system.uptime",
        ]
        items: JsonList = []
        seen: set[str] = set()
        for term in terms:
            res: JsonList = cast(
                JsonList,
                zabbix_request(
                    "item.get",
                    {
                        "output": [
                            "itemid",
                            "name",
                            "key_",
                            "units",
                            "value_type",
                        ],
                        "hostids": hostid,
                        "search": {"key_": term},
                        "searchWildcardsEnabled": True,
                        "filter": {"status": "0"},
                        "limit": 200,
                    },
                )
                or [],
            )
            for it in res:
                iid = it.get("itemid")
                if iid and iid not in seen:
                    seen.add(iid)
                    items.append(it)

        # Step 2: group items by ``value_type``
        items_by_type: dict[str, JsonList] = {}
        for it in items:
            value_type = it["value_type"]
            if value_type not in items_by_type:
                items_by_type[value_type] = []
            items_by_type[value_type].append(it)

        # Step 3: run ``history.get`` per ``value_type``
        history_map: dict[str, JsonDict] = {}
        for value_type, typed_items in items_by_type.items():
            itemids = [it["itemid"] for it in typed_items]

            try:
                hist_results: JsonList = cast(
                    JsonList,
                    zabbix_request(
                        "history.get",
                        {
                            "itemids": itemids,
                            "history": value_type,
                            "sortfield": "clock",
                            "sortorder": "DESC",
                            "limit": len(itemids),
                        },
                    )
                    or [],
                )

                # Build a map itemid -> last known value
                for hist in hist_results:
                    itemid = hist.get("itemid")
                    if itemid and itemid not in history_map:
                        history_map[itemid] = {
                            "value": hist.get("value"),
                            "clock": hist.get("clock"),
                        }
            except Exception:
                continue

        # Step 4: build ``network_data`` using the lookup map
        network_data: dict[str, JsonDict] = {}
        for it in items:
            hist_data = history_map.get(it["itemid"])
            if hist_data:
                network_data[it["key_"]] = {
                    "name": it["name"],
                    "value": hist_data["value"],
                    "timestamp": hist_data["clock"],
                }

        # Step 5: fetch recent problems (single call)
        problems: JsonList = cast(
            JsonList,
            zabbix_request(
                "problem.get",
                {
                    "output": ["eventid", "name", "severity", "clock"],
                    "hostids": hostid,
                    "recent": True,
                },
            )
            or [],
        )

        return {
            "host_info": host,
            "network_data": network_data,
            "problems": problems,
        }
    except Exception:
        return None


def get_geolocation_from_ip(ip_address: str):
    """Return lightweight geolocation information via the IP-API service."""
    try:
        response = requests.get(
            f"http://ip-api.com/json/{ip_address}",
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.debug("IP-API request failed for %s: %s", ip_address, exc)
        return None

    try:
        data = response.json()
    except ValueError as exc:
        logger.debug("Invalid IP-API response for %s: %s", ip_address, exc)
        return None

    if data.get("status") != "success":
        return None

    return {
        "country": data.get("country"),
        "region": data.get("regionName"),
        "city": data.get("city"),
        "latitude": data.get("lat"),
        "longitude": data.get("lon"),
        "isp": data.get("isp"),
        "timezone": data.get("timezone"),
    }


def check_host_connectivity(ip_address: str) -> bool:
    """Ping a host in a cross-platform manner (Windows, Linux, macOS)."""
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", "3000", ip_address]
    else:
        cmd = ["ping", "-c", "1", "-W", "3", ip_address]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    except subprocess.TimeoutExpired as exc:
        logger.debug("Ping timeout for %s: %s", ip_address, exc)
        return False
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        logger.debug("Ping execution failed for %s: %s", ip_address, exc)
        return False

    return result.returncode == 0


def extract_mac_address_from_items(
    network_data: Mapping[str, Mapping[str, Any]] | None,
) -> JsonList:
    """Return candidate MAC addresses found within item keys/values."""
    macs: JsonList = []
    for key, data in (network_data or {}).items():
        if "mac" in key.lower() or "hwaddr" in key.lower():
            macs.append(
                {
                    "interface": data.get("name"),
                    "mac": data.get("value"),
                }
            )
    return macs


# -----------------------------------------------------------------------------
# Existing utility views (kept for compatibility)
# -----------------------------------------------------------------------------

def get_interfaces(request: HttpRequest) -> JsonResponse:
    """List interfaces for a given host using ``hostinterface.get``.

    Expected query: ``?hostid=10105``
    """
    hostid = request.GET.get("hostid")
    if not hostid:
        return JsonResponse(
            {"error": "Parameter 'hostid' is required."},
            status=400,
        )

    res = cast(
        JsonList | None,
        zabbix_request(
            "hostinterface.get",
            {
                "output": [
                    "interfaceid",
                    "hostid",
                    "ip",
                    "port",
                    "type",
                    "main",
                ],
                "hostids": hostid,
            },
        ),
    )
    if res is None:
        return JsonResponse(
            {"error": "Failed to query Zabbix."},
            status=502,
        )

    return JsonResponse({"interfaces": res}, safe=False)


def translate_interface_status(value: str) -> str:
    """Translate numeric ``ifOperStatus`` values into human-friendly text."""
    return {
        "1": "UP",
        "2": "DOWN",
        "3": "TESTING",
        "4": "UNKNOWN",
        "5": "DORMANT",
        "6": "NOT PRESENT",
        "7": "LOWER LAYER DOWN",
    }.get(value, "UNKNOWN")


def port_itemid_status(request, itemid):
    """Return status information for a port item (``itemid``).

    Example: ``/status/52638/``
    """
    try:
        result = zabbix_request(
            "item.get",
            {
                "output": [
                    "itemid",
                    "name",
                    "key_",
                    "status",
                    "type",
                    "lastvalue",
                    "units",
                    "valuemapid",
                    "value_type",
                ],
                "itemids": [str(itemid)],
                "limit": 1,
            },
        )
        if result is None:
            return JsonResponse(
                {"error": "Zabbix request failed (item.get)."},
                status=502,
            )
        if not result:
            return JsonResponse(
                {"error": f"No item found with itemid={itemid}."},
                status=404,
            )

        item = result[0]
        lastvalue = item.get("lastvalue", "")
        status_text = translate_interface_status(str(lastvalue))

        # Fallback when the value map returns UNKNOWN
        if status_text == "UNKNOWN":
            retry = zabbix_request(
                "item.get",
                {
                    "output": [
                        "itemid",
                        "name",
                        "key_",
                        "status",
                        "type",
                        "lastvalue",
                        "units",
                        "valuemapid",
                        "value_type",
                    ],
                    "itemids": [str(itemid)],
                    "limit": 1,
                },
            )
            if retry:
                rv = retry[0].get("lastvalue", "")
                rt = translate_interface_status(str(rv))
                if rt != "UNKNOWN":
                    lastvalue = rv
                    status_text = rt

        return JsonResponse(
            {
                "itemid": item.get("itemid"),
                "name": item.get("name"),
                "key_": item.get("key_"),
                "status": item.get("status"),
                "type": item.get("type"),
                "lastvalue": lastvalue,
                "status_description": status_text,
                "units": item.get("units"),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        return JsonResponse({"error": f"Unexpected error: {exc}"}, status=500)


# Lookup Helpers (phase 1) -- short-lived cache for host/interface lookups
# -----------------------------------------------------------------------------

ZABBIX_LOOKUP_CACHE_TTL = getattr(settings, "ZABBIX_LOOKUP_CACHE_TTL", 30)

AVAILABILITY_STATE_LABELS = {
    "0": ("unknown", "Unknown"),
    "1": ("online", "Online"),
    "2": ("offline", "Offline"),
}


def _extract_host_availability(
    host: Mapping[str, Any],
    interfaces: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return availability metadata preferring SNMP, Agent, IPMI, then JMX."""

    channels = [
        ("snmp", host.get("snmp_available"), host.get("snmp_error")),
        ("agent", host.get("available"), host.get("error")),
        ("ipmi", host.get("ipmi_available"), host.get("ipmi_error")),
        ("jmx", host.get("jmx_available"), host.get("jmx_error")),
    ]
    for channel, value, err in channels:
        if value in (None, "", "null", "None"):
            continue
        value_str = str(value)
        label_key, human = AVAILABILITY_STATE_LABELS.get(
            value_str,
            ("unknown", "Unknown"),
        )
        return {
            "channel": channel,
            "value": value_str,
            "state": label_key,
            "label": human,
            "error": err,
        }

    availability = {
        "channel": None,
        "value": None,
        "state": "unknown",
        "label": "Unknown",
        "error": None,
    }
    iface_list = (
        interfaces
        if interfaces is not None
        else (host.get("interfaces") or [])
    )
    if availability["value"] in (None, "", "null", "None") and iface_list:
        primary_iface = next(
            (i for i in iface_list if str(i.get("main")) == "1"),
            None,
        )
        candidate_ifaces = [primary_iface] if primary_iface else []
        if not candidate_ifaces:
            candidate_ifaces = iface_list[:1]
        for iface in candidate_ifaces:
            if iface is None:
                continue
            iface_value = iface.get("available")
            if iface_value in (None, "", "null", "None"):
                continue
            iface_value_str = str(iface_value)
            if iface_value_str in {"1", "2"}:
                availability = {
                    "channel": "device",
                    "value": iface_value_str,
                    "state": "online" if iface_value_str == "1" else "offline",
                    "label": "Online" if iface_value_str == "1" else "Offline",
                    "error": None,
                }
                break

    return availability


_IP_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


def _primary_ip(interfaces):
    if not interfaces:
        return None
    main_if = next((i for i in interfaces if str(i.get("main")) == "1"), None)
    return (main_if or interfaces[0]).get("ip")


def fetch_host_availability(hostid: str) -> dict:
    """Return host availability data including interface metadata."""

    params = {
        "hostids": [str(hostid)],
        "output": [
            "hostid",
            "host",
            "name",
            "available",
            "status",
            "error",
            "snmp_available",
            "snmp_error",
            "ipmi_available",
            "ipmi_error",
            "jmx_available",
            "jmx_error",
        ],
        "selectInterfaces": [
            "interfaceid",
            "ip",
            "dns",
            "main",
            "available",
            "port",
        ],
        "limit": 1,
    }
    hosts = zabbix_request("host.get", params=params) or []
    if not hosts:
        return {
            "hostid": str(hostid),
            "availability": {
                "channel": None,
                "value": None,
                "state": "unknown",
                "label": "Unknown",
                "error": None,
            },
            "interfaces": [],
            "primary_interface": None,
        }

    host = hosts[0]
    raw_interfaces = host.get("interfaces") or []
    interfaces = []
    primary = None
    for iface in raw_interfaces:
        available_value = iface.get("available")
        payload = {
            "interfaceid": str(iface.get("interfaceid")),
            "ip": iface.get("ip"),
            "dns": iface.get("dns"),
            "port": iface.get("port"),
            "main": str(iface.get("main") or "0"),
            "available": (
                str(available_value) if available_value is not None else None
            ),
        }
        interfaces.append(payload)
        if payload["main"] == "1":
            primary = payload
    if not primary and interfaces:
        primary = interfaces[0]

    availability = _extract_host_availability(host, raw_interfaces)
    if (
        availability["state"] == "unknown"
        and primary
        and primary.get("available") in {"1", "2"}
    ):
        availability = {
            "channel": "device",
            "value": primary["available"],
            "state": "online" if primary["available"] == "1" else "offline",
            "label": "Online" if primary["available"] == "1" else "Offline",
            "error": None,
        }

    return {
        "hostid": str(hostid),
        "host": host.get("host"),
        "name": host.get("name"),
        "availability": availability,
        "interfaces": interfaces,
        "primary_interface": primary,
    }


def _cache_key(prefix, **parts):
    """Return a stable cache key (md5) that works across processes."""

    raw = "&".join(f"{k}={parts[k]}" for k in sorted(parts.keys()))
    return f"zbx:{prefix}:{hashlib.md5(raw.encode('utf-8')).hexdigest()}"


def search_hosts(query=None, groupids=None, limit=20):
    """Search hosts via ``host.get`` applying light filters and caching."""

    q = (query or "").strip()
    gids = (
        ",".join(groupids)
        if isinstance(groupids, (list, tuple))
        else (groupids or "")
    )
    key = _cache_key("search_hosts", q=q, gids=gids, limit=int(limit))
    cached = safe_cache_get(key)
    if cached is not None:
        return cached

    params = {
        "output": [
            "hostid",
            "host",
            "name",
            "available",
            "status",
            "error",
            "snmp_available",
            "snmp_error",
            "ipmi_available",
            "ipmi_error",
            "jmx_available",
            "jmx_error",
        ],
        "selectInterfaces": [
            "interfaceid",
            "ip",
            "dns",
            "main",
            "port",
            "available",
        ],
        "limit": int(limit),
    }
    if gids:
        params["groupids"] = gids.split(",") if isinstance(gids, str) else gids

    if q and not _IP_RE.match(q):
        params["search"] = {"name": q}
        params["searchWildcardsEnabled"] = True

    result = zabbix_request("host.get", params=params)

    # Fallback: search by IP via ``hostinterface.get`` when required
    if q and _IP_RE.match(q) and not result:
        if_params = {
            "output": [
                "interfaceid",
                "hostid",
                "ip",
                "dns",
                "main",
                "port",
                "available",
            ],
            "filter": {"ip": q},
            "limit": 50,
        }
        ifaces = zabbix_request("hostinterface.get", params=if_params) or []
        hostids = list({i["hostid"] for i in ifaces})
        if hostids:
            result = zabbix_request(
                "host.get",
                {
                    "hostids": hostids,
                    "output": params["output"],
                    "selectInterfaces": params["selectInterfaces"],
                    "limit": int(limit),
                },
            )

    normalized = []
    for h in result or []:
        interfaces = h.get("interfaces") or []
        availability = _extract_host_availability(h, interfaces)
        normalized.append(
            {
                "id": str(h.get("hostid")),
                "host": h.get("host"),
                "name": h.get("name"),
                "ip": _primary_ip(interfaces),
                "available": availability["value"],
                "status": h.get("status"),
                "error": h.get("error"),
                "availability": availability,
            }
        )

    safe_cache_set(key, normalized, ZABBIX_LOOKUP_CACHE_TTL)
    return normalized


def get_host_interfaces(hostid, only_main: bool = False, limit: int = 200):
    """Return host interfaces, optionally filtered to the primary one."""

    hostid = str(hostid)
    key = _cache_key(
        "host_if",
        hostid=hostid,
        main=int(bool(only_main)),
        limit=int(limit),
    )
    cached = safe_cache_get(key)
    if cached is not None:
        return cached

    params = {
        "output": [
            "interfaceid",
            "ip",
            "dns",
            "main",
            "port",
            "available",
            "type",
            "useip",
        ],
        "hostids": [hostid],
        "limit": int(limit),
    }
    res = zabbix_request("hostinterface.get", params=params) or []
    if only_main:
        res = [i for i in res if str(i.get("main")) == "1"]

    out = []
    for i in res:
        out.append(
            {
                "interfaceid": str(i.get("interfaceid")),
                "ip": i.get("ip"),
                "dns": i.get("dns"),
                "main": int(i.get("main") or 0),
                "port": str(i.get("port") or ""),
                "available": int(i.get("available") or 0),
                "type": int(i.get("type") or 0),
                "useip": int(i.get("useip") or 1),
            }
        )

    safe_cache_set(key, out, ZABBIX_LOOKUP_CACHE_TTL)
    return out


# -----------------------------------------------------------------------------
# Lookup helpers (phase 1) -- optional safe helpers
# -----------------------------------------------------------------------------


def search_hosts_by_name_ip(query: str, groupids=None, limit: int = 20):
    """Search hosts (name or IP) enriching with groups and interface data."""

    cache_key = _cache_key(
        "host_search_ext",
        q=query or "",
        gids=str(groupids or ""),
        limit=int(limit),
    )
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    base_output = [
        "hostid",
        "host",
        "name",
        "available",
        "status",
        "error",
        "description",
        "snmp_available",
        "snmp_error",
        "ipmi_available",
        "ipmi_error",
        "jmx_available",
        "jmx_error",
    ]
    params = {
        "output": base_output,
        "selectInterfaces": [
            "interfaceid",
            "ip",
            "dns",
            "main",
            "port",
            "available",
        ],
        "selectGroups": ["groupid", "name"],
        "limit": int(limit),
    }
    if groupids:
        params["groupids"] = groupids

    # 1) Try by name with wildcards
    if query and not _IP_RE.match(query):
        p = dict(params)
        p["search"] = {"name": query}
        p["searchWildcardsEnabled"] = True
        hosts = zabbix_request("host.get", p) or []
    else:
        hosts = []

    # 2) If no match and looks like an IP, resolve via hostinterface.get
    if not hosts and query and _IP_RE.match(query):
        ifaces = zabbix_request(
            "hostinterface.get",
            {
                "output": ["interfaceid", "hostid", "ip", "dns", "main"],
                "filter": {"ip": query},
                "limit": int(limit),
            },
        ) or []
        if ifaces:
            host_ids = list({i["hostid"] for i in ifaces})
            hosts = zabbix_request(
                "host.get",
                {
                    "hostids": host_ids,
                    "output": base_output,
                    "selectInterfaces": params["selectInterfaces"],
                    "selectGroups": params["selectGroups"],
                },
            ) or []

    normalized = []
    for h in hosts:
        interfaces = h.get("interfaces", [])
        availability = _extract_host_availability(h, interfaces)
        primary_ip = _primary_ip(interfaces)
        groups = [g["name"] for g in h.get("groups", [])]
        normalized.append(
            {
                "hostid": h["hostid"],
                "host": h["host"],
                "name": h.get("name", h["host"]),
                "ip": primary_ip,
                "available": availability["value"],
                "status": h.get("status", "0"),
                "error": h.get("error", ""),
                "description": h.get("description", ""),
                "groups": groups,
                "interfaces_count": len(interfaces),
                "availability": availability,
            }
        )

    safe_cache_set(cache_key, normalized, ZABBIX_LOOKUP_CACHE_TTL)
    return normalized


def get_host_interfaces_detailed(hostid: str, include_snmp_info: bool = False):
    """Return host interfaces, optionally enriching with SNMP metadata."""

    cache_key = _cache_key(
        "host_if_detailed",
        hostid=str(hostid),
        snmp=int(bool(include_snmp_info)),
    )
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    interfaces = zabbix_request(
        "hostinterface.get",
        {
            "output": [
                "interfaceid",
                "hostid",
                "ip",
                "dns",
                "port",
                "type",
                "main",
                "available",
                "useip",
            ],
            "hostids": [str(hostid)],
            "limit": 200,
        },
    ) or []

    detailed = []
    for i in interfaces:
        detailed.append(
            {
                "interfaceid": i.get("interfaceid"),
                "hostid": i.get("hostid"),
                "ip": i.get("ip", ""),
                "dns": i.get("dns", ""),
                "port": i.get("port", ""),
                "type": i.get("type", "1"),
                "main": i.get("main", "0"),
                "available": i.get("available", "0"),
                "useip": i.get("useip", "1"),
                "snmp_data": {},  # intentionally empty in this phase
            }
        )

    safe_cache_set(cache_key, detailed, ZABBIX_LOOKUP_CACHE_TTL)
    return detailed


def get_interface_snmp_details(interfaceid: str, snmpindex: str | None = None):
    """Return SNMP details for an interface if a valid ifIndex is provided."""

    # 1) Fetch hostinterface metadata first
    iface = zabbix_request(
        "hostinterface.get",
        {
            "output": [
                "interfaceid",
                "hostid",
                "ip",
                "dns",
                "port",
                "type",
                "main",
                "available",
            ],
            "interfaceids": [str(interfaceid)],
        },
    )
    if not iface:
        return None

    info = {"interface": iface[0], "snmp_data": {}}

    # 2) Without an ifIndex we only return the raw interface metadata
    if not snmpindex:
        return info

    # 3) Retrieve host items matching the suffix .{snmpindex}
    items = zabbix_request(
        "item.get",
        {
            "output": [
                "itemid",
                "name",
                "key_",
                "lastvalue",
                "units",
                "lastclock",
            ],
            "hostids": [str(info["interface"]["hostid"])],
            "search": {"key_": f".{snmpindex}"},
            "searchWildcardsEnabled": True,
            "filter": {"status": "0"},
            "limit": 500,
        },
    ) or []

    for it in items:
        key = it.get("key_", "")
        val = it.get("lastvalue")
        if f"ifAlias.{snmpindex}" in key:
            info["snmp_data"]["alias"] = val
        elif f"ifName.{snmpindex}" in key:
            info["snmp_data"]["name"] = val
        elif f"ifDescr.{snmpindex}" in key:
            info["snmp_data"]["description"] = val
        elif f"ifOperStatus.{snmpindex}" in key:
            info["snmp_data"]["oper_status"] = val
        elif f"ifAdminStatus.{snmpindex}" in key:
            info["snmp_data"]["admin_status"] = val
        elif f"ifSpeed.{snmpindex}" in key:
            info["snmp_data"]["speed"] = f"{val} {it.get('units', '')}"
        elif "ifHCInOctets" in key or "ifInOctets" in key:
            info["snmp_data"]["rx_bytes"] = val
        elif "ifHCOutOctets" in key or "ifOutOctets" in key:
            info["snmp_data"]["tx_bytes"] = val

    return info


def test_host_connectivity(hostid: str):
    """Return Zabbix availability with optional ping reachability."""

    cache_key = _cache_key("host_connectivity", hostid=str(hostid))
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    host_data = zabbix_request(
        "host.get",
        {
            "output": ["hostid", "host", "name", "available", "error"],
            "selectInterfaces": ["interfaceid", "ip", "available", "main"],
            "hostids": [str(hostid)],
            "limit": 1,
        },
    )

    if not host_data:
        return {"status": "error", "message": "Host not found"}

    host = host_data[0]
    interfaces = host.get("interfaces", []) or []
    primary = next(
        (i for i in interfaces if str(i.get("main")) == "1"),
        interfaces[0] if interfaces else None,
    )

    result = {
        "hostid": hostid,
        "host": host.get("host"),
        "name": host.get("name", host.get("host")),
        "zabbix_available": host.get("available", "0"),
        "zabbix_error": host.get("error", ""),
        "primary_interface": primary,
    }

    # Optional ping test to validate reachability
    if primary and primary.get("ip"):
        ip_addr = primary["ip"]
        result["ping_test"] = {
            "ip": ip_addr,
            "reachable": check_host_connectivity(ip_addr),
            "timestamp": time.time(),
        }

    safe_cache_set(cache_key, result, 60)
    return result


