from __future__ import annotations

import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from django.contrib.auth.decorators import login_required

from integrations.zabbix.decorators import handle_api_errors
from inventory.models import Responsible


@require_GET
@login_required
@handle_api_errors
def api_list_responsibles(request: HttpRequest) -> JsonResponse:
    """Return all responsibles ordered by name."""
    items = Responsible.objects.values("id", "name", "email", "phone", "type")
    return JsonResponse({"results": list(items)})


@require_POST
@login_required
@handle_api_errors
def api_create_responsible(request: HttpRequest) -> JsonResponse:
    """Create a new responsible."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"error": "name is required"}, status=400)

    valid_types = [c[0] for c in Responsible.TypeChoices.choices]
    type_value = (data.get("type") or "").strip()
    if type_value and type_value not in valid_types:
        return JsonResponse({"error": f"type must be one of: {valid_types}"}, status=400)

    responsible = Responsible.objects.create(
        name=name,
        email=(data.get("email") or "").strip(),
        phone=(data.get("phone") or "").strip(),
        type=type_value or Responsible.TypeChoices.TECHNICIAN,
    )
    return JsonResponse(
        {
            "id": responsible.id,
            "name": responsible.name,
            "email": responsible.email,
            "phone": responsible.phone,
            "type": responsible.type,
            "type_display": responsible.get_type_display(),
        },
        status=201,
    )
