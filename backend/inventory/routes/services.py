"""Service layer contracts for the inventory routes domain."""

from __future__ import annotations

from functools import wraps
from typing import Iterable, Mapping

from routes_builder import services as legacy_services


RouteBuildContext = legacy_services.RouteBuildContext
RouteBuildResult = legacy_services.RouteBuildResult
BatchBuildResult = legacy_services.BatchBuildResult
RouteImportPayload = legacy_services.RouteImportPayload
RouteServiceError = legacy_services.RouteServiceError
SegmentPayload = legacy_services.SegmentPayload
CACHE_KEY_ROUTE = legacy_services.CACHE_KEY_ROUTE
CACHE_KEY_SEGMENTS = legacy_services.CACHE_KEY_SEGMENTS
CACHE_KEY_EVENTS = legacy_services.CACHE_KEY_EVENTS
CACHE_KEY_SUMMARY = legacy_services.CACHE_KEY_SUMMARY


@wraps(legacy_services.rebuild_route)
def rebuild_route(
    context: legacy_services.RouteBuildContext,
) -> legacy_services.RouteBuildResult:
    return legacy_services.rebuild_route(context)


@wraps(legacy_services.rebuild_routes_batch)
def rebuild_routes_batch(
    contexts: Iterable[legacy_services.RouteBuildContext],
) -> legacy_services.BatchBuildResult:
    return legacy_services.rebuild_routes_batch(contexts)


@wraps(legacy_services.invalidate_route_cache)
def invalidate_route_cache(route_id: int) -> None:
    legacy_services.invalidate_route_cache(route_id)


@wraps(legacy_services.import_route_from_payload)
def import_route_from_payload(
    payload: Mapping[str, object] | legacy_services.RouteImportPayload,
    *,
    created_by: str = "routes_builder.task",
) -> legacy_services.RouteBuildResult:
    return legacy_services.import_route_from_payload(
        payload,
        created_by=created_by,
    )


@wraps(legacy_services.health_summary)
def health_summary() -> Mapping[str, object]:
    return legacy_services.health_summary()


__all__ = [
    "BatchBuildResult",
    "RouteBuildContext",
    "RouteBuildResult",
    "RouteImportPayload",
    "RouteServiceError",
    "SegmentPayload",
    "CACHE_KEY_ROUTE",
    "CACHE_KEY_SEGMENTS",
    "CACHE_KEY_EVENTS",
    "CACHE_KEY_SUMMARY",
    "health_summary",
    "import_route_from_payload",
    "invalidate_route_cache",
    "rebuild_route",
    "rebuild_routes_batch",
]

