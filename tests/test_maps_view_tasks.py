"""Compatibility tests ensuring maps_view.tasks shims remain intact."""

from monitoring.tasks import (
    broadcast_dashboard_snapshot as monitoring_broadcast_task,
    refresh_dashboard_cache_task as monitoring_refresh_task,
)
from monitoring.usecases import (
    get_hosts_status_data as monitoring_hosts_status,
)

from maps_view.tasks import (
    broadcast_dashboard_snapshot as maps_broadcast_task,
    get_hosts_status_data as maps_get_hosts_status,
    refresh_dashboard_cache_task as maps_refresh_task,
)


def test_maps_view_tasks_reexport_monitoring_tasks():
    """maps_view.tasks should re-export the monitoring Celery tasks."""

    assert maps_refresh_task is monitoring_refresh_task
    assert maps_broadcast_task is monitoring_broadcast_task


def test_maps_view_get_hosts_status_data_alias():
    """get_hosts_status_data remains available for legacy callers."""

    assert maps_get_hosts_status is monitoring_hosts_status
