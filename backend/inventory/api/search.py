from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from inventory.models import Device, FiberCable, Site

logger = logging.getLogger(__name__)

MAX_PER_TYPE = 6


@require_GET
@login_required
def api_global_search(request: HttpRequest) -> JsonResponse:
    """Quick global search across cables, devices and sites.

    GET /api/v1/inventory/search/?q=<term>

    Returns up to MAX_PER_TYPE results per type, each with enough info
    to centre the map (lat/lng) and identify the element (type, id, name).
    """
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})

    results: list[dict] = []

    # ── Cables ────────────────────────────────────────────────────────────
    cables = (
        FiberCable.objects.filter(name__icontains=q)
        .select_related("cable_group")
        .only("id", "name", "length_km", "path", "cable_group")[:MAX_PER_TYPE]
    )
    for cable in cables:
        lat, lng = None, None
        if cable.path:
            try:
                centroid = cable.path.centroid
                lng, lat = centroid.x, centroid.y
            except Exception:
                pass
        results.append({
            "type": "cable",
            "id": cable.id,
            "name": cable.name,
            "subtitle": (
                f"{cable.length_km:.2f} km"
                + (f" · {cable.cable_group.name}" if cable.cable_group else "")
            ),
            "lat": lat,
            "lng": lng,
        })

    # ── Devices ───────────────────────────────────────────────────────────
    devices = (
        Device.objects.filter(name__icontains=q)
        .select_related("site")
        .only("id", "name", "site__display_name", "site__latitude", "site__longitude")
        [:MAX_PER_TYPE]
    )
    for device in devices:
        site = device.site
        lat = float(site.latitude) if site.latitude is not None else None
        lng = float(site.longitude) if site.longitude is not None else None
        results.append({
            "type": "device",
            "id": device.id,
            "name": device.name,
            "subtitle": site.display_name if site else "",
            "lat": lat,
            "lng": lng,
        })

    # ── Sites ─────────────────────────────────────────────────────────────
    sites = (
        Site.objects.filter(display_name__icontains=q)
        .only("id", "display_name", "city", "state", "latitude", "longitude")
        [:MAX_PER_TYPE]
    )
    for site in sites:
        lat = float(site.latitude) if site.latitude is not None else None
        lng = float(site.longitude) if site.longitude is not None else None
        city_state = ", ".join(filter(None, [site.city, site.state]))
        results.append({
            "type": "site",
            "id": site.id,
            "name": site.display_name,
            "subtitle": city_state,
            "lat": lat,
            "lng": lng,
        })

    return JsonResponse({"results": results})
