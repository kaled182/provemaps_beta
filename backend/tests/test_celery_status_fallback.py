from typing import Any, Optional
from unittest.mock import MagicMock

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_celery_status_fallback_timeout(
    client: Any,
    monkeypatch: Any,
    settings: Any,
) -> None:
    """If stats timeout but ping works, the fallback reports degraded."""
    settings.CELERY_STATUS_TIMEOUT = 0.1  # ensure a short timeout

    # Mock ping task result (returns pong quickly)
    class PingResult:
        def get(self, timeout: Optional[float] = None) -> str:
            return "pong"

    def mock_ping_delay() -> PingResult:
        return PingResult()

    # Mock stats task result to raise TimeoutError
    class StatsResult:
        def get(self, timeout: Optional[float] = None) -> None:
            raise Exception("Simulated timeout")

    def mock_stats_delay() -> StatsResult:
        return StatsResult()

    # Import target modules lazily
    from core import celery as celery_mod

    monkeypatch.setattr(
        celery_mod,
        "ping",
        MagicMock(delay=mock_ping_delay),
    )
    monkeypatch.setattr(
        celery_mod,
        "get_queue_stats",
        MagicMock(delay=mock_stats_delay),
    )

    url = reverse("celery_status")
    resp = client.get(url)
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["worker"]["available"] is True
    assert data["worker"]["stats"] is None
    assert data["worker"]["error"] is not None
