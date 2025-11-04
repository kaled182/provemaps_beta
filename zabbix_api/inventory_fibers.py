from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_http_methods

from inventory.models import Device, FiberCable

from .decorators import api_login_required, handle_api_errors
from .domain.optical import (
    _discover_optical_keys_by_portname,
    _fetch_item_value,
    _fetch_port_optical_snapshot,
    _safe_float,
    _score_optical_candidate,
    fetch_port_optical_snapshot,
)
from .guards import diagnostics_guard, staff_guard
from .services.fiber_status import (
    combine_cable_status as combine_cable_status_service,
    fetch_interface_status_advanced,
)
from .usecases import fibers as fiber_uc

logger = logging.getLogger(__name__)

__all__ = [
    "_safe_float",
    "_fetch_item_value",
    "_score_optical_candidate",
    "_discover_optical_keys_by_portname",
    "_fetch_port_optical_snapshot",
    "fetch_port_optical_snapshot",
    "fetch_interface_status",
    "combine_cable_status",
    "api_import_fiber_kml",
    "api_create_manual_fiber",
    "api_cable_value_mapping_status",
    "import_kml_modal",
    "api_fiber_cables",
    "api_fiber_detail",
    "api_fiber_live_status",
    "api_fibers_live_status_all",
    "api_fibers_refresh_status",
]


@api_login_required
def api_import_fiber_kml(request):
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

    # Validation: single_port allows the destination port to be omitted
    if not (name and origin_device_id and origin_port_id and kml_file):
        return JsonResponse({"error": "Missing required fields"}, status=400)

    # When not in single port mode, destination identifiers are required
    if not single_port and not (dest_device_id and dest_port_id):
        return JsonResponse(
            {
                "error": (
                    "Destination port required when single port mode is off"
                ),
            },
            status=400,
        )

    # In single port mode the destination matches the origin
    if single_port:
        dest_device_id = origin_device_id
        dest_port_id = origin_port_id

    try:
        payload = fiber_uc.create_fiber_from_kml(
            name,
            origin_device_id,
            dest_device_id,
            origin_port_id,
            dest_port_id,
            kml_file,
            single_port=single_port,
        )
    except fiber_uc.FiberValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except fiber_uc.FiberUseCaseError as exc:
        return JsonResponse({"error": str(exc)}, status=500)

    return JsonResponse(payload)



def api_cable_value_mapping_status(request, cable_id):
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



def import_kml_modal(request):
    """Render the KML import modal with the device list."""
    devices = Device.objects.all().order_by("name")
    return render(
        request,
        "partials/import_kml.html",
        {
            "devices": devices,
        },
    )



@api_login_required
def api_fiber_cables(request):
    """List all fiber cables with detailed information."""
    return JsonResponse({"cables": fiber_uc.list_fiber_cables()})



@require_http_methods(["GET", "PUT", "POST", "DELETE"])
@api_login_required
def api_fiber_detail(request, cable_id):
    """Retrieve and update details for a fiber cable path."""
    try:
        cable = fiber_uc.get_fiber_cable(cable_id)
    except fiber_uc.FiberNotFound:
        return JsonResponse({"error": "FiberCable not found"}, status=404)

    if request.method == "GET":
        return JsonResponse(fiber_uc.fiber_detail_payload(cable))

    if request.method == "DELETE":
        fiber_uc.delete_fiber(cable)
        return JsonResponse({}, status=204)

    if request.method in ("POST", "PUT"):
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)

        # Process the path if provided
        path = body.get("path")
        if path is not None:
            if not isinstance(path, list):
                return JsonResponse(
                    {"error": 'Field "path" must be a list of points'},
                    status=400,
                )
            try:
                fiber_uc.update_fiber_path(cable, path)
            except fiber_uc.FiberValidationError as exc:
                return JsonResponse({"error": str(exc)}, status=400)

        # Process metadata when supplied
        name = body.get("name")
        origin_port_id = body.get("origin_port_id")
        dest_port_id = body.get("dest_port_id")

        if name or origin_port_id or dest_port_id:
            try:
                fiber_uc.update_fiber_metadata(
                    cable,
                    name=name if name else None,
                    origin_port_id=(
                        int(origin_port_id) if origin_port_id else None
                    ),
                    dest_port_id=(int(dest_port_id) if dest_port_id else None),
                )
            except fiber_uc.FiberValidationError as exc:
                return JsonResponse({"error": str(exc)}, status=400)

        # Reload from the database to keep data fresh
        cable.refresh_from_db()

        return JsonResponse(fiber_uc.fiber_detail_payload(cable))

    return HttpResponseBadRequest("Method not supported")



def fetch_interface_status(
    hostid,
    primary_item_key=None,
    interfaceid=None,
    rx_key=None,
    tx_key=None,
):
    """Legacy wrapper kept for backwards compatibility."""
    return fetch_interface_status_advanced(
        hostid,
        primary_item_key,
        interfaceid,
        rx_key,
        tx_key,
    )



def combine_cable_status(o_status, d_status):
    """Combine origin and destination into a final cable status."""
    return combine_cable_status_service(o_status, d_status)



def api_fiber_live_status(request, cable_id):
    """Fetch live status for a cable, persisting updates when needed."""
    try:
        cable = fiber_uc.get_fiber_cable(cable_id)
    except fiber_uc.FiberNotFound:
        return JsonResponse({"error": "FiberCable not found"}, status=404)

    persist = request.GET.get("persist", "1").lower() in ("1", "true", "yes")
    status = fiber_uc.compute_live_status(
        cable,
        persist=persist,
        event_reason="live-endpoint",
    )
    payload = fiber_uc.live_status_payload(cable, status, persist)
    return JsonResponse(payload)



def api_fibers_live_status_all(request):
    """Fetch live status for all cables, persisting updates when needed."""
    persist = request.GET.get("persist", "0").lower() in ("1", "true", "yes")
    cables = FiberCable.objects.select_related(
        "origin_port__device",
        "destination_port__device",
    )
    results, changed_any = fiber_uc.bulk_live_status(cables, persist=persist)
    return JsonResponse(
        {
            "cables": results,
            "persist": persist,
            "changed_persisted": changed_any,
        }
    )



def api_fibers_refresh_status(request):
    """Force evaluation and persistence of all cables using advanced logic."""
    if request.method not in ("POST", "PUT"):
        return HttpResponseBadRequest("POST or PUT expected")

    cables = FiberCable.objects.select_related(
        "origin_port__device",
        "destination_port__device",
    )
    payload = fiber_uc.refresh_fibers_status(cables)
    return JsonResponse(payload)



@require_POST
@login_required
@handle_api_errors
def api_create_manual_fiber(request):
    guard = staff_guard(request)
    if guard:
        return guard

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    try:
        result = fiber_uc.create_manual_fiber(data)
    except fiber_uc.FiberValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(result["payload"])
