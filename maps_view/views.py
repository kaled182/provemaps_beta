import logging

from django.shortcuts import render
from django.conf import settings
from setup_app.services import runtime_settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q
from typing import List, Dict, Any, Optional
from zabbix_api.services.zabbix_service import zabbix_request
from zabbix_api.models import Device
from prometheus_client import REGISTRY, generate_latest

from .realtime.events import build_dashboard_payload


logger = logging.getLogger(__name__)


class HostStatusProcessor:
    """Process host status information for dashboard and API responses."""

    AVAILABLE_MAP = {'0': 'Unknown', '1': 'Available', '2': 'Unavailable'}
    STATUS_MAP = {'0': 'Active', '1': 'Disabled'}

    @classmethod
    def get_status_class_and_color(cls, availability: str) -> tuple[str, str]:
        """Return CSS class and color code for the given availability."""
        availability_str = str(availability)
        if availability_str == '1':
            return 'bg-green-100 text-green-800 border-green-300', 'green'
        if availability_str == '2':
            return 'bg-red-100 text-red-800 border-red-300', 'red'
        return 'bg-gray-100 text-gray-800 border-gray-300', 'gray'

    @classmethod
    def get_primary_interface(cls, interfaces: List[Dict]) -> Optional[Dict]:
        """Pick the primary (main == 1) interface or fallback to the first available one."""
        if not interfaces:
            return None
        
        # Procura interface principal
        for iface in interfaces:
            main = iface.get('main')
            if str(main) == '1':  # aceita '1' ou 1
                return iface
        
        # Fallback para primeira interface
        return interfaces[0] if interfaces else None

    @classmethod
    def calculate_availability(cls, host_data: Dict, primary_interface: Optional[Dict]) -> str:
        """Compute availability, preferring interface state when host reports 'unknown'."""
        host_avail = str(host_data.get('available', '0'))
        
        # If the host is unknown but interface carries status, prefer the interface state
        if primary_interface and host_avail == '0':
            interface_avail = primary_interface.get('available')
            if interface_avail is not None:
                return str(interface_avail)
        
        return host_avail

    @classmethod
    def calculate_statistics(cls, hosts_status: List[Dict]) -> Dict[str, Any]:
        """Compute aggregated statistics for cards/JSON."""
        total = len(hosts_status)
        if total == 0:
            return {
                'total': 0, 
                'available': 0, 
                'unavailable': 0, 
                'unknown': 0, 
                'availability_percentage': 0
            }
        
        available = sum(1 for h in hosts_status if str(h.get('available')) == '1')
        unavailable = sum(1 for h in hosts_status if str(h.get('available')) == '2')
        unknown = total - available - unavailable
        
        return {
            'total': total,
            'available': available,
            'unavailable': unavailable,
            'unknown': unknown,
            'availability_percentage': round((available / total * 100), 2) if total > 0 else 0
        }


# ---------- Helpers de dados ----------

def get_devices_with_zabbix():
    """Devices com Zabbix configurado (site join para evitar N+1)."""
    return Device.objects.select_related('site').filter(
        Q(zabbix_hostid__isnull=False) & ~Q(zabbix_hostid='')
    )


def fetch_zabbix_hosts_data(hostids: List[str]) -> List[Dict]:
    """
    Perform a single call to Zabbix including the `status` field used by the API.
    Returns an empty list on failure so rendering can continue gracefully.
    """
    if not hostids:
        return []
    
    # Ensure every host id is a string and deduplicate
    unique_hostids = list(set(str(hid) for hid in hostids if hid))
    
    try:
        return zabbix_request('host.get', {
            'output': ['hostid', 'name', 'available', 'status', 'error'],
            'hostids': unique_hostids,
            'selectInterfaces': ['interfaceid', 'ip', 'available', 'main']
        }) or []
    except Exception:
        logger.exception("Falha ao consultar hosts no Zabbix", extra={"hostids": unique_hostids})
        return []


def build_zabbix_map(zabbix_hosts: List[Dict]) -> Dict[str, Dict]:
    """Converte lista de hosts do Zabbix em mapa hostid -> dados."""
    return {str(host['hostid']): host for host in zabbix_hosts}


def process_host_status(device: Device, zabbix_map: Dict[str, Dict]) -> Dict[str, Any]:
    """Format a single host entry ready for template or API consumption."""
    host_key = str(device.zabbix_hostid)
    host_data = zabbix_map.get(host_key, {})
    interfaces = host_data.get('interfaces', [])
    primary_interface = HostStatusProcessor.get_primary_interface(interfaces)

    availability = HostStatusProcessor.calculate_availability(host_data, primary_interface)
    status_class, color = HostStatusProcessor.get_status_class_and_color(availability)

    # Dados da interface com fallbacks seguros
    interface_data = {
        'interfaceid': primary_interface.get('interfaceid') if primary_interface else None,
        'ip': primary_interface.get('ip') if primary_interface else None,
        'available': str(primary_interface.get('available')) if primary_interface and primary_interface.get('available') is not None else availability,
    }

    return {
        'device_id': device.id,
        'hostid': host_key,
        'name': host_data.get('name', device.name),
        'site': device.site.name if device.site else 'N/A',
        'available': availability,
        'available_text': HostStatusProcessor.AVAILABLE_MAP.get(availability, 'Unknown'),
        'ip': interface_data['ip'],
        'status': str(host_data.get('status', '0')),
        'status_text': HostStatusProcessor.STATUS_MAP.get(str(host_data.get('status', '0')), 'Ativo'),
        'error': host_data.get('error', ''),
        'color': color,
        'status_class': status_class,
        'interface': interface_data
    }


def get_hosts_status_data() -> Dict[str, Any]:
    """
    Build host status data for reuse across views and APIs.
    Returns a dictionary with `hosts_status` and `hosts_summary`.
    """
    devices = get_devices_with_zabbix()
    hosts_status = []
    
    if devices.exists():
        hostids = [device.zabbix_hostid for device in devices]
        zabbix_hosts = fetch_zabbix_hosts_data(hostids)
        zabbix_map = build_zabbix_map(zabbix_hosts)
        
        hosts_status = [
            process_host_status(device, zabbix_map) 
            for device in devices
        ]

    return {
        'hosts_status': hosts_status,
        'hosts_summary': HostStatusProcessor.calculate_statistics(hosts_status)
    }


def build_dashboard_event_payload() -> Dict[str, Any]:
    """Helper used by background jobs to emit real-time dashboard events."""
    return build_dashboard_payload(get_hosts_status_data())


# ----------------------------- Views -----------------------------

@login_required
def dashboard_view(request):
    """Dashboard principal (HTML)."""
    context = get_hosts_status_data()
    return render(request, 'dashboard.html', {
        'GOOGLE_MAPS_API_KEY': runtime_settings.get_runtime_config().google_maps_api_key or getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        **context
    })


# Mantido para compatibilidade (se usado em outros lugares)
def dashboard_with_hosts_status():
    """Compatibility alias kept for legacy imports."""
    return get_hosts_status_data()


@login_required
@require_GET
def api_zabbix_hosts_status(request):
    """JSON API mirroring the dashboard calculations for a single source of truth."""
    data = get_hosts_status_data()

    if not data['hosts_status']:
        return JsonResponse(
            {'error': 'Nenhum device com Zabbix configurado'},
            status=404
        )

    return JsonResponse({
        'total': data['hosts_summary']['total'],
        'hosts': data['hosts_status'],
        'summary': data['hosts_summary']
    })


@login_required
def metrics_dashboard(request):
    """
    Exibe métricas Prometheus em HTML simples para facilitar inspeção manual.
    Permite filtro por nome/descrição.
    """
    raw_lines = generate_latest(REGISTRY).decode("utf-8").splitlines()
    metrics = []
    current = {"name": None, "help": "", "type": "", "samples": []}

    for line in raw_lines:
        if line.startswith("# HELP"):
            if current["name"]:
                metrics.append(current)
            _, _, remainder = line.partition("HELP ")
            name, _, help_text = remainder.partition(" ")
            current = {"name": name, "help": help_text, "type": "", "samples": []}
        elif line.startswith("# TYPE"):
            _, _, remainder = line.partition("TYPE ")
            name, _, metric_type = remainder.partition(" ")
            if current["name"] == name:
                current["type"] = metric_type
        elif line.startswith("#"):
            continue
        elif line.strip():
            sample = line.strip()
            metrics_labels = {}
            value = ""
            if "{" in sample:
                metric_name, rest = sample.split("{", 1)
                labels_part, value = rest.split("}", 1)
                for label in labels_part.split(","):
                    if "=" in label:
                        key, val = label.split("=", 1)
                        metrics_labels[key] = val.strip('"')
                value = value.strip()
            else:
                metric_name, value = sample.split(" ", 1)
            current["samples"].append(
                {"raw": sample, "value": value.strip(), "labels": metrics_labels}
            )

    if current["name"]:
        metrics.append(current)

    query = request.GET.get("q", "").lower()
    if query:
        metrics = [
            metric
            for metric in metrics
            if query in metric["name"].lower()
            or (metric["help"] and query in metric["help"].lower())
        ]

    context = {
        "metrics": metrics,
        "query": request.GET.get("q", ""),
        "metrics_source_url": request.build_absolute_uri("/metrics/"),
    }
    return render(request, "metrics_dashboard.html", context)
