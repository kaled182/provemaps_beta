from __future__ import annotations

import uuid
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from .models import Installation

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def api_telemetry_ping(request):
    """
    Receives a ping from a ProVemaps installation.
    No authentication required — installations may not share credentials.
    Rate-limiting is handled at the nginx/proxy level.
    """
    import json

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "invalid json"}, status=400)

    raw_id = body.get("id", "")
    version = str(body.get("version", "unknown"))[:32]
    os_platform = str(body.get("os", ""))[:64]

    try:
        installation_id = uuid.UUID(str(raw_id))
    except (ValueError, AttributeError):
        return JsonResponse({"error": "invalid id"}, status=400)

    installation, created = Installation.objects.get_or_create(
        installation_id=installation_id,
        defaults={"version": version, "os_platform": os_platform},
    )

    if not created:
        installation.version = version
        installation.os_platform = os_platform
        installation.ping_count += 1
        installation.save(update_fields=["version", "os_platform", "ping_count", "last_seen"])

    logger.info(
        "Telemetry ping: %s v%s (%s) — total=%d",
        installation_id,
        version,
        os_platform,
        installation.ping_count,
    )

    return JsonResponse({"ok": True, "new": created})


@require_http_methods(["GET"])
@login_required
def api_telemetry_stats(request):
    """
    Returns aggregated stats for the SystemPanel dashboard.
    Only accessible to authenticated users.
    """
    now = timezone.now()
    last_30 = now - timedelta(days=30)
    last_7 = now - timedelta(days=7)

    total = Installation.objects.count()
    active_30d = Installation.objects.filter(last_seen__gte=last_30).count()
    active_7d = Installation.objects.filter(last_seen__gte=last_7).count()

    # Version distribution (active 30d)
    from django.db.models import Count
    versions = (
        Installation.objects.filter(last_seen__gte=last_30)
        .values("version")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    return JsonResponse({
        "total": total,
        "active_30d": active_30d,
        "active_7d": active_7d,
        "versions": list(versions),
    })
