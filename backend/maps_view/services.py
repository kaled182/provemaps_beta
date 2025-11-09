"""Compatibility shim forwarding to monitoring use cases."""

from monitoring.usecases import (
    HostStatusProcessor,
    build_zabbix_map,
    fetch_zabbix_hosts_data,
    get_devices_with_zabbix,
    get_hosts_status_data,
    process_host_status,
)

__all__ = [
    "HostStatusProcessor",
    "build_zabbix_map",
    "fetch_zabbix_hosts_data",
    "get_devices_with_zabbix",
    "get_hosts_status_data",
    "process_host_status",
]
