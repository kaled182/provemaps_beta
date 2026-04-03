# pyright: reportGeneralTypeIssues=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

import json
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from django.core.cache import cache
from django.urls import reverse

from inventory.api import routes as routes_api
from inventory.routes.tasks import (
    build_route as task_build_route,
    import_route_from_payload as task_import_route_from_payload,
    invalidate_route_cache as task_invalidate_route_cache,
)


@pytest.fixture(autouse=True)
def clear_cache() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def staff_client(client: Any, admin_user: Any) -> Any:
    client.force_login(admin_user)
    return client


@pytest.fixture
def capture_apply_async(monkeypatch: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_apply_async(
        task: Any,
        *,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> SimpleNamespace:
        entry = {
            "task": task,
            "args": list(args or []),
            "kwargs": dict(kwargs or {}),
        }
        calls.append(entry)
        return SimpleNamespace(
            id=f"fake-task-{len(calls)}",
            queue="maps",
        )

    monkeypatch.setattr(routes_api, "apply_async", fake_apply_async)
    return calls


@pytest.mark.django_db
def test_enqueue_build_route_success(
    staff_client: Any,
    capture_apply_async: list[dict[str, Any]],
) -> None:
    url = reverse("inventory-api:routes-build")
    body = json.dumps(
        {
            "route_id": 42,
            "force": True,
            "options": {"initiator": "tests"},
        }
    )

    response = staff_client.post(
        url,
        data=body,
        content_type="application/json",
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "enqueued"
    assert payload["task"] == "inventory.routes.build_route"
    assert payload["route_id"] == 42
    assert capture_apply_async[0]["task"] is task_build_route
    assert capture_apply_async[0]["args"] == [42]
    assert capture_apply_async[0]["kwargs"] == {
        "force": True,
        "options": {"initiator": "tests"},
    }


@pytest.mark.django_db
def test_enqueue_build_route_requires_positive_route_id(
    staff_client: Any,
) -> None:
    url = reverse("inventory-api:routes-build")
    response = staff_client.post(
        url,
        data="{}",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.content


@pytest.mark.django_db
def test_enqueue_bulk_operations_mixed_actions(
    staff_client: Any,
    capture_apply_async: list[dict[str, Any]],
) -> None:
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
                {"action": "unknown", "route_id": 999},
            ]
        }
    )

    response = staff_client.post(
        url,
        data=body,
        content_type="application/json",
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "bulk_enqueued"
    assert data["operations"] == 4

    results = {entry["action"]: entry for entry in data["results"]}
    assert results["build"]["status"] == "enqueued"
    assert results["invalidate"]["status"] == "enqueued"
    assert results["import"]["status"] == "enqueued"
    assert results["unknown"]["status"] == "skipped"

    assert capture_apply_async[0]["task"] is task_build_route
    assert capture_apply_async[1]["task"] is task_invalidate_route_cache
    assert capture_apply_async[2]["task"] is task_import_route_from_payload


@pytest.mark.django_db
def test_enqueue_bulk_operations_rate_limit(
    staff_client: Any,
    monkeypatch: Any,
) -> None:
    url = reverse("inventory-api:routes-bulk")
    body = json.dumps(
        {
            "operations": [
                {
                    "action": "build",
                    "route_id": 301,
                }
            ]
        }
    )

    fake_result = SimpleNamespace(id="fake", queue="maps")

    def fake_apply_async(*_: Any, **__: Any) -> SimpleNamespace:
        return fake_result

    monkeypatch.setattr(routes_api, "apply_async", fake_apply_async)

    for _ in range(10):
        response = staff_client.post(
            url,
            data=body,
            content_type="application/json",
        )
        assert response.status_code == 202

    response = staff_client.post(
        url,
        data=body,
        content_type="application/json",
    )
    assert response.status_code == 429
    assert response.json()["error"] == "Rate limit exceeded"


@pytest.mark.django_db
def test_task_status_reports_success(
    staff_client: Any,
    monkeypatch: Any,
) -> None:
    class FakeAsyncResult:
        status = "SUCCESS"

        def ready(self) -> bool:
            return True

        def successful(self) -> bool:
            return True

        @property
        def result(self) -> dict[str, Any]:
            return {"ok": True}

        @property
        def traceback(self) -> None:
            return None

    def fake_async_result(_: str) -> FakeAsyncResult:
        return FakeAsyncResult()

    monkeypatch.setattr(routes_api, "AsyncResult", fake_async_result)

    url = reverse(
        "inventory-api:routes-task-status",
        kwargs={"task_id_value": "abc-123"},
    )
    response = staff_client.get(url)

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "abc-123"
    assert payload["status"] == "SUCCESS"
    assert payload["ready"] is True
    assert payload["result"] == {"ok": True}


@pytest.mark.django_db
def test_task_status_reports_failure(
    staff_client: Any,
    monkeypatch: Any,
) -> None:
    class FakeFailureResult:
        status = "FAILURE"

        def __init__(self) -> None:
            self._result = RuntimeError("boom")
            self.traceback = "trace"

        def ready(self) -> bool:
            return True

        def successful(self) -> bool:
            return False

        @property
        def result(self) -> RuntimeError:
            return self._result

    def fake_failure_result(_: str) -> FakeFailureResult:
        return FakeFailureResult()

    monkeypatch.setattr(routes_api, "AsyncResult", fake_failure_result)

    url = reverse(
        "inventory-api:routes-task-status",
        kwargs={"task_id_value": "task-err"},
    )
    response = staff_client.get(url)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILURE"
    assert payload["error"] == "boom"
    assert payload["traceback"] == "trace"


@pytest.mark.django_db
def test_enqueue_build_route_ip_safelist_denies(
    staff_client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("ADMIN_IP_SAFELIST", "10.0.0.0/24")

    url = reverse("inventory-api:routes-build")
    response = staff_client.post(
        url,
        data=json.dumps({"route_id": 10}),
        content_type="application/json",
        REMOTE_ADDR="192.168.0.5",
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden by IP safelist"
