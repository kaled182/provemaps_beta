"""Tests covering the rebuild_route service implementation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol, cast

import pytest

from routes_builder import services
from routes_builder.models import Route, RouteEvent, RouteSegment


class PortFactory(Protocol):
    def __call__(self, *, prefix: str = "port") -> Any:
        ...


@pytest.mark.django_db
def test_rebuild_route_updates_state_and_metadata(
    route: Route,
    port_factory: PortFactory,
) -> None:
    primary_segment = RouteSegment.objects.create(
        route=route,
        order=5,
        from_port=route.origin_port,
        to_port=port_factory(prefix="mid"),
        length_km=Decimal("1.500"),
    )

    second_segment = RouteSegment.objects.create(
        route=route,
        order=8,
        from_port=primary_segment.to_port,
        to_port=route.destination_port,
        length_km=Decimal("2.500"),
    )

    context = services.RouteBuildContext(
        route_id=route.id,
        force=True,
        options={"initiator": "unit-tests"},
    )
    result: services.RouteBuildResult = services.rebuild_route(context)

    route.refresh_from_db()
    primary_segment.refresh_from_db()
    second_segment.refresh_from_db()

    assert result.route_id == route.id
    assert result.status == Route.STATUS_ACTIVE
    assert result.segments_created == 2
    assert result.events_recorded == 1

    metadata_container = cast(dict[str, Any], route.metadata)
    metadata = cast(dict[str, Any], metadata_container["last_build"])
    assert metadata == result.metadata
    assert metadata["segment_count"] == 2
    assert metadata["force"] is True
    assert metadata["options"]["initiator"] == "unit-tests"
    assert metadata["reindexed_segments"] == 2
    assert abs(float(metadata["total_length_km"]) - 4.0) < 1e-6

    assert route.length_km == Decimal("4.000")
    orders = list(
        route.segments.order_by("order").values_list("order", flat=True)
    )
    assert orders == [1, 2]

    assert route.events.count() == 1
    event = route.events.first()
    assert event is not None
    assert event.event_type == RouteEvent.EVENT_BUILD
    assert event.created_by == "unit-tests"
    event_details = cast(dict[str, Any], event.details)
    assert set(event_details["segment_ids"]) == {
        primary_segment.id,
        second_segment.id,
    }


@pytest.mark.django_db
def test_rebuild_route_without_segments(port_factory: PortFactory) -> None:
    origin: Any = port_factory(prefix="solo-origin")
    destination: Any = port_factory(prefix="solo-destination")
    route = Route.objects.create(
        name="Orphan Route",
        origin_port=origin,
        destination_port=destination,
    )

    result: services.RouteBuildResult = services.rebuild_route(
        services.RouteBuildContext(route_id=route.id)
    )

    route.refresh_from_db()
    assert result.segments_created == 0
    assert route.length_km is None
    metadata_container = cast(dict[str, Any], route.metadata)
    last_build = cast(dict[str, Any], metadata_container["last_build"])
    assert last_build["segment_count"] == 0
    assert route.events.count() == 1
    event = route.events.first()
    assert event is not None
    event_details = cast(dict[str, Any], event.details)
    assert event_details["segment_ids"] == []


@pytest.mark.django_db
def test_rebuild_route_missing_route_raises() -> None:
    context = services.RouteBuildContext(route_id=999_999)
    with pytest.raises(services.RouteServiceError):
        services.rebuild_route(context)
