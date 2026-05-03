from __future__ import annotations

"""Core monitoring use cases for dashboard and host status data."""

import hashlib
import logging
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db.models import Q

from inventory.models import Device
from integrations.zabbix.zabbix_service import (
    safe_cache_get,
    safe_cache_set,
    zabbix_request,
)
HOST_STATUS_CACHE_TTL = int(
    getattr(
        settings,
        "MONITORING_HOST_STATUS_CACHE_TTL",
        getattr(settings, "SWR_FRESH_TTL", 30),
    )
)
HOST_STATUS_CACHE_PREFIX = "monitoring:zabbix_hosts"


def _host_status_cache_key(hostids: List[str]) -> str:
    """Return deterministic cache key for a hostid collection."""

    joined = ",".join(sorted(hostids))
    digest = hashlib.md5(joined.encode("utf-8", "replace")).hexdigest()
    return f"{HOST_STATUS_CACHE_PREFIX}:{digest}"


logger = logging.getLogger(__name__)


class HostStatusProcessor:
    """Process host status information for dashboard and API responses."""

    AVAILABLE_MAP = {"0": "Unknown", "1": "Available", "2": "Unavailable"}
    STATUS_MAP = {"0": "Active", "1": "Disabled"}

    @classmethod
    def get_status_class_and_color(cls, availability: str) -> tuple[str, str]:
        """Return CSS class and color code for the given availability."""
        availability_str = str(availability)
        if availability_str == "1":
            return "bg-green-100 text-green-800 border-green-300", "green"
        if availability_str == "2":
            return "bg-red-100 text-red-800 border-red-300", "red"
        return "bg-gray-100 text-gray-800 border-gray-300", "gray"

    @classmethod
    def get_primary_interface(
        cls,
        interfaces: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Return the primary interface; otherwise use the first entry."""
        if not interfaces:
            return None

        for iface in interfaces:
            main = iface.get("main")
            if str(main) == "1":
                return iface

        return interfaces[0] if interfaces else None

    @classmethod
    def calculate_availability(
        cls,
        host_data: Dict[str, Any],
        primary_interface: Optional[Dict[str, Any]],
    ) -> str:
        """Prefer interface availability when host reports an unknown state."""
        host_avail = str(host_data.get("available", "0"))

        if primary_interface and host_avail == "0":
            interface_avail = primary_interface.get("available")
            if interface_avail is not None:
                return str(interface_avail)

        return host_avail

    @classmethod
    def calculate_statistics(
        cls,
        hosts_status: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute aggregated statistics for cards/JSON."""
        total = len(hosts_status)
        if total == 0:
            return {
                "total": 0,
                "available": 0,
                "unavailable": 0,
                "unknown": 0,
                "availability_percentage": 0,
            }

        available = sum(
            1 for host in hosts_status if str(host.get("available")) == "1"
        )
        unavailable = sum(
            1 for host in hosts_status if str(host.get("available")) == "2"
        )
        unknown = total - available - unavailable

        return {
            "total": total,
            "available": available,
            "unavailable": unavailable,
            "unknown": unknown,
            "availability_percentage": round((available / total * 100), 2)
            if total > 0
            else 0,
        }


def get_devices_with_zabbix():
    """Retrieve devices with configured Zabbix (site join to avoid N+1)."""
    return Device.objects.select_related("site").filter(
        Q(zabbix_hostid__isnull=False) & ~Q(zabbix_hostid="")
    )


def fetch_zabbix_hosts_data(hostids: List[str]) -> List[Dict[str, Any]]:
    """Fetch host details from Zabbix, including status and interfaces."""
    if not hostids:
        return []

    unique_hostids = sorted({str(hid) for hid in hostids if hid})

    if not unique_hostids:
        return []

    cache_key = _host_status_cache_key(unique_hostids)
    cached_hosts = safe_cache_get(cache_key)
    if cached_hosts is not None:
        return cached_hosts

    try:
        hosts = (
            zabbix_request(
                "host.get",
                {
                    "output": [
                        "hostid",
                        "name",
                        "available",
                        "status",
                        "error",
                    ],
                    "hostids": unique_hostids,
                    "selectInterfaces": [
                        "interfaceid",
                        "ip",
                        "available",
                        "main",
                    ],
                },
            )
            or []
        )
        safe_cache_set(cache_key, hosts, HOST_STATUS_CACHE_TTL)
        return hosts
    except Exception:
        logger.exception(
            "Failed to query hosts from Zabbix",
            extra={"hostids": unique_hostids},
        )
        return []


def build_zabbix_map(
    zabbix_hosts: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Convert list of Zabbix hosts to a map hostid -> data."""
    return {str(host["hostid"]): host for host in zabbix_hosts}


def process_host_status(
    device: Device,
    zabbix_map: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Format a single host entry ready for template or API consumption."""
    host_key = str(device.zabbix_hostid)
    host_data = zabbix_map.get(host_key, {})
    interfaces = host_data.get("interfaces", [])
    primary_interface = HostStatusProcessor.get_primary_interface(interfaces)

    availability = HostStatusProcessor.calculate_availability(
        host_data,
        primary_interface,
    )
    status_class, color = HostStatusProcessor.get_status_class_and_color(
        availability,
    )

    interface_data: Dict[str, Any] = {
        "interfaceid": None,
        "ip": None,
        "available": availability,
    }
    if primary_interface:
        interface_data["interfaceid"] = primary_interface.get("interfaceid")
        interface_data["ip"] = primary_interface.get("ip")
        iface_available = primary_interface.get("available")
        if iface_available is not None:
            interface_data["available"] = str(iface_available)

    # Fetch uptime, CPU and Memory values from Zabbix if item keys are configured
    uptime_value = None
    uptime_seconds = None  # Raw value for status promotion (avail=2 + uptime>0 → online)
    cpu_value = None
    memory_value = None
    
    if device.uptime_item_key or device.cpu_usage_item_key or getattr(device, "memory_usage_item_key", ""):
        try:
            from integrations.zabbix.zabbix_service import zabbix_request
            
            items_to_fetch = []
            if device.uptime_item_key:
                items_to_fetch.append(device.uptime_item_key)
            if device.cpu_usage_item_key:
                items_to_fetch.append(device.cpu_usage_item_key)
            mem_key = getattr(device, "memory_usage_item_key", "")
            if mem_key:
                items_to_fetch.append(mem_key)
            
            item_values = zabbix_request(
                "item.get",
                {
                    "output": ["key_", "lastvalue", "units"],
                    "hostids": [device.zabbix_hostid],
                    "filter": {"key_": items_to_fetch},
                },
            )
            
            for item in item_values:
                key = item.get("key_", "")
                lastvalue = item.get("lastvalue", "")
                
                if key == device.uptime_item_key and lastvalue:
                    try:
                        seconds = int(float(lastvalue))
                        uptime_seconds = seconds
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
                
                elif key == device.cpu_usage_item_key and lastvalue:
                    try:
                        cpu_float = float(lastvalue)
                        cpu_value = f"{cpu_float:.1f}%"
                    except (ValueError, TypeError):
                        cpu_value = lastvalue
                elif key == mem_key and lastvalue:
                    try:
                        mem_float = float(lastvalue)
                        memory_value = f"{mem_float:.1f}%"
                    except (ValueError, TypeError):
                        memory_value = lastvalue
        
        except Exception as e:
            logger.warning(
                f"Failed to fetch Zabbix values for device {device.id}: {e}"
            )

    # Extract device type from inventory DeviceGroups
    device_type = None
    device_groups = device.groups.all()
    
    if device_groups:
        # Try to find a group that indicates device type
        # Priority: exact type keywords first
        type_keywords = [
            "Switch", "Router", "OLT", "Server",
            "Firewall", "Access Point", "GPON"
        ]
        
        for group in device_groups:
            group_name = group.name
            # First, try to find type keywords
            for keyword in type_keywords:
                if keyword.lower() in group_name.lower():
                    device_type = keyword
                    if keyword == "GPON" or "VSOLUTION" in group_name.upper():
                        device_type = "OLT (GPON)"
                    break
            if device_type:
                break
        
        # If no type found, use first group name as fallback
        if not device_type and device_groups:
            device_type = device_groups[0].name

    # Promoção de status: Zabbix marca como Unavailable (avail=2) quando o agent
    # ou ICMP falha, mas o device pode estar respondendo via SNMP. Se o uptime
    # via SNMP é > 0, o device está claramente vivo — promove para Available.
    # Sem isso, o mapa pinta o pin de cinza enquanto o modal mostra "ONLINE"
    # (que usa uptime/metrics como fonte alternativa).
    promoted_from_uptime = False
    if availability == "2" and uptime_seconds and uptime_seconds > 0:
        availability = "1"
        promoted_from_uptime = True
        # Recalcular as classes/cores agora que está available
        status_class, color = HostStatusProcessor.get_status_class_and_color("1")
        interface_data["available"] = "1"

    return {
        "device_id": device.pk,
        "hostid": host_key,
        "name": host_data.get("name", device.name),
        "site": device.site.name if device.site else "N/A",
        "site_id": device.site.pk if device.site else None,
        "site_name": device.site.name if device.site else None,
        "available": availability,
        "available_text": HostStatusProcessor.AVAILABLE_MAP.get(
            availability,
            "Unknown",
        ),
        "available_promoted": promoted_from_uptime,
        "ip": interface_data["ip"],
        "primary_ip": interface_data["ip"],
        "uptime_value": uptime_value,
        "cpu_value": cpu_value,
        "memory_value": memory_value,
        "device_type": device_type,
        "status": str(host_data.get("status", "0")),
        "status_text": HostStatusProcessor.STATUS_MAP.get(
            str(host_data.get("status", "0")),
            "Active",
        ),
        "error": host_data.get("error", ""),
        "color": color,
        "status_class": status_class,
        "interface": interface_data,
    }


def get_hosts_status_data() -> Dict[str, Any]:
    """Build host status data for reuse across views and APIs."""
    devices = get_devices_with_zabbix()
    hosts_status: List[Dict[str, Any]] = []

    if devices.exists():
        hostids = [device.zabbix_hostid for device in devices]
        zabbix_hosts = fetch_zabbix_hosts_data(hostids)
        zabbix_map = build_zabbix_map(zabbix_hosts)

        hosts_status = [
            process_host_status(device, zabbix_map)
            for device in devices
        ]

    return {
        "hosts_status": hosts_status,
        "hosts_summary": HostStatusProcessor.calculate_statistics(
            hosts_status
        ),
    }


def get_sites_with_devices_data() -> Dict[str, Any]:
    """Build sites data with devices grouped by site for map visualization."""
    from inventory.models import Site
    
    # Get all hosts status data first
    hosts_data = get_hosts_status_data()
    hosts_status = hosts_data.get("hosts_status", [])
    hosts_summary = hosts_data.get("hosts_summary", {})
    
    logger.info(f"get_sites_with_devices_data: Processing {len(hosts_status)} hosts")
    
    # Group devices by site
    sites_map: Dict[int, Dict[str, Any]] = {}
    
    for host in hosts_status:
        site_id = host.get("site_id")
        site_name = host.get("site_name", "N/A")
        device_name = host.get("name", "Unknown")
        
        if not site_id:
            logger.debug(f"Skipping device {device_name}: no site_id")
            continue
        
        if site_id not in sites_map:
            sites_map[site_id] = {
                "site_id": site_id,
                "site_name": site_name,
                "devices": [],
                "latitude": None,
                "longitude": None,
            }
        
        sites_map[site_id]["devices"].append(host)
        logger.debug(
            f"Added device {device_name} to site {site_name} "
            f"(total devices: {len(sites_map[site_id]['devices'])})"
        )
    
    # Enrich with Site coordinates
    site_ids = list(sites_map.keys())
    if site_ids:
        sites = Site.objects.filter(pk__in=site_ids).only(
            "pk", "display_name", "latitude", "longitude", "city"
        )
        
        for site in sites:
            if site.pk in sites_map:
                sites_map[site.pk]["latitude"] = (
                    float(site.latitude) if site.latitude else None
                )
                sites_map[site.pk]["longitude"] = (
                    float(site.longitude) if site.longitude else None
                )
                sites_map[site.pk]["city"] = site.city or ""
                
                logger.info(
                    f"Site {site.display_name}: "
                    f"{len(sites_map[site.pk]['devices'])} devices, "
                    f"coords: {sites_map[site.pk]['latitude']}, "
                    f"{sites_map[site.pk]['longitude']}"
                )
    
    # Convert to list and sort by name
    sites_list = sorted(
        sites_map.values(),
        key=lambda s: s.get("site_name", "").lower()
    )
    
    logger.info(f"Returning {len(sites_list)} sites with devices")
    
    return {
        "sites": sites_list,
        "hosts_summary": hosts_summary,
    }


__all__ = [
    "HostStatusProcessor",
    "build_zabbix_map",
    "fetch_zabbix_hosts_data",
    "get_devices_with_zabbix",
    "get_hosts_status_data",
    "get_sites_with_devices_data",
    "process_host_status",
]
