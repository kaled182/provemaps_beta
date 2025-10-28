import json
from types import SimpleNamespace

import pytest
from django.urls import reverse


@pytest.fixture
def staff_client(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture(autouse=True)
def patch_celery(monkeypatch):
    """Prevent Celery from trying to enqueue real tasks during tests."""
    fake_result = SimpleNamespace(id="fake-task-id", queue="maps")

    def fake_async(*args, **kwargs):
        return fake_result

    monkeypatch.setattr(
        "routes_builder.views_tasks.build_route.apply_async", fake_async, raising=False
    )
    monkeypatch.setattr(
        "routes_builder.views_tasks.invalidate_route_cache.apply_async",
        fake_async,
        raising=False,
    )
    monkeypatch.setattr(
        "routes_builder.views_tasks.build_routes_batch.apply_async",
        fake_async,
        raising=False,
    )
    monkeypatch.setattr(
        "routes_builder.views_tasks.health_check_routes_builder.apply_async",
        fake_async,
        raising=False,
    )
    yield


def _bulk_payload(route_id=101, *, action="build"):
    return {
        "operations": [
            {"action": action, "route_id": route_id, "force": False, "options": {}},
        ]
    }


def test_enqueue_bulk_operations_rate_limit(staff_client):
    """After 10 requests in the window, the endpoint must return HTTP 429."""
    url = reverse("routes_builder:tasks:enqueue_bulk_operations")
    body = json.dumps(_bulk_payload())

    for _ in range(10):
        response = staff_client.post(url, data=body, content_type="application/json")
        assert response.status_code == 202

    # 11th request should be blocked by the limiter
    response = staff_client.post(url, data=body, content_type="application/json")
    assert response.status_code == 429
    assert response.json()["error"] == "Rate limit exceeded"


def test_enqueue_bulk_operations_mixed_actions(staff_client):
    """Ensure build/invalidate actions are queued and reported correctly."""
    url = reverse("routes_builder:tasks:enqueue_bulk_operations")
    body = json.dumps(
        {
            "operations": [
                {"action": "build", "route_id": 200, "force": True, "options": {"foo": "bar"}},
                {"action": "invalidate", "route_id": 200},
                {"action": "unknown", "route_id": 200},
            ]
        }
    )

    response = staff_client.post(url, data=body, content_type="application/json")
    assert response.status_code == 202
    payload = response.json()

    assert payload["status"] == "bulk_enqueued"
    assert payload["operations"] == 3
    results = {entry["action"]: entry for entry in payload["results"]}
    assert results["build"]["status"] == "enqueued"
    assert results["invalidate"]["status"] == "enqueued"
    assert results["unknown"]["status"] == "skipped"
    assert "task_id" in results["build"]
    assert "task_id" in results["invalidate"]
