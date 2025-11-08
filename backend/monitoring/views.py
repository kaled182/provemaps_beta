"""Monitoring API views exposing dashboard data for the frontend."""

from __future__ import annotations

import logging
from typing import Any, Dict

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from monitoring.usecases import get_hosts_status_data
from monitoring.tasks import refresh_dashboard_cache_task
from maps_view.cache_swr import get_dashboard_cached

logger = logging.getLogger(__name__)


def _build_cache_metadata(cache_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the SWR metadata payload expected by the dashboard."""
    return {
        "is_stale": cache_result.get("is_stale", False),
        "timestamp": cache_result.get("timestamp"),
        "cache_hit": cache_result.get("cache_hit", False),
    }


@login_required
@require_GET
def api_hosts_status(request: HttpRequest) -> JsonResponse:
    """Return the dashboard hosts status using the SWR cache helper."""
    cache_result = get_dashboard_cached(
        fetch_fn=get_hosts_status_data,
        async_task=refresh_dashboard_cache_task.delay,
    )

    data = cache_result.get("data", {})
    hosts_status = data.get("hosts_status", [])

    if not hosts_status:
        return JsonResponse(
            {"error": "No devices configured with Zabbix"},
            status=404,
        )

    response = {
        "total": data.get("hosts_summary", {}).get("total", 0),
        "hosts": hosts_status,
        "summary": data.get("hosts_summary", {}),
        "cache_metadata": _build_cache_metadata(cache_result),
    }

    return JsonResponse(response)


@login_required
@require_GET
def api_dashboard_snapshot(request: HttpRequest) -> JsonResponse:
    """Return a snapshot of hosts status without engaging the SWR cache."""
    try:
        snapshot = get_hosts_status_data()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Failed to build dashboard snapshot: %s", exc)
        return JsonResponse(
            {"error": "Unable to fetch monitoring data"},
            status=500,
        )

    if not snapshot.get("hosts_status"):
        return JsonResponse(
            {"error": "No devices configured with Zabbix"},
            status=404,
        )

    return JsonResponse(snapshot)


__all__ = ["api_hosts_status", "api_dashboard_snapshot"]
