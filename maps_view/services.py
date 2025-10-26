"""
Business logic layer for maps_view app.

This module contains the core business logic for the dashboard,
decoupled from views to improve testability and reusability.
"""

import logging
from typing import List, Dict, Any, Optional
from django.db.models import Q

from inventory.models import Device
from zabbix_api.services.zabbix_service import zabbix_request


logger = logging.getLogger(__name__)


class HostStatusProcessor:
    """Process host status information for dashboard and API responses."""

    AVAILABLE_MAP = {'0': 'Unknown', '1': 'Available', '2': 'Unavailable'}
    STATUS_MAP = {'0': 'Active', '1': 'Disabled'}

    @classmethod
    def get_status_class_and_color(cls, availability: str) -> tuple[str, str]:
        """Return CSS class and color code for the given availability."""
        availability_str = str(availability)
        if availability_str == '1':
            return 'bg-green-100 text-green-800 border-green-300', 'green'
        if availability_str == '2':
            return 'bg-red-100 text-red-800 border-red-300', 'red'
        return 'bg-gray-100 text-gray-800 border-gray-300', 'gray'

    @classmethod
    def get_primary_interface(cls, interfaces: List[Dict]) -> Optional[Dict]:
        """Pick the primary (main == 1) interface or fallback to the first available one."""
        if not interfaces:
            return None
        
        # Procura interface principal
        for iface in interfaces:
            main = iface.get('main')
            if str(main) == '1':  # aceita '1' ou 1
                return iface
        
        # Fallback para primeira interface
        return interfaces[0] if interfaces else None

    @classmethod
    def calculate_availability(cls, host_data: Dict, primary_interface: Optional[Dict]) -> str:
        """Compute availability, preferring interface state when host reports 'unknown'."""
        host_avail = str(host_data.get('available', '0'))
        
        # If the host is unknown but interface carries status, prefer the interface state
        if primary_interface and host_avail == '0':
            interface_avail = primary_interface.get('available')
            if interface_avail is not None:
                return str(interface_avail)
        
        return host_avail

    @classmethod
    def calculate_statistics(cls, hosts_status: List[Dict]) -> Dict[str, Any]:
        """Compute aggregated statistics for cards/JSON."""
        total = len(hosts_status)
        if total == 0:
            return {
                'total': 0, 
                'available': 0, 
                'unavailable': 0, 
                'unknown': 0, 
                'availability_percentage': 0
            }
        
        available = sum(1 for h in hosts_status if str(h.get('available')) == '1')
        unavailable = sum(1 for h in hosts_status if str(h.get('available')) == '2')
        unknown = total - available - unavailable
        
        return {
            'total': total,
            'available': available,
            'unavailable': unavailable,
            'unknown': unknown,
            'availability_percentage': round((available / total * 100), 2) if total > 0 else 0
        }


# ---------- Data Helpers ----------

def get_devices_with_zabbix():
    """Retrieve devices with configured Zabbix (site join to avoid N+1)."""
    return Device.objects.select_related('site').filter(
        Q(zabbix_hostid__isnull=False) & ~Q(zabbix_hostid='')
    )


def fetch_zabbix_hosts_data(hostids: List[str]) -> List[Dict]:
    """
    Perform a single call to Zabbix including the `status` field used by the API.
    Returns an empty list on failure so rendering can continue gracefully.
    """
    if not hostids:
        return []
    
    # Ensure every host id is a string and deduplicate
    unique_hostids = list(set(str(hid) for hid in hostids if hid))
    
    try:
        return zabbix_request('host.get', {
            'output': ['hostid', 'name', 'available', 'status', 'error'],
            'hostids': unique_hostids,
            'selectInterfaces': ['interfaceid', 'ip', 'available', 'main']
        }) or []
    except Exception:
        logger.exception("Failed to query hosts from Zabbix", extra={"hostids": unique_hostids})
        return []


def build_zabbix_map(zabbix_hosts: List[Dict]) -> Dict[str, Dict]:
    """Convert list of Zabbix hosts to a map hostid -> data."""
    return {str(host['hostid']): host for host in zabbix_hosts}


def process_host_status(device: Device, zabbix_map: Dict[str, Dict]) -> Dict[str, Any]:
    """Format a single host entry ready for template or API consumption."""
    host_key = str(device.zabbix_hostid)
    host_data = zabbix_map.get(host_key, {})
    interfaces = host_data.get('interfaces', [])
    primary_interface = HostStatusProcessor.get_primary_interface(interfaces)

    availability = HostStatusProcessor.calculate_availability(host_data, primary_interface)
    status_class, color = HostStatusProcessor.get_status_class_and_color(availability)

    # Interface data with safe fallbacks
    interface_data = {
        'interfaceid': primary_interface.get('interfaceid') if primary_interface else None,
        'ip': primary_interface.get('ip') if primary_interface else None,
        'available': str(primary_interface.get('available')) if primary_interface and primary_interface.get('available') is not None else availability,
    }

    return {
        'device_id': device.id,
        'hostid': host_key,
        'name': host_data.get('name', device.name),
        'site': device.site.name if device.site else 'N/A',
        'available': availability,
        'available_text': HostStatusProcessor.AVAILABLE_MAP.get(availability, 'Unknown'),
        'ip': interface_data['ip'],
        'status': str(host_data.get('status', '0')),
        'status_text': HostStatusProcessor.STATUS_MAP.get(str(host_data.get('status', '0')), 'Active'),
        'error': host_data.get('error', ''),
        'color': color,
        'status_class': status_class,
        'interface': interface_data
    }


def get_hosts_status_data() -> Dict[str, Any]:
    """
    Build host status data for reuse across views and APIs.
    
    This is the main service function that orchestrates:
    - Fetching devices from local database
    - Querying Zabbix for host status
    - Processing and enriching the data
    - Computing statistics
    
    Returns:
        Dictionary with 'hosts_status' (list of processed hosts) 
        and 'hosts_summary' (aggregated statistics).
    """
    devices = get_devices_with_zabbix()
    hosts_status = []
    
    if devices.exists():
        hostids = [device.zabbix_hostid for device in devices]
        zabbix_hosts = fetch_zabbix_hosts_data(hostids)
        zabbix_map = build_zabbix_map(zabbix_hosts)
        
        hosts_status = [
            process_host_status(device, zabbix_map) 
            for device in devices
        ]

    return {
        'hosts_status': hosts_status,
        'hosts_summary': HostStatusProcessor.calculate_statistics(hosts_status)
    }
