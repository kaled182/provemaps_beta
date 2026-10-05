"""Views de vídeo: proxy HLS, pré-visualização, câmeras, mosaicos, definições, teste de stream.

Finas de propósito (EV-0017d): a lógica está em `setup_app.usecases.video`. O proxy HLS
mantém aqui o streaming da resposta porque é plumbing HTTP, não regra de domínio.
"""

from __future__ import annotations

import json
import logging

import requests
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from ..usecases import video as usecase
from ._auth import staff_required

logger = logging.getLogger(__name__)

HLS_PASSTHROUGH_HEADERS = [
    "Cache-Control",
    "Last-Modified",
    "ETag",
    "Content-Length",
    "Accept-Ranges",
]


def _error(exc: usecase.VideoError):
    return JsonResponse({"success": False, "message": str(exc)}, status=exc.status)


def _invalid_json():
    return JsonResponse({"success": False, "message": "Invalid JSON data"}, status=400)


def _stream_upstream_response(response: requests.Response, chunk_size: int = 64 * 1024):
    try:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk
    finally:
        response.close()


# ── HLS e pré-visualização ───────────────────────────────────────────────────


@require_GET
@staff_required
def proxy_video_gateway_hls(request, gateway_id: int, resource: str = "index.m3u8"):
    try:
        gateway = usecase.get_video_gateway(gateway_id)
        usecase.require_video_access(request.user, gateway)
        sanitized = usecase.sanitize_hls_resource(resource)
    except usecase.VideoError as exc:
        return _error(exc)

    upstream_params = dict(request.GET.items())
    upstream_params.setdefault("mode", "legacy")
    try:
        upstream = requests.get(
            usecase.hls_target_url(gateway, sanitized),
            params=upstream_params,
            timeout=usecase.HLS_UPSTREAM_TIMEOUT,
            stream=True,
        )
    except requests.RequestException as exc:
        logger.warning("Falha ao proxy HLS para gateway %s (%s): %s", gateway.id, sanitized, exc)
        return HttpResponse(status=502)

    if upstream.status_code >= 400:
        content_type = upstream.headers.get("Content-Type", "text/plain")
        body = upstream.content[:4096]
        upstream.close()
        return HttpResponse(body, status=upstream.status_code, content_type=content_type)

    response = StreamingHttpResponse(
        _stream_upstream_response(upstream),
        status=upstream.status_code,
        content_type=usecase.hls_content_type(sanitized, upstream.headers.get("Content-Type")),
    )
    for header in HLS_PASSTHROUGH_HEADERS:
        value = upstream.headers.get(header)
        if value:
            response[header] = value
    response["Cache-Control"] = upstream.headers.get("Cache-Control", "no-cache, private")
    return response


@require_http_methods(["POST"])
@staff_required
def start_video_gateway_preview(request, gateway_id: int):
    try:
        gateway = usecase.get_video_gateway(gateway_id)
        result = usecase.start_preview(gateway)
    except usecase.VideoError as exc:
        return _error(exc)
    proxy_url = request.build_absolute_uri(
        reverse("setup_app:video_hls_proxy", args=[gateway.id, "index.m3u8"])
    )
    return JsonResponse({"success": True, **result, "playback_proxy_url": proxy_url})


@require_http_methods(["POST"])
@staff_required
def stop_video_gateway_preview(request, gateway_id: int):
    try:
        gateway = usecase.get_video_gateway(gateway_id)
        usecase.stop_preview(gateway)
    except usecase.VideoError as exc:
        return _error(exc)
    return JsonResponse({"success": True})


# ── Câmeras e mosaicos ───────────────────────────────────────────────────────


@require_http_methods(["GET"])
@staff_required
def video_cameras_list(request):
    """Câmeras visíveis ao utilizador; `?site=<id>` (ou `site_id`) filtra pelo `display_name` do Site."""
    try:
        results = usecase.list_cameras_for(
            request.user, request.GET.get("site") or request.GET.get("site_id")
        )
    except Exception as exc:
        logger.exception("Error listing video cameras")
        return JsonResponse({"success": False, "message": str(exc)}, status=500)
    return JsonResponse({"success": True, "count": len(results), "results": results})


@require_http_methods(["GET", "POST"])
@staff_required
def video_mosaics_list(request):
    if request.method == "GET":
        try:
            mosaics = usecase.list_mosaics_for(
                request.user, request.GET.get("site_id") or request.GET.get("site")
            )
        except Exception as exc:
            logger.exception("Error listing video mosaics")
            return JsonResponse(
                {"success": False, "message": f"Failed to list mosaics: {exc}"}, status=500
            )
        return JsonResponse({"success": True, "mosaics": mosaics})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return _invalid_json()
    try:
        mosaic = usecase.create_mosaic(request.user, data)
    except usecase.VideoError as exc:
        return _error(exc)
    except Exception as exc:
        logger.exception("Error creating video mosaic")
        return JsonResponse(
            {"success": False, "message": f"Failed to create mosaic: {exc}"}, status=500
        )
    return JsonResponse(
        {"success": True, "message": "Mosaico criado com sucesso", "mosaic": mosaic}
    )


@require_http_methods(["GET", "PATCH", "DELETE"])
@staff_required
def video_mosaic_detail(request, mosaic_id: int):
    try:
        mosaic = usecase.get_mosaic_for(request.user, mosaic_id)
    except usecase.VideoError as exc:
        return _error(exc)

    if request.method == "GET":
        return JsonResponse({"success": True, "mosaic": usecase.serialize_mosaic(mosaic)})

    if request.method == "DELETE":
        try:
            name = usecase.delete_mosaic(mosaic)
        except Exception as exc:
            logger.exception("Error deleting video mosaic")
            return JsonResponse(
                {"success": False, "message": f"Failed to delete mosaic: {exc}"}, status=500
            )
        return JsonResponse({"success": True, "message": f"Mosaico '{name}' removido com sucesso"})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return _invalid_json()
    try:
        updated = usecase.update_mosaic(request.user, mosaic, data)
    except usecase.VideoError as exc:
        return _error(exc)
    except Exception as exc:
        logger.exception("Error updating video mosaic")
        return JsonResponse(
            {"success": False, "message": f"Failed to update mosaic: {exc}"}, status=500
        )
    return JsonResponse(
        {"success": True, "message": "Mosaico atualizado com sucesso", "mosaic": updated}
    )


# ── Definições e teste de stream (qualquer utilizador autenticado, como antes) ──


@login_required
@require_http_methods(["GET", "POST"])
def camera_settings(request):
    if request.method == "GET":
        try:
            return JsonResponse({"success": True, "settings": usecase.get_camera_settings()})
        except Exception as exc:
            logger.exception("Error loading camera settings")
            return JsonResponse({"success": False, "message": str(exc)}, status=500)
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError) as exc:
        return JsonResponse({"success": False, "message": f"Invalid JSON: {exc}"}, status=400)
    try:
        usecase.save_camera_settings(body)
    except Exception as exc:
        logger.exception("Error saving camera settings")
        return JsonResponse({"success": False, "message": str(exc)}, status=500)
    return JsonResponse({"success": True, "message": "Configurações de câmeras salvas."})


@login_required
@require_POST
def test_stream(request):
    """Testa alcance TCP de `host:porta` de uma URL de stream."""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError) as exc:
        return JsonResponse({"success": False, "message": f"Invalid JSON: {exc}"}, status=400)
    try:
        result = usecase.test_stream_reachability(
            body.get("stream_url") or "", int(body.get("timeout") or 5)
        )
    except usecase.VideoError as exc:
        return _error(exc)
    except Exception as exc:
        logger.exception("Error testing stream connection")
        return JsonResponse({"success": False, "message": str(exc)}, status=500)
    return JsonResponse(result)
