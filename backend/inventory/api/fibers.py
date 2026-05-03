from __future__ import annotations

import json
import logging
from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
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

from inventory.models import Device, FiberCable, FiberCableAuditLog
from inventory.usecases import fibers as fiber_uc
from inventory.usecases.fibers import (
    FiberNotFound,
    FiberUseCaseError,
    FiberValidationError,
)
from inventory.cache.fibers import get_cached_fiber_list
from inventory.usecases.fibers import build_optical_summary

logger = logging.getLogger(__name__)


@require_POST
@api_login_required
@handle_api_errors
def api_import_fiber_kml(request: HttpRequest) -> JsonResponse:
    """Import a KML file and create a fiber route using extracted points."""
    name = (request.POST.get("name") or "").strip()
    origin_device_id = request.POST.get("origin_device_id")
    dest_device_id = request.POST.get("dest_device_id")
    origin_port_id = request.POST.get("origin_port_id")
    dest_port_id = request.POST.get("dest_port_id")
    single_port = request.POST.get("single_port") == "true"
    kml_file = request.FILES.get("kml_file")
    cable_group_id = request.POST.get("cable_group_id") or None
    responsible_user_id = request.POST.get("responsible_user_id") or None
    if cable_group_id:
        try:
            cable_group_id = int(cable_group_id)
        except ValueError:
            cable_group_id = None
    if responsible_user_id:
        try:
            responsible_user_id = int(responsible_user_id)
        except ValueError:
            responsible_user_id = None

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
            cable_group_id=cable_group_id,
            responsible_user_id=responsible_user_id,
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

    # Force browsers to revalidate so new cables show up immediately after creation.
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    if not is_fresh:
        # Flag that the payload may be stale so clients can decide to refetch.
        response["X-Fiber-Data-Stale"] = "1"
    
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


def _build_cached_optical_payload(cable_id: int) -> JsonResponse:
    """Constrói o payload de cached optical status — função pura (sem decorators).

    Reusada por:
      - GET  /cached-status/        (api_fiber_cached_optical_status)
      - POST /refresh-optical/      (api_fiber_refresh_optical)
    """
    try:
        cable = FiberCable.objects.select_related(
            "origin_port__device", "destination_port__device"
        ).get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)

    origin = cable.origin_port
    dest = cable.destination_port

    if not origin or not dest:
        return JsonResponse({
            "cable_id": cable.id,
            "status": cable.status,
            "error": "Cable does not have origin/destination ports configured",
            "origin_optical": None,
            "destination_optical": None,
        }, status=200)

    summary = build_optical_summary(cable)
    origin_summary = summary.get("origin", {}) if isinstance(summary, dict) else {}
    dest_summary = summary.get("destination", {}) if isinstance(summary, dict) else {}

    payload: dict[str, Any] = {
        "cable_id": cable.id,
        "status": cable.status,
        "origin_port_id": origin.id,
        "destination_port_id": dest.id,
        "origin_optical": {
            "port_id": origin.id,
            "port_name": origin.name,
            "device_name": origin.device.name if origin.device else "Dispositivo não identificado",
            "rx_dbm": origin.last_rx_power,
            "tx_dbm": origin.last_tx_power,
            "last_check": origin.last_optical_check.isoformat() if origin.last_optical_check else None,
            "status": origin_summary.get("status"),
            "warning_threshold": origin_summary.get("warning_threshold"),
            "critical_threshold": origin_summary.get("critical_threshold"),
            "status_sources": origin_summary.get("status_sources"),
            "alarm_enabled": origin_summary.get("alarm_enabled"),
        },
        "destination_optical": {
            "port_id": dest.id,
            "port_name": dest.name,
            "device_name": dest.device.name if dest.device else "Dispositivo não identificado",
            "rx_dbm": dest.last_rx_power,
            "tx_dbm": dest.last_tx_power,
            "last_check": dest.last_optical_check.isoformat() if dest.last_optical_check else None,
            "status": dest_summary.get("status"),
            "warning_threshold": dest_summary.get("warning_threshold"),
            "critical_threshold": dest_summary.get("critical_threshold"),
            "status_sources": dest_summary.get("status_sources"),
            "alarm_enabled": dest_summary.get("alarm_enabled"),
        },
    }
    return JsonResponse(payload)


@require_GET
@api_login_required
@handle_api_errors
def api_fiber_cached_optical_status(request: HttpRequest, cable_id: int) -> JsonResponse:
    """Return cached optical status for a single cable without Zabbix calls.

    Leitura direta dos campos persistidos (last_rx_power / last_tx_power) das
    portas de origem e destino. Evita chamadas síncronas ao Zabbix durante a
    requisição web.
    """
    return _build_cached_optical_payload(cable_id)


@require_POST
@api_login_required
@handle_api_errors
def api_fiber_refresh_optical(request: HttpRequest, cable_id: int) -> JsonResponse:
    """Força fetch fresh dos níveis ópticos (origem + destino) deste cabo.

    Usado pelo botão "Atualizar agora" no popup óptico — quando o user
    quer ver IMEDIATAMENTE o estado atual sem esperar o próximo ciclo da
    task `update_all_port_optical_levels` (60s).

    Faz UMA chamada batch ao Zabbix (1 por device) e atualiza os campos
    last_rx_power / last_tx_power / last_optical_check no banco. Retorna
    o mesmo formato do GET /cached-status/.
    """
    from inventory.domain.optical import fetch_ports_optical_snapshots
    from django.utils import timezone

    try:
        cable = FiberCable.objects.select_related(
            "origin_port__device", "destination_port__device"
        ).get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)

    ports = [p for p in (cable.origin_port, cable.destination_port) if p is not None]
    if not ports:
        return JsonResponse({"error": "Cable has no ports configured"}, status=400)

    try:
        snapshots = fetch_ports_optical_snapshots(ports, persist_keys=False)
    except Exception as exc:
        logger.exception("refresh-optical: fetch failed for cable %s", cable_id)
        return JsonResponse({"error": f"Falha ao consultar Zabbix: {exc}"}, status=502)

    now = timezone.now()
    for port in ports:
        snap = snapshots.get(port.pk) or {}
        update_fields: list[str] = []
        if snap.get("rx_dbm") is not None:
            port.last_rx_power = snap["rx_dbm"]
            update_fields.append("last_rx_power")
        if snap.get("tx_dbm") is not None:
            port.last_tx_power = snap["tx_dbm"]
            update_fields.append("last_tx_power")
        if update_fields:
            port.last_optical_check = now
            update_fields.append("last_optical_check")
            port.save(update_fields=update_fields)

    # Reusa o builder do payload (sem decorators que rejeitariam o POST)
    return _build_cached_optical_payload(cable_id)


@require_GET
@api_login_required
@handle_api_errors
def api_fiber_cached_live_status(request: HttpRequest, cable_id: int) -> JsonResponse:
    """Return cached live status for a cable without Zabbix calls (Phase 9.1).
    
    Leitura direta dos campos FiberCable.last_live_* persistidos pela task
    refresh_fiber_live_status. Evita cálculo síncrono de status live durante
    requisições web.
    """
    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)
    
    payload: dict[str, Any] = {
        "cable_id": cable.id,
        "name": cable.name,
        "live_status": cable.last_live_status,
        "stored_status": cable.status,
        "last_live_check": cable.last_live_check,
        "last_status_check": cable.last_status_check,
        "origin_status": cable.last_status_origin,
        "destination_status": cable.last_status_dest,
    }
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
        try:
            fiber_uc.delete_fiber(cable, user=request.user)
            return HttpResponse(status=204)
        except ProtectedError as exc:
            blockers = fiber_uc.get_delete_blockers(cable)
            return JsonResponse(
                {
                    "error": "Delete blocked by related objects",
                    "detail": str(exc),
                    "blockers": blockers,
                },
                status=409,
            )
        except IntegrityError as exc:
            return JsonResponse(
                {
                    "error": (
                        "Integrity error while deleting cable"
                    ),
                    "detail": str(exc),
                },
                status=409,
            )

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
        "cable_group_id": payload.get("cable_group_id"),
        "responsible_id": payload.get("responsible_id"),
        "responsible_user_id": payload.get("responsible_user_id"),
        "folder_id": payload.get("folder_id"),
        "cable_type": payload.get("cable_type_id"),
    }

    if any(value is not None for value in metadata_kwargs.values()):
        fiber_uc.update_fiber_metadata(
            cable,
            name=metadata_kwargs["name"],
            origin_port_id=metadata_kwargs["origin_port_id"],
            dest_port_id=metadata_kwargs["dest_port_id"],
            cable_group_id=metadata_kwargs["cable_group_id"],
            responsible_id=metadata_kwargs["responsible_id"],
            responsible_user_id=metadata_kwargs["responsible_user_id"],
            folder_id=metadata_kwargs["folder_id"],
            cable_type=metadata_kwargs["cable_type"],
            user=request.user,
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
        result = fiber_uc.create_manual_fiber(data, user=request.user)
    except FiberValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(result["payload"])


@require_POST
@api_login_required
@handle_api_errors
def api_delete_fibers_bulk(request: HttpRequest) -> JsonResponse:
    """Delete multiple cables at once.

    Body options:
      - {"ids": [1,2,3]}: delete listed cable IDs
      - {"all": true}: delete all cables
    Requires staff privileges.
    """
    guard = staff_guard(request)
    if guard:
        return guard

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    delete_all_flag = str(payload.get("all", "")).lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    ids = payload.get("ids") or []

    if not delete_all_flag and (not isinstance(ids, list) or not ids):
        return JsonResponse(
            {"error": "Provide 'ids' list or set 'all': true"},
            status=400,
        )

    summary = fiber_uc.delete_fibers_bulk(ids=ids, delete_all=delete_all_flag)
    return JsonResponse(summary)


@require_POST
@api_login_required
@handle_api_errors
def api_force_delete_fiber(
    request: HttpRequest,
    cable_id: int,
) -> JsonResponse:
    """Staff-only force delete.

    Unlinks external segments that reference this cable's infrastructures
    (start/end) and then deletes the cable.
    """
    guard = staff_guard(request)
    if guard:
        return guard

    try:
        cable = fiber_uc.get_fiber_cable(cable_id)
    except FiberNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)

    summary = fiber_uc.force_delete_fiber(cable)
    return JsonResponse(summary)


@require_POST
@api_login_required
@handle_api_errors
def api_validate_port(request: HttpRequest) -> JsonResponse:
    """
    Validate if a port is already in use by another cable.
    
    POST body: {"port_id": 123, "cable_id": 456 (optional)}
    Returns: {"available": true/false, "used_by": cable_id, "cable_name": "..."}
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    port_id = body.get("port_id")
    cable_id = body.get("cable_id")  # Optional - for editing existing cable
    
    if not port_id:
        return JsonResponse({"error": "port_id is required"}, status=400)
    
    # Check if port exists
    from inventory.models import Port
    try:
        port = Port.objects.get(id=port_id)
    except Port.DoesNotExist:
        return JsonResponse({"error": "Port not found"}, status=404)
    
    # Find cables using this port (origin or destination)
    from django.db.models import Q
    cables_using_port = FiberCable.objects.filter(
        Q(origin_port_id=port_id) | Q(destination_port_id=port_id)
    )
    
    # Exclude current cable if editing
    if cable_id:
        cables_using_port = cables_using_port.exclude(id=cable_id)
    
    if cables_using_port.exists():
        cable = cables_using_port.first()
        return JsonResponse({
            "available": False,
            "used_by": cable.id,
            "cable_name": cable.name,
            "port_name": port.name
        })
    
    return JsonResponse({
        "available": True,
        "used_by": None,
        "cable_name": None,
        "port_name": port.name
    })


@require_POST
@api_login_required
@handle_api_errors
def api_validate_cable_name(request: HttpRequest) -> JsonResponse:
    """
    Validate if a cable name is already in use.
    
    POST body: {"name": "CABO-123", "cable_id": 456 (optional)}
    Returns: {"available": true/false, "cable_id": 123}
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    name = body.get("name", "").strip()
    cable_id = body.get("cable_id")  # Optional - for editing
    
    if not name:
        return JsonResponse({
            "available": False,
            "error": "Name is required"
        }, status=400)
    
    # Find cables with this name (case-insensitive)
    cables_with_name = FiberCable.objects.filter(name__iexact=name)
    
    # Exclude current cable if editing
    if cable_id:
        cables_with_name = cables_with_name.exclude(id=cable_id)
    
    if cables_with_name.exists():
        cable = cables_with_name.first()
        return JsonResponse({
            "available": False,
            "cable_id": cable.id,
            "message": f"Cable name '{name}' is already in use"
        })
    
    return JsonResponse({
        "available": True,
        "cable_id": None
    })


@require_POST
@api_login_required
@handle_api_errors
def api_validate_device_coordinates(request: HttpRequest) -> JsonResponse:
    """
    Validate if devices have coordinates (latitude/longitude).
    
    POST body: {"origin_device_id": 123, "dest_device_id": 456 (optional)}
    Returns: {
        "valid": true/false,
        "origin_has_coords": true/false,
        "dest_has_coords": true/false,
        "missing_devices": ["Device Name 1", ...]
    }
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    origin_device_id = body.get("origin_device_id")
    dest_device_id = body.get("dest_device_id")
    
    if not origin_device_id:
        return JsonResponse({"error": "origin_device_id is required"}, status=400)
    
    missing_devices = []
    origin_has_coords = False
    dest_has_coords = False
    
    def device_has_coords(device):
        site = getattr(device, 'site', None)
        if site and site.latitude is not None and site.longitude is not None:
            return True
        return False

    # Check origin device
    try:
        origin_device = Device.objects.select_related('site').get(id=origin_device_id)
        if device_has_coords(origin_device):
            origin_has_coords = True
        else:
            missing_devices.append(origin_device.name)
    except Device.DoesNotExist:
        return JsonResponse({"error": "Origin device not found"}, status=404)

    # Check destination device (if provided and different from origin)
    if dest_device_id and str(dest_device_id) != str(origin_device_id):
        try:
            dest_device = Device.objects.select_related('site').get(id=dest_device_id)
            if device_has_coords(dest_device):
                dest_has_coords = True
            else:
                missing_devices.append(dest_device.name)
        except Device.DoesNotExist:
            return JsonResponse({"error": "Destination device not found"}, status=404)
    else:
        # Single port mode or same device
        dest_has_coords = True
    
    is_valid = origin_has_coords and dest_has_coords
    
    return JsonResponse({
        "valid": is_valid,
        "origin_has_coords": origin_has_coords,
        "dest_has_coords": dest_has_coords,
        "missing_devices": missing_devices,
        "message": f"Devices missing coordinates: {', '.join(missing_devices)}" if missing_devices else None
    })


@require_POST
@api_login_required
@handle_api_errors
def api_validate_nearby_cables(request: HttpRequest) -> JsonResponse:
    """
    Detect cables very close to the planned path (< 50m).
    
    POST body: {
        "path": [{"lat": -15.123, "lng": -47.456}, ...],
        "cable_id": 123 (optional - exclude this cable)
    }
    Returns: {
        "has_nearby": true/false,
        "nearby_cables": [
            {"id": 123, "name": "CABO-01", "distance_meters": 25.5},
            ...
        ]
    }
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    path = body.get("path", [])
    cable_id = body.get("cable_id")
    
    if not path or len(path) < 2:
        return JsonResponse({
            "has_nearby": False,
            "nearby_cables": [],
            "message": "Path too short to analyze"
        })
    
    # Get all cables except current one
    all_cables = FiberCable.objects.exclude(id=cable_id) if cable_id else FiberCable.objects.all()
    
    nearby_cables = []
    PROXIMITY_THRESHOLD_METERS = 50
    
    # Helper function to calculate distance between two points (Haversine)
    from math import radians, sin, cos, sqrt, atan2
    
    def haversine_distance(lat1, lng1, lat2, lng2):
        R = 6371000  # Earth radius in meters
        
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lng = radians(lng2 - lng1)
        
        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c
    
    # Check each cable against the new path
    for cable in all_cables:
        if not hasattr(cable, 'path_data') or not cable.path_data:
            continue
        
        cable_path = cable.path_data if isinstance(cable.path_data, list) else []
        if len(cable_path) < 2:
            continue
        
        # Find minimum distance between any two points
        min_distance = float('inf')
        
        for new_point in path:
            if 'lat' not in new_point or 'lng' not in new_point:
                continue
            
            for cable_point in cable_path:
                if 'lat' not in cable_point or 'lng' not in cable_point:
                    continue
                
                distance = haversine_distance(
                    new_point['lat'], new_point['lng'],
                    cable_point['lat'], cable_point['lng']
                )
                
                if distance < min_distance:
                    min_distance = distance
        
        # If minimum distance is below threshold, consider it nearby
        if min_distance < PROXIMITY_THRESHOLD_METERS:
            nearby_cables.append({
                "id": cable.id,
                "name": cable.name,
                "distance_meters": round(min_distance, 1)
            })
    
    # Sort by distance (closest first)
    nearby_cables.sort(key=lambda x: x['distance_meters'])
    
    return JsonResponse({
        "has_nearby": len(nearby_cables) > 0,
        "nearby_cables": nearby_cables[:5],  # Return top 5 closest
        "threshold_meters": PROXIMITY_THRESHOLD_METERS
    })


@require_GET
@login_required
@handle_api_errors
def api_fiber_audit_log(request: HttpRequest, cable_id: int) -> JsonResponse:
    """Return audit log entries for a specific cable (most recent first)."""
    limit = min(int(request.GET.get("limit", 50)), 200)
    entries = (
        FiberCableAuditLog.objects.filter(cable_id=cable_id)
        .order_by("-timestamp")[:limit]
    )
    return JsonResponse({
        "results": [
            {
                "id": e.id,
                "action": e.action,
                "action_display": e.get_action_display(),
                "username": e.username or "—",
                "timestamp": e.timestamp.isoformat(),
                "changes": e.changes,
            }
            for e in entries
        ]
    })


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
    "api_validate_port",
    "api_validate_cable_name",
    "api_validate_device_coordinates",
    "api_validate_nearby_cables",
]
