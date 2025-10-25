"""
Views para enfileirar tasks do routes_builder com segurança.

- Protegido por autenticação: @login_required + @user_passes_test(is_staff)
- Safelist de IPs via env ADMIN_IP_SAFELIST="1.2.3.4,10.0.0.0/8"
- Rate limiting simples por usuário/ação (cache)
- Entrada/saída em JSON
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
from typing import List

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.views.decorators.http import require_POST

from celery.result import AsyncResult

from .tasks import (
    build_route,
    build_routes_batch,
    invalidate_route_cache,
    health_check_routes_builder,
)

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
    """
    Safelist por IP. Aceita entradas como:
      - "203.0.113.10"
      - "10.0.0.0/8"
    Se ADMIN_IP_SAFELIST não estiver definida, permite acesso (assumindo rede interna).
    """
    safelist = _parse_ip_safelist()
    if not safelist:
        return True

    cand = request.META.get("HTTP_X_FORWARDED_FOR", "") or request.META.get("REMOTE_ADDR", "")
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


def _require_ip_allowlist(request: HttpRequest):
    if not _is_ip_allowed(request):
        return JsonResponse({"detail": "Forbidden by IP safelist"}, status=403)
    return None


def _get_json_body(request: HttpRequest):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None


def _as_list(value) -> List[int]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


# -------------------------- Rate Limiting -------------------------------

def _rate_limit_key(request: HttpRequest, action: str) -> str:
    user_id = request.user.id if request.user.is_authenticated else "anonymous"
    return f"rate_limit:{action}:{user_id}"


def _check_rate_limit(request: HttpRequest, action: str, *, limit: int = 10, window: int = 60) -> bool:
    """
    Rate limiting simples baseado em cache.
    limit: máximo de requisições por janela
    window: segundos
    """
    key = _rate_limit_key(request, action)
    try:
        current = cache.get(key, 0)
        if current >= limit:
            return False
        cache.set(key, current + 1, timeout=window)
    except Exception:
        # Se Redis estiver offline, permite a requisição (fail-open em dev)
        pass
    return True


# -------------------------- Auditoria -----------------------------------

def _client_ip(request: HttpRequest) -> str:
    if request.META.get("HTTP_X_FORWARDED_FOR"):
        return request.META["HTTP_X_FORWARDED_FOR"].split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _log_operation(request: HttpRequest, action: str, **kwargs):
    user = request.user.username if request.user.is_authenticated else "anonymous"
    logger.info(
        "Admin operation: user=%s ip=%s action=%s %s",
        user,
        _client_ip(request),
        action,
        " ".join(f"{k}={v}" for k, v in kwargs.items()),
    )


# =============================================================================
# Views
# =============================================================================

@login_required
@user_passes_test(lambda u: u.is_staff)
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

    if not _check_rate_limit(request, "enqueue_build_route", limit=20, window=60):  # 20/min por usuário
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = _get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    route_id = body.get("route_id")
    if not isinstance(route_id, int) or route_id <= 0:
        return HttpResponseBadRequest("route_id must be a positive integer")

    force = bool(body.get("force", False))
    options = body.get("options") or {}

    # Validação opcional de existência do objeto
    try:
        from .models import Route
        if not Route.objects.filter(id=route_id).exists():
            return JsonResponse({"error": f"Route {route_id} not found"}, status=404)
    except Exception:
        # Se o model não estiver disponível por qualquer razão, seguimos em frente
        pass

    try:
        res = build_route.apply_async(args=[route_id], kwargs={"force": force, "options": options})
        _log_operation(request, "enqueue_build_route", route_id=route_id, force=force)
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.build_route",
                "task_id": res.id,
                "route_id": route_id,
                "queue": getattr(res, "queue", "maps"),
            },
            status=202,
        )
    except Exception as exc:
        logger.error("Failed to enqueue build_route for %s: %s", route_id, exc)
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff)
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

    if not _check_rate_limit(request, "enqueue_build_routes_batch", limit=10, window=60):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = _get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    route_ids = _as_list(body.get("route_ids"))
    if not route_ids or not all(isinstance(x, int) and x > 0 for x in route_ids):
        return HttpResponseBadRequest("route_ids must be a list of positive integers")

    force = bool(body.get("force", False))

    try:
        res = build_routes_batch.apply_async(kwargs={"route_ids": route_ids, "force": force})
        _log_operation(request, "enqueue_build_routes_batch", route_ids=len(route_ids), force=force)
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.build_routes_batch",
                "task_id": res.id,
                "route_ids": route_ids,
                "queue": getattr(res, "queue", "maps"),
            },
            status=202,
        )
    except Exception as exc:
        logger.error("Failed to enqueue build_routes_batch: %s", exc)
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff)
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

    if not _check_rate_limit(request, "enqueue_invalidate_route_cache", limit=30, window=60):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = _get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    route_id = body.get("route_id")
    if not isinstance(route_id, int) or route_id <= 0:
        return HttpResponseBadRequest("route_id must be a positive integer")

    try:
        res = invalidate_route_cache.apply_async(args=[route_id])
        _log_operation(request, "enqueue_invalidate_route_cache", route_id=route_id)
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.invalidate_route_cache",
                "task_id": res.id,
                "route_id": route_id,
                "queue": getattr(res, "queue", "maps"),
            },
            status=202,
        )
    except Exception as exc:
        logger.error("Failed to enqueue invalidate_route_cache for %s: %s", route_id, exc)
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def enqueue_health_check(request: HttpRequest):
    """Enfileira o health check do routes_builder."""
    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    if not _check_rate_limit(request, "enqueue_health_check", limit=30, window=60):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    try:
        res = health_check_routes_builder.apply_async()
        _log_operation(request, "enqueue_health_check")
        return JsonResponse(
            {
                "status": "enqueued",
                "task": "routes_builder.tasks.health_check_routes_builder",
                "task_id": res.id,
                "queue": getattr(res, "queue", "maps"),
            },
            status=202,
        )
    except Exception as exc:
        logger.error("Failed to enqueue health_check_routes_builder: %s", exc)
        return JsonResponse({"error": "Failed to enqueue task"}, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff)
def task_status(request: HttpRequest, task_id: str):
    """
    Consulta status de uma task Celery específica.
    GET /routes_builder/tasks/status/<task_id>
    """
    # IP safelist mesmo em GET
    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    try:
        result = AsyncResult(task_id)
        response_data = {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready(),
        }
        if result.ready():
            if result.successful():
                response_data["result"] = result.result
            else:
                response_data["error"] = str(result.result)
                response_data["traceback"] = result.traceback
        return JsonResponse(response_data)
    except Exception as exc:
        logger.error("Failed to fetch task status %s: %s", task_id, exc)
        return JsonResponse({"error": "Failed to fetch task status"}, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def enqueue_bulk_operations(request: HttpRequest):
    """
    Enfileira múltiplas operações em uma única requisição.

    Body JSON:
    {
      "operations": [
        {"action": "build", "route_id": 123, "force": true, "options": {...}},
        {"action": "invalidate", "route_id": 123},
        {"action": "build", "route_id": 456}
      ]
    }
    """
    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    if not _check_rate_limit(request, "enqueue_bulk_operations", limit=10, window=60):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    body = _get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    operations = body.get("operations", [])
    if not isinstance(operations, list):
        return HttpResponseBadRequest("operations must be a list")

    results = []

    for op in operations:
        if not isinstance(op, dict):
            continue

        action = op.get("action")
        route_id = op.get("route_id")

        try:
            if action == "build":
                if not isinstance(route_id, int) or route_id <= 0:
                    results.append({"action": action, "route_id": route_id, "status": "failed", "error": "invalid route_id"})
                    continue
                force = bool(op.get("force", False))
                options = op.get("options", {})
                res = build_route.apply_async(args=[route_id], kwargs={"force": force, "options": options})
                results.append({"action": "build", "route_id": route_id, "task_id": res.id, "status": "enqueued"})

            elif action == "invalidate":
                if not isinstance(route_id, int) or route_id <= 0:
                    results.append({"action": action, "route_id": route_id, "status": "failed", "error": "invalid route_id"})
                    continue
                res = invalidate_route_cache.apply_async(args=[route_id])
                results.append({"action": "invalidate", "route_id": route_id, "task_id": res.id, "status": "enqueued"})

            else:
                results.append({"action": action, "route_id": route_id, "status": "skipped", "error": "unknown action"})

        except Exception as exc:
            results.append({"action": action, "route_id": route_id, "status": "failed", "error": str(exc)})

    _log_operation(request, "enqueue_bulk_operations", operations=len(operations))
    return JsonResponse(
        {
            "status": "bulk_enqueued",
            "operations": len(operations),
            "successful": len([r for r in results if r.get("status") == "enqueued"]),
            "failed": len([r for r in results if r.get("status") == "failed"]),
            "results": results,
        },
        status=202,
    )
