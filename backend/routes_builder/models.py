# """Domain models for the routes_builder application."""

"""Shims exposing route models from the inventory app."""

from importlib import import_module
from typing import Any

_routes = import_module("inventory.models_routes")

Route: Any = getattr(_routes, "Route")
RouteEvent: Any = getattr(_routes, "RouteEvent")
RouteSegment: Any = getattr(_routes, "RouteSegment")

__all__ = ["Route", "RouteEvent", "RouteSegment"]
