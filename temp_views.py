"""
Views for the maps_view app.

Thin controllers that orchestrate service calls and handle HTTP responses.
Business logic is delegated to the services layer.
"""

import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from prometheus_client import REGISTRY, generate_latest
from setup_app.services import runtime_settings

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
    Primary dashboard (HTML) backed by the SWR cache helper.

    The view uses the cache to serve fresh or stale data immediately and
    schedules a background refresh when the snapshot is stale.
    """
    from maps_view.cache_swr import get_dashboard_cached
    from maps_view.tasks import refresh_dashboard_cache_task

    # Retrieve data following the SWR pattern
    cache_result = get_dashboard_cached(
        fetch_fn=get_hosts_status_data,
        async_task=refresh_dashboard_cache_task.delay,
    )

    context = cache_result["data"]

    # Inject cache metadata for the template to display status banners
    context["cache_metadata"] = {
        "is_stale": cache_result.get("is_stale", False),
        "timestamp": cache_result.get("timestamp"),
        "cache_hit": cache_result.get("cache_hit", False),
    }

    google_maps_key = (
        runtime_settings.get_runtime_config().google_maps_api_key
        or getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    )

    return render(
        request,
        'dashboard.html',
        {
            'GOOGLE_MAPS_API_KEY': google_maps_key,
            **context,
        },
    )


# Mantido para compatibilidade (se usado em outros lugares)
def dashboard_with_hosts_status():
    """Compatibility alias kept for legacy imports."""
    return get_hosts_status_data()


@login_required
def metrics_dashboard(request):
    """
    Render a simple HTML view for Prometheus metrics to aid manual inspection.

    Includes a basic client-side filter by metric name or description.
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
            current = {
                "name": name,
                "help": help_text,
                "type": "",
                "samples": [],
            }
        elif line.startswith("# TYPE"):
            _, _, remainder = line.partition("TYPE ")
            name, _, metric_type = remainder.partition(" ")
            if current["name"] == name:
                current["type"] = metric_type
        elif line.startswith("#"):
            continue
        elif line.strip():
            sample = line.strip()
            sample_labels = {}
            value = ""
            if "{" in sample:
                metric_name, rest = sample.split("{", 1)
                labels_part, value = rest.split("}", 1)
                for label in labels_part.split(","):
                    if "=" in label:
                        key, val = label.split("=", 1)
                        sample_labels[key] = val.strip('"')
                value = value.strip()
            else:
                metric_name, value = sample.split(" ", 1)
            current["samples"].append(
                {
                    "raw": sample,
                    "value": value.strip(),
                    "labels": sample_labels,
                }
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
