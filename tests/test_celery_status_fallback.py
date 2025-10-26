import json
from unittest.mock import MagicMock
import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_celery_status_fallback_timeout(client, monkeypatch, settings):
    """Se estatísticas de fila falham por timeout mas ping funciona, deve retornar degraded com available=True."""
    settings.CELERY_STATUS_TIMEOUT = 0.1  # garantir timeout curto

    # Mock ping task result (returns pong quickly)
    class PingResult:
        def get(self, timeout=None):
            return "pong"
    def mock_ping_delay():
        return PingResult()

    # Mock stats task result to raise TimeoutError
    class StatsResult:
        def get(self, timeout=None):
            raise Exception("Simulated timeout")
    def mock_stats_delay():
        return StatsResult()

    # Import alvo
    import core.views_health as vh
    from core import celery as celery_mod

    monkeypatch.setattr(celery_mod, "ping", MagicMock(delay=mock_ping_delay))
    monkeypatch.setattr(celery_mod, "get_queue_stats", MagicMock(delay=mock_stats_delay))

    url = reverse("celery_status")
    resp = client.get(url)
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["worker"]["available"] is True
    assert data["worker"]["stats"] is None
    assert data["worker"]["error"] is not None
