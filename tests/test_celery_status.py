"""Smoke tests for the Celery status endpoint."""

from typing import Any


def test_celery_status_endpoint(client: Any) -> None:
    url = "/celery/status"
    resp = client.get(url)
    assert resp.status_code in (200, 503)
    data = resp.json()

    assert "timestamp" in data
    assert "worker" in data
    assert "status" in data
    assert isinstance(data["worker"], dict)
    assert "available" in data["worker"]
    assert "stats" in data["worker"]
    assert data["status"] in ("ok", "degraded")

    stats = data["worker"]["stats"]
    if data["worker"]["available"] and isinstance(stats, dict):
        assert "timestamp" in stats or "error" in stats
