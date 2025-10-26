from __future__ import annotations

import json
import logging
from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .decorators import handle_api_errors
from .guards import diagnostics_guard, staff_guard
from .services.zabbix_service import zabbix_request as _zabbix_request
from .usecases import inventory as inventory_uc
from .usecases import fibers as fiber_uc
from .usecases.fibers import FiberNotFound, FiberValidationError, FiberUseCaseError
from .usecases.inventory import (
    InventoryNotFound,
    InventoryValidationError,
    InventoryUseCaseError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ENDPOINTS CORRIGIDOS (arquivo estava corrompido anteriormente)
# Apenas implementações essenciais; podem ser expandidas depois.
# ---------------------------------------------------------------------------

@require_GET
@login_required
@handle_api_errors
def api_update_cable_oper_status(request, cable_id: int):
    """Atualiza e retorna status operacional de um cabo de fibra."""
    try:
        payload = fiber_uc.update_cable_oper_status(cable_id)
    except FiberNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)

@require_GET
@login_required
@handle_api_errors
def api_device_port_optical_status(request, port_id: int):
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
def api_device_ports(request, device_id: int):
    try:
        payload = inventory_uc.get_device_ports(device_id)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)

@require_GET
@login_required
@handle_api_errors
def api_device_ports_with_optical(request, device_id: int):
    try:
        payload = inventory_uc.get_device_ports_with_optical(device_id)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)

@require_POST
@login_required
@handle_api_errors
def api_add_device_from_zabbix(request):
    guard = diagnostics_guard(request)
    if guard:
        return guard
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    try:
        payload = inventory_uc.add_device_from_zabbix(data)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except InventoryUseCaseError as exc:  # pragma: no cover
        logger.exception("Falha ao cadastrar device via Zabbix: %s", exc)
        return JsonResponse({"error": "Erro ao cadastrar device"}, status=500)
    return JsonResponse(payload)

@require_GET
@login_required
@handle_api_errors
def api_zabbix_discover_hosts(request):
    payload = inventory_uc.discover_zabbix_hosts()
    return JsonResponse(payload)

@require_POST
@login_required
@handle_api_errors
def api_bulk_create_inventory(request):
    guard = diagnostics_guard(request)
    if guard:
        return guard
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("JSON inválido")
    try:
        payload = inventory_uc.bulk_create_inventory(data)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryUseCaseError as exc:  # pragma: no cover
        logger.exception("Falha no bulk create: %s", exc)
        return JsonResponse({"error": "Erro ao criar inventário"}, status=500)
    return JsonResponse(payload)

@require_GET
@login_required
@handle_api_errors
def api_sites(request):
    payload = inventory_uc.list_sites()
    return JsonResponse(payload)

@require_GET
@handle_api_errors
def api_port_traffic_history(request, port_id: int):
    try:
        payload = inventory_uc.port_traffic_history(port_id, request.GET)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryUseCaseError as exc:  # pragma: no cover
        logger.exception("Erro ao consultar histórico de tráfego: %s", exc)
        return JsonResponse({"error": "Erro ao consultar histórico"}, status=500)
    return JsonResponse(payload)

# FIBERS (implementações mínimas)
@require_GET
@login_required
@handle_api_errors
def api_fiber_cables(request):
    return JsonResponse({"fibers": fiber_uc.list_fiber_cables()})

@require_GET
@login_required
@handle_api_errors
def api_fiber_detail(request, cable_id: int):
    try:
        cable = fiber_uc.get_fiber_cable(cable_id)
    except FiberNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(fiber_uc.fiber_detail_payload(cable))

@require_GET
@login_required
@handle_api_errors
def api_fiber_live_status(request, cable_id: int):
    try:
        cable = fiber_uc.get_fiber_cable(cable_id)
    except FiberNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    status = fiber_uc.compute_live_status(cable, persist=False, event_reason="live-status")
    return JsonResponse(fiber_uc.live_status_payload(cable, status, persist=False))

@require_GET
@login_required
@handle_api_errors
def api_fibers_live_status_all(request):
    cables = [fiber_uc.get_fiber_cable(c.id) for c in fiber_uc.FiberCable.objects.all()]
    results, _ = fiber_uc.bulk_live_status(cables, persist=False)
    return JsonResponse({"results": results})

@require_GET
@login_required
@handle_api_errors
def api_fibers_refresh_status(request):
    cables = fiber_uc.FiberCable.objects.all()
    payload = fiber_uc.refresh_fibers_status(cables)
    return JsonResponse(payload)

@require_GET
@login_required
@handle_api_errors
def api_cable_value_mapping_status(request, cable_id: int):
    try:
        cable = fiber_uc.get_fiber_cable(cable_id)
    except FiberNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    result = fiber_uc.cable_value_mapping_status(cable, None, None)
    return JsonResponse(result)

@require_POST
@login_required
@handle_api_errors
def api_import_fiber_kml(request):
    guard = staff_guard(request)
    if guard:
        return guard
    try:
        name = request.POST.get("name", "").strip()
        origin_device_id = request.POST.get("origin_device_id")
        dest_device_id = request.POST.get("dest_device_id")
        origin_port_id = request.POST.get("origin_port_id")
        dest_port_id = request.POST.get("dest_port_id")
        kml_file = request.FILES.get("kml_file")
        if not kml_file:
            return JsonResponse({"error": "Arquivo KML ausente"}, status=400)
        fiber = fiber_uc.create_fiber_from_kml(
            name,
            origin_device_id,
            dest_device_id,
            origin_port_id,
            dest_port_id,
            kml_file,
        )
        return JsonResponse(fiber)
    except FiberValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

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
        return JsonResponse({"error": "JSON inválido"}, status=400)
    try:
        result = fiber_uc.create_manual_fiber(data)
    except FiberValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except FiberUseCaseError as exc:  # pragma: no cover
        logger.exception("Falha ao criar fibra manual: %s", exc)
        return JsonResponse({"error": "Erro ao criar fibra manual"}, status=500)
    return JsonResponse(result["payload"])

@require_GET
@login_required
def import_kml_modal(request):  # simples placeholder HTML/JSON
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
    "import_kml_modal",
    "api_fiber_cables",
    "api_fiber_detail",
    "api_fiber_live_status",
    "api_fibers_live_status_all",
    "api_fibers_refresh_status",
    "api_cable_value_mapping_status",
    "api_create_manual_fiber",
]

@require_GET
@login_required
@handle_api_errors
def api_device_port_optical_status(request, port_id):
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
def api_device_ports(request, device_id):
    try:
        payload = inventory_uc.get_device_ports(device_id)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_device_ports_with_optical(request, device_id):
    try:
        payload = inventory_uc.get_device_ports_with_optical(device_id)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)


@require_POST
@login_required
@handle_api_errors
def api_add_device_from_zabbix(request):
    guard = diagnostics_guard(request)
    if guard:
        return guard

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    try:
        payload = inventory_uc.add_device_from_zabbix(data)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except InventoryUseCaseError as exc:
        logger.exception("Falha ao cadastrar device via Zabbix: %s", exc)
        return JsonResponse({"error": "Erro ao cadastrar device"}, status=500)

    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_zabbix_discover_hosts(request):
    payload = inventory_uc.discover_zabbix_hosts()
    return JsonResponse(payload)


@login_required
@handle_api_errors
def api_bulk_create_inventory(request):
    guard = diagnostics_guard(request)
    if guard:
        return guard

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("JSON inválido")

    try:
        payload = inventory_uc.bulk_create_inventory(data)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryUseCaseError as exc:
        logger.exception("Falha no bulk create: %s", exc)
        return JsonResponse({"error": "Erro ao criar inventário"}, status=500)

    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_sites(request):
    payload = inventory_uc.list_sites()
    return JsonResponse(payload)


@require_GET
@handle_api_errors
def api_port_traffic_history(request, port_id):
    try:
        payload = inventory_uc.port_traffic_history(port_id, request.GET)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryUseCaseError as exc:
        logger.exception("Erro ao consultar histórico de tráfego: %s", exc)
        return JsonResponse({"error": "Erro ao consultar histórico"}, status=500)
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
        return JsonResponse({"error": "JSON inválido"}, status=400)

    try:
        result = fiber_uc.create_manual_fiber(data)
    except FiberValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except FiberUseCaseError as exc:
        logger.exception("Falha ao criar fibra manual: %s", exc)
        return JsonResponse({"error": "Erro ao criar fibra manual"}, status=500)

    return JsonResponse(result["payload"])


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
    "fetch_interface_status",
    "combine_cable_status",
    "api_fiber_live_status",
    "api_fibers_live_status_all",
    "api_fibers_refresh_status",
]
