"""Unit tests for routes_builder domain models."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from routes_builder.models import Route, RouteSegment


@pytest.mark.django_db
def test_route_unique_name_constraint(route, port_factory):
    """Routes should enforce unique names across the table."""

    new_origin = port_factory(prefix="origin-dup")
    new_destination = port_factory(prefix="destination-dup")

    with pytest.raises(IntegrityError):
        Route.objects.create(
            name=route.name,
            origin_port=new_origin,
            destination_port=new_destination,
        )


@pytest.mark.django_db
def test_route_update_status_persists_and_falls_back(route):
    """update_status persists valid values and falls back for unknown ones."""

    route.update_status(Route.STATUS_ACTIVE)
    route.refresh_from_db()
    assert route.status == Route.STATUS_ACTIVE

    route.update_status("unknown-status")
    route.refresh_from_db()
    assert route.status == Route.STATUS_DEGRADED


@pytest.mark.django_db
def test_route_update_status_without_save(route):
    """update_status(save=False) mutates in-memory state only."""

    route.update_status(Route.STATUS_ACTIVE, save=False)
    assert route.status == Route.STATUS_ACTIVE

    route.refresh_from_db()
    assert route.status == Route.STATUS_PLANNED


@pytest.mark.django_db
def test_route_clean_rejects_identical_ports(port_factory):
    """Route validation prevents using the same port twice."""

    port = port_factory(prefix="loop")
    candidate = Route(
        name="Loop Route",
        origin_port=port,
        destination_port=port,
    )

    with pytest.raises(ValidationError) as exc:
        candidate.full_clean()

    assert "destination_port" in exc.value.error_dict


@pytest.mark.django_db
def test_route_segment_unique_order(route, port_factory):
    """Each route must keep segment ordering unique."""

    RouteSegment.objects.create(
        route=route,
        order=1,
        from_port=route.origin_port,
        to_port=route.destination_port,
    )

    with pytest.raises(IntegrityError):
        RouteSegment.objects.create(
            route=route,
            order=1,
            from_port=port_factory(prefix="alt-origin"),
            to_port=port_factory(prefix="alt-destination"),
        )


@pytest.mark.django_db
def test_route_segment_clean_rejects_same_endpoints(route):
    """Segment validation rejects same from/to port combinations."""

    segment = RouteSegment(
        route=route,
        order=2,
        from_port=route.origin_port,
        to_port=route.origin_port,
    )

    with pytest.raises(ValidationError) as exc:
        segment.full_clean()

    assert "to_port" in exc.value.error_dict


@pytest.mark.django_db
def test_route_event_fixture_persists(route_event):
    """RouteEvent fixture should be properly persisted."""

    event = route_event
    assert event.pk is not None
    assert str(event).startswith(event.route.name)
    assert event.route.events.count() == 1
