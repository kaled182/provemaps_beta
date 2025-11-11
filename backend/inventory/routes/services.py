# pyright: reportGeneralTypeIssues=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

"""Service layer for the inventory routes domain.

This module consolidates the legacy routes_builder logic under the
``inventory.routes`` namespace while preserving the public API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
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
from inventory.models_routes import Route, RouteEvent, RouteSegment


logger = logging.getLogger(__name__)


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


class RouteServiceError(RuntimeError):
    """Base error for failures raised by the service layer."""


CACHE_KEY_ROUTE = "routes_builder:route:{route_id}"
CACHE_KEY_SEGMENTS = "routes_builder:segments:{route_id}"
CACHE_KEY_EVENTS = "routes_builder:events:{route_id}"
CACHE_KEY_SUMMARY = "routes_builder:summary"


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


def rebuild_route(context: RouteBuildContext) -> RouteBuildResult:
    """Rebuild an existing route from persisted segments/data sources."""

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

        if route.status != Route.STATUS_ACTIVE or context.force:
            route.update_status(Route.STATUS_ACTIVE, save=False)

        route.save(
            update_fields=[
                "status",
                "length_km",
                "metadata",
                "updated_at",
            ]
        )

        event_details: MutableMapping[str, Any] = dict(metadata_snapshot)
        event_details["segment_ids"] = [segment.id for segment in segments]

        RouteEvent.objects.create(
            route=route,
            event_type=RouteEvent.EVENT_BUILD,
            message="Route rebuilt",
            details=event_details,
            created_by=str(options.get("initiator", "inventory.routes")),
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
    processed: list[RouteBuildResult] = []
    failures: list[int] = []

    for context in contexts:
        try:
            processed.append(rebuild_route(context))
        except RouteServiceError as exc:
            logger.warning(
                "Failed to rebuild route %s: %s",
                context.route_id,
                exc,
            )
            failures.append(context.route_id)
        except Exception:  # pragma: no cover - defensive logging path
            logger.exception(
                "Unexpected error rebuilding route id=%s",
                context.route_id,
            )
            failures.append(context.route_id)

    return BatchBuildResult(
        processed=tuple(processed),
        failures=tuple(failures),
    )


def import_route_from_payload(
    payload: Mapping[str, Any] | RouteImportPayload,
    *,
    created_by: str = "inventory.routes",
) -> RouteBuildResult:
    data = dict(cast(Mapping[str, Any], payload))

    required_fields = ["name", "origin_port_id", "destination_port_id"]
    for field in required_fields:
        if field not in data:
            raise RouteServiceError(
                f"Missing required payload field: {field}"
            )

    origin_port = _get_port(data.get("origin_port_id"))
    destination_port = _get_port(data.get("destination_port_id"))

    if origin_port is None or destination_port is None:
        raise RouteServiceError("Origin and destination ports must resolve.")

    status = data.get("status", Route.STATUS_PLANNED)
    description = data.get("description", "") or ""
    import_source = data.get("import_source", "json")

    raw_metadata = data.get("metadata")
    if raw_metadata is not None and not isinstance(raw_metadata, Mapping):
        raise RouteServiceError("Metadata payload must be a mapping.")
    metadata_payload = dict(raw_metadata or {})

    raw_options = data.get("options")
    if raw_options is not None and not isinstance(raw_options, Mapping):
        raise RouteServiceError("Options payload must be a mapping.")
    options_payload = cast(Mapping[str, Any], raw_options or {})

    raw_segments = data.get("segments")
    segments_payload: list[Mapping[str, Any]] = []
    if raw_segments is not None:
        if not isinstance(raw_segments, Sequence):
            raise RouteServiceError("Segments payload must be a sequence.")
        for entry in raw_segments:
            if not isinstance(entry, Mapping):
                raise RouteServiceError("Each segment must be a mapping.")
            segments_payload.append(cast(Mapping[str, Any], entry))

    created = False
    segments_supplied = len(segments_payload)

    with transaction.atomic():
        route_id = data.get("id")
        if route_id:
            try:
                route = (
                    Route.objects.select_for_update()
                    .select_related("origin_port", "destination_port")
                    .get(pk=route_id)
                )
                route.name = cast(str, data["name"])
            except Route.DoesNotExist as exc:
                raise RouteServiceError(
                    f"Route {route_id} could not be found for import."
                ) from exc
        else:
            route, created = Route.objects.select_for_update().get_or_create(
                name=cast(str, data["name"]),
                defaults={
                    "origin_port": origin_port,
                    "destination_port": destination_port,
                    "description": description,
                    "status": status,
                    "import_source": import_source,
                    "metadata": metadata_payload,
                },
            )

        route.origin_port = origin_port
        route.destination_port = destination_port
        route.description = description
        route.import_source = import_source

        if raw_metadata is not None:
            route.metadata = metadata_payload

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

        RouteSegment.objects.filter(route=route).delete()

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
        "segments_supplied": segments_supplied,
        "source": options["source"],
    }

    with transaction.atomic():
        route_ref = Route.objects.select_for_update().get(pk=route.id)
        metadata_state: MutableMapping[str, Any] = dict(
            route_ref.metadata or {}
        )
        metadata_state.setdefault("imports", [])
        metadata_state["last_import"] = {
            "created_by": created_by,
            "segments_supplied": segments_supplied,
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
    keys = [
        CACHE_KEY_ROUTE.format(route_id=route_id),
        CACHE_KEY_SEGMENTS.format(route_id=route_id),
        CACHE_KEY_EVENTS.format(route_id=route_id),
        CACHE_KEY_SUMMARY,
    ]

    try:
        cache.delete_many(keys)
    except Exception:  # pragma: no cover - cache backend defensive path
        logger.debug("Cache delete_many failed", exc_info=True)

    delete_pattern = getattr(cache, "delete_pattern", None)
    if callable(delete_pattern):
        pattern = f"routes_builder:*:{route_id}"
        try:
            delete_pattern(pattern)
        except Exception:  # pragma: no cover - backend specific path
            logger.debug(
                "Cache delete_pattern failed for %s",
                pattern,
                exc_info=True,
            )


def health_summary() -> Mapping[str, Any]:
    summary: Dict[str, Any] = {
        "routes": Route.objects.count(),
        "segments": RouteSegment.objects.count(),
        "events": RouteEvent.objects.count(),
        "recent_events": [],
        "generated_at": timezone.now().isoformat(),
    }

    recent_events = RouteEvent.objects.select_related("route").order_by(
        "-created_at"
    )[:5]

    summary["recent_events"] = [
        {
            "event_id": event.id,
            "route_id": event.route_id,
            "event_type": event.event_type,
            "created_at": event.created_at.isoformat()
            if event.created_at
            else None,
            "route_status": event.route.status if event.route_id else None,
        }
        for event in recent_events
    ]

    return summary


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

