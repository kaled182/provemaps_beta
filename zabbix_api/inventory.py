from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .decorators import handle_api_errors
from .guards import diagnostics_guard, staff_guard
from .services.zabbix_service import zabbix_request as _zabbix_request
from .usecases import inventory as inventory_uc
from .usecases import fibers as fiber_uc
from .usecases.fibers import FiberUseCaseError, FiberValidationError
from .usecases.inventory import (
    InventoryNotFound,
    InventoryUseCaseError,
    InventoryValidationError,
)
from .inventory_fibers import (
    api_import_fiber_kml,
    api_cable_value_mapping_status,
    import_kml_modal,
    api_fiber_cables,
    api_fiber_detail,
    fetch_interface_status,
    combine_cable_status as fiber_combine_cable_status,
    api_fiber_live_status,
    api_fibers_live_status_all,
    api_fibers_refresh_status,
)

logger = logging.getLogger(__name__)
combine_cable_status = fiber_combine_cable_status
zabbix_request = _zabbix_request


def _call_zabbix_request(method, params=None, **kwargs):
    return zabbix_request(method, params, **kwargs)


inventory_uc.ZABBIX_REQUEST = _call_zabbix_request


@login_required
@handle_api_errors
def api_update_cable_oper_status(request, cable_id):
    try:
        payload = fiber_uc.update_cable_oper_status(cable_id)
    except fiber_uc.FiberNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)


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
        return JsonResponse({"error": "JSON invalido"}, status=400)

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
        return HttpResponseBadRequest("JSON invalido")

    try:
        payload = inventory_uc.bulk_create_inventory(data)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryUseCaseError as exc:
        logger.exception("Falha no bulk create: %s", exc)
        return JsonResponse({"error": "Erro ao criar inventario"}, status=500)

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
        logger.exception("Erro ao consultar historico de traffic: %s", exc)
        return JsonResponse({"error": "Erro ao consultar historico"}, status=500)
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
