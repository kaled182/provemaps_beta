from __future__ import annotations

import logging
from typing import Any
from monitoring import tasks as monitoring_tasks
from monitoring.tasks import (
    broadcast_dashboard_snapshot,
    refresh_dashboard_cache_task,
)
from monitoring.usecases import get_hosts_status_data as _get_hosts_status_data
from maps_view.realtime.publisher import (
    broadcast_dashboard_status as _broadcast_dashboard_status,
)

logger = logging.getLogger(__name__)

__all__ = [
    "broadcast_dashboard_status",
    "broadcast_dashboard_snapshot",
    "refresh_dashboard_cache_task",
    "get_hosts_status_data",
]


# Compatibility export for legacy patches/tests
get_hosts_status_data = _get_hosts_status_data
broadcast_dashboard_status = _broadcast_dashboard_status


def _get_hosts_status_data_proxy(*args: Any, **kwargs: Any) -> Any:
    """Delegate monitoring usecase lookups to the compatibility alias."""
    return get_hosts_status_data(*args, **kwargs)


monitoring_tasks.monitoring_usecases.get_hosts_status_data = (
    _get_hosts_status_data_proxy
)


def _broadcast_dashboard_status_proxy(*args: Any, **kwargs: Any) -> Any:
    """Ensure monitoring.tasks resolves the broadcaster through this shim."""
    return broadcast_dashboard_status(*args, **kwargs)


monitoring_tasks.broadcast_dashboard_status = _broadcast_dashboard_status_proxy

