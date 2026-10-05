"""Vídeo e câmeras: pré-visualização HLS, lista de câmeras, mosaicos, definições, teste de stream.

Saiu de `setup_app/api_views.py` em EV-0017d. As câmeras são `MessagingGateway` do tipo
`video`; o transmuxer e o MediaMTX ficam atrás de `services/video_gateway.py`. RBAC por
departamento (`core.Department`): superuser vê tudo, câmera/mosaico sem departamentos é
público, senão vale a interseção com os departamentos do perfil do utilizador.
"""

from __future__ import annotations

import logging
import os
import socket
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.db.models import Q

from core.models import Department
from inventory.models import Site

from ..models import MessagingGateway, VideoMosaic
from ..services import video_gateway as video_gateway_service
from ..utils import env_manager
from .gateways import user_can_access_video_gateway

logger = logging.getLogger(__name__)

PREVIEW_STARTUP_TIMEOUT = 30.0
HLS_UPSTREAM_TIMEOUT = 15
DEFAULT_STREAM_PORTS = {"rtsp": 554, "rtmp": 1935, "rtmps": 443, "http": 80, "https": 443}


class VideoError(ValueError):
    status = 400


class VideoNotFound(VideoError):
    status = 404


class VideoForbidden(VideoError):
    status = 403


class PreviewTimeout(VideoError):
    status = 504


class PreviewServiceError(VideoError):
    status = 502


class PreviewFailed(VideoError):
    status = 500


# ── Gateways de vídeo ────────────────────────────────────────────────────────


def get_video_gateway(gateway_id: int) -> MessagingGateway:
    try:
        return MessagingGateway.objects.get(id=gateway_id, gateway_type="video")
    except MessagingGateway.DoesNotExist as exc:
        raise VideoNotFound("Gateway de vídeo não encontrado.") from exc


def require_video_access(user, gateway: MessagingGateway) -> None:
    if not user_can_access_video_gateway(user, gateway):
        raise VideoForbidden("Sem permissão para acessar esta câmera.")


def sanitize_hls_resource(resource: str | None) -> str:
    """Caminho relativo dentro do stream HLS; vazio ou «pasta» vira `index.m3u8`; `..` é recusado."""
    sanitized = (resource or "index.m3u8").strip()
    if not sanitized or sanitized.endswith("/"):
        sanitized = f"{sanitized.rstrip('/')}/index.m3u8"
    sanitized = sanitized.lstrip("/")
    if ".." in sanitized:
        raise VideoError("Recurso inválido.")
    return sanitized


def hls_target_url(gateway: MessagingGateway, resource: str) -> str:
    stream_key = video_gateway_service.get_stream_key(gateway)
    return video_gateway_service.build_internal_hls_url(stream_key, resource)


def hls_content_type(resource: str, upstream_content_type: str | None) -> str:
    if upstream_content_type:
        return upstream_content_type
    return (
        "application/vnd.apple.mpegurl"
        if resource.endswith(".m3u8")
        else "application/octet-stream"
    )


def start_preview(gateway: MessagingGateway) -> dict[str, Any]:
    """Aciona o transmuxer e espera o manifesto HLS; devolve as URLs de pré-visualização."""
    stream_url = ((gateway.config or {}).get("stream_url") or "").strip()
    if not stream_url:
        raise VideoError("Configure a URL do stream antes de iniciar a pré-visualização.")
    try:
        video_gateway_service.ensure_stream_for_gateway(
            gateway, wait_ready=True, startup_timeout=PREVIEW_STARTUP_TIMEOUT
        )
    except video_gateway_service.PreviewStartTimeout as exc:
        logger.warning("Pré-visualização do gateway %s não ficou pronta: %s", gateway.id, exc)
        raise PreviewTimeout(
            "Stream HLS não ficou pronto a tempo. Verifique a origem do vídeo."
        ) from exc
    except video_gateway_service.VideoGatewayError as exc:
        logger.warning("Falha ao acionar transmuxer para gateway %s: %s", gateway.id, exc)
        raise PreviewServiceError("Não foi possível acionar o serviço de vídeo.") from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(
            "Falha inesperada ao iniciar pré-visualização do gateway %s: %s", gateway.id, exc
        )
        raise PreviewFailed("Não foi possível iniciar a pré-visualização do stream.") from exc

    gateway.refresh_from_db(fields=["config", "updated_at"])
    return {
        "preview_url": (gateway.config or {}).get("preview_url", ""),
        "playback_url": video_gateway_service.build_playback_url(gateway),
    }


def stop_preview(gateway: MessagingGateway) -> None:
    try:
        video_gateway_service.stop_stream_for_gateway(gateway)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Falha ao encerrar pré-visualização do gateway %s: %s", gateway.id, exc)
        raise PreviewFailed("Não foi possível encerrar a pré-visualização do stream.") from exc


# ── Câmeras ──────────────────────────────────────────────────────────────────


def _whep_url(gateway: MessagingGateway) -> str | None:
    cfg = gateway.config or {}
    webrtc_base = (cfg.get("webrtc_public_base_url") or "").strip()
    if not webrtc_base:
        webrtc_base = getattr(settings, "VIDEO_WEBRTC_PUBLIC_BASE_URL", None) or os.environ.get(
            "VIDEO_WEBRTC_PUBLIC_BASE_URL"
        )
    if not webrtc_base:
        return None
    restream_key = cfg.get("restream_key") or f"gateway_{gateway.id}"
    return f"{str(webrtc_base).rstrip('/')}/whep/{restream_key}"


def _restrict_to_user_departments(qs, user):
    if user.is_superuser:
        return qs
    user_depts = user.profile.departments.all()
    return qs.filter(Q(departments__in=user_depts) | Q(departments__isnull=True)).distinct()


def list_cameras_for(user, site_param: str | None = None) -> list[dict[str, Any]]:
    """Câmeras ativas visíveis ao utilizador; `site_param` (id de `inventory.Site`) filtra por `site_name`."""
    qs = _restrict_to_user_departments(
        MessagingGateway.objects.filter(gateway_type="video", enabled=True), user
    )
    site_name = None
    if site_param:
        try:
            site_name = Site.objects.get(pk=int(site_param)).display_name
        except Exception:
            site_name = None
    if site_name:
        qs = qs.filter(site_name=site_name)

    return [
        {
            "id": gw.id,
            "name": gw.name,
            "enabled": gw.enabled,
            "site_name": gw.site_name,
            "playback_url": video_gateway_service.build_playback_url(gw),
            "whep_url": _whep_url(gw),
        }
        for gw in qs.order_by("name")
    ]


# ── Mosaicos ─────────────────────────────────────────────────────────────────


def serialize_mosaic(mosaic: VideoMosaic) -> dict[str, Any]:
    return {
        "id": mosaic.id,
        "name": mosaic.name,
        "layout": mosaic.layout,
        "cameras": mosaic.cameras or [],
        "site_id": mosaic.site_id,
        "departments": [{"id": d.id, "name": d.name} for d in mosaic.departments.all()],
        "created_at": mosaic.created_at.isoformat() if mosaic.created_at else None,
        "updated_at": mosaic.updated_at.isoformat() if mosaic.updated_at else None,
    }


def list_mosaics_for(user, site_id_param: str | None = None) -> list[dict[str, Any]]:
    mosaics = _restrict_to_user_departments(VideoMosaic.objects.all(), user).order_by("name")
    if site_id_param:
        try:
            mosaics = mosaics.filter(site_id=int(site_id_param))
        except ValueError:
            pass
    return [serialize_mosaic(m) for m in mosaics]


def _check_department_assignment(user, department_ids, message: str) -> None:
    if user.is_superuser or not department_ids:
        return
    user_dept_ids = set(user.profile.departments.values_list("id", flat=True))
    if not set(department_ids).issubset(user_dept_ids):
        raise VideoForbidden(message)


def create_mosaic(user, data: dict[str, Any]) -> dict[str, Any]:
    name = str(data.get("name", "")).strip()
    if not name:
        raise VideoError("Nome do mosaico é obrigatório")
    department_ids = data.get("department_ids", [])
    _check_department_assignment(
        user, department_ids, "Você só pode criar mosaicos em departamentos aos quais pertence."
    )
    site_id = data.get("site_id")
    mosaic = VideoMosaic.objects.create(
        name=name,
        layout=data.get("layout", "2x2"),
        cameras=data.get("cameras", []),
        site_id=site_id if isinstance(site_id, int) else None,
    )
    if department_ids:
        mosaic.departments.set(Department.objects.filter(id__in=department_ids))
    return serialize_mosaic(mosaic)


def get_mosaic_for(user, mosaic_id: int) -> VideoMosaic:
    try:
        mosaic = VideoMosaic.objects.get(pk=mosaic_id)
    except VideoMosaic.DoesNotExist as exc:
        raise VideoNotFound("Mosaico não encontrado") from exc
    if not user.is_superuser:
        user_depts = user.profile.departments.all()
        has_access = (
            not mosaic.departments.exists()
            or mosaic.departments.filter(id__in=[d.id for d in user_depts]).exists()
        )
        if not has_access:
            raise VideoForbidden("Sem permissão para acessar este mosaico.")
    return mosaic


def update_mosaic(user, mosaic: VideoMosaic, data: dict[str, Any]) -> dict[str, Any]:
    if "name" in data:
        name = str(data["name"]).strip()
        if not name:
            raise VideoError("Nome do mosaico não pode ser vazio")
        mosaic.name = name
    if "layout" in data:
        mosaic.layout = data["layout"]
    if "cameras" in data:
        mosaic.cameras = data["cameras"]
    if "site_id" in data:
        raw_site_id = data["site_id"]
        mosaic.site_id = raw_site_id if isinstance(raw_site_id, int) else None
    if "department_ids" in data:
        department_ids = data["department_ids"]
        _check_department_assignment(
            user, department_ids, "Você só pode atribuir departamentos aos quais pertence."
        )
        mosaic.departments.set(Department.objects.filter(id__in=department_ids))
    mosaic.save()
    return serialize_mosaic(mosaic)


def delete_mosaic(mosaic: VideoMosaic) -> str:
    name = mosaic.name
    mosaic.delete()
    return name


# ── Definições de câmeras (.env) ─────────────────────────────────────────────

CAMERA_DEFAULTS: dict[str, Any] = {
    "default_stream_type": "rtmp",
    "default_resolution": "1080p",
    "default_fps": 30,
    "default_codec": "h264",
    "enable_hardware_acceleration": True,
    "max_concurrent_streams": 10,
    "stream_timeout_seconds": 30,
    "reconnect_attempts": 3,
    "reconnect_delay_ms": 2000,
}

CAMERA_KEY_MAP = {
    "CAMERA_DEFAULT_STREAM_TYPE": "default_stream_type",
    "CAMERA_DEFAULT_RESOLUTION": "default_resolution",
    "CAMERA_DEFAULT_FPS": "default_fps",
    "CAMERA_DEFAULT_CODEC": "default_codec",
    "CAMERA_ENABLE_HARDWARE_ACCELERATION": "enable_hardware_acceleration",
    "CAMERA_MAX_CONCURRENT_STREAMS": "max_concurrent_streams",
    "CAMERA_STREAM_TIMEOUT_SECONDS": "stream_timeout_seconds",
    "CAMERA_RECONNECT_ATTEMPTS": "reconnect_attempts",
    "CAMERA_RECONNECT_DELAY_MS": "reconnect_delay_ms",
}
CAMERA_KEYS = list(CAMERA_KEY_MAP)


def get_camera_settings() -> dict[str, Any]:
    """Defaults sobrepostos pelo .env, com o tipo do default (bool/int/str)."""
    raw = env_manager.read_values(CAMERA_KEYS)
    result = dict(CAMERA_DEFAULTS)
    for env_key, setting_key in CAMERA_KEY_MAP.items():
        val = raw.get(env_key)
        if val in (None, ""):
            continue
        default = CAMERA_DEFAULTS.get(setting_key)
        if isinstance(default, bool):
            result[setting_key] = str(val).lower() in ("true", "1", "yes")
        elif isinstance(default, int):
            try:
                result[setting_key] = int(val)
            except (TypeError, ValueError):
                pass
        else:
            result[setting_key] = val
    return result


def save_camera_settings(body: dict[str, Any]) -> dict[str, str]:
    """Escreve no .env só as chaves presentes; devolve o que foi escrito."""
    to_write: dict[str, str] = {}
    for env_key, setting_key in CAMERA_KEY_MAP.items():
        if setting_key in body:
            val = body[setting_key]
            default = CAMERA_DEFAULTS.get(setting_key)
            to_write[env_key] = (
                ("true" if val else "false") if isinstance(default, bool) else str(val)
            )
    if to_write:
        env_manager.write_values(to_write)
    return to_write


# ── Teste de stream ──────────────────────────────────────────────────────────


def test_stream_reachability(stream_url: str, timeout: int = 5) -> dict[str, Any]:
    """Abre um TCP a `host:porta` da URL (porta por omissão pelo esquema). Falhas de rede
    são resultado (`success: False`), não exceção; URL vazia ou sem host é `VideoError`."""
    stream_url = (stream_url or "").strip()
    if not stream_url:
        raise VideoError("stream_url é obrigatório.")
    parsed = urlparse(stream_url)
    host = parsed.hostname
    if not host:
        raise VideoError("URL inválida: host não encontrado.")
    port = parsed.port or DEFAULT_STREAM_PORTS.get(parsed.scheme.lower(), 554)
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
    except TimeoutError:
        return {"success": False, "message": "Timeout ao conectar com o servidor de stream."}
    except OSError as exc:
        return {"success": False, "message": f"Falha na conexão: {exc}"}
    return {"success": True, "message": f"Conexão bem-sucedida com {host}:{port}."}
