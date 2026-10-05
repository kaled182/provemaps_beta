"""Gateways de mensagens (SMS, SMTP, WhatsApp, Telegram) e câmeras: regras sem HttpRequest.

Saiu de `setup_app/api_views.py` em EV-0017c. Cobre: serialização, criação dos gateways
por omissão a partir do `.env`, espelho do gateway ativo no `.env` (`sync_gateway_env`),
CRUD com RBAC por departamento para câmeras e o fluxo de QR Code do WhatsApp (serviço
externo `services/whatsapp-qr`). As views em `setup_app/api/gateways.py` só traduzem
exceções em códigos HTTP.
"""

from __future__ import annotations

from typing import Any

import requests
from django.db.models import Q

from ..models import MessagingGateway
from ..services import runtime_settings, video_gateway as video_gateway_service
from ..services.config_loader import clear_runtime_config_cache
from ..utils import env_manager

GATEWAY_TYPES = {"sms", "whatsapp", "telegram", "smtp", "video"}
NON_VIDEO_TYPES = ["sms", "whatsapp", "telegram", "smtp"]
ENV_SYNCED_TYPES = {"sms", "smtp"}

# Chaves de `config` que, vazias no PATCH, significam «manter» (o ecrã nunca devolve segredos).
SENSITIVE_CONFIG_KEYS = {
    "password",
    "api_token",
    "access_token",
    "bot_token",
    "aws_secret_access_key",
    "oauth_client_secret",
    "oauth_refresh_token",
}
# Mudar uma destas numa câmera obriga a parar o stream antes de gravar.
VIDEO_STREAM_KEYS = {"stream_url", "stream_type", "restream_key"}

QR_START_TIMEOUT = 15
QR_STATUS_TIMEOUT = 10
QR_TEST_TIMEOUT = 20


class GatewayError(ValueError):
    status = 400


class GatewayNotFound(GatewayError):
    status = 404


class GatewayForbidden(GatewayError):
    status = 403


class QrServiceError(GatewayError):
    """O serviço de QR Code falhou ou recusou; a mensagem já traz o prefixo da operação."""


# ── Serialização e RBAC ──────────────────────────────────────────────────────


def serialize_gateway(gateway: MessagingGateway) -> dict[str, Any]:
    serialized: dict[str, Any] = {
        "id": gateway.id,
        "name": gateway.name,
        "gateway_type": gateway.gateway_type,
        "provider": gateway.provider or "",
        "priority": gateway.priority,
        "enabled": gateway.enabled,
        "is_active": gateway.enabled,  # alias que o frontend ainda lê
        "site_name": gateway.site_name or "",
        "config": gateway.config or {},
        "created_at": gateway.created_at.isoformat(),
        "updated_at": gateway.updated_at.isoformat(),
    }
    if gateway.gateway_type == "video":
        try:
            playback_url = video_gateway_service.build_playback_url(gateway)
            if playback_url:
                serialized["playback_url"] = playback_url
        except Exception:
            pass  # sem URL de reprodução o campo simplesmente não aparece
    return serialized


def user_can_access_video_gateway(user, gateway: MessagingGateway) -> bool:
    """Superuser vê tudo; câmera sem departamentos é pública; senão, interseção de departamentos."""
    if user.is_superuser:
        return True
    if not gateway.departments.exists():
        return True
    profile = getattr(user, "profile", None)
    if not profile:
        return False
    user_department_ids = list(profile.departments.values_list("id", flat=True))
    if not user_department_ids:
        return False
    return gateway.departments.filter(id__in=user_department_ids).exists()


# ── Defaults e espelho no .env ───────────────────────────────────────────────


def ensure_default_gateways() -> None:
    """Cria um gateway SMS/SMTP a partir do `.env` quando ainda não existe nenhum do tipo."""
    runtime_config = runtime_settings.get_runtime_config()

    if not MessagingGateway.objects.filter(gateway_type="sms").exists():
        sms_filled = any(
            [
                runtime_config.sms_provider,
                runtime_config.sms_username,
                runtime_config.sms_api_url,
                runtime_config.sms_sender_id,
                runtime_config.sms_enabled,
            ]
        )
        if sms_filled:
            MessagingGateway.objects.create(
                name=(runtime_config.sms_provider or "SMSNET").upper(),
                gateway_type="sms",
                provider=runtime_config.sms_provider or "smsnet",
                priority=int(runtime_config.sms_provider_rank or 1),
                enabled=bool(runtime_config.sms_enabled),
                config={
                    "username": runtime_config.sms_username or "",
                    "password": runtime_config.sms_password or "",
                    "api_token": runtime_config.sms_api_token or "",
                    "api_url": runtime_config.sms_api_url or "",
                    "sender_id": runtime_config.sms_sender_id or "",
                    "test_recipient": runtime_config.sms_test_recipient or "",
                    "test_message": runtime_config.sms_test_message or "",
                    "aws_region": runtime_config.sms_aws_region or "",
                    "aws_access_key_id": runtime_config.sms_aws_access_key_id or "",
                    "aws_secret_access_key": runtime_config.sms_aws_secret_access_key or "",
                    "infobip_base_url": runtime_config.sms_infobip_base_url or "",
                },
            )

    if not MessagingGateway.objects.filter(gateway_type="smtp").exists():
        smtp_filled = any(
            [
                runtime_config.smtp_host,
                runtime_config.smtp_user,
                runtime_config.smtp_from_email,
                runtime_config.smtp_enabled,
            ]
        )
        if smtp_filled:
            MessagingGateway.objects.create(
                name="SMTP Principal",
                gateway_type="smtp",
                provider="smtp",
                priority=1,
                enabled=bool(runtime_config.smtp_enabled),
                config={
                    "host": runtime_config.smtp_host or "",
                    "port": runtime_config.smtp_port or "",
                    "security": runtime_config.smtp_security or "",
                    "user": runtime_config.smtp_user or "",
                    "password": runtime_config.smtp_password or "",
                    "auth_mode": runtime_config.smtp_auth_mode or "password",
                    "from_name": runtime_config.smtp_from_name or "",
                    "from_email": runtime_config.smtp_from_email or "",
                    "test_recipient": runtime_config.smtp_test_recipient or "",
                    "oauth_client_id": runtime_config.smtp_oauth_client_id or "",
                    "oauth_client_secret": runtime_config.smtp_oauth_client_secret or "",
                    "oauth_refresh_token": runtime_config.smtp_oauth_refresh_token or "",
                },
            )


def _sms_env_payload(active: MessagingGateway) -> dict[str, str]:
    config = active.config or {}
    return {
        "SMS_ENABLED": "True" if active.enabled else "False",
        "SMS_PROVIDER": active.provider or "smsnet",
        "SMS_PROVIDER_RANK": str(active.priority or 1),
        "SMS_USERNAME": config.get("username", ""),
        "SMS_PASSWORD": config.get("password", ""),
        "SMS_API_TOKEN": config.get("api_token", ""),
        "SMS_API_URL": config.get("api_url", ""),
        "SMS_SENDER_ID": config.get("sender_id", ""),
        "SMS_TEST_RECIPIENT": config.get("test_recipient", ""),
        "SMS_TEST_MESSAGE": config.get("test_message", ""),
        "SMS_PRIORITY": config.get("priority", ""),
        "SMS_AWS_REGION": config.get("aws_region", ""),
        "SMS_AWS_ACCESS_KEY_ID": config.get("aws_access_key_id", ""),
        "SMS_AWS_SECRET_ACCESS_KEY": config.get("aws_secret_access_key", ""),
        "SMS_INFOBIP_BASE_URL": config.get("infobip_base_url", ""),
    }


def _smtp_env_payload(active: MessagingGateway) -> dict[str, str]:
    config = active.config or {}
    security = (config.get("security") or "tls").lower()
    from_email = config.get("from_email") or config.get("user") or ""
    return {
        "SMTP_ENABLED": "True" if active.enabled else "False",
        "SMTP_HOST": config.get("host", ""),
        "SMTP_PORT": str(config.get("port", "")),
        "SMTP_SECURITY": security,
        "SMTP_USER": config.get("user", ""),
        "SMTP_PASSWORD": config.get("password", ""),
        "SMTP_AUTH_MODE": config.get("auth_mode", "password"),
        "SMTP_OAUTH_CLIENT_ID": config.get("oauth_client_id", ""),
        "SMTP_OAUTH_CLIENT_SECRET": config.get("oauth_client_secret", ""),
        "SMTP_OAUTH_REFRESH_TOKEN": config.get("oauth_refresh_token", ""),
        "SMTP_FROM_NAME": config.get("from_name", ""),
        "SMTP_FROM_EMAIL": config.get("from_email", ""),
        "SMTP_TEST_RECIPIENT": config.get("test_recipient", ""),
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "EMAIL_HOST": config.get("host", ""),
        "EMAIL_PORT": str(config.get("port", "")),
        "EMAIL_HOST_USER": config.get("user", ""),
        "EMAIL_HOST_PASSWORD": config.get("password", ""),
        "EMAIL_USE_TLS": "True" if security == "tls" else "False",
        "EMAIL_USE_SSL": "True" if security == "ssl" else "False",
        "DEFAULT_FROM_EMAIL": from_email,
        "SERVER_EMAIL": from_email,
    }


def _write_env(payload: dict[str, str]) -> None:
    env_manager.write_values(payload)
    clear_runtime_config_cache()
    runtime_settings.reload_config()


def sync_gateway_env(gateway_type: str) -> None:
    """Espelha no `.env` o gateway SMS/SMTP ativo de maior prioridade (ou desliga o tipo)."""
    if gateway_type not in ENV_SYNCED_TYPES:
        return
    active = (
        MessagingGateway.objects.filter(gateway_type=gateway_type, enabled=True)
        .order_by("priority", "id")
        .first()
    )
    if not active:
        if MessagingGateway.objects.filter(gateway_type=gateway_type).exists():
            flag = "SMS_ENABLED" if gateway_type == "sms" else "SMTP_ENABLED"
            _write_env({flag: "False"})
        return
    _write_env(_sms_env_payload(active) if gateway_type == "sms" else _smtp_env_payload(active))


# ── CRUD ─────────────────────────────────────────────────────────────────────


def list_gateways_for(user) -> list[dict[str, Any]]:
    """Todos para superuser; para os outros, os não-vídeo e as câmeras dos seus departamentos ou públicas."""
    ensure_default_gateways()
    if user.is_superuser:
        gateways = MessagingGateway.objects.all().order_by("gateway_type", "priority", "name")
    else:
        user_depts = user.profile.departments.all()
        gateways = (
            MessagingGateway.objects.filter(
                Q(gateway_type__in=NON_VIDEO_TYPES)
                | Q(gateway_type="video", departments__in=user_depts)
                | Q(gateway_type="video", departments__isnull=True)
            )
            .distinct()
            .order_by("gateway_type", "priority", "name")
        )
    return [serialize_gateway(gw) for gw in gateways]


def _parse_priority(raw: Any, default: int) -> int:
    try:
        priority = int(raw)
    except (TypeError, ValueError):
        priority = default
    return max(priority, 1)


def create_gateway(data: dict[str, Any]) -> dict[str, Any]:
    gateway_type = str(data.get("gateway_type", "")).strip()
    if gateway_type not in GATEWAY_TYPES:
        raise GatewayError("Tipo de gateway inválido.")
    name = str(data.get("name", "")).strip()
    if not name:
        raise GatewayError("Nome do gateway é obrigatório.")

    config = data.get("config", {}) if isinstance(data.get("config"), dict) else {}
    gateway = MessagingGateway.objects.create(
        name=name,
        gateway_type=gateway_type,
        provider=str(data.get("provider", "")).strip() or None,
        priority=_parse_priority(data.get("priority", 1), 1),
        enabled=bool(data.get("enabled", True)),
        site_name=str(data.get("site_name", "")).strip() or None,
        config=config,
    )
    sync_gateway_env(gateway.gateway_type)
    return serialize_gateway(gateway)


def get_gateway_for(user, gateway_id: int) -> MessagingGateway:
    """Gateway pelo id; câmeras exigem acesso por departamento (superuser passa sempre)."""
    try:
        gateway = MessagingGateway.objects.get(id=gateway_id)
    except MessagingGateway.DoesNotExist as exc:
        raise GatewayNotFound("Gateway não encontrado.") from exc
    if gateway.gateway_type == "video" and not user.is_superuser:
        user_depts = user.profile.departments.all()
        has_access = (
            not gateway.departments.exists()
            or gateway.departments.filter(id__in=[d.id for d in user_depts]).exists()
        )
        if not has_access:
            raise GatewayForbidden("Sem permissão para acessar esta câmera.")
    return gateway


def delete_gateway(gateway: MessagingGateway) -> None:
    gateway_type = gateway.gateway_type
    if gateway_type == "video":
        video_gateway_service.stop_stream_for_gateway(gateway, clear_preview=True)
    gateway.delete()
    sync_gateway_env(gateway_type)


def update_gateway(gateway: MessagingGateway, data: dict[str, Any]) -> dict[str, Any]:
    """Atualização parcial; segredos vazios mantêm-se; câmera que muda de stream pára antes de gravar."""
    original_enabled = gateway.enabled

    if "name" in data:
        gateway.name = str(data.get("name", "")).strip() or gateway.name
    if "provider" in data:
        gateway.provider = str(data.get("provider", "")).strip() or gateway.provider
    if "site_name" in data:
        gateway.site_name = str(data.get("site_name", "")).strip() or None
    if "priority" in data:
        gateway.priority = _parse_priority(data.get("priority", gateway.priority), gateway.priority)

    stop_before_save = False
    config_updated = False
    updated_config = dict(gateway.config or {})

    if "enabled" in data:
        new_enabled = bool(data.get("enabled"))
        gateway.enabled = new_enabled
        if original_enabled and not new_enabled and gateway.gateway_type == "video":
            stop_before_save = True

    if "config" in data and isinstance(data.get("config"), dict):
        for key, value in data["config"].items():
            if key in SENSITIVE_CONFIG_KEYS and value == "":
                continue
            if (
                gateway.gateway_type == "video"
                and key in VIDEO_STREAM_KEYS
                and updated_config.get(key) != value
            ):
                stop_before_save = True
            updated_config[key] = value
            config_updated = True

    if gateway.gateway_type == "video" and stop_before_save:
        updated_config.pop("preview_url", None)
        video_gateway_service.stop_stream_for_gateway(gateway)

    if config_updated:
        gateway.config = updated_config

    gateway.save()
    sync_gateway_env(gateway.gateway_type)
    return serialize_gateway(gateway)


# ── WhatsApp por QR Code ─────────────────────────────────────────────────────


def get_whatsapp_qr_service_url(gateway: MessagingGateway) -> str:
    config = gateway.config or {}
    service_url = (config.get("qr_service_url") or "").strip()
    if service_url:
        return service_url
    values = env_manager.read_values(["WHATSAPP_QR_SERVICE_URL"])
    return values.get("WHATSAPP_QR_SERVICE_URL", "").strip()


def update_gateway_qr_state(
    gateway: MessagingGateway, status: str, qr_image_url: str | None
) -> None:
    merged = dict(gateway.config or {})
    if status:
        merged["qr_status"] = status
    if qr_image_url is not None:
        merged["qr_image_url"] = qr_image_url
    gateway.config = merged
    gateway.save(update_fields=["config", "updated_at"])


def get_qr_gateway(gateway_id: int) -> MessagingGateway:
    """Gateway WhatsApp em modo QR; 404 se não existir, 400 se estiver noutro modo."""
    try:
        gateway = MessagingGateway.objects.get(id=gateway_id, gateway_type="whatsapp")
    except MessagingGateway.DoesNotExist as exc:
        raise GatewayNotFound("Gateway WhatsApp não encontrado.") from exc
    if (gateway.config or {}).get("auth_mode") != "qr":
        raise GatewayError("Gateway não está em modo QR Code.")
    return gateway


def _resolve_qr_service_url(
    gateway: MessagingGateway, override: str = "", *, require_default: bool = True
) -> str:
    """URL do serviço: a do pedido vence, mas (salvo `require_default=False`) a configurada
    tem de existir — as rotas de QR legadas recusavam antes de olhar para o override."""
    default = get_whatsapp_qr_service_url(gateway)
    if require_default and not default:
        raise GatewayError("Serviço de QR Code não configurado.")
    service_url = (override or "").strip() or default
    if not service_url:
        raise GatewayError("Serviço de QR Code não configurado.")
    return service_url.rstrip("/")


def _call_qr_service(
    method: str, url: str, *, fail_prefix: str, timeout: int, **kwargs
) -> dict[str, Any]:
    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}
    except Exception as exc:
        raise QrServiceError(f"{fail_prefix}: {exc}") from exc


def _qr_image(data: dict[str, Any]) -> str | None:
    qr_image_url = data.get("qr_image_url")
    if qr_image_url is None:
        qr_image_url = data.get("qr")
    return qr_image_url


def qr_start(gateway: MessagingGateway, override_url: str = "") -> dict[str, Any]:
    service_url = _resolve_qr_service_url(gateway, override_url)
    data = _call_qr_service(
        "POST",
        f"{service_url}/qr/start",
        fail_prefix="Falha ao gerar QR",
        timeout=QR_START_TIMEOUT,
        json={"gateway_id": gateway.id, "name": gateway.name},
    )
    qr_image_url = _qr_image(data)
    status = data.get("status") or data.get("qr_status") or "pending"
    update_gateway_qr_state(gateway, status, qr_image_url)
    return {
        "qr_image_url": qr_image_url,
        "qr_status": status,
        "last_disconnect_reason": data.get("last_disconnect_reason"),
        "last_disconnect_message": data.get("last_disconnect_message", ""),
        "message": data.get("message", "QR gerado."),
    }


def qr_status(gateway: MessagingGateway, override_url: str = "") -> dict[str, Any]:
    service_url = _resolve_qr_service_url(gateway, override_url)
    data = _call_qr_service(
        "GET",
        f"{service_url}/qr/status",
        fail_prefix="Falha ao consultar status",
        timeout=QR_STATUS_TIMEOUT,
        params={"gateway_id": gateway.id},
    )
    qr_image_url = _qr_image(data)
    status = data.get("status") or data.get("qr_status") or "pending"
    if status in {"connected", "disconnected"} and not qr_image_url:
        qr_image_url = ""
    update_gateway_qr_state(gateway, status, qr_image_url)
    return {
        "qr_image_url": qr_image_url,
        "qr_status": status,
        "last_disconnect_reason": data.get("last_disconnect_reason"),
        "last_disconnect_message": data.get("last_disconnect_message", ""),
        "message": data.get("message", "Status atualizado."),
    }


def qr_disconnect(gateway: MessagingGateway, override_url: str = "") -> dict[str, Any]:
    service_url = _resolve_qr_service_url(gateway, override_url)
    data = _call_qr_service(
        "POST",
        f"{service_url}/qr/disconnect",
        fail_prefix="Falha ao desconectar",
        timeout=QR_START_TIMEOUT,
        json={"gateway_id": gateway.id},
    )
    status = data.get("status") or data.get("qr_status") or "disconnected"
    update_gateway_qr_state(gateway, status, "")
    return {
        "qr_status": status,
        "last_disconnect_reason": data.get("last_disconnect_reason"),
        "last_disconnect_message": data.get("last_disconnect_message", ""),
        "message": data.get("message", "Desconectado."),
    }


def qr_reset(gateway: MessagingGateway, override_url: str = "") -> dict[str, Any]:
    service_url = _resolve_qr_service_url(gateway, override_url)
    data = _call_qr_service(
        "POST",
        f"{service_url}/qr/reset",
        fail_prefix="Falha ao resetar",
        timeout=QR_START_TIMEOUT,
        json={"gateway_id": gateway.id},
    )
    update_gateway_qr_state(gateway, "pending", "")
    return {"qr_status": "pending", "message": data.get("message", "Sessão resetada.")}


def qr_test_message(
    gateway: MessagingGateway, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload = payload or {}
    config = gateway.config or {}
    recipient = (payload.get("recipient") or config.get("test_recipient") or "").strip()
    message = (payload.get("message") or config.get("test_message") or "").strip()
    if not message:
        message = "Teste WhatsApp ProveMaps."
    if not recipient:
        raise GatewayError("Informe o telefone de teste.")

    service_url = _resolve_qr_service_url(
        gateway, payload.get("qr_service_url") or "", require_default=False
    )
    data = _call_qr_service(
        "POST",
        f"{service_url}/message/test",
        fail_prefix="Falha ao enviar teste",
        timeout=QR_TEST_TIMEOUT,
        json={"gateway_id": gateway.id, "recipient": recipient, "message": message},
    )
    return {
        "message": data.get("message", "Mensagem enviada."),
        "status": data.get("status"),
        "recipient": data.get("recipient", recipient),
    }
