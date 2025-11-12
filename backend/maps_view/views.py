"""
Views for the maps_view app.

Thin controllers that orchestrate service calls and handle HTTP responses.
Business logic is delegated to the services layer.
"""

import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
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
    """Dashboard entrypoint.

    When feature flag ``USE_VUE_DASHBOARD`` is enabled this serves the Vue 3
    SPA (static HTML from ``staticfiles/vue-spa/index.html``).
    Otherwise it falls back to the legacy Django template ``dashboard.html``.

    Canary rollout: If ``VUE_DASHBOARD_ROLLOUT_PERCENTAGE`` is set (0-100),
    only that percentage of users will see the Vue dashboard.
    User assignment is based on session ID hash for consistency.
    """
    import hashlib

    google_maps_key = (
        runtime_settings.get_runtime_config().google_maps_api_key
        or getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    )

    template_name = 'dashboard.html'
    use_vue = getattr(settings, 'USE_VUE_DASHBOARD', False)

    if use_vue:
        # Canary rollout logic
        rollout_pct = getattr(
            settings, 'VUE_DASHBOARD_ROLLOUT_PERCENTAGE', 100
        )

        if rollout_pct < 100:
            # Ensure session exists
            if not request.session.session_key:
                request.session.create()

            # Hash session ID to get consistent user assignment
            session_hash = hashlib.md5(
                request.session.session_key.encode()
            ).hexdigest()
            user_bucket = int(session_hash[:8], 16) % 100

            # Serve Vue to users in rollout bucket
            if user_bucket < rollout_pct:
                template_name = 'spa.html'
        else:
            # 100% rollout - serve Vue to everyone
            template_name = 'spa.html'

    context = {
            'GOOGLE_MAPS_API_KEY': google_maps_key,
            'USE_VUE_DASHBOARD': getattr(
                settings, 'USE_VUE_DASHBOARD', False
            ),
            'VUE_DASHBOARD_ROLLOUT_PERCENTAGE': getattr(
                settings, 'VUE_DASHBOARD_ROLLOUT_PERCENTAGE', 0
            ),
        }

    return render(request, template_name, context)


@login_required
def dashboard_data_api(request):
    """
    JSON API endpoint for dashboard data (hosts_status + hosts_summary).

    Uses the same SWR cache as the legacy view to avoid duplicate Zabbix queries.
    Frontend polls this endpoint to update the map without blocking page load.
    """
    from maps_view.cache_swr import get_dashboard_cached
    from maps_view.tasks import refresh_dashboard_cache_task

    # Retrieve data following the SWR pattern
    cache_result = get_dashboard_cached(
        fetch_fn=get_hosts_status_data,
        async_task=refresh_dashboard_cache_task.delay,
    )

    response_data = cache_result["data"]
    response_data["cache_metadata"] = {
        "is_stale": cache_result.get("is_stale", False),
        "timestamp": cache_result.get("timestamp"),
        "cache_hit": cache_result.get("cache_hit", False),
    }

    return JsonResponse(response_data)


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
                {
                    "raw": sample,
                    "value": value.strip(),
                    "labels": metrics_labels,
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
