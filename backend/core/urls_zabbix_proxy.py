"""
Zabbix API proxy URLs.
Redirect legacy /zabbix_api/ endpoints to new inventory API paths.
"""
from django.urls import path
from django.http import HttpRequest, JsonResponse, HttpResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

from inventory.api import devices as device_api

app_name = "zabbix_api"


@require_GET
@login_required
def lookup_hosts_proxy(request: HttpRequest) -> HttpResponse:
    """
    Proxy to zabbix discover hosts endpoint with search support.
    Accepts query params: q (search term), groupids (comma-separated).
    """
    from integrations.zabbix.zabbix_service import zabbix_request
    from typing import Any, Dict, List
    
    search_term = request.GET.get('q', '').strip()
    groupids_str = request.GET.get('groupids', '').strip()
    
    # Build Zabbix API params
    params: Dict[str, Any] = {
        "output": ["hostid", "host", "name", "status"],
        "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type"],
    }
    
    # Add search filter if provided
    if search_term:
        params["search"] = {"name": search_term, "host": search_term}
        params["searchWildcardsEnabled"] = True
    
    # Add group filter if provided
    if groupids_str:
        try:
            groupids = [gid.strip() for gid in groupids_str.split(',')]
            params["groupids"] = groupids
        except (ValueError, AttributeError):
            pass
    
    try:
        raw_hosts = zabbix_request("host.get", params)
        hosts: List[Any] = (
            raw_hosts if isinstance(raw_hosts, list) else []
        )
        
        # Normalize response
        results = []
        for host in hosts:
            interfaces = host.get("interfaces", [])
            results.append({
                "hostid": host.get("hostid"),
                "name": host.get("name") or host.get("host"),
                "host": host.get("host"),
                "status": host.get("status"),
                "interfaces": interfaces,
            })
        
        return JsonResponse({"data": results, "count": len(results)})
    except Exception as exc:
        return JsonResponse(
            {"error": f"Zabbix API error: {str(exc)}"}, status=500
        )


@require_GET
@login_required
def lookup_host_status_proxy(
    request: HttpRequest, hostid: str
) -> JsonResponse:
    """Proxy for host status - not implemented yet, return placeholder."""
    return JsonResponse({
        "data": {
            "availability": {
                "value": "1",
                "channel": "agent",
                "label": "Online"
            },
            "primary_interface": {"ip": ""}
        }
    })


@require_GET
@login_required
def lookup_host_interfaces_proxy(
    request: HttpRequest, hostid: str
) -> JsonResponse:
    """Proxy for host interfaces - not implemented yet, return placeholder."""
    return JsonResponse({"data": []})


urlpatterns = [
    # Legacy zabbix_api endpoints
    path("lookup/hosts/", lookup_hosts_proxy, name="lookup-hosts"),
    path(
        "lookup/hosts/<str:hostid>/status/",
        lookup_host_status_proxy,
        name="lookup-host-status",
    ),
    path(
        "lookup/hosts/<str:hostid>/interfaces/",
        lookup_host_interfaces_proxy,
        name="lookup-host-interfaces",
    ),
    # API endpoints - proxy to inventory API
    path(
        "api/add-device-from-zabbix/",
        device_api.api_add_device_from_zabbix,
        name="add-device-from-zabbix",
    ),
    path(
        "api/device-ports-optical/<int:device_id>/",
        device_api.api_device_ports_with_optical,
        name="device-ports-optical",
    ),
    path(
        "api/port-optical-status/<int:port_id>/",
        device_api.api_device_port_optical_status,
        name="port-optical-status",
    ),
    path(
        "api/port-traffic-history/<int:port_id>/",
        device_api.api_port_traffic_history,
        name="port-traffic-history",
    ),
]
