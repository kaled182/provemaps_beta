from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
)

from integrations.zabbix.decorators import (
    api_login_required,
    handle_api_errors,
)
from integrations.zabbix.guards import diagnostics_guard, staff_guard

from inventory.models import Device, FiberCable
from inventory.usecases import fibers as fiber_uc
from inventory.usecases.fibers import (
    FiberNotFound,
    FiberUseCaseError,
    FiberValidationError,
)
from inventory.cache.fibers import get_cached_fiber_list

logger = logging.getLogger(__name__)


@require_POST
@api_login_required
@handle_api_errors
def api_import_fiber_kml(request: HttpRequest) -> JsonResponse:
    """Import a KML file and create a fiber route using extracted points."""
    guard = diagnostics_guard(request)
    if guard:
        return guard

    name = (request.POST.get("name") or "").strip()
    origin_device_id = request.POST.get("origin_device_id")
    dest_device_id = request.POST.get("dest_device_id")
    origin_port_id = request.POST.get("origin_port_id")
    dest_port_id = request.POST.get("dest_port_id")
    single_port = request.POST.get("single_port") == "true"
    kml_file = request.FILES.get("kml_file")

    if not (name and origin_device_id and origin_port_id and kml_file):
        return JsonResponse({"error": "Missing required fields"}, status=400)

    if not single_port and not (dest_device_id and dest_port_id):
        return JsonResponse(
            {
                "error": (
                    "Destination port required when single port mode is off"
                ),
            },
            status=400,
        )

    if single_port:
        dest_device_id = origin_device_id
        dest_port_id = origin_port_id

    try:
        payload = fiber_uc.create_fiber_from_kml(
            str(name),
            str(origin_device_id),
            str(dest_device_id),
            str(origin_port_id),
            str(dest_port_id),
            kml_file,
            single_port=single_port,
        )
    except FiberValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except FiberUseCaseError as exc:
        return JsonResponse({"error": str(exc)}, status=500)

    return JsonResponse(payload)


@api_login_required
@handle_api_errors
def api_cable_value_mapping_status(
    request: HttpRequest,
    cable_id: int,
) -> JsonResponse:
    """Fetch cable status using a Zabbix 0/1 value map."""
    guard = diagnostics_guard(request)
    if guard:
        return guard

    try:
        cable = FiberCable.objects.select_related(
            "origin_port__device",
            "destination_port__device",
        ).get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)

    payload = fiber_uc.cable_value_mapping_status(
        cable,
        request.GET.get("item_key_origin"),
        request.GET.get("item_key_dest"),
    )
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def import_kml_modal(request: HttpRequest) -> HttpResponse:
    """Render the KML import modal with the device list."""
    devices = Device.objects.all().order_by("name")
    return render(
        request,
        "partials/import_kml.html",
        {
            "devices": devices,
        },
    )


@require_GET
@api_login_required
@handle_api_errors
def api_fiber_cables(request: HttpRequest) -> JsonResponse:
    """List all fiber cables with detailed information (cached with SWR)."""
    data, is_fresh = get_cached_fiber_list(fiber_uc.list_fiber_cables)
    
    response = JsonResponse({"cables": data})
    
    # Add cache headers to help client-side caching
    if is_fresh:
        response["Cache-Control"] = "public, max-age=60"
    else:
        response["Cache-Control"] = "public, max-age=300, stale-while-revalidate=300"
    
    return response


@require_GET
@login_required
@handle_api_errors
def api_fibers_oper_status(request: HttpRequest) -> JsonResponse:
    """
    Return operational status metadata for one or more cables.
    
    OPTIMIZED: Reads from pre-calculated cache populated by Celery task
    instead of making synchronous Zabbix calls on every request.
    
    This prevents the "hundreds of Zabbix queries" bottleneck that
    was causing 30+ second delays in the dashboard.
    """
    from django.core.cache import cache

    ids_param = (request.GET.get("ids") or "").strip()
    cables_qs = FiberCable.objects.all()
    requested_ids: list[int] = []

    if ids_param:
        for raw in ids_param.split(","):
            try:
                requested_ids.append(int(raw.strip()))
            except ValueError:
                continue

        if requested_ids:
            cables_qs = cables_qs.filter(id__in=requested_ids)
        else:
            cables_qs = FiberCable.objects.none()

    cable_ids = [int(pk) for pk in cables_qs.values_list("id", flat=True)]
    present_ids = set(cable_ids)
    missing_ids = [cid for cid in requested_ids if cid not in present_ids]

    # NEW: Read from cache instead of calling Zabbix
    results = []
    cache_misses = []
    
    for cable_id in cable_ids:
        cache_key = f"cable:oper_status:{cable_id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            results.append(cached_data)
        else:
            # Fallback: If cache miss, compute on-demand
            # (this should be rare once Celery task is running)
            cache_misses.append(cable_id)
            status_data = fiber_uc.update_cable_oper_status(cable_id)
            results.append(status_data)
            # Store for next time (2-minute cache)
            cache.set(cache_key, status_data, timeout=120)

    payload: dict[str, object] = {"results": results}
    if missing_ids:
        payload["missing_ids"] = missing_ids
    if cache_misses:
        payload["cache_misses"] = cache_misses  # For debugging
    
    return JsonResponse(payload)


@require_http_methods(["GET", "PUT", "DELETE"])
@api_login_required
@handle_api_errors
def api_fiber_detail(
    request: HttpRequest,
    cable_id: int,
) -> HttpResponse:
    try:
        cable = fiber_uc.get_fiber_cable(cable_id)
    except FiberNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)

    if request.method == "GET":
        return JsonResponse(fiber_uc.fiber_detail_payload(cable))

    guard = staff_guard(request)
    if guard:
        return guard

    if request.method == "DELETE":
        fiber_uc.delete_fiber(cable)
        return HttpResponse(status=204)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    updated = False

    if "path" in payload:
        fiber_uc.update_fiber_path(cable, payload["path"])
        updated = True

    metadata_kwargs = {
        "name": payload.get("name"),
        "origin_port_id": payload.get("origin_port_id"),
        "dest_port_id": payload.get("dest_port_id"),
    }

    if any(value is not None for value in metadata_kwargs.values()):
        fiber_uc.update_fiber_metadata(
            cable,
            name=metadata_kwargs["name"],
            origin_port_id=metadata_kwargs["origin_port_id"],
            dest_port_id=metadata_kwargs["dest_port_id"],
        )
        updated = True

    if not updated:
        return JsonResponse(
            {"error": "No updatable fields provided"},
            status=400,
        )

    return JsonResponse(fiber_uc.fiber_detail_payload(cable))


@require_GET
@api_login_required
@handle_api_errors
def api_fiber_live_status(
    request: HttpRequest,
    cable_id: int,
) -> JsonResponse:
    try:
        cable = fiber_uc.get_fiber_cable(cable_id)
    except FiberNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)

    status = fiber_uc.compute_live_status(
        cable,
        persist=False,
        event_reason="live-status",
    )
    payload = fiber_uc.live_status_payload(cable, status, persist=False)
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_fibers_live_status_all(request: HttpRequest) -> JsonResponse:
    cables = [
        fiber_uc.get_fiber_cable(c.pk)
        for c in FiberCable.objects.all()
    ]
    results, _ = fiber_uc.bulk_live_status(cables, persist=False)
    return JsonResponse({"results": results})


@require_GET
@login_required
@handle_api_errors
def api_fibers_refresh_status(request: HttpRequest) -> HttpResponse:
    cables = FiberCable.objects.all()
    payload = fiber_uc.refresh_fibers_status(cables)
    return JsonResponse(payload)


@require_POST
@login_required
@handle_api_errors
def api_create_manual_fiber(request: HttpRequest) -> JsonResponse:
    guard = staff_guard(request)
    if guard:
        return guard

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON payload"},
            status=400,
        )

    try:
        result = fiber_uc.create_manual_fiber(data)
    except FiberValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(result["payload"])


__all__ = [
    "api_import_fiber_kml",
    "api_cable_value_mapping_status",
    "import_kml_modal",
    "api_fiber_cables",
    "api_fiber_detail",
    "api_fiber_live_status",
    "api_fibers_live_status_all",
    "api_fibers_refresh_status",
    "api_create_manual_fiber",
]
