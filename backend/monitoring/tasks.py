from __future__ import annotations

"""Monitoring Celery tasks for dashboard snapshots and cache refresh."""

import logging
import time
from typing import Any, Dict

from celery import shared_task  # type: ignore[import-not-found]

from monitoring import usecases as monitoring_usecases
from maps_view.cache_swr import dashboard_cache
from maps_view.realtime.publisher import broadcast_dashboard_status

logger = logging.getLogger(__name__)


@shared_task
def broadcast_dashboard_snapshot() -> Dict[str, Any]:
    """Capture the current dashboard snapshot and fan out through Channels."""
    try:
        snapshot = monitoring_usecases.get_hosts_status_data()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Failed to capture dashboard snapshot: %s", exc)
        return {"broadcasted": False, "error": str(exc)}

    if not snapshot:
        return {"broadcasted": False, "reason": "empty_snapshot"}

    broadcasted = broadcast_dashboard_status(snapshot)
    if not broadcasted:
        logger.debug(
            "No channel layer configured; realtime broadcast skipped."
        )

    return {
        "broadcasted": broadcasted,
        "hosts_count": len(snapshot.get("hosts_status", [])),
    }


@shared_task
def refresh_dashboard_cache_task() -> Dict[str, Any]:
    """Refresh the dashboard SWR cache in the background."""
    start = time.time()

    try:
        fresh_data = monitoring_usecases.get_hosts_status_data()
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


__all__ = [
    "broadcast_dashboard_snapshot",
    "refresh_dashboard_cache_task",
]
