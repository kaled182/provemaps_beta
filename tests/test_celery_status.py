import os

# Ativa modo eager para tentar execução imediata (se possível)
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")


def test_celery_status_endpoint(client):
    url = "/celery/status"
    resp = client.get(url)
    # Aceita 200 (ok) ou 503 (degraded) dependendo da presença de worker
    assert resp.status_code in (200, 503)
    data = resp.json()
    # Estrutura mínima
    assert "timestamp" in data
    assert "worker" in data
    assert "status" in data
    assert isinstance(data["worker"], dict)
    # Campos esperados dentro de worker
    assert "available" in data["worker"]
    assert "stats" in data["worker"]
    # status coerente
    assert data["status"] in ("ok", "degraded")

    # Se disponível e sem erro interno, stats deve ser dict
    stats = data["worker"]["stats"]
    if data["worker"]["available"] and isinstance(stats, dict):
        assert "timestamp" in stats or "error" in stats
