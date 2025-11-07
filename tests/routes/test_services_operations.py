# pyright: reportGeneralTypeIssues=false

"""Tests for batch rebuild, JSON import, and cache invalidation services."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping, Protocol, cast

import pytest
from django.apps import apps
from django.core.cache import cache

from inventory import routes as services

RouteModel = RouteEventModel = RouteSegmentModel = Any

Route = cast("type[RouteModel]", apps.get_model("inventory", "Route"))
RouteEvent = cast(
    "type[RouteEventModel]",
    apps.get_model("inventory", "RouteEvent"),
)
RouteSegment = cast(
    "type[RouteSegmentModel]",
    apps.get_model("inventory", "RouteSegment"),
)


class PortFactory(Protocol):
    def __call__(self, *, prefix: str = "port") -> Any:
        ...


@pytest.mark.django_db
def test_rebuild_routes_batch_handles_success_and_failures(
    route: RouteModel,
    port_factory: PortFactory,
) -> None:
    second_route = Route.objects.create(
        name="Batch Route Two",
        origin_port=port_factory(prefix="batch-origin"),
        destination_port=port_factory(prefix="batch-dest"),
    )
    RouteSegment.objects.create(
        route=second_route,
        order=1,
        from_port=second_route.origin_port,
        to_port=second_route.destination_port,
        length_km=Decimal("3.200"),
    )

    contexts: list[services.RouteBuildContext] = [
        services.RouteBuildContext(route_id=route.id),
        services.RouteBuildContext(route_id=second_route.id, force=True),
        services.RouteBuildContext(route_id=999_999),
    ]

    result: services.BatchBuildResult = services.rebuild_routes_batch(contexts)

    assert len(result.processed) == 2
    assert result.failures == (999_999,)

    status_by_route = {
        record.route_id: record.status for record in result.processed
    }
    assert status_by_route[route.id] == Route.STATUS_ACTIVE
    assert status_by_route[second_route.id] == Route.STATUS_ACTIVE

    assert (
        RouteEvent.objects.filter(
            route=route,
            event_type=RouteEvent.EVENT_BUILD,
        ).count()
        == 1
    )
    assert (
        RouteEvent.objects.filter(
            route=second_route,
            event_type=RouteEvent.EVENT_BUILD,
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_import_route_from_payload_creates_full_structure(
    port_factory: PortFactory,
) -> None:
    origin: Any = port_factory(prefix="imp-origin")
    mid: Any = port_factory(prefix="imp-mid")
    destination: Any = port_factory(prefix="imp-dest")

    payload: dict[str, Any] = {
        "name": "Imported Route",
        "description": "Generated via JSON",
        "origin_port_id": origin.id,
        "destination_port_id": destination.id,
        "metadata": {"source": "planner"},
        "segments": [
            {
                "order": 1,
                "from_port_id": origin.id,
                "to_port_id": mid.id,
                "length_km": "1.25",
                "metadata": {"label": "A"},
            },
            {
                "from_port_id": mid.id,
                "to_port_id": destination.id,
                "length_km": "2.75",
            },
        ],
    }

    result: services.RouteBuildResult = services.import_route_from_payload(
        payload, created_by="importer"
    )

    route = Route.objects.get(name="Imported Route")
    route.refresh_from_db()

    assert route.status == Route.STATUS_ACTIVE
    assert route.segments.count() == 2
    assert route.events.filter(event_type=RouteEvent.EVENT_BUILD).count() == 1
    assert route.events.filter(event_type=RouteEvent.EVENT_IMPORT).count() == 1

    orders = list(
        route.segments.order_by("order").values_list("order", flat=True)
    )
    assert orders == [1, 2]
    assert route.length_km == Decimal("4.000")

    route_metadata = cast(dict[str, Any], route.metadata)
    result_metadata = cast(dict[str, Any], result.metadata)

    assert result.events_recorded == 2
    assert result.segments_created == 2
    assert result_metadata["import"]["segments_supplied"] == 2
    assert route_metadata["last_import"]["created_by"] == "importer"
    assert route_metadata["source"] == "planner"


@pytest.mark.django_db
def test_import_route_updates_existing_route(
    route: RouteModel,
    port_factory: PortFactory,
) -> None:
    new_mid: Any = port_factory(prefix="upd-mid")
    new_dest: Any = port_factory(prefix="upd-dest")

    payload: dict[str, Any] = {
        "id": route.id,
        "name": route.name,
        "origin_port_id": route.origin_port_id,
        "destination_port_id": new_dest.id,
        "metadata": {"tag": "updated"},
        "segments": [
            {
                "from_port_id": route.origin_port_id,
                "to_port_id": new_mid.id,
                "length_km": "3.50",
            }
        ],
    }

    result = services.import_route_from_payload(payload, created_by="updater")

    route.refresh_from_db()
    route_metadata = cast(dict[str, Any], route.metadata)
    result_metadata = cast(dict[str, Any], result.metadata)

    assert route.destination_port_id == new_dest.id
    assert route.segments.count() == 1
    assert route_metadata["tag"] == "updated"
    assert route_metadata["last_import"]["segments_supplied"] == 1
    assert result_metadata["import"]["segments_supplied"] == 1
    assert result.segments_created == 1
    assert result.events_recorded == 2


@pytest.mark.django_db
def test_import_route_invalid_port_raises(port_factory: PortFactory) -> None:
    origin: Any = port_factory(prefix="invalid-origin")

    payload: dict[str, Any] = {
        "name": "Invalid Route",
        "origin_port_id": origin.id,
        "destination_port_id": 9_999_999,
    }

    with pytest.raises(services.RouteServiceError):
        services.import_route_from_payload(payload, created_by="tester")


def test_invalidate_route_cache_clears_expected_keys() -> None:
    route_id = 42
    keys = [
        services.CACHE_KEY_ROUTE.format(route_id=route_id),
        services.CACHE_KEY_SEGMENTS.format(route_id=route_id),
        services.CACHE_KEY_EVENTS.format(route_id=route_id),
        services.CACHE_KEY_SUMMARY,
    ]

    for key in keys:
        cache.set(key, "value")

    services.invalidate_route_cache(route_id)

    for key in keys:
        assert cache.get(key) is None


@pytest.mark.django_db
def test_health_summary_includes_recent_events(
    route_event: RouteEventModel,
    route_segment: RouteSegmentModel,
) -> None:
    summary = cast(Mapping[str, Any], services.health_summary())

    assert summary["routes"] >= 1
    assert summary["segments"] >= 1
    assert summary["events"] >= 1
    assert summary["recent_events"], "recent events list should not be empty"

    event_summary = summary["recent_events"][0]
    assert {
        "event_id",
        "route_id",
        "event_type",
        "created_at",
        "route_status",
    } <= set(event_summary)
