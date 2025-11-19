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
from django.utils import timezone
from django.db import models

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


@shared_task(name="inventory.tasks.update_all_port_optical_levels")
def update_all_port_optical_levels() -> dict[str, Any]:
    """
    Coleta níveis ópticos (RX/TX) para todas as portas com item keys configuradas
    e persiste nos campos "last_*" do modelo Port.

    Objetivo: Eliminar chamadas síncronas ao Zabbix em endpoints REST.
    As APIs passam a ler diretamente do banco (Port.last_rx_power / last_tx_power).
    """
    logger.info("[Optical Levels Task] Iniciando atualização de níveis ópticos")

    # Seleciona apenas portas que possuem ao menos uma key de RX ou TX
    ports_qs = (
        Port.objects.select_related("device")
        .only(
            "id",
            "name",
            "rx_power_item_key",
            "tx_power_item_key",
            "device__zabbix_hostid",
        )
        .filter(
            (
                models.Q(rx_power_item_key__isnull=False)
                & ~models.Q(rx_power_item_key="")
            )
            | (
                models.Q(tx_power_item_key__isnull=False)
                & ~models.Q(tx_power_item_key="")
            )
        )
    )

    total = ports_qs.count()
    updated = 0
    errors: list[str] = []
    now = timezone.now()

    for port in ports_qs.iterator():
        try:
            snapshot = fetch_port_optical_snapshot(port, persist_keys=False)
            rx_dbm = snapshot.get("rx_dbm")
            tx_dbm = snapshot.get("tx_dbm")

            # Apenas atualiza se houve algum valor retornado
            update_fields: list[str] = []
            if rx_dbm is not None:
                port.last_rx_power = rx_dbm
                update_fields.append("last_rx_power")
            if tx_dbm is not None:
                port.last_tx_power = tx_dbm
                update_fields.append("last_tx_power")
            if update_fields:
                port.last_optical_check = now
                update_fields.append("last_optical_check")
                port.save(update_fields=update_fields)
                updated += 1
        except Exception as exc:  # noqa: BLE001
            msg = f"Port {port.id} ({port.name}) falhou: {exc}"
            logger.warning("[Optical Levels Task] %s", msg)
            errors.append(msg)

    result = {
        "success": True,
        "total": total,
        "updated": updated,
        "errors": len(errors),
    }
    logger.info(
        "[Optical Levels Task] Concluído: %d/%d portas atualizadas (%d erros)",
        updated,
        total,
        len(errors),
    )
    return result


@shared_task(name="inventory.tasks.refresh_fiber_list_cache")
def refresh_fiber_list_cache() -> dict[str, Any]:
    """
    Refresh the fiber list cache in background.
    
    This task can be triggered manually or scheduled periodically
    to keep the cache warm.
    
    Returns:
        dict with refresh statistics
    """
    from inventory.cache.fibers import get_cached_fiber_list
    from inventory.usecases import fibers as fiber_uc
    
    logger.info("[Fiber Cache Task] Starting background refresh")
    
    # Force a fresh fetch by calling the function directly
    data, _ = get_cached_fiber_list(fiber_uc.list_fiber_cables)
    
    result = {
        "success": True,
        "cables_count": len(data),
        "refreshed_at": "background_task",
    }
    
    logger.info(
        "[Fiber Cache Task] Cache refreshed: %d cables",
        len(data),
    )
    
    return result


@shared_task(
    name="inventory.tasks.refresh_cables_oper_status",
    bind=True,
    time_limit=300,  # 5 minutes max
)
def refresh_cables_oper_status(self: Any) -> dict[str, Any]:
    """
    Pre-calculate operational status for all fiber cables.
    
    Phase 9.1: Enhanced to persist status in FiberCable model fields
    instead of relying solely on Redis cache.
    
    This task runs periodically to:
    1. Fetch all cables from DB
    2. Query Zabbix for each cable's port status
    3. Store results in FiberCable model (DB-backed)
    4. Store in Redis cache (optional acceleration layer)
    5. Broadcast updates via WebSocket
    
    The API endpoint reads from FiberCable.last_status_* fields
    (database = source of truth, Redis = optional cache).
    
    Returns:
        dict with processing statistics
    """
    from django.core.cache import cache
    from inventory.models import FiberCable
    from inventory.usecases import fibers as fiber_uc
    from maps_view.realtime.publisher import broadcast_cable_status_update
    
    logger.info("[Cable Status Task] Starting background refresh")
    
    start_time = __import__('time').time()
    now = timezone.now()
    
    # Fetch all cables
    cables = FiberCable.objects.select_related(
        "origin_port__device",
        "destination_port__device"
    ).all()
    
    total_count = cables.count()
    success_count = 0
    error_count = 0
    
    # Collect updates for WebSocket broadcast
    cable_updates = []
    
    for cable in cables:
        try:
            # Call the existing function that queries Zabbix
            status_data = fiber_uc.update_cable_oper_status(cable.id)
            
            # PHASE 9.1: Persist in database (source of truth)
            cable.last_status_origin = status_data.get("origin_status", "unknown")
            cable.last_status_dest = status_data.get("destination_status", "unknown")
            cable.last_status_check = now
            cable.save(update_fields=[
                "last_status_origin",
                "last_status_dest",
                "last_status_check",
            ])
            
            # Store in Redis cache (optional acceleration layer)
            cache_key = f"cable:oper_status:{cable.id}"
            cache.set(cache_key, status_data, timeout=120)
            
            # Add to WebSocket broadcast batch
            cable_updates.append(status_data)
            
            success_count += 1
            
        except Exception as exc:
            logger.warning(
                "[Cable Status Task] Failed to process cable %d: %s",
                cable.id,
                exc,
            )
            error_count += 1
    
    # Broadcast all updates via WebSocket (if channel layer configured)
    if cable_updates:
        try:
            broadcast_cable_status_update(cable_updates)
        except Exception as exc:
            logger.warning(
                "[Cable Status Task] Failed to broadcast updates: %s",
                exc,
            )
    
    elapsed = __import__('time').time() - start_time
    
    result = {
        "success": True,
        "total_cables": total_count,
        "processed": success_count,
        "errors": error_count,
        "broadcasted": len(cable_updates),
        "elapsed_seconds": round(elapsed, 2),
    }
    
    logger.info(
        "[Cable Status Task] Completed: %d/%d cables in %.2fs "
        "(%d errors, %d broadcasted)",
        success_count,
        total_count,
        elapsed,
        error_count,
        len(cable_updates),
    )
    
    return result


@shared_task(
    name="inventory.tasks.refresh_fiber_live_status",
    bind=True,
    time_limit=300,  # 5 minutes max
)
def refresh_fiber_live_status(self: Any) -> dict[str, Any]:
    """
    Calculate live status for all fiber cables (Phase 9.1).
    
    Similar to refresh_cables_oper_status but calls compute_live_status
    which performs more advanced status detection including optical power
    checks and interface status validation.
    
    Results are persisted to FiberCable.last_live_status and last_live_check.
    
    Returns:
        dict with processing statistics
    """
    from inventory.models import FiberCable
    from inventory.usecases import fibers as fiber_uc
    
    logger.info("[Live Status Task] Starting background refresh")
    
    start_time = __import__('time').time()
    now = timezone.now()
    
    # Fetch all cables
    cables = FiberCable.objects.select_related(
        "origin_port__device",
        "destination_port__device"
    ).all()
    
    total_count = cables.count()
    success_count = 0
    error_count = 0
    changed_count = 0
    
    for cable in cables:
        try:
            # Compute live status (may update cable.status if changed)
            live_status = fiber_uc.compute_live_status(
                cable,
                persist=True,  # Allow status updates
                event_reason="celery-live-status-refresh",
            )
            
            # PHASE 9.1: Persist live status result in database
            cable.last_live_status = live_status.combined_status
            cable.last_live_check = now
            cable.save(update_fields=["last_live_status", "last_live_check"])
            
            if live_status.changed:
                changed_count += 1
            
            success_count += 1
            
        except Exception as exc:
            logger.warning(
                "[Live Status Task] Failed to process cable %d: %s",
                cable.id,
                exc,
            )
            error_count += 1
    
    elapsed = __import__('time').time() - start_time
    
    result = {
        "success": True,
        "total_cables": total_count,
        "processed": success_count,
        "changed": changed_count,
        "errors": error_count,
        "elapsed_seconds": round(elapsed, 2),
    }
    
    logger.info(
        "[Live Status Task] Completed: %d/%d cables in %.2fs "
        "(%d changed, %d errors)",
        success_count,
        total_count,
        elapsed,
        changed_count,
        error_count,
    )
    
    return result


@shared_task(
    name="inventory.refresh_radius_search_cache",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    queue="maps"
)
def refresh_radius_search_cache(
    self: Any,
    lat: float,
    lng: float,
    radius_km: float,
    limit: int = 100
) -> dict[str, Any]:
    """
    Async task to refresh radius search cache with fresh data from DB.
    
    Queued when cache is stale (30-60s old). Fetches fresh results
    and updates cache to serve subsequent requests quickly.
    
    Args:
        lat: Latitude (WGS84)
        lng: Longitude (WGS84)
        radius_km: Search radius in kilometers
        limit: Maximum number of results
    
    Returns:
        dict with refresh status and statistics
    
    Example:
        from inventory.tasks import refresh_radius_search_cache
        refresh_radius_search_cache.delay(-15.7801, -47.9292, 10, 100)
    """
    from inventory.usecases.spatial import get_sites_within_radius
    from inventory.cache.radius_search import set_cached_radius_search
    
    logger.info(
        "[Refresh Cache Task] Starting for lat=%.6f, lng=%.6f, "
        "r=%dkm, limit=%d",
        lat, lng, radius_km, limit
    )
    
    start_time = __import__('time').time()
    
    try:
        # Fetch fresh data from database
        sites = get_sites_within_radius(lat, lng, radius_km, limit)
        
        # Update cache
        success = set_cached_radius_search(lat, lng, radius_km, limit, sites)
        
        elapsed = __import__('time').time() - start_time
        
        result = {
            "success": success,
            "site_count": len(sites),
            "elapsed_seconds": round(elapsed, 3),
            "cache_updated": success
        }
        
        logger.info(
            "[Refresh Cache Task] Completed: %d sites in %.3fs "
            "(cache_updated=%s)",
            len(sites),
            elapsed,
            success
        )
        
        return result
        
    except Exception as exc:
        logger.error(
            "[Refresh Cache Task] Failed: %s",
            exc.__class__.__name__,
            exc_info=exc
        )
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            logger.info(
                "[Refresh Cache Task] Retrying (attempt %d/%d)",
                self.request.retries + 1,
                self.max_retries
            )
            raise self.retry(exc=exc)
        
        return {
            "success": False,
            "error": str(exc),
            "error_type": exc.__class__.__name__
        }

