"""Service layer contracts for routes_builder.

The implementations will orchestrate database updates, cache invalidation and
auxiliary integrations. This module currently exposes the public API so tests
and Celery tasks can share the same expectations before the heavy logic is
introduced.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Iterable,
    Mapping,
    MutableMapping,
    NotRequired,
    Optional,
    Required,
    Sequence,
    TypedDict,
    cast,
)

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from inventory.models import Port
from routes_builder.models import Route, RouteEvent, RouteSegment


logger = logging.getLogger(__name__)


# =============================================================================
# Data containers
# =============================================================================


class SegmentPayload(TypedDict, total=False):
    order: int
    from_port_id: int | None
    to_port_id: int | None
    path_coordinates: Sequence[Mapping[str, float]] | None
    length_km: Decimal | float | str | None
    estimated_loss_db: Decimal | float | str | None
    measured_loss_db: Decimal | float | str | None
    metadata: Mapping[str, Any] | None


class RouteImportPayload(TypedDict, total=False):
    name: Required[str]
    origin_port_id: Required[int]
    destination_port_id: Required[int]
    id: NotRequired[int]
    status: NotRequired[str]
    description: NotRequired[str]
    import_source: NotRequired[str]
    metadata: NotRequired[Mapping[str, Any]]
    options: NotRequired[Mapping[str, Any]]
    segments: NotRequired[Sequence[SegmentPayload]]


@dataclass(frozen=True)
class RouteBuildContext:
    """Input context provided to the rebuild pipeline."""

    route_id: int
    force: bool = False
    options: Optional[Mapping[str, Any]] = None


@dataclass(frozen=True)
class RouteBuildResult:
    """Outcome information for a single route rebuild."""

    route_id: int
    status: str
    segments_created: int
    events_recorded: int
    metadata: MutableMapping[str, Any]


@dataclass(frozen=True)
class BatchBuildResult:
    """Aggregated outcome for batch build operations."""

    processed: Sequence[RouteBuildResult]
    failures: Sequence[int]


# =============================================================================
# Exceptions
# =============================================================================

class RouteServiceError(RuntimeError):
    """Base error for failures raised by the service layer."""


# =============================================================================
# Cache helpers
# =============================================================================

CACHE_KEY_ROUTE = "routes_builder:route:{route_id}"
CACHE_KEY_SEGMENTS = "routes_builder:segments:{route_id}"
CACHE_KEY_EVENTS = "routes_builder:events:{route_id}"
CACHE_KEY_SUMMARY = "routes_builder:summary"


# =============================================================================
# Internal helpers
# =============================================================================

def _as_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise RouteServiceError(f"Invalid decimal value: {value}") from exc


def _get_port(port_id: Optional[int]) -> Optional[Port]:
    if port_id in (None, ""):
        return None
    try:
        return Port.objects.get(pk=port_id)
    except Port.DoesNotExist as exc:
        raise RouteServiceError(f"Port {port_id} could not be found.") from exc


# =============================================================================
# Public API placeholders
# =============================================================================


def rebuild_route(context: RouteBuildContext) -> RouteBuildResult:
    """Rebuild an existing route from persisted segments/data sources.

    The implementation must:
    - Retrieve the target route and associated inventory context.
    - Recompute segments and metadata when requested.
    - Record RouteEvent entries describing the actions performed.
    - Persist the updated state atomically (single DB transaction).
    - Return a rich ``RouteBuildResult`` summarising the work done.
    """

    options = dict(context.options or {})

    try:
        route = (
            Route.objects.select_related(
                "origin_port__device__site",
                "destination_port__device__site",
            )
            .prefetch_related("segments")
            .get(pk=context.route_id)
        )
    except Route.DoesNotExist as exc:
        raise RouteServiceError(
            f"Route {context.route_id} could not be found."
        ) from exc

    with transaction.atomic():
        segments = list(route.segments.order_by("order", "id"))
        reindexed_segments = 0

        for index, segment in enumerate(segments, start=1):
            if segment.order != index:
                segment.order = index
                segment.save(update_fields=["order", "updated_at"])
                reindexed_segments += 1

        total_length = sum(
            ((segment.length_km or Decimal("0")) for segment in segments),
            Decimal("0"),
        )

        route.length_km = total_length if segments else None

        metadata_snapshot: MutableMapping[str, Any] = {
            "segment_count": len(segments),
            "total_length_km": float(total_length),
            "force": context.force,
            "options": options,
            "reindexed_segments": reindexed_segments,
        }

        combined_metadata: MutableMapping[str, Any] = dict(
            route.metadata or {}
        )
        combined_metadata["last_build"] = metadata_snapshot
        route.metadata = combined_metadata

        if route.status != Route.STATUS_ACTIVE:
            route.update_status(Route.STATUS_ACTIVE, save=False)

        route.save(
            update_fields=["status", "length_km", "metadata", "updated_at"]
        )

        event_details = dict(metadata_snapshot)
        event_details["segment_ids"] = [segment.id for segment in segments]

        RouteEvent.objects.create(
            route=route,
            event_type=RouteEvent.EVENT_BUILD,
            message="Route rebuilt",
            details=event_details,
            created_by=str(options.get("initiator", "routes_builder.service")),
        )

    invalidate_route_cache(route.id)

    return RouteBuildResult(
        route_id=route.id,
        status=route.status,
        segments_created=len(segments),
        events_recorded=1,
        metadata=metadata_snapshot,
    )


def rebuild_routes_batch(
    contexts: Iterable[RouteBuildContext],
) -> BatchBuildResult:
    """Process multiple routes sequentially or in mini-batches.

    Responsibilities:
    - Iterate through each context and call ``rebuild_route``.
    - Collect successful ``RouteBuildResult`` objects.
    - Track route IDs that failed and return them via ``failures``.
    """

    processed: list[RouteBuildResult] = []
    failures: list[int] = []

    for ctx in contexts:
        try:
            processed.append(rebuild_route(ctx))
        except RouteServiceError as exc:
            logger.warning(
                "Route rebuild failed for id=%s: %s",
                ctx.route_id,
                exc,
            )
            failures.append(ctx.route_id)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception(
                "Unexpected error rebuilding route id=%s", ctx.route_id
            )
            failures.append(ctx.route_id)

    return BatchBuildResult(
        processed=tuple(processed),
        failures=tuple(failures),
    )


def import_route_from_payload(
    payload: Mapping[str, Any] | RouteImportPayload,
    *,
    created_by: str,
) -> RouteBuildResult:
    """Create or update a route given an import payload.

    Expectations:
    - Parse the payload (JSON-decoded dict) into domain objects.
    - Upsert Route, RouteSegment and RouteEvent records.
    - Return a ``RouteBuildResult`` describing the final state.
    """

    if not isinstance(  # pyright: ignore[reportUnnecessaryIsInstance]
        payload,
        Mapping,
    ):
        raise RouteServiceError("Payload must be a mapping.")

    typed_payload = cast(RouteImportPayload, payload)

    required_fields = ["name", "origin_port_id", "destination_port_id"]
    for field in required_fields:
        if field not in typed_payload:
            raise RouteServiceError(f"Missing required payload field: {field}")

    origin_port = _get_port(typed_payload.get("origin_port_id"))
    destination_port = _get_port(typed_payload.get("destination_port_id"))

    if origin_port is None or destination_port is None:
        raise RouteServiceError("Origin and destination ports must resolve.")

    status = typed_payload.get("status", Route.STATUS_PLANNED)
    description = typed_payload.get("description", "")
    import_source = typed_payload.get("import_source", "json")
    metadata_in_payload = typed_payload.get("metadata")

    raw_options = typed_payload.get("options")
    options_payload: Mapping[str, Any]
    if raw_options is None:
        options_payload = {}
    else:
        options_payload = raw_options

    raw_segments = typed_payload.get("segments")
    segments_payload: Sequence[SegmentPayload]
    if raw_segments is None:
        segments_payload = ()
    else:
        segments_payload = raw_segments

    route: Optional[Route] = None
    created = False

    with transaction.atomic():
        route_id = typed_payload.get("id")
        if route_id:
            try:
                route = (
                    Route.objects.select_for_update()
                    .select_related("origin_port", "destination_port")
                    .get(pk=route_id)
                )
                route.name = typed_payload["name"]
            except Route.DoesNotExist as exc:
                raise RouteServiceError(
                    f"Route {route_id} could not be found for import."
                ) from exc
        else:
            route, created = Route.objects.select_for_update().get_or_create(
                name=typed_payload["name"],
                defaults={
                    "origin_port": origin_port,
                    "destination_port": destination_port,
                    "description": description,
                    "status": status,
                    "import_source": import_source,
                    "metadata": metadata_in_payload or {},
                },
            )

        assert route is not None

        route.origin_port = origin_port
        route.destination_port = destination_port
        route.description = description
        route.import_source = import_source

        if metadata_in_payload is not None:
            route.metadata = metadata_in_payload

        route.update_status(status, save=False)
        route.full_clean()
        route.save(
            update_fields=[
                "name",
                "origin_port",
                "destination_port",
                "description",
                "status",
                "import_source",
                "metadata",
                "updated_at",
            ]
        )

        route.segments.all().delete()

        segment_objects: list[RouteSegment] = []
        for index, segment_payload in enumerate(segments_payload, start=1):
            order_raw = segment_payload.get("order", index)
            try:
                order = int(order_raw)
            except (TypeError, ValueError) as exc:
                raise RouteServiceError(
                    f"Invalid segment order value: {order_raw}"
                ) from exc

            segment_objects.append(
                RouteSegment(
                    route=route,
                    order=order,
                    from_port=_get_port(segment_payload.get("from_port_id")),
                    to_port=_get_port(segment_payload.get("to_port_id")),
                    path_coordinates=segment_payload.get("path_coordinates"),
                    length_km=_as_decimal(segment_payload.get("length_km")),
                    estimated_loss_db=_as_decimal(
                        segment_payload.get("estimated_loss_db")
                    ),
                    measured_loss_db=_as_decimal(
                        segment_payload.get("measured_loss_db")
                    ),
                    metadata=segment_payload.get("metadata"),
                )
            )

        if segment_objects:
            RouteSegment.objects.bulk_create(segment_objects)

    options = dict(options_payload)
    options.setdefault("initiator", created_by)
    options.setdefault("source", "json_import")

    build_result = rebuild_route(
        RouteBuildContext(route_id=route.id, force=True, options=options)
    )

    import_details: Dict[str, Any] = {
        "created": created,
        "segments_supplied": len(segments_payload),
        "source": options["source"],
    }

    with transaction.atomic():
        route_ref = Route.objects.select_for_update().get(pk=route.id)
        metadata_state: MutableMapping[str, Any] = dict(
            route_ref.metadata or {}
        )
        metadata_state["last_import"] = {
            "created_by": created_by,
            "segments_supplied": len(segments_payload),
            "source": options["source"],
        }
        route_ref.metadata = metadata_state
        route_ref.save(update_fields=["metadata", "updated_at"])

        RouteEvent.objects.create(
            route=route_ref,
            event_type=RouteEvent.EVENT_IMPORT,
            message="Route imported from JSON payload",
            details=import_details,
            created_by=created_by,
        )

    invalidate_route_cache(route.id)

    combined_metadata: MutableMapping[str, Any] = dict(build_result.metadata)
    combined_metadata["import"] = import_details

    return RouteBuildResult(
        route_id=build_result.route_id,
        status=build_result.status,
        segments_created=build_result.segments_created,
        events_recorded=build_result.events_recorded + 1,
        metadata=combined_metadata,
    )


def invalidate_route_cache(route_id: int) -> None:
    """Invalidate cache entries related to the supplied route ID."""

    keys = [
        CACHE_KEY_ROUTE.format(route_id=route_id),
        CACHE_KEY_SEGMENTS.format(route_id=route_id),
        CACHE_KEY_EVENTS.format(route_id=route_id),
        CACHE_KEY_SUMMARY,
    ]

    try:
        cache.delete_many(keys)
    except Exception:  # pragma: no cover - cache backend defensive path
        logger.debug("Cache backend delete_many failed", exc_info=True)

    delete_pattern = getattr(cache, "delete_pattern", None)
    if callable(delete_pattern):
        patterns = [f"routes_builder:*:{route_id}"]
        for pattern in patterns:
            try:
                delete_pattern(pattern)
            except Exception:  # pragma: no cover - backend specific
                logger.debug(
                    "Cache backend delete_pattern failed for %s", pattern,
                    exc_info=True,
                )


def health_summary() -> Dict[str, Any]:
    """Return a lightweight diagnostic payload used by Celery tasks."""
    routes_count = Route.objects.count()
    segments_count = RouteSegment.objects.count()
    events_count = RouteEvent.objects.count()

    recent_events_queryset = (
        RouteEvent.objects.select_related("route")
        .order_by("-created_at")
        [:5]
    )
    recent_events = [
        {
            "event_id": event.id,
            "route_id": event.route_id,
            "event_type": event.event_type,
            "created_at": event.created_at.isoformat(),
            "route_status": event.route.status,
        }
        for event in recent_events_queryset
    ]

    return {
        "routes": routes_count,
        "segments": segments_count,
        "events": events_count,
        "recent_events": recent_events,
        "generated_at": timezone.now().isoformat(),
    }
