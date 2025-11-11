"""REST endpoints that back the fiber route builder UI."""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from .models import Device, Port, Route, Site

JsonDict = dict[str, Any]


def _parse_json_body(request: HttpRequest) -> JsonDict:
    """Return request body as JSON, raising ValueError on malformed payload."""

    try:
        raw_body = request.body or b"{}"
        return json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON payload") from exc


@require_GET
@login_required
def list_sites(request: HttpRequest) -> JsonResponse:
    """Return all sites that have coordinates available."""

    site_rows = (
        Site.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .order_by("display_name")
        .values(
            "id",
            "display_name",
            "latitude",
            "longitude",
            "city",
            "state",
        )
    )

    sites: list[JsonDict] = []
    for row in site_rows:
        sites.append(
            {
                "id": row["id"],
                "display_name": row["display_name"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "city": row["city"],
                "state": row["state"],
            }
        )

    return JsonResponse({"sites": sites})


@require_GET
@login_required
def list_routes(request: HttpRequest) -> JsonResponse:
    """Return saved fiber routes with origin/destination metadata."""

    base_qs = Route.objects.select_related(
        "origin_port__device__site",
        "destination_port__device__site",
    )

    annotated = base_qs.annotate(
        origin_site_name=F("origin_port__device__site__display_name"),
        destination_site_name=F(
            "destination_port__device__site__display_name"
        ),
        origin_site_lat=F("origin_port__device__site__latitude"),
        origin_site_lng=F("origin_port__device__site__longitude"),
        destination_site_lat=F(
            "destination_port__device__site__latitude"
        ),
        destination_site_lng=F(
            "destination_port__device__site__longitude"
        ),
    )

    value_rows = annotated.order_by("name").values(
        "id",
        "name",
        "description",
        "status",
        "length_km",
        "estimated_loss_db",
        "measured_loss_db",
        "created_at",
        "origin_site_name",
        "destination_site_name",
        "origin_site_lat",
        "origin_site_lng",
        "destination_site_lat",
        "destination_site_lng",
    )

    routes: list[JsonDict] = []
    for row in value_rows:
        payload: JsonDict = dict(row)
        for field in (
            "length_km",
            "estimated_loss_db",
            "measured_loss_db",
            "origin_site_lat",
            "origin_site_lng",
            "destination_site_lat",
            "destination_site_lng",
        ):
            if payload[field] is not None:
                payload[field] = float(payload[field])
        if payload["created_at"] is not None:
            payload["created_at"] = payload["created_at"].isoformat()
        routes.append(payload)

    return JsonResponse({"routes": routes})


@require_http_methods(["POST"])
@login_required
def calculate_route(request: HttpRequest) -> JsonResponse:
    """Return attenuation estimate for a requested site pair."""

    try:
        data = _parse_json_body(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    origin_site_id = data.get("origin_site_id")
    destination_site_id = data.get("destination_site_id")
    distance_km = data.get("distance_km")

    if not all([origin_site_id, destination_site_id, distance_km]):
        return JsonResponse(
            {"error": "Missing required parameters"}, status=400
        )

    try:
        origin_site = Site.objects.get(id=origin_site_id)
        destination_site = Site.objects.get(id=destination_site_id)
    except Site.DoesNotExist as exc:
        return JsonResponse({"error": str(exc)}, status=404)

    attenuation_per_km = Decimal("0.3")
    estimated_loss = Decimal(str(distance_km)) * attenuation_per_km

    response = {
        "success": True,
        "route_data": {
            "origin_site": {
                "id": origin_site.id,
                "name": origin_site.display_name,
                "lat": float(origin_site.latitude)
                if origin_site.latitude is not None
                else None,
                "lng": float(origin_site.longitude)
                if origin_site.longitude is not None
                else None,
            },
            "destination_site": {
                "id": destination_site.id,
                "name": destination_site.display_name,
                "lat": float(destination_site.latitude)
                if destination_site.latitude is not None
                else None,
                "lng": float(destination_site.longitude)
                if destination_site.longitude is not None
                else None,
            },
            "distance_km": distance_km,
            "estimated_loss_db": float(estimated_loss),
        },
    }

    return JsonResponse(response)


@require_http_methods(["POST"])
@login_required
@transaction.atomic
def save_route(request: HttpRequest) -> JsonResponse:
    """Persist a calculated fiber route."""

    try:
        data = _parse_json_body(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    required_fields = (
        "name",
        "origin_site_id",
        "destination_site_id",
        "distance_km",
        "estimated_loss_db",
    )
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return JsonResponse(
            {
                "error": (
                    "Missing required route parameters: "
                    + ", ".join(missing)
                )
            },
            status=400,
        )

    origin_site = Site.objects.filter(id=data["origin_site_id"]).first()
    destination_site = Site.objects.filter(
        id=data["destination_site_id"]
    ).first()
    if not origin_site or not destination_site:
        return JsonResponse(
            {"error": "Origin and destination sites must exist"}, status=404
        )

    origin_device, _ = Device.objects.get_or_create(
        site=origin_site,
        name=f"{origin_site.display_name} - Main",
        defaults={"vendor": "Generic", "model": "Router"},
    )
    destination_device, _ = Device.objects.get_or_create(
        site=destination_site,
        name=f"{destination_site.display_name} - Main",
        defaults={"vendor": "Generic", "model": "Router"},
    )

    origin_port, _ = Port.objects.get_or_create(
        device=origin_device,
        name="fiber-out",
        defaults={
            "notes": "Automatically created for route builder",
        },
    )
    destination_port, _ = Port.objects.get_or_create(
        device=destination_device,
        name="fiber-in",
        defaults={
            "notes": "Automatically created for route builder",
        },
    )

    route = Route.objects.create(
        name=data["name"],
        description=data.get("description", ""),
        origin_port=origin_port,
        destination_port=destination_port,
        length_km=Decimal(str(data["distance_km"])),
        estimated_loss_db=Decimal(str(data["estimated_loss_db"])),
        status=Route.STATUS_PLANNED,
        last_built_at=timezone.now(),
        last_built_by=request.user.username,
        import_source="web_route_builder",
    )

    return JsonResponse(
        {
            "success": True,
            "route_id": route.id,
            "message": f"Route '{route.name}' created successfully",
        }
    )
