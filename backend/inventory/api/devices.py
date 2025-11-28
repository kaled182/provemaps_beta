from __future__ import annotations

import ipaddress
import json
import logging
import platform
import re
import socket
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, cast

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.test import RequestFactory
from django.views.decorators.http import (
    require_GET,
    require_POST,
    require_http_methods,
)

from integrations.zabbix.decorators import handle_api_errors
from integrations.zabbix.guards import diagnostics_guard

from inventory.usecases import devices as device_uc
from inventory.usecases.devices import (
    InventoryNotFound,
    InventoryUseCaseError,
    InventoryValidationError,
)
from inventory.usecases import fibers as fiber_uc
from inventory.usecases.fibers import FiberNotFound
from inventory.models import FiberCable, FiberEvent

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60

JsonDict = Dict[str, Any]


def _current_status(cable: FiberCable) -> str:
    status_value: Any = getattr(cable, "status")
    if isinstance(status_value, str):
        return status_value
    return str(status_value)


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
    try:
        payload = fiber_uc.update_cable_oper_status(cable_id)
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
        payload = device_uc.device_port_optical_status(port_id)
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
        payload = device_uc.get_device_ports(device_id)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_device_ports_live(
    request: HttpRequest,
    device_id: int,
) -> HttpResponse:
    """
    Retorna portas do dispositivo com dados em tempo real do Zabbix.
    Endpoint: GET /api/v1/inventory/devices/{device_id}/ports/live/
    
    Sem cache - sempre busca dados atualizados do Zabbix.
    Inclui: status operacional, velocidade, níveis de sinal óptico.
    """
    try:
        payload = device_uc.get_device_ports_with_live_status(device_id)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_device_select_options(request: HttpRequest) -> HttpResponse:
    payload = device_uc.list_device_select_options()
    return JsonResponse({"devices": payload})


@require_GET
@login_required
@handle_api_errors
def api_device_ports_with_optical(
    request: HttpRequest,
    device_id: int,
) -> HttpResponse:
    cache_key = f"inventory_device_ports_optical_{device_id}"
    payload = cache.get(cache_key)

    if payload is None:
        try:
            payload = device_uc.get_device_ports_with_optical(device_id)
        except InventoryNotFound as exc:
            return JsonResponse({"error": str(exc)}, status=404)
        cache.set(cache_key, payload, CACHE_TTL_SECONDS)
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
        payload = device_uc.add_device_from_zabbix(data)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except InventoryUseCaseError as exc:
        logger.exception("Failed to register device via Zabbix: %s", exc)
        detail = str(exc).strip()
        payload: Dict[str, Any] = {"error": "Failed to register device"}
        if detail:
            payload["detail"] = detail
        return JsonResponse(payload, status=500)
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_zabbix_discover_hosts(request: HttpRequest) -> HttpResponse:
    payload = device_uc.discover_zabbix_hosts()
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
        payload = device_uc.bulk_create_inventory(data)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryUseCaseError as exc:
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
    payload = device_uc.list_sites()
    return JsonResponse(payload)


@require_GET
@handle_api_errors
def api_port_traffic_history(
    request: HttpRequest,
    port_id: int,
) -> HttpResponse:
    try:
        payload = device_uc.port_traffic_history(port_id, request.GET)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except InventoryValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except InventoryUseCaseError as exc:
        logger.exception("Failed to fetch traffic history: %s", exc)
        return JsonResponse(
            {"error": "Failed to fetch traffic history"},
            status=500,
        )
    return JsonResponse(payload)


@require_GET
@login_required
@handle_api_errors
def api_test_telnet(request: HttpRequest) -> JsonResponse:
    guard = diagnostics_guard(request)
    if guard:
        return guard

    host = (request.GET.get("ip") or request.GET.get("host") or "").strip()
    port_raw = request.GET.get("port", "23")
    timeout_raw = request.GET.get("timeout", "3")
    started = time.time()

    if not host:
        return JsonResponse(
            {"error": "Parameter ip/host is required"},
            status=400,
        )
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9.-]+", host):
            return JsonResponse(
                {"error": "Invalid host/IP"},
                status=400,
            )
    try:
        port = int(port_raw)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        return JsonResponse(
            {"error": "Invalid port"},
            status=400,
        )
    try:
        timeout = float(timeout_raw)
        if timeout <= 0 or timeout > 30:
            timeout = 3.0
    except ValueError:
        timeout = 3.0

    result: Dict[str, Any] = {"host": host, "port": port, "timeout": timeout}
    try:
        with socket.create_connection((host, port), timeout=timeout) as conn:
            elapsed = time.time() - started
            result.update(
                {
                    "status": "success",
                    "elapsed_ms": int(elapsed * 1000),
                    "peername": conn.getpeername(),
                }
            )
        return JsonResponse(result)
    except Exception as exc:  # pragma: no cover - network failures vary
        elapsed = time.time() - started
        result.update(
            {
                "status": "failed",
                "error": str(exc)[:300],
                "elapsed_ms": int(elapsed * 1000),
            }
        )
        return JsonResponse(result, status=502)


@require_GET
@login_required
@handle_api_errors
def api_test_ping(request: HttpRequest) -> JsonResponse:
    guard = diagnostics_guard(request)
    if guard:
        return guard

    host = (request.GET.get("ip") or request.GET.get("host") or "").strip()
    if not host:
        return JsonResponse(
            {"error": "Parameter ip/host is required"},
            status=400,
        )

    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9.-]+", host):
            return JsonResponse(
                {"error": "Invalid host/IP"},
                status=400,
            )

    try:
        count = int(request.GET.get("count", "1"))
        if count < 1 or count > 4:
            count = 1
    except ValueError:
        count = 1
    try:
        timeout = float(request.GET.get("timeout", "3"))
        if timeout <= 0 or timeout > 15:
            timeout = 3.0
    except ValueError:
        timeout = 3.0

    system = platform.system().lower()
    if system == "windows":
        per_timeout_ms = int(max(1, min(timeout, 5)) * 1000)
        cmd = ["ping", "-n", str(count), "-w", str(per_timeout_ms), host]
    else:
        per_wait = int(max(1, min(timeout, 5)))
        cmd = ["ping", "-c", str(count), "-W", str(per_wait), host]

    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + count + 1,
        )
    except subprocess.TimeoutExpired:
        return JsonResponse(
            {"host": host, "count": count, "status": "timeout"},
            status=504,
        )

    elapsed = time.time() - started
    stdout = proc.stdout or ""
    transmitted = received = packet_loss = None
    avg_ms = None
    try:
        if system == "windows":
            m_stats = re.search(
                (
                    r"Enviados = (\d+), Recebidos = (\d+), "
                    r"Perdidos = (\d+).*?\((\d+)%"
                ),
                stdout,
                re.S,
            ) or re.search(
                (
                    r"Sent = (\d+), Received = (\d+), "
                    r"Lost = (\d+).*?\((\d+)%"
                ),
                stdout,
                re.S,
            )
            if m_stats:
                transmitted, received, _lost, packet_loss = map(
                    int, m_stats.groups()
                )
            m_rtt = re.search(r"Average = (\d+)ms", stdout)
            if m_rtt:
                avg_ms = float(m_rtt.group(1))
        else:
            m_stats = re.search(
                (
                    r"(\d+) packets transmitted, (\d+) "
                    r"(?:packets )?received, (\d+)% packet loss"
                ),
                stdout,
            )
            if m_stats:
                transmitted, received, packet_loss = map(
                    int, m_stats.groups()
                )
            m_rtt = re.search(
                r"rtt min/avg/max/[a-z]+ = [0-9.]+/([0-9.]+)/",
                stdout,
            )
            if m_rtt:
                avg_ms = float(m_rtt.group(1))
    except Exception:  # pragma: no cover - defensive parsing
        pass

    success = proc.returncode == 0 and received and received > 0
    return JsonResponse(
        {
            "host": host,
            "count": count,
            "status": "success" if success else "failed",
            "return_code": proc.returncode,
            "elapsed_ms": int(elapsed * 1000),
            "transmitted": transmitted,
            "received": received,
            "packet_loss_percent": packet_loss,
            "avg_rtt_ms": avg_ms,
            "raw_output": stdout.splitlines()[-6:] if stdout else [],
        }
    )


@require_GET
@login_required
@handle_api_errors
def api_test_ping_telnet(request: HttpRequest) -> JsonResponse:
    guard = diagnostics_guard(request)
    if guard:
        return guard

    factory = RequestFactory()
    ip = request.GET.get("ip") or request.GET.get("host") or ""
    port = request.GET.get("port", "23")
    if not ip:
        return JsonResponse(
            {"error": "Parameter ip/host is required"},
            status=400,
        )

    ping_request = factory.get("/diagnostics/ping", {"ip": ip, "count": "1"})
    ping_request.user = request.user
    ping_response = api_test_ping(ping_request)

    telnet_request = factory.get(
        "/diagnostics/telnet",
        {"ip": ip, "port": port},
    )
    telnet_request.user = request.user
    telnet_response = api_test_telnet(telnet_request)

    return JsonResponse(
        {
            "host": ip,
            "port": port,
            "ping": getattr(ping_response, "json", lambda: None)(),
            "telnet": getattr(telnet_response, "json", lambda: None)(),
            "timestamp": datetime.now().isoformat(),
        }
    )


@require_POST
@login_required
@handle_api_errors
def api_test_set_cable_up(
    request: HttpRequest,
    cable_id: int,
) -> JsonResponse:
    guard = diagnostics_guard(request)
    if guard:
        return guard

    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)

    previous = _current_status(cable)
    cable.update_status("up")
    FiberEvent.objects.create(
        fiber=cable,
        previous_status=previous,
        new_status="up",
        detected_reason="diagnostic-up",
    )
    return JsonResponse(
        {
            "fiber_id": int(cable.pk),
            "status": "up",
            "previous_status": previous,
        }
    )


@require_POST
@login_required
@handle_api_errors
def api_test_set_cable_down(
    request: HttpRequest,
    cable_id: int,
) -> JsonResponse:
    guard = diagnostics_guard(request)
    if guard:
        return guard

    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)

    previous = _current_status(cable)
    cable.update_status("down")
    FiberEvent.objects.create(
        fiber=cable,
        previous_status=previous,
        new_status="down",
        detected_reason="diagnostic-down",
    )
    return JsonResponse(
        {
            "fiber_id": int(cable.pk),
            "status": "down",
            "previous_status": previous,
        }
    )


@require_POST
@login_required
@handle_api_errors
def api_test_set_cable_unknown(
    request: HttpRequest,
    cable_id: int,
) -> JsonResponse:
    guard = diagnostics_guard(request)
    if guard:
        return guard

    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "FiberCable not found"}, status=404)

    previous = _current_status(cable)
    cable.update_status("unknown")
    FiberEvent.objects.create(
        fiber=cable,
        previous_status=previous,
        new_status="unknown",
        detected_reason="diagnostic-unknown",
    )
    return JsonResponse(
        {
            "fiber_id": int(cable.pk),
            "status": "unknown",
            "previous_status": previous,
        }
    )


# ============================================================================
# DEVICE IMPORT SYSTEM APIS (Phase 11 - Nov 2025)
# ============================================================================

@login_required
@require_GET
def api_inventory_grouped(request: HttpRequest) -> JsonResponse:
    """
    Retorna o inventário organizado por grupos para a aba 'Inventário (Pós)'.
    
    Endpoint: GET /api/v1/inventory/devices/grouped/
    Response: Array de objetos {group_id, group_name, devices: [...]}
    """
    from inventory.models import DeviceGroup, Device
    from inventory.serializers import DeviceSerializer
    
    try:
        # Busca todos os grupos que tenham devices associados
        groups = DeviceGroup.objects.prefetch_related(
            'primary_devices__site'
        ).filter(primary_devices__isnull=False).distinct()
        
        response_data = []
        
        # Grupos definidos
        for group in groups:
            devices = group.primary_devices.select_related('site').all()
            if devices.exists():
                response_data.append({
                    "group_id": group.id,
                    "group_name": group.name,
                    "device_count": devices.count(),
                    "devices": DeviceSerializer(devices, many=True).data
                })
        
        # Devices sem grupo (órfãos)
        orphan_devices = Device.objects.filter(
            monitoring_group__isnull=True
        ).select_related('site')
        
        if orphan_devices.exists():
            response_data.append({
                "group_id": "orphans",
                "group_name": "Sem Grupo Definido",
                "device_count": orphan_devices.count(),
                "devices": DeviceSerializer(orphan_devices, many=True).data
            })

        return JsonResponse(response_data, safe=False)
    
    except Exception as e:
        logger.exception("Erro ao buscar inventário agrupado")
        return JsonResponse(
            {"error": str(e)},
            status=500
        )


@login_required
@require_POST
def api_import_batch(request: HttpRequest) -> JsonResponse:
    """
    Processa importação/edição vinda do DeviceEditModal.vue (Batch ou Single).
    
    Endpoint: POST /api/v1/inventory/devices/import-batch/
    
    Body (Batch):
    {
        "mode": "batch",
        "devices": [
            {
                "name": "Router-01",
                "ip": "192.168.1.1",
                "zabbix_id": "10084",
                "category": "backbone",
                "group": "Backbone Principal",
                "is_new_group": false,
                "alerts": {"screen": true, "whatsapp": false, "email": false}
            }
        ]
    }
    
    Body (Single):
    {
        "name": "Router-01",
        "ip_address": "192.168.1.1",
        ...
    }
    
    Response:
    {
        "success": true,
        "message": "X dispositivos processados com sucesso",
        "ids": [1, 2, 3],
        "created": 2,
        "updated": 1
    }
    """
    from django.db import transaction
    from inventory.models import Device, DeviceGroup, Site
    
    try:
        data = json.loads(request.body)
        mode = data.get('mode', 'single')
        
        # DEBUG: Log do payload recebido
        logger.info(f"[IMPORT_DEBUG] Mode: {mode}")
        logger.info(
            f"[IMPORT_DEBUG] Payload: {json.dumps(data, indent=2)}"
        )
        
        # Normaliza entrada para sempre ser uma lista
        if mode == 'batch':
            items_to_process = data.get('devices', [])
        else:
            # Single mode: wrap em array
            items_to_process = [data]
        
        if not items_to_process:
            return JsonResponse(
                {"success": False, "error": "Nenhum dispositivo fornecido"},
                status=400
            )
        
        processed_ids = []
        created_count = 0
        updated_count = 0
        errors = []
        
        with transaction.atomic():
            for idx, item in enumerate(items_to_process):
                try:
                    # 1. Lógica de Grupo (Criar ou Buscar)
                    group_instance = None
                    group_name = item.get('group')
                    
                    if group_name:
                        # get_or_create garante que o grupo exista
                        # Gera ID seguro: MANUAL_GROUPNAME (limitado a 32)
                        safe_group_id = (
                            f"MANUAL_{group_name.upper().replace(' ', '_')}"
                        )[:32]
                        
                        group_instance, created = (
                            DeviceGroup.objects.get_or_create(
                                name=group_name,
                                defaults={'zabbix_groupid': safe_group_id}
                            )
                        )
                        if created:
                            logger.info(
                                f"Novo grupo criado: {group_name} "
                                f"(ID: {safe_group_id})"
                            )
                    
                    # 2. Lógica de Site (Obrigatório para Device Model)
                    site_instance = None
                    site_id_or_name = item.get('site')
                    is_new_site = item.get('is_new_site', False)
                    site_coordinates = item.get('site_coordinates')
                    
                    if not site_id_or_name:
                        # Tenta pegar o primeiro site ou cria um padrão
                        default_site = Site.objects.first()
                        if not default_site:
                            # Cria site padrão se não existir
                            default_site = Site.objects.create(
                                display_name="Site Padrão",
                                city="Default"
                            )
                            logger.info(
                                "Site padrão criado automaticamente"
                            )
                        site_instance = default_site
                    elif is_new_site:
                        # Criar novo Site com coordenadas
                        from django.contrib.gis.geos import Point
                        
                        new_site_name = site_id_or_name
                        site_defaults = {
                            'city': 'A definir',
                        }
                        
                        # Adiciona coordenadas se fornecidas
                        has_coords = (
                            site_coordinates
                            and 'lat' in site_coordinates
                            and 'lng' in site_coordinates
                        )
                        if has_coords:
                            lat = float(site_coordinates['lat'])
                            lng = float(site_coordinates['lng'])
                            site_defaults['latitude'] = lat
                            site_defaults['longitude'] = lng
                            # PostGIS Point: (longitude, latitude) order!
                            site_defaults['location'] = Point(lng, lat)
                            logger.info(
                                f"Criando site '{new_site_name}' com "
                                f"coordenadas: ({lat}, {lng})"
                            )
                        
                        site_instance, created = (
                            Site.objects.get_or_create(
                                display_name=new_site_name,
                                defaults=site_defaults
                            )
                        )
                        if created:
                            logger.info(f"Novo site criado: {new_site_name}")
                        else:
                            logger.info(
                                f"Site '{new_site_name}' já existe, "
                                f"reutilizado"
                            )
                    else:
                        # Usar Site existente por ID
                        try:
                            site_instance = Site.objects.get(
                                id=int(site_id_or_name)
                            )
                        except (ValueError, Site.DoesNotExist):
                            # Fallback: buscar por nome
                            site_instance = Site.objects.filter(
                                display_name=site_id_or_name
                            ).first()
                            if not site_instance:
                                # Se não encontrar, cria site padrão
                                site_instance = Site.objects.first()
                                if not site_instance:
                                    site_instance = Site.objects.create(
                                        display_name="Site Padrão",
                                        city="Default"
                                    )
                                logger.warning(
                                    f"Site ID/nome '{site_id_or_name}' não "
                                    f"encontrado, usando "
                                    f"'{site_instance.display_name}'"
                                )
                    
                    # 3. Identificar Dispositivo (Atualizar ou Criar)
                    device_qs = Device.objects.none()
                    
                    # Tenta identificar por Zabbix ID
                    zabbix_id = (
                        item.get('zabbix_id') or item.get('zabbix_hostid')
                    )
                    if zabbix_id:
                        device_qs = Device.objects.filter(
                            zabbix_hostid=zabbix_id
                        )
                    
                    # Fallback: IP address
                    if not device_qs.exists():
                        ip = (
                            item.get('ip') or
                            item.get('ip_address') or
                            item.get('primary_ip')
                        )
                        if ip:
                            device_qs = Device.objects.filter(primary_ip=ip)
                    
                    # Fallback: ID direto
                    if not device_qs.exists() and item.get('id'):
                        device_qs = Device.objects.filter(id=item.get('id'))
                    
                    # Atualizar ou Criar
                    if device_qs.exists():
                        device = device_qs.first()
                        device.name = item.get('name', device.name)
                        device.category = item.get('category', device.category)
                        device.monitoring_group = group_instance
                        updated_count += 1
                        logger.info(f"Device atualizado: {device.name}")
                    else:
                        # Criar novo
                        device = Device(
                            name=item.get('name', f'Device-{idx+1}'),
                            primary_ip=(
                                item.get('ip') or item.get('ip_address')
                            ),
                            zabbix_hostid=zabbix_id or '',
                            site=site_instance,
                            category=item.get('category', 'backbone'),
                            monitoring_group=group_instance,
                            vendor=item.get('vendor', ''),
                            model=item.get('model', '')
                        )
                        created_count += 1
                        logger.info(f"Novo device criado: {device.name}")
                    
                    # 4. Salva Alertas
                    alerts = item.get('alerts', {})
                    device.enable_screen_alert = alerts.get('screen', True)
                    device.enable_whatsapp_alert = (
                        alerts.get('whatsapp', False)
                    )
                    device.enable_email_alert = alerts.get('email', False)
                    
                    device.save()
                    processed_ids.append(device.id)
                    
                    # 5. Adiciona ao ManyToMany 'groups' se grupo existir
                    if group_instance:
                        if not device.groups.filter(
                            id=group_instance.id
                        ).exists():
                            device.groups.add(group_instance)
                    
                    # 6. IMPORTA INTERFACES DO ZABBIX AUTOMATICAMENTE
                    if device.zabbix_hostid:
                        try:
                            import_stats = (
                                device_uc.import_interfaces_from_zabbix(
                                    device
                                )
                            )
                            logger.info(
                                f"Interfaces importadas para "
                                f"{device.name}: "
                                f"{import_stats.get('created', 0)} criadas, "
                                f"{import_stats.get('updated', 0)} "
                                f"atualizadas"
                            )
                        except Exception as import_error:
                            logger.warning(
                                f"Erro ao importar interfaces para "
                                f"{device.name}: {str(import_error)}"
                            )
                            # Não quebra o processo se importação falhar
                        # 6b. Sincroniza campos de monitoração (uptime/cpu/host groups) na primeira importação
                        try:
                            device_uc.add_device_from_zabbix(
                                {
                                    "hostid": device.zabbix_hostid,
                                    # Não tocar no site definido na pré-importação a menos que o usuário escolha na sincronização
                                    "update_site": False,
                                }
                            )
                            logger.info(
                                f"[IMPORT_DEBUG] Sync inicial Zabbix aplicada para {device.name}"
                            )
                        except Exception as sync_error:
                            logger.warning(
                                f"[IMPORT_DEBUG] Falha ao aplicar sync inicial "
                                f"para {device.name}: {sync_error}"
                            )
                
                except Exception as item_error:
                    import traceback
                    error_msg = f"Erro no item {idx+1}: {str(item_error)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    # Continua processando os demais (não quebra o batch)
        
        # Resposta consolidada
        response_data = {
            "success": len(processed_ids) > 0,
            "message": (
                f"{len(processed_ids)} dispositivos "
                f"processados com sucesso."
            ),
            "ids": processed_ids,
            "created": created_count,
            "updated": updated_count,
            "total": len(items_to_process),
            "errors": errors if errors else None
        }
        
        return JsonResponse(response_data)
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON inválido: {e}")
        return JsonResponse(
            {"success": False, "error": "JSON inválido no body da requisição"},
            status=400
        )
    except Exception as e:
        logger.exception("Erro ao processar importação em lote")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500
        )


@require_http_methods(["DELETE"])
@login_required
def api_device_delete(request: HttpRequest, device_id: int) -> JsonResponse:
    """
    Exclui um dispositivo do inventário.
    
    Endpoint: DELETE /api/v1/inventory/devices/{device_id}/
    
    Response:
    {
        "success": true,
        "message": "Dispositivo excluído com sucesso"
    }
    """
    from inventory.models import Device
    
    try:
        device = Device.objects.get(id=device_id)
        device_name = device.name
        device.delete()
        
        logger.info(f"Device excluído: {device_name} (ID: {device_id})")
        
        return JsonResponse({
            "success": True,
            "message": f"Dispositivo '{device_name}' excluído com sucesso"
        })
    
    except Device.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Dispositivo não encontrado"},
            status=404
        )
    except Exception as e:
        logger.exception(f"Erro ao excluir device {device_id}")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500
        )


@require_GET
def api_devices_zabbix_status(request: HttpRequest) -> JsonResponse:
    """
    Retorna status do Zabbix para múltiplos devices em batch.
    
    Endpoint: GET /api/v1/inventory/devices/zabbix-status/
    Query params: device_ids (comma-separated)
    
    Response: {
        "statuses": {
            "123": "online",
            "456": "offline",
            "789": "unknown"
        }
    }
    """
    from inventory.models import Device
    from integrations.zabbix.zabbix_service import zabbix_request
    
    try:
        device_ids_param = request.GET.get('device_ids', '')
        if not device_ids_param:
            return JsonResponse({"statuses": {}})
        
        device_ids = [
            int(id.strip())
            for id in device_ids_param.split(',')
            if id.strip()
        ]
        
        # Busca devices com zabbix_hostid
        devices = Device.objects.filter(
            id__in=device_ids,
            zabbix_hostid__isnull=False
        ).exclude(zabbix_hostid='')
        
        logger.info(f"[Zabbix Status] Devices solicitados: {device_ids}")
        device_info = [
            (d.id, d.name, d.zabbix_hostid) for d in devices
        ]
        logger.info(
            f"[Zabbix Status] Devices com zabbix_hostid: {device_info}"
        )
        
        # Coleta todos os hostids
        hostids = [d.zabbix_hostid for d in devices]
        
        if not hostids:
            # Nenhum device tem zabbix_hostid
            logger.warning(
                "[Zabbix Status] Nenhum device tem zabbix_hostid configurado"
            )
            return JsonResponse({
                "statuses": {str(d_id): "unknown" for d_id in device_ids}
            })
        
        # Busca status de todos os hosts em uma única chamada
        try:
            logger.info(
                f"[Zabbix Status] Chamando Zabbix com hostids: {hostids}"
            )
            result = zabbix_request("host.get", {
                "output": ["hostid", "name", "available", "status"],
                "hostids": hostids,
                "selectInterfaces": ["interfaceid", "available", "main"],
            })
            logger.info(f"[Zabbix Status] Resposta Zabbix: {result}")
        except Exception as e:
            logger.error(f"Erro ao buscar status Zabbix em batch: {e}")
            return JsonResponse({
                "statuses": {str(d_id): "unknown" for d_id in device_ids}
            })
        
        # Mapeia hostid → status
        hostid_status = {}
        for host in result:
            hostid = host.get("hostid")
            zabbix_status = int(host.get("status", 1))
            host_available = str(host.get("available", "0"))
            
            # Lógica do dashboard: preferir interface availability
            interfaces = host.get("interfaces", [])
            primary_interface = None
            for iface in interfaces:
                if str(iface.get("main", "0")) == "1":
                    primary_interface = iface
                    break
            
            # Se não achou interface principal, usa a primeira
            if not primary_interface and interfaces:
                primary_interface = interfaces[0]
            
            # Availability final: interface ou host
            availability = host_available
            if primary_interface and host_available == "0":
                interface_avail = primary_interface.get("available")
                if interface_avail is not None:
                    availability = str(interface_avail)
            
            # Converte para status string
            if zabbix_status == 1:  # Disabled no Zabbix
                status = "disabled"
            elif availability == "1":  # Available
                status = "online"
            elif availability == "2":  # Unavailable
                status = "offline"
            else:  # Unknown
                status = "unknown"
            
            logger.info(
                f"[Zabbix Status] Host {hostid}: "
                f"host_status={zabbix_status}, host_avail={host_available}, "
                f"interface_avail={availability} → {status}"
            )
            hostid_status[hostid] = status
        
        # Mapeia device_id → status
        device_status = {}
        for device in devices:
            device_status[str(device.id)] = hostid_status.get(
                device.zabbix_hostid,
                "unknown"
            )
            logger.info(
                f"[Zabbix Status] Device {device.id} ({device.name}): "
                f"zabbix_hostid={device.zabbix_hostid} → "
                f"{device_status[str(device.id)]}"
            )
        
        # Adiciona devices sem zabbix_hostid como unknown
        for d_id in device_ids:
            if str(d_id) not in device_status:
                device_status[str(d_id)] = "unknown"
        
        logger.info(f"[Zabbix Status] Resultado final: {device_status}")
        return JsonResponse({"statuses": device_status})
    
    except Exception as e:
        logger.exception("Erro ao buscar status Zabbix")
        return JsonResponse(
            {"error": str(e), "statuses": {}},
            status=500
        )


__all__ = [
    "api_update_cable_oper_status",
    "api_device_port_optical_status",
    "api_device_ports",
    "api_device_ports_live",
    "api_device_select_options",
    "api_device_ports_with_optical",
    "api_add_device_from_zabbix",
    "api_zabbix_discover_hosts",
    "api_bulk_create_inventory",
    "api_sites",
    "api_port_traffic_history",
    "api_test_telnet",
    "api_test_ping",
    "api_test_ping_telnet",
    "api_test_set_cable_up",
    "api_test_set_cable_down",
    "api_test_set_cable_unknown",
    # Phase 11: Device Import System
    "api_inventory_grouped",
    "api_import_batch",
    "api_device_delete",
    "api_devices_zabbix_status",
]
