"""
Views para gerenciamento de fibras ?pticas, integra??o Zabbix e opera??es de rede.
Inclui endpoints para manipula??o de cabos, importa??o KML, integra??o Zabbix,
status em tempo real, e utilit?rios para testes e invent?rio.

Este arquivo mescla as funcionalidades dos dois arquivos enviados, mantendo
tratamento de erros, organiza??o, e decorators para garantir robustez.
"""

import json
import logging
import re
import xml.etree.ElementTree as ET
from math import radians, sin, cos, sqrt, atan2
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Prefetch
from django.http import (
    JsonResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
)
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from zabbix_api.services.zabbix_service import zabbix_request
from zabbix_api.models import Site, Device, Port, FiberCable, FiberEvent


logger = logging.getLogger(__name__)

# =============================================================================
# UTILIT?RIOS / DECORATORS
# =============================================================================

def conditional_cache_page(timeout):
    """Permite bypass do cache via ?no_cache=true."""
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            if request.GET.get("no_cache") == "true":
                return func(request, *args, **kwargs)
            return cache_page(timeout)(func)(request, *args, **kwargs)
        return wrapper
    return decorator

def handle_api_errors(func):
    """Captura exce??es inesperadas e retorna JSON 500 padronizado."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception("Erro no endpoint %s: %s", func.__name__, e)
            return JsonResponse({"error": "Erro interno do servidor"}, status=500)
    return wrapper

# =============================================================================
# TEST HELPERS (para ambienta??o/teste)
# =============================================================================

@csrf_exempt
@require_POST
@handle_api_errors
def test_set_cable_up(request, cable_id):
    """For?a status 'up' em um cabo para testes."""
    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({'error': 'FiberCable n?o encontrado'}, status=404)
    prev = cable.status
    cable.update_status('up')
    FiberEvent.objects.create(fiber=cable, previous_status=prev, new_status='up', detected_reason='test-up')
    return JsonResponse({'fiber_id': cable.id, 'status': 'up', 'previous_status': prev})

@csrf_exempt
@require_POST
@handle_api_errors
def test_set_cable_down(request, cable_id):
    """For?a status 'down' em um cabo para testes."""
    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({'error': 'FiberCable n?o encontrado'}, status=404)
    prev = cable.status
    cable.update_status('down')
    FiberEvent.objects.create(fiber=cable, previous_status=prev, new_status='down', detected_reason='test-down')
    return JsonResponse({'fiber_id': cable.id, 'status': 'down', 'previous_status': prev})

@csrf_exempt
@require_POST
@handle_api_errors
def test_set_cable_unknown(request, cable_id):
    """For?a status 'unknown' em um cabo para testes."""
    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({'error': 'FiberCable n?o encontrado'}, status=404)
    prev = cable.status
    cable.update_status('unknown')
    FiberEvent.objects.create(fiber=cable, previous_status=prev, new_status='unknown', detected_reason='test-unknown')
    return JsonResponse({'fiber_id': cable.id, 'status': 'unknown', 'previous_status': prev})

# =============================================================================
# ZABBIX INTEGRA??ES (oper-status e device import)
# =============================================================================

@require_POST
@handle_api_errors
def api_update_cable_oper_status(request, cable_id):
    """
    Consulta status operacional via Zabbix, atualiza DB e retorna status traduzido.
    """
    try:
        cable = FiberCable.objects.select_related('origin_port__device').get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({'error': 'FiberCable n?o encontrado'}, status=404)
    device = cable.origin_port.device
    port_name = cable.origin_port.name
    status, raw, valuemap = get_oper_status_from_zabbix(device, port_name)
    prev_status = cable.status
    if status != prev_status:
        cable.update_status(status)
        FiberEvent.objects.create(
            fiber=cable,
            previous_status=prev_status,
            new_status=status,
            detected_reason='zabbix-oper-status'
        )
    return JsonResponse({
        'cable_id': cable.id,
        'status': status,
        'raw_value': raw,
        'valuemap': valuemap,
        'updated': status != prev_status,
        'previous_status': prev_status
    })

@handle_api_errors
def api_device_ports(request, device_id):
    """
    Lista portas de um device.
    """
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    try:
        device = Device.objects.get(id=device_id)
    except Device.DoesNotExist:
        return JsonResponse({'error': 'Device n?o encontrado'}, status=404)
    ports = Port.objects.filter(device=device).order_by('name')
    return JsonResponse({'ports': [
        {'id': p.id, 'name': p.name, 'device': device.name}
        for p in ports
    ]})

@csrf_exempt
@handle_api_errors
def api_import_fiber_kml(request):
    """
    Importa arquivo KML e cria rota de fibra (FiberCable) com pontos extra?dos.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'M?todo n?o permitido'}, status=405)
    name = request.POST.get('name')
    origin_device_id = request.POST.get('origin_device_id')
    dest_device_id = request.POST.get('dest_device_id')
    origin_port_id = request.POST.get('origin_port_id')
    dest_port_id = request.POST.get('dest_port_id')
    kml_file = request.FILES.get('kml_file')
    if not (name and origin_device_id and dest_device_id and origin_port_id and dest_port_id and kml_file):
        return JsonResponse({'error': 'Campos obrigat?rios ausentes'}, status=400)
    # Parse KML
    try:
        tree = ET.parse(kml_file)
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        coords = []
        for linestring in root.findall('.//kml:LineString', ns):
            coord_text = linestring.find('kml:coordinates', ns)
            if coord_text is not None:
                raw = (coord_text.text or "").strip().replace('\n', ' ')
                for pair in raw.split():
                    parts = pair.split(',')
                    if len(parts) >= 2:
                        lng, lat = float(parts[0]), float(parts[1])
                        if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
                            coords.append({'lat': lat, 'lng': lng})
        if not coords:
            return JsonResponse({'error': 'Nenhum ponto encontrado no KML'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erro ao processar KML: {e}'}, status=400)
    # Criar FiberCable
    try:
        origin_port = Port.objects.get(id=origin_port_id)
        dest_port = Port.objects.get(id=dest_port_id)
    except Port.DoesNotExist:
        return JsonResponse({'error': 'Porta de origem ou destino n?o encontrada'}, status=404)
    fiber = FiberCable.objects.create(
        name=name,
        origin_port=origin_port,
        destination_port=dest_port,
        path_coordinates=coords,
        status=FiberCable.STATUS_UNKNOWN
    )
    return JsonResponse({'fiber_id': fiber.id, 'points': len(coords)})

@csrf_exempt
@handle_api_errors
def api_add_device_from_zabbix(request):
    """
    Recebe hostid, consulta Zabbix e cadastra Device no banco.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'M?todo n?o permitido'}, status=405)
    try:
        body = (request.body or b'').decode('utf-8')
        data = json.loads(body) if body else {}
    except Exception:
        return JsonResponse({'error': 'JSON inv?lido'}, status=400)
    hostid = data.get('hostid') or data.get('device_name')
    if not hostid:
        return JsonResponse({'error': 'hostid obrigat?rio'}, status=400)
    # Consulta Zabbix
    zabbix_data = zabbix_request('host.get', {
        'output': ['hostid', 'name', 'host'],
        'hostids': hostid,
        'selectInterfaces': ['interfaceid', 'ip', 'dns', 'port', 'type']
    })
    if not zabbix_data:
        return JsonResponse({'error': 'Host n?o encontrado no Zabbix'}, status=404)
    host = zabbix_data[0]
    site_name = host.get('name') or host.get('host')
    # Busca invent?rio para geolocaliza??o
    lat, lon, address = None, None, None
    if 'inventory' in host:
        inv = host['inventory']
        lat = inv.get('location_lat')
        lon = inv.get('location_lon')
        address = inv.get('site_address') or inv.get('location')
    else:
        inv_data = zabbix_request('host.get', {
            'output': ['hostid'],
            'hostids': hostid,
            'selectInventory': 'extend'
        })
        if inv_data and 'inventory' in inv_data[0]:
            inv = inv_data[0]['inventory']
            lat = inv.get('location_lat')
            lon = inv.get('location_lon')
            address = inv.get('site_address') or inv.get('location')
    site, _ = Site.objects.get_or_create(name=site_name)
    update_fields = []
    if lat:
        try:
            site.latitude = float(lat)
            update_fields.append('latitude')
        except Exception:
            pass
    if lon:
        try:
            site.longitude = float(lon)
            update_fields.append('longitude')
        except Exception:
            pass
    if address:
        site.city = address
        update_fields.append('city')
    if update_fields:
        site.save(update_fields=update_fields)
    device, created = Device.objects.get_or_create(
        site=site,
        name=host.get('host'),
        defaults={
            'vendor': '',
            'model': '',
            'zabbix_hostid': hostid
        }
    )
    ports_created = []
    items = zabbix_request('item.get', {
        'output': ['itemid', 'key_', 'name'],
        'hostids': hostid,
        'filter': {'status': '0'},
        'search': {'key_': 'lastDownTime['},
        'searchByAny': True,
        'limit': 100
    }) or []
    for it in items:
        key = it.get('key_') or ''
        m = re.match(r'lastDownTime\[(.+)\]', key)
        if m:
            port_name = m.group(1)
            port, port_created = Port.objects.get_or_create(
                device=device,
                name=port_name,
                defaults={
                    'zabbix_item_key': key,
                    'zabbix_interfaceid': '',
                    'notes': it.get('name', '')
                }
            )
            if port_created:
                ports_created.append({
                    'id': port.id,
                    'name': port.name,
                    'zabbix_item_key': port.zabbix_item_key,
                    'zabbix_interfaceid': port.zabbix_interfaceid
                })
    return JsonResponse({
        'created': created,
        'device': {
            'id': device.id,
            'name': device.name,
            'site': site.name,
            'zabbix_hostid': device.zabbix_hostid
        },
        'ports_created': ports_created
    })

# =============================================================================
# VALUE MAPPING (0/1) PARA STATUS DE CABO
# =============================================================================

@require_GET
@handle_api_errors
def api_cable_value_mapping_status(request, cable_id):
    """
    Obt?m status de um cabo baseado em um item Zabbix com value mapping 0/1 (Down/Up).
    Query params:
      item_key_origin: chave do item para porta/device de origem
      item_key_dest: chave do item para porta/device de destino (opcional; se n?o enviado usa origin)
    Retorna status interpretado (up/down/unknown) e valor cru.
    """
    try:
        cable = FiberCable.objects.select_related('origin_port__device', 'destination_port__device').get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({'error': 'FiberCable n?o encontrado'}, status=404)
    item_key_origin = request.GET.get('item_key_origin') or cable.origin_port.zabbix_item_key
    item_key_dest = request.GET.get('item_key_dest') or cable.destination_port.zabbix_item_key or item_key_origin
    def fetch_value(hostid, key):
        if not (hostid and key):
            return None
        items = zabbix_request('item.get', {
            'output': ['itemid', 'key_', 'lastvalue', 'value_type'],
            'hostids': hostid,
            'search': {'key_': key},
            'searchByAny': True,
            'limit': 1
        }) or []
        if items:
            val = items[0].get('lastvalue')
            if val is None:
                hist = zabbix_request('history.get', {
                    'itemids': items[0]['itemid'],
                    'history': items[0].get('value_type', 3),
                    'sortfield': 'clock', 'sortorder': 'DESC', 'limit': 1
                }) or []
                if hist:
                    val = hist[0].get('value')
            return str(val) if val is not None else None
        return None
    raw_o = fetch_value(cable.origin_port.device.zabbix_hostid, item_key_origin)
    raw_d = fetch_value(cable.destination_port.device.zabbix_hostid, item_key_dest)
    def interpret(raw):
        if raw == '1':
            return 'up'
        if raw == '0':
            return 'down'
        if raw is not None:
            return f"Desconhecido ({raw})"
        return 'unknown'
    o_status = interpret(raw_o)
    d_status = interpret(raw_d)
    combined = combine_cable_status_service(
        'up' if o_status == 'up' else ('down' if o_status == 'down' else 'unknown'),
        'up' if d_status == 'up' else ('down' if d_status == 'down' else 'unknown')
    )
    return JsonResponse({
        'cable_id': cable.id,
        'origin_raw': raw_o,
        'dest_raw': raw_d,
        'origin_status': o_status,
        'dest_status': d_status,
        'combined_status': combined
    })

# =============================================================================
# VIEWS DE TEMPLATES
# =============================================================================

@login_required
@handle_api_errors
def import_kml_modal(request):
    """Renderiza o modal de importa??o KML com a lista de devices."""
    devices = Device.objects.all().order_by('name')
    return render(request, 'partials/import_kml.html', {
        'devices': devices
    })

@login_required
@handle_api_errors
def dashboard_view(request):
    """P?gina principal do mapa de fibras."""
    return render(request, 'dashboard.html', {
        "GOOGLE_MAPS_API_KEY": getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    })

@login_required
@require_GET
@conditional_cache_page(60)
def api_fiber_cables(request):
    """
    Lista todos os cabos de fibra com informa??es detalhadas.
    """
    cables = FiberCable.objects.select_related(
        'origin_port__device__site', 'destination_port__device__site'
    )
    data = []
    for c in cables:
        origin_site = c.origin_port.device.site
        dest_site = c.destination_port.device.site
        data.append({
            'id': c.id,
            'name': c.name,
            'status': c.status,
            'length_km': float(c.length_km) if c.length_km is not None else None,
            'origin': {
                'site': origin_site.name,
                'city': origin_site.city,
                'lat': float(origin_site.latitude) if origin_site.latitude is not None else None,
                'lng': float(origin_site.longitude) if origin_site.longitude is not None else None,
                'device': c.origin_port.device.name,
                'port': c.origin_port.name,
            },
            'destination': {
                'site': dest_site.name,
                'city': dest_site.city,
                'lat': float(dest_site.latitude) if dest_site.latitude is not None else None,
                'lng': float(dest_site.longitude) if dest_site.longitude is not None else None,
                'device': c.destination_port.device.name,
                'port': c.destination_port.name,
            },
            'path': c.path_coordinates or []
        })
    return JsonResponse({'cables': data})

def _haversine_km(lat1, lon1, lat2, lon2):
    """
    Calcula a dist?ncia entre dois pontos geogr?ficos usando a f?rmula de Haversine.
    """
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def _calculate_path_length(path_points):
    """
    Calcula o comprimento total de um caminho de pontos geogr?ficos.
    """
    if not path_points or len(path_points) < 2:
        return 0
    total = 0
    for i in range(len(path_points) - 1):
        p1 = path_points[i]
        p2 = path_points[i + 1]
        if None in (p1.get('lat'), p1.get('lng'), p2.get('lat'), p2.get('lng')):
            continue
        total += _haversine_km(p1['lat'], p1['lng'], p2['lat'], p2['lng'])
    return round(total, 3)

@login_required
@handle_api_errors
def api_fiber_detail(request, cable_id):
    """
    Detalhes e atualiza??o de path de um cabo de fibra.
    """
    try:
        cable = FiberCable.objects.select_related(
            'origin_port__device__site', 'destination_port__device__site'
        ).get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({'error': 'FiberCable n?o encontrado'}, status=404)

    if request.method == 'GET':
        origin_site = cable.origin_port.device.site
        dest_site = cable.destination_port.device.site
        return JsonResponse({
            'id': cable.id,
            'name': cable.name,
            'status': cable.status,
            'length_km': float(cable.length_km) if cable.length_km is not None else None,
            'origin': {
                'site': origin_site.name,
                'lat': float(origin_site.latitude) if origin_site.latitude is not None else None,
                'lng': float(origin_site.longitude) if origin_site.longitude is not None else None,
                'device': cable.origin_port.device.name,
                'port': cable.origin_port.name,
            },
            'destination': {
                'site': dest_site.name,
                'lat': float(dest_site.latitude) if dest_site.latitude is not None else None,
                'lng': float(dest_site.longitude) if dest_site.longitude is not None else None,
                'device': cable.destination_port.device.name,
                'port': cable.destination_port.name,
            },
            'path': cable.path_coordinates or []
        })

    if request.method in ('POST', 'PUT'):
        try:
            body = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return HttpResponseBadRequest('JSON inv?lido')
        path = body.get('path')
        if path is None or not isinstance(path, list):
            return HttpResponseBadRequest('Campo "path" deve ser lista de pontos')
        sanitized = []
        for p in path:
            if not isinstance(p, dict):
                continue
            lat = p.get('lat')
            lng = p.get('lng')
            try:
                lat = float(lat)
                lng = float(lng)
            except (TypeError, ValueError):
                continue
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                sanitized.append({'lat': lat, 'lng': lng})
        if len(sanitized) < 2:
            return HttpResponseBadRequest('Path precisa de pelo menos 2 pontos v?lidos')
        length_km = _calculate_path_length(sanitized)
        cable.path_coordinates = sanitized
        cable.length_km = length_km
        cable.save(update_fields=['path_coordinates', 'length_km'])
        return JsonResponse({'status': 'ok', 'length_km': length_km, 'points': len(sanitized)})

    return HttpResponseBadRequest('M?todo n?o suportado')

@login_required
@handle_api_errors
def fiber_route_builder_view(request):
    """
    Renderiza o modal de importa??o KML com a lista de devices.
    """
    devices = Device.objects.all().order_by('name')
    return render(request, 'fiber_route_builder.html', {
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        'devices': devices
    })

# =============================================================================
# LIVE STATUS / REALTIME
# =============================================================================

def fetch_interface_status(hostid, primary_item_key=None, interfaceid=None, rx_key=None, tx_key=None):
    """
    Wrapper legado para manter compatibilidade de endpoints j? existentes.
    """
    return fetch_interface_status_advanced(hostid, primary_item_key, interfaceid, rx_key, tx_key)

def combine_cable_status(o_status, d_status):
    """
    Combina status de origem e destino para determinar status final do cabo.
    """
    return combine_cable_status_service(o_status, d_status)

@login_required
@handle_api_errors
def api_fiber_live_status(request, cable_id):
    """
    Consulta status em tempo real de um cabo, atualiza se necess?rio.
    """
    try:
        cable = FiberCable.objects.select_related('origin_port__device', 'destination_port__device').get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({'error': 'FiberCable n?o encontrado'}, status=404)
    o_dev = cable.origin_port.device
    d_dev = cable.destination_port.device
    o_status, o_reason = fetch_interface_status(
        o_dev.zabbix_hostid,
        primary_item_key=cable.origin_port.zabbix_item_key,
        interfaceid=cable.origin_port.zabbix_interfaceid,
        rx_key=cable.origin_port.rx_power_item_key,
        tx_key=cable.origin_port.tx_power_item_key,
    )
    d_status, d_reason = fetch_interface_status(
        d_dev.zabbix_hostid,
        primary_item_key=cable.destination_port.zabbix_item_key,
        interfaceid=cable.destination_port.zabbix_interfaceid,
        rx_key=cable.destination_port.rx_power_item_key,
        tx_key=cable.destination_port.tx_power_item_key,
    )
    combined = combine_cable_status(o_status, d_status)
    persist = request.GET.get('persist', '1').lower() in ('1', 'true', 'yes')
    changed = combined != cable.status
    if persist and changed:
        prev = cable.status
        cable.update_status(combined)
        FiberEvent.objects.create(
            fiber=cable,
            previous_status=prev,
            new_status=combined,
            detected_reason='live-endpoint'
        )
    return JsonResponse({
        'cable_id': cable.id,
        'name': cable.name,
        'origin_status': o_status,
        'destination_status': d_status,
        'origin_reason': o_reason,
        'destination_reason': d_reason,
        'combined_status': combined,
        'stored_status': cable.status,
        'changed': changed,
        'persisted': persist and changed,
    })

@login_required
@require_GET
@conditional_cache_page(60)
@handle_api_errors
def api_fibers_live_status_all(request):
    """
    Consulta status em tempo real de todos os cabos, atualiza se necess?rio.
    """
    persist = request.GET.get('persist', '0').lower() in ('1', 'true', 'yes')
    results = []
    cables = FiberCable.objects.select_related('origin_port__device', 'destination_port__device')
    changed_any = 0
    for cable in cables:
        o_dev = cable.origin_port.device
        d_dev = cable.destination_port.device
        o_status, o_reason = fetch_interface_status(
            o_dev.zabbix_hostid,
            primary_item_key=cable.origin_port.zabbix_item_key,
            interfaceid=cable.origin_port.zabbix_interfaceid,
            rx_key=cable.origin_port.rx_power_item_key,
            tx_key=cable.origin_port.tx_power_item_key,
        )
        d_status, d_reason = fetch_interface_status(
            d_dev.zabbix_hostid,
            primary_item_key=cable.destination_port.zabbix_item_key,
            interfaceid=cable.destination_port.zabbix_interfaceid,
            rx_key=cable.destination_port.rx_power_item_key,
            tx_key=cable.destination_port.tx_power_item_key,
        )
        combined = combine_cable_status(o_status, d_status)
        changed = combined != cable.status
        if persist and changed:
            prev = cable.status
            cable.update_status(combined)
            FiberEvent.objects.create(
                fiber=cable,
                previous_status=prev,
                new_status=combined,
                detected_reason='live-endpoint-bulk'
            )
            changed_any += 1
        results.append({
            'cable_id': cable.id,
            'name': cable.name,
            'origin_status': o_status,
            'destination_status': d_status,
            'origin_reason': o_reason,
            'destination_reason': d_reason,
            'combined_status': combined,
            'stored_status': cable.status,
            'changed': changed,
            'will_persist': persist,
        })
    return JsonResponse({
        'cables': results,
        'persist': persist,
        'changed_persisted': changed_any,
    })

@login_required
@handle_api_errors
def api_fibers_refresh_status(request):
    """
    For?a avalia??o e persist?ncia de todos os cabos usando l?gica avan?ada.
    ?til para disparo manual ou integra??o externa sem usar management command.
    """
    if request.method not in ('POST', 'PUT'):
        return HttpResponseBadRequest('POST ou PUT esperado')
    cables = FiberCable.objects.select_related('origin_port__device', 'destination_port__device')
    updated = 0
    results = []
    for cable in cables:
        eval_data = evaluate_cable_status_for_cable(cable)
        if eval_data['changed']:
            prev = cable.status
            cable.update_status(eval_data['combined_status'])
            FiberEvent.objects.create(
                fiber=cable,
                previous_status=prev,
                new_status=eval_data['combined_status'],
                detected_reason='api-refresh'
            )
            updated += 1
        results.append({
            'cable_id': cable.id,
            'name': cable.name,
            'old_status': eval_data['previous_status'],
            'new_status': eval_data['combined_status'],
            'changed': eval_data['changed']
        })
    return JsonResponse({'updated': updated, 'total': len(results), 'results': results})

# =============================================================================
# IMPORTA??O SIMPLIFICADA DO ZABBIX
# =============================================================================

@login_required
@require_GET
@conditional_cache_page(60)
@handle_api_errors
def api_zabbix_discover_hosts(request):
    """
    Descobre hosts cadastrados no Zabbix.
    """
    hosts = zabbix_request('host.get', {
        'output': ['hostid', 'host', 'name'],
        'selectInterfaces': ['interfaceid', 'ip', 'dns', 'port', 'type']
    }) or []
    results = []
    for h in hosts:
        interfaces = h.get('interfaces', [])
        results.append({
            'hostid': h.get('hostid'),
            'name': h.get('name') or h.get('host'),
            'interfaces': interfaces,
        })
    return JsonResponse({'hosts': results})

@login_required
@handle_api_errors
def api_bulk_create_inventory(request):
    """
    Cria invent?rio em lote (sites, devices, ports, fibers) via payload JSON.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest('POST esperado')
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return HttpResponseBadRequest('JSON inv?lido')
    sites_payload = payload.get('sites', [])
    devices_payload = payload.get('devices', [])
    ports_payload = payload.get('ports', [])
    fibers_payload = payload.get('fibers', [])
    created = {'sites': 0, 'devices': 0, 'ports': 0, 'fibers': 0}
    site_map = {s.name: s for s in Site.objects.all()}
    device_map = {}
    # Sites
    for s in sites_payload:
        name = s.get('name')
        if not name:
            continue
        site, was_created = Site.objects.get_or_create(name=name, defaults={
            'city': s.get('city', ''),
            'latitude': s.get('lat'),
            'longitude': s.get('lng'),
            'description': s.get('description', '')
        })
        if was_created:
            created['sites'] += 1
        site_map[site.name] = site
    # Devices
    for d in devices_payload:
        site_name = d.get('site')
        site = site_map.get(site_name)
        if not site:
            continue
        device, was_created = Device.objects.get_or_create(
            site=site,
            name=d.get('name'),
            defaults={
                'vendor': d.get('vendor', ''),
                'model': d.get('model', ''),
                'zabbix_hostid': d.get('zabbix_hostid', '')
            }
        )
        if was_created:
            created['devices'] += 1
        device_map[(site.name, device.name)] = device
    # Ports
    port_map = {}
    for p in ports_payload:
        site_name = p.get('site')
        device_name = p.get('device')
        device = device_map.get((site_name, device_name))
        if not device:
            continue
        port, was_created = Port.objects.get_or_create(
            device=device,
            name=p.get('name'),
            defaults={
                'zabbix_item_key': p.get('zabbix_item_key', ''),
                'zabbix_interfaceid': p.get('zabbix_interfaceid', ''),
                'notes': p.get('notes', '')
            }
        )
        if was_created:
            created['ports'] += 1
        port_map[(device.id, port.name)] = port
    # Fibers
    for f in fibers_payload:
        o_dev = device_map.get((f.get('origin_site'), f.get('origin_device')))
        d_dev = device_map.get((f.get('dest_site'), f.get('dest_device')))
        o = port_map.get((o_dev.id, f.get('origin_port'))) if o_dev else None
        d = port_map.get((d_dev.id, f.get('dest_port'))) if d_dev else None
        if not o or not d:
            continue
        fiber, was_created = FiberCable.objects.get_or_create(
            name=f.get('name'),
            defaults={
                'origin_port': o,
                'destination_port': d,
                'length_km': f.get('length_km'),
                'path_coordinates': f.get('path'),
                'status': FiberCable.STATUS_UNKNOWN
            }
        )
        if was_created:
            created['fibers'] += 1
    return JsonResponse({'created': created})

@login_required
@require_GET
@conditional_cache_page(120)
@handle_api_errors
def api_sites(request):
    """
    Lista todos os sites com devices associados.
    """
    sites = Site.objects.prefetch_related(
        Prefetch('devices', queryset=Device.objects.only('id', 'name', 'zabbix_hostid'))
    )
    data = []
    for s in sites:
        data.append({
            'id': s.id,
            'name': s.name,
            'city': s.city,
            'lat': float(s.latitude) if s.latitude is not None else None,
            'lng': float(s.longitude) if s.longitude is not None else None,
            'devices': [
                {
                    'id': d.id,
                    'name': d.name,
                    'zabbix_hostid': d.zabbix_hostid,
                } for d in s.devices.all()
            ]
        })
    return JsonResponse({'sites': data})
