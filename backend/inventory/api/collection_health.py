"""Saúde da coleta óptica (EV-0085).

GET /api/v1/inventory/collection-health/?stale_hours=2
Equipamentos com host Zabbix inexistente, equipamentos sem nenhuma leitura e as portas
com chave óptica sem leitura, com o motivo. A lógica vive em
``inventory.usecases.collection_health``.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from integrations.zabbix.decorators import handle_api_errors
from inventory.usecases.collection_health import (
    STALE_HOURS_DEFAULT,
    STALE_HOURS_MAX,
    STALE_HOURS_MIN,
    collection_health,
)


@require_GET
@login_required
@handle_api_errors
def api_collection_health(request: HttpRequest) -> JsonResponse:
    raw = (request.GET.get("stale_hours") or "").strip()
    if not raw:
        stale_hours = STALE_HOURS_DEFAULT
    else:
        try:
            stale_hours = int(raw)
        except ValueError:
            stale_hours = 0
        if not STALE_HOURS_MIN <= stale_hours <= STALE_HOURS_MAX:
            return JsonResponse(
                {
                    "error": (
                        f"stale_hours deve ser um inteiro entre {STALE_HOURS_MIN} "
                        f"e {STALE_HOURS_MAX}"
                    )
                },
                status=400,
            )
    return JsonResponse(collection_health(stale_hours=stale_hours))
