from __future__ import annotations

import logging
from typing import Dict, Any

from celery import shared_task

from maps_view.realtime.publisher import broadcast_dashboard_status
from maps_view.services import get_hosts_status_data

logger = logging.getLogger(__name__)


@shared_task
def broadcast_dashboard_snapshot() -> Dict[str, Any]:
    """
    Celery task that captures the current dashboard snapshot and pushes it to
    the realtime channel layer. Returns a small summary for logging/inspection.
    """
    try:
        snapshot = get_hosts_status_data()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Failed to capture dashboard snapshot: %s", exc)
        return {"broadcasted": False, "error": str(exc)}

    if not snapshot:
        return {"broadcasted": False, "reason": "empty_snapshot"}

    broadcasted = broadcast_dashboard_status(snapshot)
    if not broadcasted:
        logger.debug("No channel layer configured; realtime broadcast skipped.")

    return {
        "broadcasted": broadcasted,
        "hosts_count": len(snapshot.get("hosts_status", [])),
    }


@shared_task
def refresh_dashboard_cache_task() -> Dict[str, Any]:
    """
    Celery task para refresh de cache SWR do dashboard em background.
    
    Esta task é disparada automaticamente quando dados stale são servidos,
    garantindo que o próximo request terá dados frescos.
    
    Returns:
        Dict com status do refresh (success, hosts_count, duration)
    """
    import time
    from maps_view.cache_swr import dashboard_cache

    start = time.time()
    
    try:
        # Busca dados frescos (sem usar cache)
        fresh_data = get_hosts_status_data()
        
        # Atualiza cache
        dashboard_cache.set_cached_data(fresh_data)
        
        duration = time.time() - start
        hosts_count = len(fresh_data.get("hosts_status", []))
        
        logger.info(
            "Dashboard cache refreshed successfully: %d hosts, %.2fs",
            hosts_count,
            duration,
        )
        
        return {
            "success": True,
            "hosts_count": hosts_count,
            "duration_seconds": round(duration, 3),
        }
        
    except Exception as exc:
        duration = time.time() - start
        logger.exception("Failed to refresh dashboard cache: %s", exc)
        return {
            "success": False,
            "error": str(exc),
            "duration_seconds": round(duration, 3),
        }

