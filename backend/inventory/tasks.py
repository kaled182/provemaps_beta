"""
Celery tasks for inventory app.

Background tasks for inventory synchronization and maintenance.
"""
from __future__ import annotations

import logging
from typing import Any, cast

from celery import shared_task  # type: ignore[import-not-found]
from django.core.management import call_command

from inventory.domain import optical as optical_domain
from inventory.models import Port

logger = logging.getLogger(__name__)

fetch_port_optical_snapshot = getattr(
    optical_domain,
    "fetch_port_optical_snapshot",
)


@shared_task(
    name="inventory.sync_zabbix_inventory",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def sync_zabbix_inventory_task(
    self: Any,
    limit: int | None = None,
    host_filter: str | None = None,
    update_only: bool = False
) -> dict[str, Any]:
    """
    Background task to sync Zabbix inventory with local database.

    Args:
        limit: Limit number of hosts to sync
        host_filter: Filter hosts by name pattern
        update_only: Only update existing devices

    Returns:
        dict with sync results and statistics

    Raises:
        Exception: If sync fails (will trigger retry)
    """
    logger.info(
        f"Starting Zabbix inventory sync task "
        f"(limit={limit}, filter={host_filter}, update_only={update_only})"
    )

    try:
        # Call management command programmatically
        command_args = []
        command_kwargs = {}

        if limit:
            command_kwargs["limit"] = limit
        if host_filter:
            command_kwargs["host_filter"] = host_filter
        if update_only:
            command_kwargs["update_only"] = True

        # Capture output
        from io import StringIO
        import sys

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            call_command(
                "sync_zabbix_inventory",
                *command_args,
                **command_kwargs,
            )
            output = captured_output.getvalue()
        finally:
            sys.stdout = old_stdout
        logger.info("Zabbix inventory sync completed successfully")

        return {
            "success": True,
            "output": output,
            "limit": limit,
            "host_filter": host_filter,
            "update_only": update_only,
        }

    except Exception as e:
        logger.exception(f"Zabbix inventory sync failed: {e}")
        # Retry the task
        raise self.retry(exc=e)


@shared_task(name="inventory.cleanup_orphaned_ports")
def cleanup_orphaned_ports_task() -> dict[str, int]:
    """
    Remove ports that reference devices no longer in Zabbix.

    This is a maintenance task that should run periodically.

    Returns:
        dict with cleanup statistics
    """
    from inventory.models import Device, Port

    logger.info("Starting orphaned ports cleanup")

    # Find devices without zabbix_hostid
    orphaned_devices = Device.objects.filter(zabbix_hostid="")
    orphaned_count = orphaned_devices.count()

    if orphaned_count > 0:
        logger.warning(f"Found {orphaned_count} devices without zabbix_hostid")

    # Count ports to be deleted
    ports_to_delete = Port.objects.filter(device__in=orphaned_devices)
    ports_count = ports_to_delete.count()

    if ports_count > 0:
        logger.info(f"Deleting {ports_count} orphaned port(s)")
        ports_to_delete.delete()

    result = {
        "orphaned_devices": orphaned_count,
        "ports_deleted": ports_count,
    }

    logger.info(f"Orphaned ports cleanup completed: {result}")
    return result


@shared_task(name="inventory.tasks.warm_port_optical_cache")
def warm_port_optical_cache(port_id: int) -> None:
    """Refresh the cached optical snapshot for a single port."""
    port = (
        Port.objects.select_related("device")
        .only(
            "id",
            "device_id",
            "device__zabbix_hostid",
            "rx_power_item_key",
            "tx_power_item_key",
        )
        .filter(id=port_id)
        .first()
    )
    if not port:
        return

    fetch_port_optical_snapshot(
        port,
        discovery_cache={},
        persist_keys=False,
    )


@shared_task(name="inventory.tasks.warm_device_ports")
def warm_device_ports(device_id: int) -> None:
    """Warm optical snapshots for every port belonging to a device."""
    ports = (
        Port.objects.select_related("device")
        .only(
            "id",
            "device_id",
            "device__zabbix_hostid",
            "rx_power_item_key",
            "tx_power_item_key",
        )
        .filter(device_id=device_id)
    )
    for port in ports:
        fetch_port_optical_snapshot(
            port,
            discovery_cache={},
            persist_keys=False,
        )


@shared_task(name="inventory.tasks.warm_all_optical_snapshots")
def warm_all_optical_snapshots() -> None:
    """Queue optical cache refresh for every monitored port."""
    port_ids = list(Port.objects.values_list("id", flat=True))
    for port_id in port_ids:
        cast(Any, warm_port_optical_cache).delay(int(port_id))
