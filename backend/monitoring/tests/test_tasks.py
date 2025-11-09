"""Tests for monitoring Celery tasks that power the dashboard cache."""

from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings

from monitoring.tasks import refresh_dashboard_cache_task


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-monitoring-tasks",
        }
    }
)
def test_refresh_dashboard_cache_task_updates_cache():
    """Ensure the SWR cache gets populated on refresh."""
    cache.clear()

    fresh_payload = {
        "hosts_status": [
            {"device_id": 1, "hostid": "101", "available": "1"}
        ],
        "hosts_summary": {"total": 1, "available": 1, "unavailable": 0},
    }

    with patch(
        "monitoring.usecases.get_hosts_status_data", return_value=fresh_payload
    ) as mock_fetch:
        result = refresh_dashboard_cache_task()

    assert mock_fetch.called
    assert result["success"] is True
    assert result["hosts_count"] == 1

    # Cache data is stored under dashboard key (set_cached_data writes payload)
    cached = cache.get("dashboard:hosts_status")
    assert cached == fresh_payload

    timestamp = cache.get("dashboard:hosts_status:timestamp")
    assert isinstance(timestamp, float)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-monitoring-tasks-errors",
        }
    }
)
def test_refresh_dashboard_cache_task_handles_errors():
    """Task should capture exceptions and return error payload."""
    cache.clear()

    with patch(
        "monitoring.usecases.get_hosts_status_data",
        side_effect=RuntimeError("boom"),
    ) as mock_fetch:
        result = refresh_dashboard_cache_task()

    assert mock_fetch.called
    assert result["success"] is False
    assert "error" in result
    assert cache.get("dashboard:hosts_status") is None
