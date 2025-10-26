"""
Views for the maps_view app.

Thin controllers that orchestrate service calls and handle HTTP responses.
Business logic is delegated to the services layer.
"""

import logging

from django.shortcuts import render
from django.conf import settings
from setup_app.services import runtime_settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from prometheus_client import REGISTRY, generate_latest

from .services import get_hosts_status_data
from .realtime.events import build_dashboard_payload


logger = logging.getLogger(__name__)


def build_dashboard_event_payload():
    """Helper used by background jobs to emit real-time dashboard events."""
    return build_dashboard_payload(get_hosts_status_data())


# ----------------------------- Views -----------------------------

@login_required
def dashboard_view(request):
    """
    Dashboard principal (HTML) com Cache SWR.
    
    Serve dados do cache (frescos ou stale) imediatamente.
    Se stale, dispara refresh em background.
    """
    from maps_view.cache_swr import get_dashboard_cached
    from maps_view.tasks import refresh_dashboard_cache_task
    
    # Get data com SWR pattern
    cache_result = get_dashboard_cached(
        fetch_fn=get_hosts_status_data,
        async_task=refresh_dashboard_cache_task.delay,
    )
    
    context = cache_result["data"]
    
    # Adiciona metadata de cache para o template
    context["cache_metadata"] = {
        "is_stale": cache_result.get("is_stale", False),
        "timestamp": cache_result.get("timestamp"),
        "cache_hit": cache_result.get("cache_hit", False),
    }
    
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
    """
    JSON API mirroring dashboard calculations with SWR cache.
    
    Returns data with cache metadata (is_stale, timestamp).
    """
    from maps_view.cache_swr import get_dashboard_cached
    from maps_view.tasks import refresh_dashboard_cache_task
    
    # Get data com SWR pattern
    cache_result = get_dashboard_cached(
        fetch_fn=get_hosts_status_data,
        async_task=refresh_dashboard_cache_task.delay,
    )
    
    data = cache_result["data"]

    if not data['hosts_status']:
        return JsonResponse(
            {'error': 'Nenhum device com Zabbix configurado'},
            status=404
        )

    return JsonResponse({
        'total': data['hosts_summary']['total'],
        'hosts': data['hosts_status'],
        'summary': data['hosts_summary'],
        'cache_metadata': {
            'is_stale': cache_result.get("is_stale", False),
            'timestamp': cache_result.get("timestamp"),
            'cache_hit': cache_result.get("cache_hit", False),
        }
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
