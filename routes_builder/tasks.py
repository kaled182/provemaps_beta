"""Celery tasks wrapping routes_builder service operations."""

from __future__ import annotations

import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    Optional,
    TypeVar,
)

from inventory import routes as services

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from typing import Protocol

    class CeleryTask(Protocol):
        request: Any

    FuncT = TypeVar("FuncT", bound=Callable[..., Any])

    def shared_task(*args: Any, **kwargs: Any) -> Callable[[FuncT], FuncT]:
        ...
else:  # pragma: no cover - import for runtime execution only
    from celery import shared_task

    CeleryTask = Any


# =============================================================================
# CELERY TASKS
# =============================================================================

@shared_task(bind=True, name="routes_builder.build_route")
def build_route(
    self: CeleryTask,
    route_id: int,
    force: bool = False,
    options: Optional[Dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build or rebuild a single route via the service layer."""

    logger.info("Task build_route started for route_id=%s", route_id)
    payload_options = dict(options or {})

    context = services.RouteBuildContext(
        route_id=route_id,
        force=force,
        options=payload_options,
    )

    try:
        result = services.rebuild_route(context)
        response = {
            "status": "success",
            "route_id": result.route_id,
            "route_status": result.status,
            "segments_created": result.segments_created,
            "events_recorded": result.events_recorded,
            "metadata": result.metadata,
        }
        logger.info(
            "Task build_route finished for route_id=%s status=%s",
            route_id,
            result.status,
        )
        return response
    except services.RouteServiceError as exc:
        logger.warning(
            "Task build_route failed for route_id=%s: %s",
            route_id,
            exc,
        )
        return {
            "status": "error",
            "route_id": route_id,
            "message": str(exc),
        }


@shared_task(bind=True, name="routes_builder.build_routes_batch")
def build_routes_batch(
    self: CeleryTask,
    route_ids: Iterable[int],
    force: bool = False,
    options: Optional[Dict[str, Any]] = None,
) -> dict[str, Any]:
    """Process multiple routes by delegating to the batch rebuild service."""

    route_ids_list = list(route_ids)
    logger.info(
        "Task build_routes_batch started for %d routes", len(route_ids_list)
    )

    shared_options = dict(options or {})
    contexts = [
        services.RouteBuildContext(
            route_id=route_id,
            force=force,
            options=shared_options,
        )
        for route_id in route_ids_list
    ]

    result = services.rebuild_routes_batch(contexts)

    processed_payload = [
        {
            "route_id": item.route_id,
            "route_status": item.status,
            "segments_created": item.segments_created,
            "events_recorded": item.events_recorded,
            "metadata": item.metadata,
        }
        for item in result.processed
    ]

    summary = {
        "status": "success",
        "processed": processed_payload,
        "failures": list(result.failures),
    }

    logger.info(
        "Task build_routes_batch finished processed=%d failures=%d",
        len(processed_payload),
        len(result.failures),
    )

    return summary


@shared_task(bind=True, name="routes_builder.invalidate_route_cache")
def invalidate_route_cache(self: CeleryTask, route_id: int) -> dict[str, Any]:
    """Invalidate cached data associated with a given route."""

    logger.info(
        "Task invalidate_route_cache started for route_id=%s", route_id
    )
    services.invalidate_route_cache(route_id)
    return {
        "status": "success",
        "route_id": route_id,
    }


@shared_task(bind=True, name="routes_builder.import_route_from_payload")
def import_route_from_payload(
    self: CeleryTask,
    payload: Dict[str, Any] | services.RouteImportPayload,
    created_by: str = "routes_builder.task",
) -> dict[str, Any]:
    """Import or update a route using a JSON-like payload."""

    logger.info(
        "Task import_route_from_payload started created_by=%s", created_by
    )

    try:
        result = services.import_route_from_payload(
            payload,
            created_by=created_by,
        )
        return {
            "status": "success",
            "route_id": result.route_id,
            "route_status": result.status,
            "segments_created": result.segments_created,
            "events_recorded": result.events_recorded,
            "metadata": result.metadata,
        }
    except services.RouteServiceError as exc:
        logger.warning("Task import_route_from_payload failed: %s", exc)
        return {
            "status": "error",
            "message": str(exc),
        }


@shared_task(bind=True, name="routes_builder.health_check")
def health_check_routes_builder(self: CeleryTask) -> dict[str, Any]:
    """Light-weight health check for the routes worker/queue."""
    logger.info("Task health_check_routes_builder executed")
    summary = services.health_summary()
    return {
        "status": "success",
        "summary": summary,
    }

