from __future__ import annotations

import json

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import (
    require_GET,
    require_POST,
    require_http_methods,
)

from django.contrib.auth.decorators import login_required

from integrations.zabbix.decorators import handle_api_errors
from inventory.models import CableType, FiberCable


def _type_dict(t: CableType) -> dict:
    return {"id": t.id, "name": t.name, "order": t.order}


@require_GET
@login_required
@handle_api_errors
def api_list_cable_types(request: HttpRequest) -> JsonResponse:
    """Return all cable types ordered by order, name."""
    types = CableType.objects.all()
    return JsonResponse({"results": [_type_dict(t) for t in types]})


@require_POST
@login_required
@handle_api_errors
def api_create_cable_type(request: HttpRequest) -> JsonResponse:
    """Create a new cable type."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"error": "name is required"}, status=400)

    if CableType.objects.filter(name__iexact=name).exists():
        return JsonResponse(
            {"error": "A type with this name already exists"}, status=400
        )

    order = CableType.objects.count()
    ct = CableType.objects.create(name=name, order=order)
    return JsonResponse(_type_dict(ct), status=201)


@require_http_methods(["PATCH"])
@login_required
@handle_api_errors
def api_update_cable_type(request: HttpRequest, type_id: int) -> JsonResponse:
    """Rename an existing cable type."""
    try:
        ct = CableType.objects.get(id=type_id)
    except CableType.DoesNotExist:
        return JsonResponse({"error": "Type not found"}, status=404)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"error": "name is required"}, status=400)

    if CableType.objects.filter(name__iexact=name).exclude(id=type_id).exists():
        return JsonResponse({"error": "A type with this name already exists"}, status=400)

    ct.name = name
    ct.save()
    return JsonResponse(_type_dict(ct))


@require_http_methods(["DELETE"])
@login_required
@handle_api_errors
def api_delete_cable_type(request: HttpRequest, type_id: int) -> HttpResponse:
    """Delete a cable type, unlinking any cables that reference it."""
    try:
        ct = CableType.objects.get(id=type_id)
    except CableType.DoesNotExist:
        return JsonResponse({"error": "Type not found"}, status=404)

    FiberCable.objects.filter(cable_type=ct).update(cable_type=None)
    ct.delete()
    return HttpResponse(status=204)
