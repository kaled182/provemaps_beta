"""HTTP endpoints for administering route-building tasks."""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, cast

from celery.result import AsyncResult as CeleryAsyncResult
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.views.decorators.http import require_POST

from inventory.api._admin_tasks import (
    SupportsApplyAsync,
    apply_async,
    as_int_list,
    check_rate_limit,
    get_json_body,
    is_staff_user,
    log_operation,
    require_ip_allowlist,
    task_id,
)
from inventory.routes.tasks import (
    build_route,
    build_routes_batch,
    health_check_routes_builder,
    import_route_from_payload,
    invalidate_route_cache,
)

AsyncResult = CeleryAsyncResult

logger = logging.getLogger(__name__)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def enqueue_build_route(request: HttpRequest) -> HttpResponse:
    deny = require_ip_allowlist(request)
    if deny:
        return deny

    if not check_rate_limit(
        request,
        "enqueue_build_route",
        limit=20,
        window=60,
    ):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    route_id = body.get("route_id")
    if not isinstance(route_id, int) or route_id <= 0:
        return HttpResponseBadRequest("route_id must be a positive integer")

    force = bool(body.get("force", False))
    options_raw = body.get("options")
    options: Dict[str, Any] = (
        dict(cast(Mapping[str, Any], options_raw))
        if isinstance(options_raw, Mapping)
        else {}
    )

    try:
        result = apply_async(
            cast(SupportsApplyAsync, build_route),
            args=[route_id],
            kwargs={"force": force, "options": options},
        )
        log_operation(
            request,
            "enqueue_build_route",
            route_id=route_id,
            force=force,
        )
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.build_route",
                "task_id": task_id(result),
                "route_id": route_id,
                "queue": getattr(result, "queue", "maps"),
            },
            status=202,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to enqueue build_route for %s: %s", route_id, exc)
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def enqueue_build_routes_batch(request: HttpRequest) -> HttpResponse:
    deny = require_ip_allowlist(request)
    if deny:
        return deny

    if not check_rate_limit(
        request,
        "enqueue_build_routes_batch",
        limit=10,
        window=60,
    ):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    route_ids = as_int_list(body.get("route_ids"))
    if not route_ids or any(route_id <= 0 for route_id in route_ids):
        return HttpResponseBadRequest(
            "route_ids must be a list of positive integers"
        )

    force = bool(body.get("force", False))

    try:
        result = apply_async(
            cast(SupportsApplyAsync, build_routes_batch),
            kwargs={"route_ids": route_ids, "force": force},
        )
        log_operation(
            request,
            "enqueue_build_routes_batch",
            route_count=len(route_ids),
            force=force,
        )
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.build_routes_batch",
                "task_id": task_id(result),
                "route_ids": route_ids,
                "queue": getattr(result, "queue", "maps"),
            },
            status=202,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to enqueue build_routes_batch: %s", exc)
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def enqueue_import_route(request: HttpRequest) -> HttpResponse:
    deny = require_ip_allowlist(request)
    if deny:
        return deny

    if not check_rate_limit(
        request,
        "enqueue_import_route",
        limit=10,
        window=60,
    ):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    payload_raw = body.get("payload")
    if not isinstance(payload_raw, Mapping):
        return HttpResponseBadRequest("payload must be an object")
    payload = dict(cast(Mapping[str, Any], payload_raw))

    created_by_raw = body.get("created_by")
    created_by = (
        created_by_raw
        if isinstance(created_by_raw, str) and created_by_raw
        else request.user.get_username() or "routes_builder"
    )

    try:
        result = apply_async(
            cast(SupportsApplyAsync, import_route_from_payload),
            args=[payload],
            kwargs={"created_by": created_by},
        )
        log_operation(
            request,
            "enqueue_import_route",
            created_by=created_by,
            payload_name=payload.get("name"),
        )
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.import_route_from_payload",
                "task_id": task_id(result),
                "queue": getattr(result, "queue", "maps"),
                "created_by": created_by,
            },
            status=202,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to enqueue import_route_from_payload: %s", exc)
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def enqueue_invalidate_route_cache(request: HttpRequest) -> HttpResponse:
    deny = require_ip_allowlist(request)
    if deny:
        return deny

    if not check_rate_limit(
        request,
        "enqueue_invalidate_route_cache",
        limit=30,
        window=60,
    ):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    route_id = body.get("route_id")
    if not isinstance(route_id, int) or route_id <= 0:
        return HttpResponseBadRequest("route_id must be a positive integer")

    try:
        result = apply_async(
            cast(SupportsApplyAsync, invalidate_route_cache),
            args=[route_id],
        )
        log_operation(
            request,
            "enqueue_invalidate_route_cache",
            route_id=route_id,
        )
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.invalidate_route_cache",
                "task_id": task_id(result),
                "route_id": route_id,
                "queue": getattr(result, "queue", "maps"),
            },
            status=202,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(
            "Failed to enqueue invalidate_route_cache for %s: %s",
            route_id,
            exc,
        )
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def enqueue_health_check(request: HttpRequest) -> HttpResponse:
    deny = require_ip_allowlist(request)
    if deny:
        return deny

    if not check_rate_limit(
        request,
        "enqueue_health_check",
        limit=30,
        window=60,
    ):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    try:
        result = apply_async(
            cast(SupportsApplyAsync, health_check_routes_builder)
        )
        log_operation(request, "enqueue_health_check")
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.health_check_routes_builder",
                "task_id": task_id(result),
                "queue": getattr(result, "queue", "maps"),
            },
            status=202,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to enqueue health_check_routes_builder: %s", exc)
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(is_staff_user)
def task_status(request: HttpRequest, task_id_value: str) -> HttpResponse:
    deny = require_ip_allowlist(request)
    if deny:
        return deny

    try:
        result = AsyncResult(task_id_value)
        status_value = getattr(result, "status", "PENDING")
        status_str = (
            status_value
            if isinstance(status_value, str)
            else str(status_value)
        )
        response: Dict[str, Any] = {
            "task_id": task_id_value,
            "status": status_str,
            "ready": result.ready(),
        }
        if result.ready():
            if result.successful():
                response["result"] = getattr(result, "result", None)
            else:
                response["error"] = str(getattr(result, "result", None))
                response["traceback"] = (
                    str(getattr(result, "traceback", None))
                    if getattr(result, "traceback", None) is not None
                    else None
                )
        return JsonResponse(response)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to fetch task status %s: %s", task_id_value, exc)
        return JsonResponse(
            {"error": "Failed to fetch task status"},
            status=500,
        )


@login_required
@user_passes_test(is_staff_user)
@require_POST
def enqueue_bulk_operations(request: HttpRequest) -> HttpResponse:
    deny = require_ip_allowlist(request)
    if deny:
        return deny

    if not check_rate_limit(
        request,
        "enqueue_bulk_operations",
        limit=10,
        window=60,
    ):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    operations_raw = body.get("operations")
    if not isinstance(operations_raw, list):
        return HttpResponseBadRequest("operations must be a list")

    operations: list[Mapping[str, Any]] = []
    for entry in operations_raw:
        if isinstance(entry, Mapping):
            operations.append(cast(Mapping[str, Any], entry))

    results: list[Dict[str, Any]] = []

    for operation in operations:
        action = operation.get("action")
        route_id = operation.get("route_id")

        try:
            if action == "build":
                if not isinstance(route_id, int) or route_id <= 0:
                    results.append(
                        {
                            "action": action,
                            "route_id": route_id,
                            "status": "failed",
                            "error": "invalid route_id",
                        }
                    )
                    continue
                force = bool(operation.get("force", False))
                options_raw = operation.get("options")
                options_mapping = (
                    cast(Mapping[str, Any], options_raw)
                    if isinstance(options_raw, Mapping)
                    else None
                )
                options = dict(options_mapping) if options_mapping else {}
                result = apply_async(
                    cast(SupportsApplyAsync, build_route),
                    args=[route_id],
                    kwargs={"force": force, "options": options},
                )
                results.append(
                    {
                        "action": "build",
                        "route_id": route_id,
                        "task_id": task_id(result),
                        "status": "enqueued",
                    }
                )

            elif action == "invalidate":
                if not isinstance(route_id, int) or route_id <= 0:
                    results.append(
                        {
                            "action": action,
                            "route_id": route_id,
                            "status": "failed",
                            "error": "invalid route_id",
                        }
                    )
                    continue
                result = apply_async(
                    cast(SupportsApplyAsync, invalidate_route_cache),
                    args=[route_id],
                )
                results.append(
                    {
                        "action": "invalidate",
                        "route_id": route_id,
                        "task_id": task_id(result),
                        "status": "enqueued",
                    }
                )

            elif action == "import":
                payload_raw = operation.get("payload")
                if not isinstance(payload_raw, Mapping):
                    results.append(
                        {
                            "action": action,
                            "status": "failed",
                            "error": "payload must be an object",
                        }
                    )
                    continue
                payload = dict(cast(Mapping[str, Any], payload_raw))
                created_by = (
                    operation.get("created_by")
                    or request.user.get_username()
                    or "routes_builder"
                )
                result = apply_async(
                    cast(SupportsApplyAsync, import_route_from_payload),
                    args=[payload],
                    kwargs={"created_by": created_by},
                )
                results.append(
                    {
                        "action": "import",
                        "task_id": task_id(result),
                        "status": "enqueued",
                        "created_by": created_by,
                        "payload_name": payload.get("name"),
                    }
                )

            else:
                results.append(
                    {
                        "action": action,
                        "route_id": route_id,
                        "status": "skipped",
                        "error": "unknown action",
                    }
                )

        except Exception as exc:  # pragma: no cover - defensive logging
            results.append(
                {
                    "action": action,
                    "route_id": route_id,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    log_operation(
        request,
        "enqueue_bulk_operations",
        operations=len(operations),
    )
    return JsonResponse(
        {
            "status": "bulk_enqueued",
            "operations": len(operations),
            "successful": len(
                [
                    entry
                    for entry in results
                    if entry.get("status") == "enqueued"
                ]
            ),
            "failed": len(
                [entry for entry in results if entry.get("status") == "failed"]
            ),
            "results": results,
        },
        status=202,
    )
