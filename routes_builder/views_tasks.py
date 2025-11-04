# pyright: reportMissingTypeStubs=false
"""
Secure task enqueue views for routes_builder.

- Authentication enforced: @login_required + @user_passes_test(is_staff)
- IP safelist via ADMIN_IP_SAFELIST="1.2.3.4,10.0.0.0/8"
- Basic per-user rate limiting handled by cache
- JSON input/output for all endpoints
- Endpoints:
    POST /routes_builder/tasks/build
    POST /routes_builder/tasks/batch
    POST /routes_builder/tasks/invalidate
    POST /routes_builder/tasks/health
    GET  /routes_builder/tasks/status/<task_id>
    POST /routes_builder/tasks/bulk
"""

from __future__ import annotations

import ipaddress
import json
import logging
import os
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Dict, List, Optional, Protocol, cast

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.views.decorators.http import require_POST

from celery.result import AsyncResult as CeleryAsyncResult
from .tasks import (
    build_route,
    build_routes_batch,
    health_check_routes_builder,
    import_route_from_payload,
    invalidate_route_cache,
)

AsyncResult = CeleryAsyncResult

logger = logging.getLogger(__name__)

# =============================================================================
# Config / Helpers
# =============================================================================


def _parse_ip_safelist() -> List[str]:
    raw = os.getenv("ADMIN_IP_SAFELIST", "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def _is_ip_allowed(request: HttpRequest) -> bool:
    """Validate the requester IP against ADMIN_IP_SAFELIST entries."""
    safelist = _parse_ip_safelist()
    if not safelist:
        return True

    cand = (
        request.META.get("HTTP_X_FORWARDED_FOR", "")
        or request.META.get("REMOTE_ADDR", "")
    )
    client_ip = cand.split(",")[0].strip() if cand else "0.0.0.0"

    try:
        ip_obj = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for entry in safelist:
        try:
            if "/" in entry:
                if ip_obj in ipaddress.ip_network(entry, strict=False):
                    return True
            else:
                if ip_obj == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            continue
    return False


def _require_ip_allowlist(request: HttpRequest) -> Optional[JsonResponse]:
    if not _is_ip_allowed(request):
        return JsonResponse({"detail": "Forbidden by IP safelist"}, status=403)
    return None


def _get_json_body(request: HttpRequest) -> Optional[Mapping[str, Any]]:
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None
    if isinstance(data, Mapping):
        return cast(Mapping[str, Any], data)
    return None


def _as_list(value: object) -> List[int]:
    if value is None:
        return []
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        items: List[int] = []
        for item in cast(Iterable[object], value):
            if isinstance(item, int):
                items.append(item)
        return items
    if isinstance(value, int):
        return [value]
    return []


# -------------------------- Rate Limiting -------------------------------

def _rate_limit_key(request: HttpRequest, action: str) -> str:
    if request.user.is_authenticated:
        user_pk = getattr(request.user, "pk", None)
        if user_pk is not None:
            user_identifier = str(user_pk)
        else:
            user_identifier = request.user.get_username() or "anonymous"
    else:
        user_identifier = "anonymous"
    return f"rate_limit:{action}:{user_identifier}"


def _check_rate_limit(
    request: HttpRequest,
    action: str,
    *,
    limit: int = 10,
    window: int = 60,
) -> bool:
    """Simple cache-based rate limiting helper."""
    key = _rate_limit_key(request, action)
    try:
        current = cache.get(key, 0)
        current_count = int(current) if isinstance(current, int) else 0
        if current_count >= limit:
            return False
        cache.set(key, current_count + 1, timeout=window)
    except Exception:
        # Fail open if the cache backend is not available
        pass
    return True


# -------------------------- Auditoria -----------------------------------

def _client_ip(request: HttpRequest) -> str:
    if request.META.get("HTTP_X_FORWARDED_FOR"):
        return request.META["HTTP_X_FORWARDED_FOR"].split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _log_operation(
    request: HttpRequest,
    action: str,
    **kwargs: Any,
) -> None:
    user = (
        request.user.get_username()
        if request.user.is_authenticated
        else "anonymous"
    )
    logger.info(
        "Admin operation: user=%s ip=%s action=%s %s",
        user,
        _client_ip(request),
        action,
        " ".join(f"{k}={v}" for k, v in kwargs.items()),
    )


def _is_staff_user(user: Any) -> bool:
    return bool(getattr(user, "is_staff", False))


class _SupportsApplyAsync(Protocol):
    def apply_async(
        self,
        *,
        args: Optional[Sequence[Any]] = ...,
        kwargs: Optional[Dict[str, Any]] = ...,
    ) -> AsyncResult:
        ...


def _apply_async(
    task: _SupportsApplyAsync,
    *,
    args: Optional[Sequence[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> AsyncResult:
    return task.apply_async(args=args, kwargs=kwargs)


def _task_id(result: AsyncResult) -> str:
    value = getattr(result, "id", None)
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


# =============================================================================
# Views
# =============================================================================

@login_required
@user_passes_test(_is_staff_user)
@require_POST
def enqueue_build_route(request: HttpRequest):
    """
    Body JSON:
    {
      "route_id": 123,
      "force": false,
      "options": {"recalc_topology": true}
    }
    """
    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    if not _check_rate_limit(
        request,
        "enqueue_build_route",
        limit=20,
        window=60,
    ):  # 20 per minute per user
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = _get_json_body(request)
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

    # Optional object existence validation
    try:
        from .models import Route

        if not Route.objects.filter(id=route_id).exists():
            return JsonResponse(
                {"error": f"Route {route_id} not found"},
                status=404,
            )
    except Exception:
        # If the model import fails for any reason we allow the call to proceed
        pass

    try:
        res = _apply_async(
            cast(_SupportsApplyAsync, build_route),
            args=[route_id],
            kwargs={"force": force, "options": options},
        )
        _log_operation(
            request,
            "enqueue_build_route",
            route_id=route_id,
            force=force,
        )
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.build_route",
                "task_id": _task_id(res),
                "route_id": route_id,
                "queue": getattr(res, "queue", "maps"),
            },
            status=202,
        )
    except Exception as exc:
        logger.error("Failed to enqueue build_route for %s: %s", route_id, exc)
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(_is_staff_user)
@require_POST
def enqueue_build_routes_batch(request: HttpRequest):
    """
    Body JSON:
    {
      "route_ids": [1,2,3],
      "force": false
    }
    """
    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    if not _check_rate_limit(
        request,
        "enqueue_build_routes_batch",
        limit=10,
        window=60,
    ):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = _get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    route_ids = _as_list(body.get("route_ids"))
    if not route_ids or any(route_id <= 0 for route_id in route_ids):
        return HttpResponseBadRequest(
            "route_ids must be a list of positive integers"
        )

    force = bool(body.get("force", False))

    try:
        res = _apply_async(
            cast(_SupportsApplyAsync, build_routes_batch),
            kwargs={"route_ids": route_ids, "force": force},
        )
        _log_operation(
            request,
            "enqueue_build_routes_batch",
            route_ids=len(route_ids),
            force=force,
        )
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.build_routes_batch",
                "task_id": _task_id(res),
                "route_ids": route_ids,
                "queue": getattr(res, "queue", "maps"),
            },
            status=202,
        )
    except Exception as exc:
        logger.error("Failed to enqueue build_routes_batch: %s", exc)
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(_is_staff_user)
@require_POST
def enqueue_import_route(request: HttpRequest):
    """Enqueue a route import/update task using a JSON payload."""

    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    if not _check_rate_limit(
        request,
        "enqueue_import_route",
        limit=10,
        window=60,
    ):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = _get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    payload_raw = body.get("payload")
    if not isinstance(payload_raw, Mapping):
        return HttpResponseBadRequest("payload must be an object")
    payload: Dict[str, Any] = dict(cast(Mapping[str, Any], payload_raw))

    created_by_raw = body.get("created_by")
    created_by = (
        created_by_raw
        if isinstance(created_by_raw, str) and created_by_raw
        else request.user.get_username() or "routes_builder"
    )

    try:
        res = _apply_async(
            cast(_SupportsApplyAsync, import_route_from_payload),
            args=[payload],
            kwargs={"created_by": created_by},
        )
        _log_operation(
            request,
            "enqueue_import_route",
            created_by=created_by,
            payload_name=payload.get("name"),
        )
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.import_route_from_payload",
                "task_id": _task_id(res),
                "queue": getattr(res, "queue", "maps"),
                "created_by": created_by,
            },
            status=202,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to enqueue import_route_from_payload: %s", exc)
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(_is_staff_user)
@require_POST
def enqueue_invalidate_route_cache(request: HttpRequest):
    """
    Body JSON:
    {
      "route_id": 123
    }
    """
    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    if not _check_rate_limit(
        request,
        "enqueue_invalidate_route_cache",
        limit=30,
        window=60,
    ):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = _get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    route_id = body.get("route_id")
    if not isinstance(route_id, int) or route_id <= 0:
        return HttpResponseBadRequest("route_id must be a positive integer")

    try:
        res = _apply_async(
            cast(_SupportsApplyAsync, invalidate_route_cache),
            args=[route_id],
        )
        _log_operation(
            request,
            "enqueue_invalidate_route_cache",
            route_id=route_id,
        )
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.invalidate_route_cache",
                "task_id": _task_id(res),
                "route_id": route_id,
                "queue": getattr(res, "queue", "maps"),
            },
            status=202,
        )
    except Exception as exc:
        logger.error(
            "Failed to enqueue invalidate_route_cache for %s: %s",
            route_id,
            exc,
        )
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(_is_staff_user)
@require_POST
def enqueue_health_check(request: HttpRequest):
    """Enqueue the routes_builder health check task."""
    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    if not _check_rate_limit(
        request,
        "enqueue_health_check",
        limit=30,
        window=60,
    ):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    try:
        res = _apply_async(
            cast(_SupportsApplyAsync, health_check_routes_builder),
        )
        _log_operation(request, "enqueue_health_check")
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.health_check_routes_builder",
                "task_id": _task_id(res),
                "queue": getattr(res, "queue", "maps"),
            },
            status=202,
        )
    except Exception as exc:
        logger.error("Failed to enqueue health_check_routes_builder: %s", exc)
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(_is_staff_user)
def task_status(request: HttpRequest, task_id: str):
    """Return the status of a given Celery task.

    GET /routes_builder/tasks/status/<task_id>
    """
    # Apply IP safelist even for GET requests
    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    try:
        result = AsyncResult(task_id)
        status_value = getattr(result, "status", "PENDING")
        status_str = (
            status_value
            if isinstance(status_value, str)
            else str(status_value)
        )
        response_data: Dict[str, Any] = {
            "task_id": task_id,
            "status": status_str,
            "ready": result.ready(),
        }
        if result.ready():
            if result.successful():
                response_payload: Any = getattr(result, "result", None)
                response_data["result"] = response_payload
            else:
                error_payload: Any = getattr(result, "result", None)
                response_data["error"] = str(error_payload)
                traceback_payload = getattr(result, "traceback", None)
                response_data["traceback"] = (
                    str(traceback_payload)
                    if traceback_payload is not None
                    else None
                )
        return JsonResponse(response_data)
    except Exception as exc:
        logger.error("Failed to fetch task status %s: %s", task_id, exc)
        return JsonResponse(
            {"error": "Failed to fetch task status"},
            status=500,
        )


@login_required
@user_passes_test(_is_staff_user)
@require_POST
def enqueue_bulk_operations(request: HttpRequest):
    """Enqueue multiple operations in a single request.

    Body JSON example:
        {
            "operations": [
                {"action": "build", "route_id": 123, "force": true},
                {"action": "invalidate", "route_id": 123}
            ]
        }
    """
    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    if not _check_rate_limit(
        request,
        "enqueue_bulk_operations",
        limit=10,
        window=60,
    ):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = _get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    operations_raw = body.get("operations")
    if not isinstance(operations_raw, list):
        return HttpResponseBadRequest("operations must be a list")
    operations_raw_list = cast(List[Any], operations_raw)
    operations: List[Mapping[str, Any]] = []
    for entry in operations_raw_list:
        if isinstance(entry, Mapping):
            operations.append(cast(Mapping[str, Any], entry))

    results: List[Dict[str, Any]] = []

    for op in operations:
        action = op.get("action")
        route_id = op.get("route_id")

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
                force = bool(op.get("force", False))
                options_raw = op.get("options")
                options_mapping = (
                    cast(Mapping[str, Any], options_raw)
                    if isinstance(options_raw, Mapping)
                    else None
                )
                options = dict(options_mapping) if options_mapping else {}
                res = _apply_async(
                    cast(_SupportsApplyAsync, build_route),
                    args=[route_id],
                    kwargs={"force": force, "options": options},
                )
                results.append(
                    {
                        "action": "build",
                        "route_id": route_id,
                        "task_id": _task_id(res),
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
                res = _apply_async(
                    cast(_SupportsApplyAsync, invalidate_route_cache),
                    args=[route_id],
                )
                results.append(
                    {
                        "action": "invalidate",
                        "route_id": route_id,
                        "task_id": _task_id(res),
                        "status": "enqueued",
                    }
                )

            elif action == "import":
                payload_raw = op.get("payload")
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
                    op.get("created_by")
                    or request.user.get_username()
                    or "routes_builder"
                )
                res = _apply_async(
                    cast(_SupportsApplyAsync, import_route_from_payload),
                    args=[payload],
                    kwargs={"created_by": created_by},
                )
                results.append(
                    {
                        "action": "import",
                        "task_id": _task_id(res),
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

    _log_operation(
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
                    result
                    for result in results
                    if result.get("status") == "enqueued"
                ]
            ),
            "failed": len([r for r in results if r.get("status") == "failed"]),
            "results": results,
        },
        status=202,
    )
