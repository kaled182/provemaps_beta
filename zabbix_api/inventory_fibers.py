from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .decorators import handle_api_errors
from .domain.optical import (
    _discover_optical_keys_by_portname,
    _fetch_item_value,
    _fetch_port_optical_snapshot,
    _safe_float,
    _score_optical_candidate,
)
from .guards import diagnostics_guard, staff_guard
from inventory.models import Device, FiberCable
from .services.fiber_status import (
    combine_cable_status as combine_cable_status_service,
    fetch_interface_status_advanced,
)
from .services.zabbix_service import zabbix_request
from .usecases import fibers as fiber_uc

logger = logging.getLogger(__name__)

__all__ = [
    '_safe_float',
    '_fetch_item_value',
    '_score_optical_candidate',
    '_discover_optical_keys_by_portname',
    '_fetch_port_optical_snapshot',
    'fetch_interface_status',
    'combine_cable_status',
    'api_import_fiber_kml',
    'api_create_manual_fiber',
    'api_cable_value_mapping_status',
    'import_kml_modal',
    'api_fiber_cables',
    'api_fiber_detail',
    'api_fiber_live_status',
    'api_fibers_live_status_all',
    'api_fibers_refresh_status',
]

def api_import_fiber_kml(request):
    """
    Importa arquivo KML e cria rota de fibra (FiberCable) com pontos extraídos.
    """
    guard = diagnostics_guard(request)
    if guard:
        return guard

    name = (request.POST.get("name") or "").strip()
    origin_device_id = request.POST.get("origin_device_id")
    dest_device_id = request.POST.get("dest_device_id")
    origin_port_id = request.POST.get("origin_port_id")
    dest_port_id = request.POST.get("dest_port_id")
    kml_file = request.FILES.get("kml_file")

    if not (name and origin_device_id and dest_device_id and origin_port_id and dest_port_id and kml_file):
        return JsonResponse({"error": "Campos obrigatorios ausentes"}, status=400)

    try:
        payload = fiber_uc.create_fiber_from_kml(
            name,
            origin_device_id,
            dest_device_id,
            origin_port_id,
            dest_port_id,
            kml_file,
        )
    except fiber_uc.FiberValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except fiber_uc.FiberUseCaseError as exc:
        return JsonResponse({"error": str(exc)}, status=500)

    return JsonResponse(payload)

def api_cable_value_mapping_status(request, cable_id):
    """
    Obtém status de um cabo baseado em um item Zabbix com value mapping 0/1 (Down/Up).
    """
    guard = diagnostics_guard(request)
    if guard:
        return guard

    try:
        cable = FiberCable.objects.select_related("origin_port__device", "destination_port__device").get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable nao encontrado"}, status=404)

    payload = fiber_uc.cable_value_mapping_status(
        cable,
        request.GET.get("item_key_origin"),
        request.GET.get("item_key_dest"),
    )
    return JsonResponse(payload)

def import_kml_modal(request):
    """Renderiza o modal de importacao KML com a lista de devices."""
    devices = Device.objects.all().order_by('name')
    return render(request, 'partials/import_kml.html', {
        'devices': devices
    })

def api_fiber_cables(request):
    """
    Lista todos os cabos de fibra com informações detalhadas.
    """
    return JsonResponse({"cables": fiber_uc.list_fiber_cables()})

def api_fiber_detail(request, cable_id):
    """
    Detalhes e atualizacao de path de um cabo de fibra.
    """
    try:
        cable = fiber_uc.get_fiber_cable(cable_id)
    except fiber_uc.FiberNotFound:
        return JsonResponse({"error": "FiberCable nao encontrado"}, status=404)

    if request.method == "GET":
        return JsonResponse(fiber_uc.fiber_detail_payload(cable))

    if request.method == "DELETE":
        fiber_uc.delete_fiber(cable)
        return JsonResponse({}, status=204)

    if request.method in ("POST", "PUT"):
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return HttpResponseBadRequest("JSON invalido")

        path = body.get("path")
        if path is None or not isinstance(path, list):
            return HttpResponseBadRequest('Campo "path" deve ser lista de pontos')

        try:
            payload = fiber_uc.update_fiber_path(cable, path)
        except fiber_uc.FiberValidationError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(payload)

    return HttpResponseBadRequest("Metodo nao suportado")

def fetch_interface_status(hostid, primary_item_key=None, interfaceid=None, rx_key=None, tx_key=None):
    """
    Wrapper legado para manter compatibilidade de endpoints ja existentes.
    """
    return fetch_interface_status_advanced(hostid, primary_item_key, interfaceid, rx_key, tx_key)

def combine_cable_status(o_status, d_status):
    """
    Combina status de origem e destino para determinar status final do cabo.
    """
    return combine_cable_status_service(o_status, d_status)

def api_fiber_live_status(request, cable_id):
    """
    Consulta status em tempo real de um cabo, atualiza se necessario.
    """
    try:
        cable = fiber_uc.get_fiber_cable(cable_id)
    except fiber_uc.FiberNotFound:
        return JsonResponse({'error': 'FiberCable nao encontrado'}, status=404)
    persist = request.GET.get('persist', '1').lower() in ('1', 'true', 'yes')
    status = fiber_uc.compute_live_status(cable, persist=persist, event_reason='live-endpoint')
    payload = fiber_uc.live_status_payload(cable, status, persist)
    return JsonResponse(payload)

def api_fibers_live_status_all(request):
    """
    Consulta status em tempo real de todos os cabos, atualiza se necessario.
    """
    persist = request.GET.get('persist', '0').lower() in ('1', 'true', 'yes')
    cables = FiberCable.objects.select_related('origin_port__device', 'destination_port__device')
    results, changed_any = fiber_uc.bulk_live_status(cables, persist=persist)
    return JsonResponse({
        'cables': results,
        'persist': persist,
        'changed_persisted': changed_any,
    })

def api_fibers_refresh_status(request):
    """
    Forca avaliacao e persistencia de todos os cabos usando logica avancada.
    ??til para disparo manual ou integracao externa sem usar management command.
    """
    if request.method not in ('POST', 'PUT'):
        return HttpResponseBadRequest('POST ou PUT esperado')

    cables = FiberCable.objects.select_related('origin_port__device', 'destination_port__device')
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
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

    try:
        result = fiber_uc.create_manual_fiber(data)
    except fiber_uc.FiberValidationError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    return JsonResponse(result['payload'])
