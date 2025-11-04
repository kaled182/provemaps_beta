from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, cast

from django.contrib.auth.decorators import login_required
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.views.decorators.http import require_GET, require_POST

from .decorators import api_login_required, handle_api_errors
from .guards import diagnostics_guard, staff_guard
from .services.zabbix_service import zabbix_request as _zabbix_request
from .usecases import inventory as inventory_uc
from .usecases import fibers as fiber_uc
from .usecases.fibers import (
    FiberNotFound,
    FiberUseCaseError,
    FiberValidationError,
)
from .usecases.inventory import (
    InventoryNotFound,
    InventoryValidationError,
    InventoryUseCaseError,
)

logger = logging.getLogger(__name__)

# Maintain compatibility with legacy code that imports zabbix_request
# from here.
zabbix_request = _zabbix_request

JsonDict = Dict[str, Any]


def _load_json_body(request: HttpRequest) -> JsonDict:
    """Parse a JSON request body and guarantee a dictionary response."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON payload") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON payload must be an object")
    return cast(JsonDict, data)


@require_GET
@login_required
@handle_api_errors
def api_update_cable_oper_status(
    request: HttpRequest,
    cable_id: int,
) -> HttpResponse:
    """Update and return the operational status of a fiber cable."""
    try:
        update_oper_status = cast(
            Callable[[int], JsonDict],
            getattr(fiber_uc, "update_cable_oper_status"),
        )
        payload = update_oper_status(cable_id)
    except FiberNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_device_port_optical_status(
    request: HttpRequest,
    port_id: int,
) -> HttpResponse:
    try:
        payload = inventory_uc.device_port_optical_status(port_id)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_device_ports(
    request: HttpRequest,
    device_id: int,
) -> HttpResponse:
    try:
        payload = inventory_uc.get_device_ports(device_id)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_device_ports_with_optical(
    request: HttpRequest,
    device_id: int,
) -> HttpResponse:
    try:
        payload = inventory_uc.get_device_ports_with_optical(device_id)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)


@require_POST
@login_required
@handle_api_errors
def api_add_device_from_zabbix(request: HttpRequest) -> HttpResponse:
    guard_response = diagnostics_guard(request)
    if guard_response is not None:
        return guard_response

    try:
        data = _load_json_body(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    try:
        payload = inventory_uc.add_device_from_zabbix(data)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except InventoryUseCaseError as exc:  # pragma: no cover
        logger.exception("Failed to register device via Zabbix: %s", exc)
        return JsonResponse(
            {"error": "Failed to register device"},
            status=500,
        )
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_zabbix_discover_hosts(request: HttpRequest) -> HttpResponse:
    payload = inventory_uc.discover_zabbix_hosts()
    return JsonResponse(payload)


@require_POST
@login_required
@handle_api_errors
def api_bulk_create_inventory(request: HttpRequest) -> HttpResponse:
    guard_response = diagnostics_guard(request)
    if guard_response is not None:
        return guard_response

    try:
        data = _load_json_body(request)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))

    try:
        payload = inventory_uc.bulk_create_inventory(data)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryUseCaseError as exc:  # pragma: no cover
        logger.exception("Bulk create failed: %s", exc)
        return JsonResponse(
            {"error": "Failed to create inventory"},
            status=500,
        )
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_sites(request: HttpRequest) -> HttpResponse:
    payload = inventory_uc.list_sites()
    return JsonResponse(payload)


@require_GET
@handle_api_errors
def api_port_traffic_history(
    request: HttpRequest,
    port_id: int,
) -> HttpResponse:
    try:
        payload = inventory_uc.port_traffic_history(port_id, request.GET)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryUseCaseError as exc:  # pragma: no cover
        logger.exception("Failed to fetch traffic history: %s", exc)
        return JsonResponse(
            {"error": "Failed to fetch traffic history"},
            status=500,
        )
    return JsonResponse(payload)


# Fiber endpoints (minimal subset)
@require_GET
@api_login_required
@handle_api_errors
def api_fiber_cables(request: HttpRequest) -> HttpResponse:
    return JsonResponse({"fibers": fiber_uc.list_fiber_cables()})


@require_GET
@api_login_required
@handle_api_errors
def api_fiber_detail(request: HttpRequest, cable_id: int) -> HttpResponse:
    try:
        cable = fiber_uc.get_fiber_cable(cable_id)
    except FiberNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(fiber_uc.fiber_detail_payload(cable))


@require_GET
@login_required
@handle_api_errors
def api_fiber_live_status(
    request: HttpRequest,
    cable_id: int,
) -> HttpResponse:
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
def api_fibers_live_status_all(request: HttpRequest) -> HttpResponse:
    cables = [
        fiber_uc.get_fiber_cable(c.pk)
        for c in fiber_uc.FiberCable.objects.all()
    ]
    results, _ = fiber_uc.bulk_live_status(cables, persist=False)
    return JsonResponse({"results": results})


@require_GET
@login_required
@handle_api_errors
def api_fibers_refresh_status(request: HttpRequest) -> HttpResponse:
    cables = fiber_uc.FiberCable.objects.all()
    payload = fiber_uc.refresh_fibers_status(cables)
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_cable_value_mapping_status(
    request: HttpRequest,
    cable_id: int,
) -> HttpResponse:
    try:
        cable = fiber_uc.get_fiber_cable(cable_id)
    except FiberNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    result = fiber_uc.cable_value_mapping_status(cable, None, None)
    return JsonResponse(result)


@require_POST
@login_required
@handle_api_errors
def api_import_fiber_kml(request: HttpRequest) -> HttpResponse:
    guard_response = staff_guard(request)
    if guard_response is not None:
        return guard_response

    try:
        name = (request.POST.get("name", "") or "").strip()
        origin_device_id = (request.POST.get("origin_device_id") or "").strip()
        dest_device_id = (request.POST.get("dest_device_id") or "").strip()
        origin_port_id = (request.POST.get("origin_port_id") or "").strip()
        dest_port_id = (request.POST.get("dest_port_id") or "").strip()
        kml_file = cast(Any, request.FILES.get("kml_file"))
        if not kml_file:
            return JsonResponse({"error": "Missing KML file"}, status=400)
        create_fiber = getattr(fiber_uc, "create_fiber_from_kml")
        fiber_data = cast(
            JsonDict,
            create_fiber(
                name,
                origin_device_id,
                dest_device_id,
                origin_port_id,
                dest_port_id,
                kml_file,
            ),
        )
        return JsonResponse(fiber_data)
    except FiberValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@require_POST
@login_required
@handle_api_errors
def api_create_manual_fiber(request: HttpRequest) -> HttpResponse:
    guard_response = staff_guard(request)
    if guard_response is not None:
        return guard_response

    try:
        data = _load_json_body(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    try:
        result = fiber_uc.create_manual_fiber(data)
    except FiberValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except FiberUseCaseError as exc:  # pragma: no cover
        logger.exception("Failed to create manual fiber: %s", exc)
        return JsonResponse(
            {"error": "Failed to create manual fiber"},
            status=500,
        )
    return JsonResponse(result["payload"])


@require_GET
@login_required
def import_kml_modal(request: HttpRequest) -> HttpResponse:
    """Return a minimal placeholder payload used by the KML modal."""
    return JsonResponse({"modal": True, "status": "ok"})


__all__ = [
    "api_update_cable_oper_status",
    "api_device_port_optical_status",
    "api_device_ports",
    "api_device_ports_with_optical",
    "api_add_device_from_zabbix",
    "api_zabbix_discover_hosts",
    "api_bulk_create_inventory",
    "api_sites",
    "api_port_traffic_history",
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

