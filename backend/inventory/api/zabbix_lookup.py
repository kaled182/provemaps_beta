"""Zabbix lookup endpoints exposed under the inventory API namespace."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, TypedDict, cast

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from integrations.zabbix.zabbix_service import zabbix_request
from setup_app.services.runtime_settings import get_runtime_config


_AVAILABILITY_LABELS: Dict[str, Dict[str, str]] = {
    "0": {"state": "unknown", "label": "Unknown"},
    "1": {"state": "online", "label": "Online"},
    "2": {"state": "offline", "label": "Offline"},
}


class AvailabilityEntry(TypedDict, total=False):
    value: Optional[str]
    channel: Optional[str]
    label: str
    state: str
    error: Optional[str]


def _normalise_interfaces(
    raw: Iterable[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    interfaces: List[Dict[str, Any]] = []
    for iface in raw:
        available_value = iface.get("available")
        interfaces.append(
            {
                "interfaceid": iface.get("interfaceid"),
                "ip": iface.get("ip"),
                "dns": iface.get("dns"),
                "port": iface.get("port"),
                "type": iface.get("type"),
                "main": iface.get("main"),
                "useip": iface.get("useip"),
                "available": str(available_value)
                if available_value not in (None, "")
                else None,
                "error": cast(Optional[str], iface.get("error") or None),
            }
        )
    return interfaces


def _build_availability(
    host: Dict[str, Any],
    interfaces: Optional[Iterable[Dict[str, Any]]] = None,
) -> AvailabilityEntry:
    channels = [
        ("available", "agent", "error"),
        ("snmp_available", "snmp", "snmp_error"),
        ("jmx_available", "jmx", "jmx_error"),
        ("ipmi_available", "ipmi", "ipmi_error"),
    ]

    fallback: Optional[AvailabilityEntry] = None

    for field, channel, error_field in channels:
        value = host.get(field)
        if value is None or value == "":
            continue

        value_str = str(value)
        label_info = _AVAILABILITY_LABELS.get(
            value_str,
            _AVAILABILITY_LABELS["0"],
        )
        error_msg = cast(Optional[str], host.get(error_field) or None)
        entry: AvailabilityEntry = {
            "value": value_str,
            "channel": channel,
            "label": label_info["label"],
            "state": label_info["state"],
            "error": error_msg,
        }

        if value_str in {"1", "2"}:
            return entry

        if fallback is None:
            fallback = entry

    channel_map = {
        "1": "agent",
        "2": "snmp",
        "3": "ipmi",
        "4": "jmx",
    }

    iface_iterable = interfaces or host.get("interfaces", [])
    for iface in iface_iterable:
        value = iface.get("available")
        if value in (None, ""):
            continue

        value_str = str(value)
        label_info = _AVAILABILITY_LABELS.get(
            value_str,
            _AVAILABILITY_LABELS["0"],
        )
        channel = channel_map.get(str(iface.get("type")), "interface")
        entry = AvailabilityEntry(
            value=value_str,
            channel=channel,
            label=label_info["label"],
            state=label_info["state"],
            error=cast(Optional[str], iface.get("error") or None),
        )

        if value_str in {"1", "2"}:
            return entry

        if fallback is None:
            fallback = entry

    if fallback is not None:
        return fallback

    return AvailabilityEntry(
        value=None,
        channel=None,
        label=_AVAILABILITY_LABELS["0"]["label"],
        state=_AVAILABILITY_LABELS["0"]["state"],
        error=None,
    )


def _pick_primary_interface(
    interfaces: Iterable[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    primary: Optional[Dict[str, Any]] = None

    for iface in interfaces:
        if str(iface.get("main")) == "1":
            primary = iface
            break
    if primary is None:
        try:
            primary = next(iter(interfaces))
        except StopIteration:
            return None
    return {
        "interfaceid": primary.get("interfaceid"),
        "ip": primary.get("ip"),
        "dns": primary.get("dns"),
        "port": primary.get("port"),
    }


@require_GET
@login_required
def lookup_zabbix_server_info(request: HttpRequest) -> JsonResponse:
    """Returns information about the configured Zabbix server."""
    config = get_runtime_config()
    
    # Extract server URL and parse
    zabbix_url = config.zabbix_api_url or ""
    
    # Parse server name/IP from URL
    server_info = "Servidor Zabbix Configurado"
    if zabbix_url:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(zabbix_url)
            server_info = parsed.netloc or parsed.path.split('/')[0]
        except Exception:
            server_info = "Zabbix Server"
    
    return JsonResponse({
        "server_name": server_info,
        "api_url": zabbix_url,
        "configured": bool(zabbix_url and config.zabbix_api_user)
    })


@require_GET
@login_required
def lookup_hosts_grouped(request: HttpRequest) -> JsonResponse:
    """Returns Zabbix hosts grouped by hostgroup for import preview."""
    
    params: Dict[str, Any] = {
        "output": [
            "hostid",
            "host",
            "name",
            "status",
            "available",
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
            "port",
            "type",
            "main",
            "useip",
            "available",
            "error",
        ],
        "selectGroups": ["groupid", "name"],
    }

    try:
        raw_hosts = cast(
            List[Dict[str, Any]],
            zabbix_request("host.get", params) or [],
        )
    except Exception as exc:
        return JsonResponse({"error": f"Zabbix API error: {exc}"}, status=502)

    # Fetch all imported devices from database for drift detection
    from inventory.models import Device
    imported_devices = {
        device.zabbix_hostid: device
        for device in Device.objects.filter(
            zabbix_hostid__isnull=False
        ).select_related('monitoring_group')
    }

    # Group hosts by hostgroup
    groups_dict: Dict[str, Dict[str, Any]] = {}
    
    for host in raw_hosts:
        interfaces = _normalise_interfaces(host.get("interfaces", []))
        availability = _build_availability(host, interfaces)
        primary_interface = _pick_primary_interface(interfaces)
        
        host_status = (
            "online" if availability.get("state") == "online" else "offline"
        )
        
        hostid = host.get("hostid")
        zabbix_name = host.get("name") or host.get("host")
        zabbix_ip = primary_interface.get("ip") if primary_interface else None
        
        # Drift detection: compare Zabbix data with saved device
        has_drift = False
        drift_fields = []
        
        if hostid in imported_devices:
            device = imported_devices[hostid]
            
            # Compare name
            if device.name != zabbix_name:
                has_drift = True
                drift_msg = f"nome ('{device.name}' → '{zabbix_name}')"
                drift_fields.append(drift_msg)
            
            # Compare IP
            if (device.primary_ip and zabbix_ip and
                    device.primary_ip != zabbix_ip):
                has_drift = True
                drift_msg = f"IP ('{device.primary_ip}' → '{zabbix_ip}')"
                drift_fields.append(drift_msg)
            
            # Compare groups (simplified: just check if groups changed)
            zabbix_group_ids = {
                g.get("groupid") for g in host.get("groups", [])
            }
            device_group_ids = {
                str(g.zabbix_groupid)
                for g in device.groups.all()
                if g.zabbix_groupid
            }
            
            if zabbix_group_ids != device_group_ids:
                has_drift = True
                drift_fields.append("grupos do Zabbix")
        
        host_data = {
            "zabbix_id": hostid,
            "name": zabbix_name,
            "ip": zabbix_ip,
            "status": host_status,
            "is_imported": False,  # Frontend will mark this
            "has_drift": has_drift,
            "drift_fields": drift_fields,
        }
        
        # Add to each group this host belongs to
        host_groups = host.get("groups", [])
        
        if not host_groups:
            # Add to "Sem Grupo" if no groups
            if "0" not in groups_dict:
                groups_dict["0"] = {
                    "zabbix_group_id": "0",
                    "name": "Sem Grupo Definido",
                    "hosts": []
                }
            groups_dict["0"]["hosts"].append(host_data)
        else:
            for group in host_groups:
                group_id = group.get("groupid")
                group_name = group.get("name")
                
                if group_id not in groups_dict:
                    groups_dict[group_id] = {
                        "zabbix_group_id": group_id,
                        "name": group_name,
                        "hosts": []
                    }
                
                groups_dict[group_id]["hosts"].append(host_data)
    
    # Convert to list and sort by group name
    groups_list = sorted(groups_dict.values(), key=lambda g: g["name"])
    
    return JsonResponse({"data": groups_list, "count": len(groups_list)})


@require_GET
@login_required
def lookup_hosts(request: HttpRequest) -> JsonResponse:
    search_term = request.GET.get("q", "").strip()
    groupids_raw = request.GET.get("groupids", "").strip()

    params: Dict[str, Any] = {
        "output": [
            "hostid",
            "host",
            "name",
            "status",
            "available",
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
            "port",
            "type",
            "main",
            "useip",
            "available",
            "error",
        ],
    }

    if search_term:
        params["search"] = {"name": search_term, "host": search_term}
        params["searchWildcardsEnabled"] = True

    if groupids_raw:
        groupids = [
            gid.strip()
            for gid in groupids_raw.split(",")
            if gid.strip()
        ]
        if groupids:
            params["groupids"] = groupids

    try:
        raw_hosts = cast(
            List[Dict[str, Any]],
            zabbix_request("host.get", params) or [],
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        return JsonResponse({"error": f"Zabbix API error: {exc}"}, status=502)

    hosts: List[Dict[str, Any]] = []
    for host in raw_hosts:
        interfaces = _normalise_interfaces(host.get("interfaces", []))
        availability = _build_availability(host, interfaces)
        hosts.append(
            {
                "hostid": host.get("hostid"),
                "name": host.get("name") or host.get("host"),
                "host": host.get("host"),
                "status": host.get("status"),
                "available": availability.get("value"),
                "availability": availability,
                "interfaces": interfaces,
            }
        )

    return JsonResponse({"data": hosts, "count": len(hosts)})


@require_GET
@login_required
def lookup_host_status(
    request: HttpRequest,
    hostid: str,
) -> JsonResponse:
    params: Dict[str, Any] = {
        "hostids": [hostid],
        "output": [
            "hostid",
            "host",
            "name",
            "status",
            "available",
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
            "port",
            "type",
            "main",
            "useip",
            "available",
            "error",
        ],
    }

    try:
        raw_hosts = cast(
            List[Dict[str, Any]],
            zabbix_request("host.get", params) or [],
        )
    except Exception as exc:  # pragma: no cover
        return JsonResponse({"error": f"Zabbix API error: {exc}"}, status=502)

    if not raw_hosts:
        return JsonResponse({"error": "Host not found"}, status=404)

    host = raw_hosts[0]
    interfaces = _normalise_interfaces(host.get("interfaces", []))
    availability = _build_availability(host, interfaces)

    return JsonResponse(
        {
            "data": {
                "availability": availability,
                "primary_interface": _pick_primary_interface(interfaces),
            }
        }
    )


@require_GET
@login_required
def lookup_host_interfaces(
    request: HttpRequest, hostid: str
) -> JsonResponse:
    params: Dict[str, Any] = {
        "hostids": [hostid],
        "output": [
            "interfaceid",
            "ip",
            "dns",
            "port",
            "type",
            "main",
            "useip",
            "available",
            "error",
        ],
    }

    try:
        interfaces = cast(
            List[Dict[str, Any]],
            zabbix_request("hostinterface.get", params) or [],
        )
    except Exception as exc:  # pragma: no cover
        return JsonResponse({"error": f"Zabbix API error: {exc}"}, status=502)
    normalised = _normalise_interfaces(interfaces)

    normalised.sort(
        key=lambda iface: (
            0 if str(iface.get("main")) == "1" else 1,
            str(iface.get("interfaceid") or ""),
        )
    )

    only_main = request.GET.get("only_main", "").lower()
    if only_main in {"1", "true", "yes"}:
        normalised = [
            iface for iface in normalised if str(iface.get("main")) == "1"
        ]

    return JsonResponse({"data": normalised})


@require_GET
@login_required
def lookup_host_groups(request: HttpRequest) -> JsonResponse:
    params: Dict[str, Any] = {
        "output": ["groupid", "name"],
        "sortfield": "name",
        "selectHosts": "count",
    }

    exclude_param = request.GET.get("exclude_empty", "").strip().lower()
    exclude_empty = exclude_param in {"1", "true", "yes", "on"}

    try:
        raw_groups = cast(
            List[Dict[str, Any]],
            zabbix_request("hostgroup.get", params) or [],
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        return JsonResponse({"error": f"Zabbix API error: {exc}"}, status=502)

    formatted: List[Dict[str, Any]] = []
    for group in raw_groups:
        groupid = group.get("groupid")
        name = group.get("name")
        hosts_count_raw = group.get("hosts")
        try:
            host_count = (
                int(hosts_count_raw)
                if hosts_count_raw not in (None, "")
                else 0
            )
        except (TypeError, ValueError):
            host_count = 0

        if exclude_empty and host_count <= 0:
            continue

        formatted.append(
            {
                "groupid": groupid,
                "name": name,
                "host_count": host_count,
            }
        )

    return JsonResponse({"data": formatted, "count": len(formatted)})


__all__ = [
    "lookup_hosts",
    "lookup_hosts_grouped",
    "lookup_host_status",
    "lookup_host_interfaces",
    "lookup_host_groups",
    "lookup_zabbix_server_info",
]
