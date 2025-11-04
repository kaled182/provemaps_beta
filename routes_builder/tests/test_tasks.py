"""Tests for Celery tasks integrating with the routes_builder services."""

from __future__ import annotations

from typing import Any, Iterable, cast

import pytest

from routes_builder import services
from routes_builder.models import Route
from routes_builder.tasks import (
    build_route,
    build_routes_batch,
    health_check_routes_builder,
    import_route_from_payload,
    invalidate_route_cache,
)


@pytest.mark.django_db
def test_build_route_task_success(monkeypatch: Any, route: Route) -> None:
    metadata: dict[str, Any] = {"segment_count": 0}

    captured_context: dict[str, Any] = {}

    def fake_rebuild(
        context: services.RouteBuildContext,
    ) -> services.RouteBuildResult:
        captured_context["context"] = context
        return services.RouteBuildResult(
            route_id=route.id,
            status=services.Route.STATUS_ACTIVE,
            segments_created=0,
            events_recorded=1,
            metadata=metadata,
        )

    monkeypatch.setattr(services, "rebuild_route", fake_rebuild)

    result = cast(Any, build_route).run(
        route_id=route.id,
        force=True,
        options={"initiator": "tests"},
    )

    context = captured_context["context"]
    assert context.route_id == route.id
    assert context.force is True
    assert context.options["initiator"] == "tests"

    assert result == {
        "status": "success",
        "route_id": route.id,
        "route_status": services.Route.STATUS_ACTIVE,
        "segments_created": 0,
        "events_recorded": 1,
        "metadata": metadata,
    }


@pytest.mark.django_db
def test_build_route_task_handles_service_error(monkeypatch: Any) -> None:
    def fake_rebuild(
        context: services.RouteBuildContext,
    ) -> services.RouteBuildResult:
        # context used implicitly to match signature
        raise services.RouteServiceError("route missing")

    monkeypatch.setattr(services, "rebuild_route", fake_rebuild)

    result = cast(Any, build_route).run(route_id=999)

    assert result["status"] == "error"
    assert result["route_id"] == 999
    assert "route missing" in result["message"]


@pytest.mark.django_db
def test_build_routes_batch_task(monkeypatch: Any, route: Route) -> None:
    second_result = services.RouteBuildResult(
        route_id=route.id + 1,
        status=services.Route.STATUS_ACTIVE,
        segments_created=2,
        events_recorded=1,
        metadata={"segment_count": 2},
    )
    first_result = services.RouteBuildResult(
        route_id=route.id,
        status=services.Route.STATUS_ACTIVE,
        segments_created=1,
        events_recorded=1,
        metadata={"segment_count": 1},
    )

    captured_contexts: dict[str, Any] = {}

    def fake_batch(
        contexts: Iterable[services.RouteBuildContext],
    ) -> services.BatchBuildResult:
        contexts_list = list(contexts)
        captured_contexts["contexts"] = contexts_list
        return services.BatchBuildResult(
            processed=(first_result, second_result),
            failures=(42,),
        )

    monkeypatch.setattr(services, "rebuild_routes_batch", fake_batch)

    result = cast(Any, build_routes_batch).run(
        route_ids=[route.id, route.id + 1],
        force=True,
        options={"initiator": "tests"},
    )

    contexts = captured_contexts["contexts"]
    assert [ctx.route_id for ctx in contexts] == [route.id, route.id + 1]
    assert all(ctx.force for ctx in contexts)
    assert all(ctx.options["initiator"] == "tests" for ctx in contexts)

    assert result["status"] == "success"
    assert len(result["processed"]) == 2
    assert result["failures"] == [42]


@pytest.mark.django_db
def test_import_route_task_success(monkeypatch: Any, route: Route) -> None:
    payload: dict[str, Any] = {"id": route.id, "name": route.name}
    metadata: dict[str, Any] = {"segment_count": 1}

    def fake_import(
        data: dict[str, Any], *, created_by: str
    ) -> services.RouteBuildResult:
        assert data is payload
        assert created_by == "tests"
        return services.RouteBuildResult(
            route_id=route.id,
            status=services.Route.STATUS_ACTIVE,
            segments_created=1,
            events_recorded=2,
            metadata=metadata,
        )

    monkeypatch.setattr(services, "import_route_from_payload", fake_import)

    result = cast(Any, import_route_from_payload).run(
        payload, created_by="tests"
    )

    assert result["status"] == "success"
    assert result["route_id"] == route.id
    assert result["segments_created"] == 1
    assert result["metadata"] == metadata


@pytest.mark.django_db
def test_import_route_task_error(monkeypatch: Any) -> None:
    def fake_import(
        payload: dict[str, Any], *, created_by: str
    ) -> services.RouteBuildResult:
        # For coverage depth we just simulate the error path
        raise services.RouteServiceError("invalid payload")

    monkeypatch.setattr(services, "import_route_from_payload", fake_import)

    result = cast(Any, import_route_from_payload).run({"name": "fail"})

    assert result["status"] == "error"
    assert "invalid payload" in result["message"]


def test_invalidate_route_cache_task(monkeypatch: Any) -> None:
    called: dict[str, Any] = {}

    def fake_invalidate(route_id: int) -> None:
        called["route_id"] = route_id

    monkeypatch.setattr(services, "invalidate_route_cache", fake_invalidate)

    result = cast(Any, invalidate_route_cache).run(77)

    assert called["route_id"] == 77
    assert result == {"status": "success", "route_id": 77}


@pytest.mark.django_db
def test_health_check_task(monkeypatch: Any) -> None:
    summary: dict[str, Any] = {
        "routes": 1,
        "segments": 2,
        "events": 3,
        "recent_events": [],
    }

    def fake_summary() -> dict[str, Any]:
        return summary

    monkeypatch.setattr(services, "health_summary", fake_summary)

    result = cast(Any, health_check_routes_builder).run()

    assert result == {"status": "success", "summary": summary}
