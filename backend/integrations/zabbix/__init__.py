"""Integration layer entrypoint for Zabbix adapters.

Provides a stable namespace (`integrations.zabbix`) for the resilient client,
service helpers, and request guards that used to live under `zabbix_api`.
"""

from . import zabbix_service
from .client import ResilientZabbixClient, resilient_client
from .decorators import api_login_required, handle_api_errors
from .guards import diagnostics_guard, staff_guard

__all__ = [
    "ResilientZabbixClient",
    "resilient_client",
    "api_login_required",
    "handle_api_errors",
    "diagnostics_guard",
    "staff_guard",
    "zabbix_service",
]
