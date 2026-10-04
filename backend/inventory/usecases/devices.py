"""Fachada dos usecases de dispositivos (compatibilidade de import).

Em EV-0017f o módulo de 2.527 linhas foi partido em três: `devices_common` (tipos, exceções,
utilitários e `ZABBIX_REQUEST`), `devices_ports` (portas, óptico, tráfego) e
`devices_discovery` (descoberta e criação a partir do Zabbix, listagens). Este módulo só
re-exporta os nomes públicos — código novo importa dos módulos irmãos; nos testes, o alvo do
patch do Zabbix é `inventory.usecases.devices_common.ZABBIX_REQUEST`.
"""

from __future__ import annotations

from .devices_common import (
    ZABBIX_REQUEST,
    DeviceLike,
    HostItem,
    HostItemList,
    InventoryNotFound,
    InventoryUseCaseError,
    InventoryValidationError,
    PortLike,
    PortRecord,
    SiteLike,
    TrafficChannel,
    TrafficData,
    TrafficPoint,
)
from .devices_discovery import (
    add_device_from_zabbix,
    bulk_create_inventory,
    discover_zabbix_hosts,
    list_device_select_options,
    list_devices_autocomplete,
    list_sites,
)
from .devices_ports import (
    OPTICAL_DISCOVERY_CACHE_TTL,
    device_port_optical_status,
    get_device_ports,
    get_device_ports_with_live_status,
    get_device_ports_with_optical,
    import_interfaces_from_zabbix,
    port_traffic_history,
)

__all__ = [
    "InventoryUseCaseError",
    "InventoryValidationError",
    "InventoryNotFound",
    "HostItem",
    "HostItemList",
    "TrafficPoint",
    "TrafficChannel",
    "TrafficData",
    "PortRecord",
    "PortLike",
    "DeviceLike",
    "SiteLike",
    "OPTICAL_DISCOVERY_CACHE_TTL",
    "get_device_ports",
    "get_device_ports_with_live_status",
    "import_interfaces_from_zabbix",
    "get_device_ports_with_optical",
    "device_port_optical_status",
    "port_traffic_history",
    "add_device_from_zabbix",
    "discover_zabbix_hosts",
    "bulk_create_inventory",
    "list_sites",
    "list_device_select_options",
    "list_devices_autocomplete",
    "ZABBIX_REQUEST",
]
