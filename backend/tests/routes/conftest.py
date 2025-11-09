# pyright: reportGeneralTypeIssues=false

"""Fixtures dedicated to the inventory route domain tests."""

from __future__ import annotations

import itertools
import uuid
from typing import Any, Protocol, cast

import pytest

from django.apps import apps
from inventory.models import Device, Port, Site

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


_PORT_COUNTER = itertools.count()
_ROUTE_COUNTER = itertools.count()


class PortFactory(Protocol):
    def __call__(self, *, prefix: str = "port") -> Port:
        """Build and persist a fresh port instance."""
        ...


@pytest.fixture
def port_factory(db: Any) -> PortFactory:
    """Create inventory ports with unique device/site combos."""

    def factory(*, prefix: str = "port") -> Port:
        counter = next(_PORT_COUNTER)
        site = Site.objects.create(name=f"Test Site {uuid.uuid4().hex[:8]}")
        device = Device.objects.create(
            site=site,
            name=f"Test Device {prefix}-{counter}",
        )
        return Port.objects.create(
            device=device,
            name=f"{prefix.upper()}-{counter}",
        )

    return factory


@pytest.fixture
def route(port_factory: PortFactory) -> RouteModel:
    """Persisted route ready for tests."""

    origin = port_factory(prefix="origin")
    destination = port_factory(prefix="destination")
    counter = next(_ROUTE_COUNTER)
    return Route.objects.create(
        name=f"Test Route {counter}",
        origin_port=origin,
        destination_port=destination,
    )


@pytest.fixture
def route_segment(
    route: RouteModel,
    port_factory: PortFactory,
) -> RouteSegmentModel:
    """Persisted segment linked to the base route."""

    return RouteSegment.objects.create(
        route=route,
        order=1,
        from_port=route.origin_port,
        to_port=route.destination_port,
    )


@pytest.fixture
def route_event(route: RouteModel) -> RouteEventModel:
    """Persisted event associated with the base route."""

    return RouteEvent.objects.create(
        route=route,
        event_type=RouteEvent.EVENT_BUILD,
        message="Initial build",
        created_by="tests",
    )
