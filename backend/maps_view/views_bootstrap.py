"""
Endpoint agregado para inicializar o mapa de backbone.

Em vez de o frontend disparar 6 requests (sites, devices, fiber-cables,
cable-folders, cameras, zabbix status), faz tudo em uma única chamada
no servidor — reduzindo round-trips, overhead de DRF e tempo total.
"""

from __future__ import annotations

import logging
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _build_folders_tree() -> dict:
    from inventory.models import CableFolder, FiberCable
    from inventory.api.cable_folders import _build_tree

    folders = list(CableFolder.objects.select_related("parent").order_by("order", "name"))
    counts_qs = (
        FiberCable.objects.filter(folder__isnull=False)
        .values("folder_id")
        .annotate(n=Count("id"))
    )
    cable_counts = {row["folder_id"]: row["n"] for row in counts_qs}
    tree = _build_tree(folders, cable_counts)
    no_folder_count = FiberCable.objects.filter(folder__isnull=True).count()
    return {"tree": tree, "no_folder_count": no_folder_count}


def _serialize_cameras(request) -> list[dict]:
    from setup_app.models import MessagingGateway
    from setup_app.services import video_gateway as video_gateway_service

    qs = MessagingGateway.objects.filter(gateway_type="video", enabled=True)
    if not request.user.is_superuser:
        user_depts = request.user.profile.departments.all()
        qs = qs.filter(Q(departments__in=user_depts) | Q(departments__isnull=True)).distinct()

    def _whep_url(gw):
        cfg = gw.config or {}
        webrtc_base = (cfg.get("webrtc_public_base_url") or "").strip()
        if not webrtc_base:
            webrtc_base = getattr(settings, "VIDEO_WEBRTC_PUBLIC_BASE_URL", None) or os.environ.get("VIDEO_WEBRTC_PUBLIC_BASE_URL")
        if not webrtc_base:
            return None
        restream_key = cfg.get("restream_key") or f"gateway_{gw.id}"
        return f"{str(webrtc_base).rstrip('/')}/whep/{restream_key}"

    results = []
    for gw in qs.order_by("name"):
        results.append({
            "id": gw.id,
            "name": gw.name,
            "display_name": gw.name,
            "enabled": gw.enabled,
            "site_name": gw.site_name,
            "playback_url": video_gateway_service.build_playback_url(gw),
            "whep_url": _whep_url(gw),
            "status": "online" if gw.enabled else "offline",
            "latitude": None,
            "longitude": None,
            "description": "",
        })
    return results


@login_required
def backbone_init_api(request):
    """
    GET /api/v1/maps/backbone/init/

    Retorna em uma única resposta tudo que o `CustomMapViewer` precisa
    para renderizar o mapa de backbone:
        {
          "sites": [...],
          "devices": [...],
          "cables": [...],
          "folders": {tree, no_folder_count},
          "cameras": [...],
          "zabbix": {hosts_status, hosts_summary, ...}
        }
    """
    from inventory.models import Site, Device, FiberCable
    from inventory.serializers import (
        SiteSerializer,
        DeviceSerializer,
        FiberCableSerializer,
    )
    from maps_view.cache_swr import get_dashboard_cached
    from maps_view.services import get_hosts_status_data
    from maps_view.tasks import refresh_dashboard_cache_task

    try:
        sites_qs = Site.objects.all().order_by("display_name")[:500]
        devices_qs = (
            Device.objects.select_related("site")
            .order_by("site__display_name", "name")[:1000]
        )
        cables_qs = FiberCable.objects.all()

        sites_data = SiteSerializer(sites_qs, many=True).data
        devices_data = DeviceSerializer(devices_qs, many=True).data
        cables_data = FiberCableSerializer(cables_qs, many=True).data

        folders_data = _build_folders_tree()

        try:
            cameras_data = _serialize_cameras(request)
        except Exception as exc:
            logger.warning("backbone_init: cameras failed: %s", exc, exc_info=True)
            cameras_data = []

        try:
            zabbix_cache = get_dashboard_cached(
                fetch_fn=get_hosts_status_data,
                async_task=refresh_dashboard_cache_task.delay,
            )
            zabbix_data = zabbix_cache.get("data") or {}
        except Exception as exc:
            logger.warning("backbone_init: zabbix failed: %s", exc, exc_info=True)
            zabbix_data = {"hosts_status": [], "hosts_summary": {}}

        return JsonResponse({
            "sites": sites_data,
            "devices": devices_data,
            "cables": cables_data,
            "folders": folders_data,
            "cameras": cameras_data,
            "zabbix": zabbix_data,
        })
    except Exception as exc:
        logger.exception("backbone_init failed")
        return JsonResponse(
            {"error": "Failed to load backbone init", "detail": str(exc)},
            status=500,
        )
