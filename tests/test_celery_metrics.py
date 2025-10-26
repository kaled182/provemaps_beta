import time
from typing import Any, Dict


class DummyGauge:
    def __init__(self) -> None:
        self.value: Any = None

    def set(self, v: Any) -> None:  # noqa: D401 - método simples
        self.value = v


def test_update_metrics_gauges(monkeypatch: Any) -> None:
    """Valida que update_metrics atualiza todos os gauges com payload válido.

    Usa dummies para evitar dependências de estado global do prometheus_client.
    """
    from core import metrics_celery as mc

    # Força habilitação, substitui gauges por dummies
    monkeypatch.setattr(mc, "METRICS_ENABLED", True)
    g_available = DummyGauge()
    g_latency = DummyGauge()
    g_active = DummyGauge()
    g_sched = DummyGauge()
    g_reserved = DummyGauge()
    g_workers = DummyGauge()

    monkeypatch.setattr(
        mc, "CELERY_WORKER_AVAILABLE", g_available, raising=False
    )
    monkeypatch.setattr(
        mc, "CELERY_STATUS_LATENCY_MS", g_latency, raising=False
    )
    monkeypatch.setattr(mc, "CELERY_ACTIVE_TASKS", g_active, raising=False)
    monkeypatch.setattr(mc, "CELERY_SCHEDULED_TASKS", g_sched, raising=False)
    monkeypatch.setattr(mc, "CELERY_RESERVED_TASKS", g_reserved, raising=False)
    monkeypatch.setattr(mc, "CELERY_WORKER_COUNT", g_workers, raising=False)

    payload: Dict[str, Any] = {
        "latency_ms": 123.45,
        "worker": {
            "available": True,
            "stats": {
                "workers": ["celery@test-host"],
                "active_tasks": {"celery@test-host": ["t1", "t2"]},
                "scheduled_tasks": {"celery@test-host": ["s1"]},
                "reserved_tasks": {"celery@test-host": []},
                "timestamp": time.time(),
            },
        },
    }

    mc.update_metrics(payload)

    assert g_available.value == 1
    assert g_latency.value == 123.45
    assert g_workers.value == 1
    assert g_active.value == 2
    assert g_sched.value == 1
    assert g_reserved.value == 0


def test_update_metrics_disabled(monkeypatch: Any) -> None:
    """Se METRICS_ENABLED=False, não deve lançar e gauges permanecem None."""
    from core import metrics_celery as mc

    monkeypatch.setattr(mc, "METRICS_ENABLED", False)
    g_available = DummyGauge()
    monkeypatch.setattr(
        mc, "CELERY_WORKER_AVAILABLE", g_available, raising=False
    )

    payload: Dict[str, Any] = {
        "latency_ms": 10,
        "worker": {"available": True, "stats": None},
    }
    mc.update_metrics(payload)

    # Não atualizado porque métricas desabilitadas
    assert g_available.value is None
