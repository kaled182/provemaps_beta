"""
Views para enfileirar tasks do routes_builder com segurança.

- Protegido por autenticação: @login_required + @user_passes_test(is_staff)
- (Opcional) Safelist de IPs via env ADMIN_IP_SAFELIST="1.2.3.4,10.0.0.0/8"
- Entrada/saída em JSON
- NÃO executa nada sincronamente: apenas enfileira as Celery tasks
"""

from __future__ import annotations

import ipaddress
import json
import os
from typing import Iterable, List

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpRequest, HttpResponseBadRequest
from django.views.decorators.http import require_POST

from .tasks import build_route, build_routes_batch, invalidate_route_cache, health_check_routes_builder


# ------------------------------------------------------------------------------
# Helpers de segurança
# ------------------------------------------------------------------------------

def _parse_ip_safelist() -> List[str]:
    raw = os.getenv("ADMIN_IP_SAFELIST", "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def _is_ip_allowed(request: HttpRequest) -> bool:
    """
    Permite request apenas de IPs/intervalos na safelist, se configurada.
    Se ADMIN_IP_SAFELIST não estiver definida, permite acesso (assumindo rede interna).
    Aceita entradas como:
      - "203.0.113.10"
      - "10.0.0.0/8"
    """
    safelist = _parse_ip_safelist()
    if not safelist:
        return True

    # Tenta obter o IP real (por trás de proxy)
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
            # Entrada malformada → ignora
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


# ------------------------------------------------------------------------------
# Views: enfileirar tasks
# ------------------------------------------------------------------------------

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def enqueue_build_route(request: HttpRequest):
    """
    Enfileira a task de construção de uma rota.

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

    body = _get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    route_id = body.get("route_id")
    if not isinstance(route_id, int):
        return HttpResponseBadRequest("route_id (int) is required")

    force = bool(body.get("force", False))
    options = body.get("options") or {}

    res = build_route.apply_async(args=[route_id], kwargs={"force": force, "options": options})
    return JsonResponse(
        {"status": "enqueued", "task": "routes_builder.tasks.build_route", "task_id": res.id, "route_id": route_id},
        status=202,
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def enqueue_build_routes_batch(request: HttpRequest):
    """
    Enfileira a task em lote.

    Body JSON:
    {
      "route_ids": [1,2,3],
      "force": false
    }
    """
    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    body = _get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    route_ids = _as_list(body.get("route_ids"))
    if not route_ids or not all(isinstance(x, int) for x in route_ids):
        return HttpResponseBadRequest("route_ids must be a list of integers")

    force = bool(body.get("force", False))

    res = build_routes_batch.apply_async(kwargs={"route_ids": route_ids, "force": force})
    return JsonResponse(
        {
            "status": "enqueued",
            "task": "routes_builder.tasks.build_routes_batch",
            "task_id": res.id,
            "route_ids": route_ids,
        },
        status=202,
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def enqueue_invalidate_route_cache(request: HttpRequest):
    """
    Enfileira a invalidação de cache de uma rota.

    Body JSON:
    {
      "route_id": 123
    }
    """
    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    body = _get_json_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    route_id = body.get("route_id")
    if not isinstance(route_id, int):
        return HttpResponseBadRequest("route_id (int) is required")

    res = invalidate_route_cache.apply_async(args=[route_id])
    return JsonResponse(
        {
            "status": "enqueued",
            "task": "routes_builder.tasks.invalidate_route_cache",
            "task_id": res.id,
            "route_id": route_id,
        },
        status=202,
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def enqueue_health_check(request: HttpRequest):
    """
    Enfileira o health check do routes_builder (útil para testar worker/fila).
    """
    deny = _require_ip_allowlist(request)
    if deny:
        return deny

    res = health_check_routes_builder.apply_async()
    return JsonResponse(
        {
            "status": "enqueued",
            "task": "routes_builder.tasks.health_check_routes_builder",
            "task_id": res.id,
        },
        status=202,
    )
