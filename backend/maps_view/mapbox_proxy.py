"""Mapbox API proxy to bypass CSP restrictions in development.

All endpoints remain protected via Django sessions (`@login_required`).
The proxy fetches assets server-side to avoid mixed-content issues when the
SPA runs over HTTP.
"""
from __future__ import annotations

import logging
from typing import Optional

import requests
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from setup_app.models import FirstTimeSetup

logger = logging.getLogger(__name__)

MAPBOX_API_BASE = "https://api.mapbox.com"
TIMEOUT = 10  # seconds


def _get_mapbox_token() -> Optional[str]:
    """Return the stored Mapbox token or ``None`` if missing."""
    try:
        config = FirstTimeSetup.objects.first()
        token = getattr(config, "mapbox_token", None)
        if token:
            return token
        logger.warning("[MapboxProxy] Token Mapbox não configurado")
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.error("[MapboxProxy] Erro ao obter token Mapbox: %s", exc)
    return None


def _log_request(request: HttpRequest, resource: str) -> None:
    logger.info(
        "[MapboxProxy] %s | user=%s authenticated=%s path=%s",
        resource,
        getattr(request.user, "username", "anon"),
        request.user.is_authenticated,
        request.path,
    )


@login_required
@csrf_exempt
@require_http_methods(["GET"])
def proxy_mapbox_style(request: HttpRequest, style_id: str) -> HttpResponse:
    """Proxy `/styles/v1/{style_id}` JSON styles."""
    _log_request(request, "style")
    token = _get_mapbox_token()
    if not token:
        return JsonResponse({"error": "Token Mapbox não configurado"}, status=500)

    params = dict(request.GET)
    params["access_token"] = token
    url = f"{MAPBOX_API_BASE}/styles/v1/{style_id}"

    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
        return HttpResponse(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type", "application/json"),
        )
    except requests.RequestException as exc:  # pragma: no cover
        logger.error("[MapboxProxy] Falha ao buscar style: %s", exc)
        return JsonResponse({"error": str(exc)}, status=502)


@login_required
@csrf_exempt
@require_http_methods(["GET"])
def proxy_mapbox_tiles(
    request: HttpRequest,
    tileset: str,
    z: int,
    x: int,
    y: int,
) -> HttpResponse:
    """Proxy Mapbox vector tiles."""
    _log_request(request, "tile")
    token = _get_mapbox_token()
    if not token:
        return HttpResponse(status=500)

    params = {"access_token": token}
    url = f"{MAPBOX_API_BASE}/v4/{tileset}/{z}/{x}/{y}.vector.pbf"

    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
        return HttpResponse(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type", "application/x-protobuf"),
        )
    except requests.RequestException as exc:  # pragma: no cover
        logger.error("[MapboxProxy] Falha ao buscar tile: %s", exc)
        return JsonResponse({"error": str(exc)}, status=502)


@login_required
@csrf_exempt
@require_http_methods(["GET"])
def proxy_mapbox_sprites(
    request: HttpRequest,
    style_id: str,
    sprite_file: str,
) -> HttpResponse:
    """Proxy sprite JSON/PNG assets."""
    _log_request(request, "sprite")
    token = _get_mapbox_token()
    if not token:
        return HttpResponse(status=500)

    params = {"access_token": token}
    url = f"{MAPBOX_API_BASE}/styles/v1/{style_id}/sprite/{sprite_file}"

    content_type = "application/json"
    if sprite_file.endswith(".png"):
        content_type = "image/png"
    elif sprite_file.endswith(".webp"):
        content_type = "image/webp"

    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
        return HttpResponse(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type", content_type),
        )
    except requests.RequestException as exc:  # pragma: no cover
        logger.error("[MapboxProxy] Falha ao buscar sprite: %s", exc)
        return HttpResponse(status=502)


@login_required
@csrf_exempt
@require_http_methods(["GET"])
def proxy_mapbox_glyphs(
    request: HttpRequest,
    font_stack: str,
    glyph_range: str,
) -> HttpResponse:
    """Proxy glyph PBF files."""
    _log_request(request, "glyph")
    token = _get_mapbox_token()
    if not token:
        return HttpResponse(status=500)

    params = {"access_token": token}
    url = f"{MAPBOX_API_BASE}/fonts/v1/mapbox/{font_stack}/{glyph_range}.pbf"

    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
        return HttpResponse(
            response.content,
            status=response.status_code,
            content_type="application/x-protobuf",
        )
    except requests.RequestException as exc:  # pragma: no cover
        logger.error("[MapboxProxy] Falha ao buscar glyph: %s", exc)
        return HttpResponse(status=502)
