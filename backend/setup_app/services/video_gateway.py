from __future__ import annotations

import logging
import os
import time
from typing import Dict, Optional

import requests
from django.conf import settings
from django.utils import timezone

from setup_app.models import MessagingGateway

logger = logging.getLogger(__name__)


class VideoGatewayError(Exception):

	"""Erro generico ao orquestrar streams de video."""


class PreviewStartTimeout(VideoGatewayError):

	"""Manifesto HLS nao ficou pronto dentro do tempo esperado."""


def _get_transmuxer_url() -> str:
	value = getattr(settings, "VIDEO_TRANSMUXER_URL", None) or os.environ.get(
		"VIDEO_TRANSMUXER_URL", "http://video-transmuxer:9000"
	)
	return value.rstrip("/")


def _get_hls_probe_base_url() -> str:
	value = getattr(settings, "VIDEO_HLS_BASE_URL", None) or os.environ.get(
		"VIDEO_HLS_BASE_URL", "http://video-hls:8080/hls"
	)
	return value.rstrip("/")


def _get_hls_public_base_url(config: Optional[Dict[str, object]] = None) -> str:
	if config:
		override = (config.get("hls_public_base_url") or "").strip()
		if override:
			return override.rstrip("/")
	value = getattr(settings, "VIDEO_HLS_PUBLIC_BASE_URL", None) or os.environ.get(
		"VIDEO_HLS_PUBLIC_BASE_URL"
	)
	if value:
		return value.rstrip("/")
	return _get_hls_probe_base_url()


def build_playback_url(gateway: MessagingGateway) -> str:
	"""Resolve the best playback URL for the gateway preview.

	Se o preview atual já for HLS, retorna-o. Caso contrário, tenta construir
	um manifesto HLS público usando a base configurada e a stream key.
	"""
	config = gateway.config or {}
	stored = str(config.get("preview_playback_url") or "").strip()
	if stored:
		return stored
	preview_url = str(config.get("preview_url") or "").strip()
	if preview_url.lower().endswith(".m3u8"):
		return preview_url
	stream_url = str(config.get("stream_url") or "").strip()
	if stream_url.lower().startswith("http"):
		# Streams HTTP diretos não passam pelo transmuxer; usar URL original.
		return preview_url or stream_url
	stream_key = _get_stream_key(gateway)
	if not stream_key:
		return preview_url
	public_base = _get_hls_public_base_url(config)
	if public_base:
		return f"{public_base}/{stream_key}.m3u8"
	return preview_url

def _get_webrtc_public_base_url(config: Optional[Dict[str, object]] = None) -> Optional[str]:
	if config:
		override = (config.get("webrtc_public_base_url") or "").strip()
		if override:
			return override.rstrip("/")
	value = getattr(settings, "VIDEO_WEBRTC_PUBLIC_BASE_URL", None) or os.environ.get(
		"VIDEO_WEBRTC_PUBLIC_BASE_URL"
	)
	if value:
		return str(value).rstrip("/")
	return None

def _get_stream_key(gateway: MessagingGateway) -> str:
	config = gateway.config or {}
	key = config.get("restream_key") or f"gateway_{gateway.id}"
	return key


def _persist_config(
	gateway: MessagingGateway, updates: Dict[str, object]
) -> Dict[str, object]:
	config = dict(gateway.config or {})
	changed = False
	for key, value in updates.items():
		if value in {None, ""}:
			if key in config:
				config.pop(key)
				changed = True
		elif config.get(key) != value:
			config[key] = value
			changed = True
	if changed:
		gateway.config = config
		gateway.updated_at = timezone.now()
		gateway.save(update_fields=["config", "updated_at"])
	return config


def stop_stream_for_gateway(
	gateway: MessagingGateway, *, clear_preview: bool = False
) -> None:
	stream_key = _get_stream_key(gateway)
	try:
		response = requests.delete(
			f"{_get_transmuxer_url()}/streams/{stream_key}", timeout=5
		)
		if response.status_code not in {200, 404}:
			logger.warning(
				"Falha ao encerrar stream %s: %s", stream_key, response.text
			)
	except Exception as exc:
		logger.debug("Erro ao encerrar stream %s: %s", stream_key, exc)
	updates: Dict[str, object] = {"preview_active": False}
	if clear_preview:
		updates["preview_url"] = None
		updates["preview_playback_url"] = None
	_persist_config(gateway, updates)


def _wait_for_manifest(stream_key: str, *, timeout: float = 30.0, interval: float = 0.6) -> None:
	manifest_url = f"{_get_hls_probe_base_url()}/{stream_key}.m3u8"
	deadline = time.monotonic() + timeout
	last_error = ""
	while time.monotonic() < deadline:
		try:
			response = requests.get(manifest_url, timeout=2)
			success = (
				response.status_code == 200
				and "#EXTM3U" in response.text
				and "#EXTINF" in response.text
			)
			if success:
				return
			last_error = f"status={response.status_code}"
		except requests.RequestException as exc:
			last_error = str(exc)
		time.sleep(interval)
	raise PreviewStartTimeout(
		f"Manifesto HLS indisponivel apos {timeout:.0f}s ({last_error or 'sem resposta'})"
	)


def ensure_stream_for_gateway(
	gateway: MessagingGateway,
	*,
	wait_ready: bool = True,
	startup_timeout: float = 30.0,
) -> None:
	config = gateway.config or {}
	stream_url = (config.get("stream_url") or "").strip()
	stream_type = (config.get("stream_type") or "rtmp").lower()

	if not stream_url:
		stop_stream_for_gateway(gateway)
		return

	if stream_url.lower().startswith("http"):
		stop_stream_for_gateway(gateway, clear_preview=False)
		_persist_config(
			gateway,
			{
				"preview_url": stream_url,
				"preview_playback_url": stream_url,
				"preview_active": True,
			},
		)
		return

	stream_key = _get_stream_key(gateway)
	public_base = _get_hls_public_base_url(config)
	webrtc_base = _get_webrtc_public_base_url(config)
	use_webrtc = bool(webrtc_base)
	if use_webrtc:
		# MediaMTX WebRTC player page (barra final obrigatória)
		preview_url = f"{webrtc_base}/{stream_key}/"
	else:
		preview_url = f"{public_base}/{stream_key}.m3u8"
	hls_candidate: Optional[str] = None
	if not use_webrtc:
		hls_candidate = preview_url
	elif public_base:
		hls_candidate = f"{public_base}/{stream_key}.m3u8"
	playback_url = hls_candidate or preview_url

	# Verificar se stream já está ativo
	stream_active = False
	try:
		response = requests.get(
			f"{_get_transmuxer_url()}/streams/{stream_key}",
			timeout=3,
		)
		if response.status_code == 200:
			data = response.json()
			stream_active = data.get("running", False)
	except Exception:
		stream_active = False

	should_wait_hls = bool(hls_candidate)
	manifest_timeout = startup_timeout
	if use_webrtc and should_wait_hls:
		manifest_timeout = min(startup_timeout, 6.0)
	if stream_active:
		logger.debug("Stream %s já está ativo, reutilizando.", stream_key)
		# Garantir que preview_url e restream_key estão salvos
		if (
			config.get("preview_url") != preview_url
			or config.get("restream_key") != stream_key
			or config.get("preview_active") is not True
			or config.get("preview_playback_url") != playback_url
		):
			config = _persist_config(
				gateway,
				{
					"preview_url": preview_url,
					"preview_playback_url": playback_url,
					"restream_key": stream_key,
					"preview_active": True,
				},
			)
		hls_ready = True
		# Validar manifesto mesmo se stream já estiver ativo
		if wait_ready and should_wait_hls:
			try:
				_wait_for_manifest(stream_key, timeout=manifest_timeout)
			except PreviewStartTimeout as exc:
				if use_webrtc:
					logger.warning(
						"Stream %s ativo sem manifesto HLS. Mantendo preview via WebRTC: %s",
						stream_key,
						exc,
					)
					hls_ready = False
				else:
					logger.warning(
						"Stream %s ativo mas sem manifesto HLS, recriando.",
						stream_key,
					)
					stop_stream_for_gateway(gateway, clear_preview=False)
					stream_active = False
		if not hls_ready:
			playback_url = preview_url
			should_wait_hls = False
			config = _persist_config(
				gateway,
				{
					"preview_playback_url": playback_url,
					"preview_active": True,
				},
			)

	if not stream_active:
		_persist_config(gateway, {"restream_key": stream_key})
		payload = {
			"stream_id": stream_key,
			"source_url": stream_url,
			"stream_type": stream_type,
			"target_key": stream_key,
		}
		try:
			response = requests.post(
				f"{_get_transmuxer_url()}/streams",
				json=payload,
				timeout=10,
			)
			response.raise_for_status()
		except requests.RequestException as exc:
			logger.warning(
				"Falha ao iniciar restream para gateway %s (%s): %s",
				gateway.id,
				stream_type,
				exc,
			)
			raise VideoGatewayError("Nao foi possivel iniciar o processo de restream.") from exc

		hls_ready = True
		if wait_ready and should_wait_hls:
			try:
				_wait_for_manifest(stream_key, timeout=manifest_timeout)
			except PreviewStartTimeout as exc:
				if use_webrtc:
					logger.warning(
						"Manifesto HLS indisponivel para stream %s. Recuando para WebRTC: %s",
						stream_key,
						exc,
					)
					hls_ready = False
				else:
					stop_stream_for_gateway(gateway, clear_preview=False)
					raise
		if not hls_ready:
			playback_url = preview_url
			should_wait_hls = False

		config = _persist_config(
			gateway,
			{
				"preview_url": preview_url,
				"preview_playback_url": playback_url,
				"preview_active": True,
			},
		)


def sync_gateway_stream(gateway: MessagingGateway) -> None:
	if gateway.gateway_type != "video":
		return
	if not gateway.enabled:
		stop_stream_for_gateway(gateway)
		return
	ensure_stream_for_gateway(gateway)