import json
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from django.urls import reverse


@pytest.fixture
def staff_client(client: Any, admin_user: Any) -> Any:
    client.force_login(admin_user)
    return client


@pytest.fixture(autouse=True)
def patch_celery(monkeypatch: Any) -> Iterator[None]:
    """Prevent Celery from trying to enqueue real tasks during tests."""
    fake_result = SimpleNamespace(id="fake-task-id", queue="maps")

    def fake_async(*args: Any, **kwargs: Any) -> SimpleNamespace:
        return fake_result

    monkeypatch.setattr(
        "inventory.api.routes.apply_async",
        fake_async,
        raising=False,
    )
    yield


def _bulk_payload(
    route_id: int = 101,
    *,
    action: str = "build",
) -> Dict[str, List[Dict[str, Any]]]:
    return {
        "operations": [
            {
                "action": action,
                "route_id": route_id,
                "force": False,
                "options": {},
            },
        ]
    }


def test_enqueue_bulk_operations_rate_limit(staff_client: Any) -> None:
    """After 10 requests in the window, the endpoint must return HTTP 429."""
    url = reverse("inventory-api:routes-bulk")
    body = json.dumps(_bulk_payload())

    for _ in range(10):
        response = staff_client.post(
            url,
            data=body,
            content_type="application/json",
        )
        assert response.status_code == 202

    # 11th request should be blocked by the limiter
    response = staff_client.post(
        url,
        data=body,
        content_type="application/json",
    )
    assert response.status_code == 429
    assert response.json()["error"] == "Rate limit exceeded"


def test_enqueue_bulk_operations_mixed_actions(staff_client: Any) -> None:
    """Ensure build/invalidate actions are queued and reported correctly."""
    url = reverse("inventory-api:routes-bulk")
    body = json.dumps(
        {
            "operations": [
                {
                    "action": "build",
                    "route_id": 200,
                    "force": True,
                    "options": {"foo": "bar"},
                },
                {"action": "invalidate", "route_id": 200},
                {
                    "action": "import",
                    "payload": {
                        "name": "Route X",
                        "origin_port_id": 1,
                        "destination_port_id": 2,
                    },
                    "created_by": "tester",
                },
                {"action": "unknown", "route_id": 200},
            ]
        }
    )

    response = staff_client.post(
        url,
        data=body,
        content_type="application/json",
    )
    assert response.status_code == 202
    payload = response.json()

    assert payload["status"] == "bulk_enqueued"
    assert payload["operations"] == 4
    results = {entry["action"]: entry for entry in payload["results"]}
    assert results["build"]["status"] == "enqueued"
    assert results["invalidate"]["status"] == "enqueued"
    assert results["import"]["status"] == "enqueued"
    assert results["unknown"]["status"] == "skipped"
    assert "task_id" in results["build"]
    assert "task_id" in results["invalidate"]
    assert "task_id" in results["import"]


def test_enqueue_import_route_requires_payload(staff_client: Any) -> None:
    url = reverse("inventory-api:routes-import")
    response = staff_client.post(
        url,
        data="{}",
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.content


def test_enqueue_import_route_success(staff_client: Any) -> None:
    url = reverse("inventory-api:routes-import")
    body = json.dumps(
        {
            "payload": {
                "name": "New Route",
                "origin_port_id": 1,
                "destination_port_id": 2,
            },
            "created_by": "tests",
        }
    )

    response = staff_client.post(
        url,
        data=body,
        content_type="application/json",
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "enqueued"
    assert data["task"] == "inventory.routes.import_route_from_payload"
    assert data["created_by"] == "tests"
