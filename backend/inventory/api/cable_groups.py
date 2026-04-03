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
from inventory.models import CableGroup, FiberCable


@require_GET
@login_required
@handle_api_errors
def api_list_cable_groups(request: HttpRequest) -> JsonResponse:
    """Return all cable groups ordered by name."""
    groups = CableGroup.objects.values(
        "id",
        "name",
        "manufacturer",
        "fiber_count",
        "attenuation_db_per_km",
    )
    return JsonResponse({"results": list(groups)})


@require_POST
@login_required
@handle_api_errors
def api_create_cable_group(request: HttpRequest) -> JsonResponse:
    """Create a new cable group."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"error": "name is required"}, status=400)

    if CableGroup.objects.filter(name__iexact=name).exists():
        return JsonResponse(
            {"error": "A group with this name already exists"}, status=400
        )

    group = CableGroup.objects.create(
        name=name,
        manufacturer=(data.get("manufacturer") or "").strip(),
        fiber_count=data.get("fiber_count") or None,
        attenuation_db_per_km=data.get("attenuation_db_per_km") or None,
    )
    return JsonResponse(
        {
            "id": group.id,
            "name": group.name,
            "manufacturer": group.manufacturer,
            "fiber_count": group.fiber_count,
            "attenuation_db_per_km": (
                str(group.attenuation_db_per_km)
                if group.attenuation_db_per_km is not None
                else None
            ),
        },
        status=201,
    )


@require_http_methods(["PATCH"])
@login_required
@handle_api_errors
def api_update_cable_group(request: HttpRequest, group_id: int) -> JsonResponse:
    """Rename an existing cable group."""
    try:
        group = CableGroup.objects.get(id=group_id)
    except CableGroup.DoesNotExist:
        return JsonResponse({"error": "Group not found"}, status=404)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"error": "name is required"}, status=400)

    if CableGroup.objects.filter(name__iexact=name).exclude(id=group_id).exists():
        return JsonResponse({"error": "A group with this name already exists"}, status=400)

    group.name = name

    if "fiber_count" in data:
        raw_fc = data.get("fiber_count")
        group.fiber_count = int(raw_fc) if raw_fc not in (None, "") else None

    if "attenuation_db_per_km" in data:
        raw_att = data.get("attenuation_db_per_km")
        try:
            group.attenuation_db_per_km = float(raw_att) if raw_att not in (None, "") else None
        except (ValueError, TypeError):
            group.attenuation_db_per_km = None

    group.save()
    return JsonResponse({
        "id": group.id,
        "name": group.name,
        "fiber_count": group.fiber_count,
        "attenuation_db_per_km": (
            str(group.attenuation_db_per_km) if group.attenuation_db_per_km is not None else None
        ),
    })


@require_http_methods(["DELETE"])
@login_required
@handle_api_errors
def api_delete_cable_group(request: HttpRequest, group_id: int) -> HttpResponse:
    """Delete a cable group, unlinking any cables that reference it."""
    try:
        group = CableGroup.objects.get(id=group_id)
    except CableGroup.DoesNotExist:
        return JsonResponse({"error": "Group not found"}, status=404)

    FiberCable.objects.filter(cable_group=group).update(cable_group=None)
    group.delete()
    return HttpResponse(status=204)
