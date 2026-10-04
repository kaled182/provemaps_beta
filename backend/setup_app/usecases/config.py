"""Configuração do sistema: ficheiro .env, leitura/gravação da configuração, exportar/importar.

Saiu de `setup_app/api_views.py` em EV-0017b. A configuração viva está na base
(`FirstTimeSetup`, lida por `runtime_settings`); o `.env` é o modelo de arranque
e o sítio onde ficam algumas chaves que o código lê diretamente.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from django.conf import settings
from django.core.management import call_command

from integrations.zabbix.guards import reload_diagnostics_flag_cache

from ..models import FirstTimeSetup
from ..models_audit import ConfigurationAudit
from ..services import runtime_settings
from ..services.config_loader import clear_runtime_config_cache
from ..services.service_reloader import trigger_restart
from ..utils import env_manager
from .backups import MIN_BACKUP_PASSWORD_LEN, upload_backup_if_enabled, upload_backup_via_ftp
from .common import to_bool

ENV_MAX_BYTES = 512_000
REDACTED = "***EXPORTED_BUT_REDACTED***"

# Chaves que o ecrã de configuração lê/escreve (ordem = ordem da resposta)
EDITABLE_KEYS = [
    "SECRET_KEY",
    "DEBUG",
    "ZABBIX_API_URL",
    "ZABBIX_API_USER",
    "ZABBIX_API_PASSWORD",
    "ZABBIX_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "MAP_PROVIDER",
    "MAPBOX_TOKEN",
    # Map configuration - Google Maps
    "MAP_DEFAULT_ZOOM",
    "MAP_DEFAULT_LAT",
    "MAP_DEFAULT_LNG",
    "MAP_TYPE",
    "MAP_STYLES",
    "ENABLE_STREET_VIEW",
    "ENABLE_TRAFFIC",
    # Map configuration - Mapbox
    "MAPBOX_STYLE",
    "MAPBOX_CUSTOM_STYLE",
    "MAPBOX_ENABLE_3D",
    # Map configuration - Esri
    "ESRI_API_KEY",
    "ESRI_BASEMAP",
    # Map configuration - Common
    "MAP_LANGUAGE",
    "MAP_THEME",
    "ENABLE_MAP_CLUSTERING",
    "ENABLE_DRAWING_TOOLS",
    "ENABLE_FULLSCREEN",
    "ALLOWED_HOSTS",
    "CSRF_TRUSTED_ORIGINS",
    "ENABLE_DIAGNOSTIC_ENDPOINTS",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "REDIS_URL",
    "REDIS_PASSWORD",
    "DOMAIN_NAME",
    "CERTBOT_EMAIL",
    "SENTRY_DSN",
    "SERVICE_RESTART_COMMANDS",
    "BACKUP_ZIP_PASSWORD",
    "FTP_ENABLED",
    "FTP_HOST",
    "FTP_PORT",
    "FTP_USER",
    "FTP_PASSWORD",
    "FTP_PATH",
    "GDRIVE_ENABLED",
    "GDRIVE_AUTH_MODE",
    "GDRIVE_CREDENTIALS_JSON",
    "GDRIVE_FOLDER_ID",
    "GDRIVE_SHARED_DRIVE_ID",
    "GDRIVE_OAUTH_CLIENT_ID",
    "GDRIVE_OAUTH_CLIENT_SECRET",
    "GDRIVE_OAUTH_USER_EMAIL",
    "SMTP_ENABLED",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_SECURITY",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_AUTH_MODE",
    "SMTP_OAUTH_CLIENT_ID",
    "SMTP_OAUTH_CLIENT_SECRET",
    "SMTP_OAUTH_REFRESH_TOKEN",
    "SMTP_FROM_NAME",
    "SMTP_FROM_EMAIL",
    "SMTP_TEST_RECIPIENT",
    "SMS_ENABLED",
    "SMS_PROVIDER",
    "SMS_PROVIDER_RANK",
    "SMS_USERNAME",
    "SMS_PASSWORD",
    "SMS_API_TOKEN",
    "SMS_API_URL",
    "SMS_SENDER_ID",
    "SMS_TEST_RECIPIENT",
    "SMS_TEST_MESSAGE",
    "SMS_PRIORITY",
    "SMS_AWS_REGION",
    "SMS_AWS_ACCESS_KEY_ID",
    "SMS_AWS_SECRET_ACCESS_KEY",
    "SMS_INFOBIP_BASE_URL",
    # Network thresholds
    "OPTICAL_RX_WARNING_THRESHOLD",
    "OPTICAL_RX_CRITICAL_THRESHOLD",
    "OPTICAL_THRESHOLDS_BY_DISTANCE",
    # Backup automation
    "BACKUP_AUTO_ENABLED",
    "BACKUP_FREQUENCY",
    "BACKUP_RETENTION_DAYS",
    "BACKUP_CLOUD_UPLOAD",
    "BACKUP_CLOUD_PROVIDER",
    "BACKUP_CLOUD_PATH",
]

# O export antigo não levava estas chaves (origens CSRF, Redis password, domínio,
# Sentry, thresholds, automação de backup). Mantém-se o conjunto para a exportação
# continuar a produzir o mesmo ficheiro.
_EXPORT_EXCLUDED = {
    "CSRF_TRUSTED_ORIGINS",
    "REDIS_PASSWORD",
    "DOMAIN_NAME",
    "CERTBOT_EMAIL",
    "SENTRY_DSN",
    "OPTICAL_RX_WARNING_THRESHOLD",
    "OPTICAL_RX_CRITICAL_THRESHOLD",
    "OPTICAL_THRESHOLDS_BY_DISTANCE",
    "BACKUP_AUTO_ENABLED",
    "BACKUP_FREQUENCY",
    "BACKUP_RETENTION_DAYS",
    "BACKUP_CLOUD_UPLOAD",
    "BACKUP_CLOUD_PROVIDER",
    "BACKUP_CLOUD_PATH",
}

# Chaves cujo valor autoritativo vive na base (`FirstTimeSetup`), não no .env: código
# antigo escrevia defaults no .env e eles ganhavam ao que o utilizador gravou no ecrã.
DB_AUTHORITATIVE_KEYS = frozenset(
    {"MAP_DEFAULT_LAT", "MAP_DEFAULT_LNG", "MAP_DEFAULT_ZOOM", "MAP_PROVIDER", "MAPBOX_TOKEN"}
)

# Limiares ópticos por categoria de distância (km) — tooltip/alarmes dos cabos.
DEFAULT_DISTANCE_THRESHOLDS: dict[str, dict[str, float]] = {
    "10": {"warning": -20.0, "critical": -28.0},
    "40": {"warning": -23.0, "critical": -30.0},
    "80": {"warning": -26.0, "critical": -30.0},
    "100": {"warning": -28.0, "critical": -35.0},
}


def parse_distance_thresholds(value: Any) -> dict[str, dict[str, float]]:
    """Normaliza o dict de limiares por distância; qualquer entrada inválida cai no default."""
    defaults = DEFAULT_DISTANCE_THRESHOLDS
    if not value:
        return dict(defaults)
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return dict(defaults)
    if not isinstance(value, dict):
        return dict(defaults)
    result: dict[str, dict[str, float]] = {}
    for cat, default in defaults.items():
        entry = value.get(cat, default)
        try:
            result[cat] = {
                "warning": float(entry.get("warning", default["warning"])),
                "critical": float(entry.get("critical", default["critical"])),
            }
        except (AttributeError, TypeError, ValueError):
            result[cat] = dict(default)
    return result


EXPORT_KEYS = [k for k in EDITABLE_KEYS if k not in _EXPORT_EXCLUDED] + [
    "GDRIVE_OAUTH_REFRESH_TOKEN"
]

SENSITIVE_KEYS = [
    "SECRET_KEY",
    "ZABBIX_API_PASSWORD",
    "ZABBIX_API_KEY",
    "DB_PASSWORD",
    "BACKUP_ZIP_PASSWORD",
    "FTP_PASSWORD",
    "GDRIVE_CREDENTIALS_JSON",
    "GDRIVE_OAUTH_CLIENT_SECRET",
    "GDRIVE_OAUTH_REFRESH_TOKEN",
    "SMTP_PASSWORD",
    "SMTP_OAUTH_CLIENT_SECRET",
    "SMTP_OAUTH_REFRESH_TOKEN",
    "SMS_PASSWORD",
    "SMS_API_TOKEN",
    "SMS_AWS_SECRET_ACCESS_KEY",
]

BOOL_KEYS = {
    "DEBUG",
    "ENABLE_DIAGNOSTIC_ENDPOINTS",
    "FTP_ENABLED",
    "GDRIVE_ENABLED",
    "SMTP_ENABLED",
    "SMS_ENABLED",
    "BACKUP_AUTO_ENABLED",
    "BACKUP_CLOUD_UPLOAD",
    "ENABLE_STREET_VIEW",
    "ENABLE_TRAFFIC",
    "MAPBOX_ENABLE_3D",
    "ENABLE_MAP_CLUSTERING",
    "ENABLE_DRAWING_TOOLS",
    "ENABLE_FULLSCREEN",
}


class ConfigError(ValueError):
    """Erro de validação da configuração (HTTP 400)."""


class EnvTooLarge(ConfigError):
    pass


class MissingRequiredFields(ConfigError):
    def __init__(self, fields: list[str]):
        self.fields = fields
        super().__init__(f"Missing required fields: {', '.join(fields)}")


# ── Ficheiro .env ────────────────────────────────────────────────────────────


def read_env_file() -> str:
    env_path = env_manager.ENV_PATH
    if not env_path.exists():
        return ""
    content = env_path.read_text(encoding="utf-8")
    if len(content) > ENV_MAX_BYTES:
        raise EnvTooLarge("Env file is too large to edit.")
    return content


def write_env_file(content: Any) -> None:
    """Substitui o .env e recarrega a configuração em memória."""
    if not isinstance(content, str):
        raise ConfigError("Invalid content payload.")
    if len(content) > ENV_MAX_BYTES:
        raise EnvTooLarge("Env content is too large.")
    env_path = env_manager.ENV_PATH
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if content and not content.endswith("\n"):
        content = f"{content}\n"
    env_path.write_text(content, encoding="utf-8")
    _reload_runtime()


def _reload_runtime() -> None:
    clear_runtime_config_cache()
    runtime_settings.reload_config()
    reload_diagnostics_flag_cache()


# ── Configuração ─────────────────────────────────────────────────────────────


def _db_record() -> FirstTimeSetup | None:
    """Registo vivo da configuração, lido direto da base: campos que mudam sem reiniciar não
    podem vir do `lru_cache` de um worker que não processou o POST de gravação."""
    return FirstTimeSetup.objects.filter(configured=True).order_by("-configured_at").first()


def _db_str(record: Any, field: str, default: str) -> str:
    value = getattr(record, field, None) if record is not None else None
    return str(value) if value is not None and value != "" else default


def _fallback_values(current_values: dict[str, str]) -> dict[str, Any]:
    runtime_config = runtime_settings.get_runtime_config()
    record = _db_record()
    return {
        "SECRET_KEY": getattr(settings, "SECRET_KEY", ""),
        "DEBUG": getattr(settings, "DEBUG", False),
        "ZABBIX_API_URL": runtime_config.zabbix_api_url,
        "ZABBIX_API_USER": runtime_config.zabbix_api_user,
        "ZABBIX_API_PASSWORD": runtime_config.zabbix_api_password,
        "ZABBIX_API_KEY": runtime_config.zabbix_api_key,
        "GOOGLE_MAPS_API_KEY": runtime_config.google_maps_api_key,
        "MAP_PROVIDER": _db_str(record, "map_provider", runtime_config.map_provider or "google"),
        "MAPBOX_TOKEN": _db_str(record, "mapbox_token", runtime_config.mapbox_token or ""),
        "MAP_DEFAULT_ZOOM": _db_str(record, "map_default_zoom", "12"),
        "MAP_DEFAULT_LAT": _db_str(record, "map_default_lat", "-15.7801"),
        "MAP_DEFAULT_LNG": _db_str(record, "map_default_lng", "-47.9292"),
        "MAP_TYPE": "terrain",
        "MAP_STYLES": "",
        "ENABLE_STREET_VIEW": True,
        "ENABLE_TRAFFIC": False,
        "MAPBOX_STYLE": "mapbox://styles/mapbox/streets-v12",
        "MAPBOX_CUSTOM_STYLE": "",
        "MAPBOX_ENABLE_3D": False,
        "ESRI_API_KEY": "",
        "ESRI_BASEMAP": "streets",
        "MAP_LANGUAGE": "pt-BR",
        "MAP_THEME": "light",
        "ENABLE_MAP_CLUSTERING": True,
        "ENABLE_DRAWING_TOOLS": True,
        "ENABLE_FULLSCREEN": True,
        "ALLOWED_HOSTS": ",".join(runtime_config.allowed_hosts),
        "CSRF_TRUSTED_ORIGINS": current_values.get("CSRF_TRUSTED_ORIGINS", ""),
        "ENABLE_DIAGNOSTIC_ENDPOINTS": runtime_config.diagnostics_enabled,
        "DB_HOST": runtime_config.db_host,
        "DB_PORT": runtime_config.db_port,
        "DB_NAME": runtime_config.db_name,
        "DB_USER": runtime_config.db_user,
        "DB_PASSWORD": runtime_config.db_password,
        "REDIS_URL": runtime_config.redis_url,
        "SERVICE_RESTART_COMMANDS": getattr(settings, "SERVICE_RESTART_COMMANDS", ""),
        "BACKUP_ZIP_PASSWORD": current_values.get("BACKUP_ZIP_PASSWORD", ""),
        "FTP_ENABLED": runtime_config.ftp_enabled,
        "FTP_HOST": runtime_config.ftp_host,
        "FTP_PORT": runtime_config.ftp_port,
        "FTP_USER": runtime_config.ftp_user,
        "FTP_PASSWORD": runtime_config.ftp_password,
        "FTP_PATH": runtime_config.ftp_path,
        "GDRIVE_ENABLED": runtime_config.gdrive_enabled,
        "GDRIVE_AUTH_MODE": runtime_config.gdrive_auth_mode,
        "GDRIVE_CREDENTIALS_JSON": runtime_config.gdrive_credentials_json,
        "GDRIVE_FOLDER_ID": runtime_config.gdrive_folder_id,
        "GDRIVE_SHARED_DRIVE_ID": runtime_config.gdrive_shared_drive_id,
        "GDRIVE_OAUTH_CLIENT_ID": runtime_config.gdrive_oauth_client_id,
        "GDRIVE_OAUTH_CLIENT_SECRET": runtime_config.gdrive_oauth_client_secret,
        "GDRIVE_OAUTH_USER_EMAIL": runtime_config.gdrive_oauth_user_email,
        "SMTP_ENABLED": runtime_config.smtp_enabled,
        "SMTP_HOST": runtime_config.smtp_host,
        "SMTP_PORT": runtime_config.smtp_port,
        "SMTP_SECURITY": runtime_config.smtp_security,
        "SMTP_USER": runtime_config.smtp_user,
        "SMTP_PASSWORD": runtime_config.smtp_password,
        "SMTP_AUTH_MODE": runtime_config.smtp_auth_mode,
        "SMTP_OAUTH_CLIENT_ID": runtime_config.smtp_oauth_client_id,
        "SMTP_OAUTH_CLIENT_SECRET": runtime_config.smtp_oauth_client_secret,
        "SMTP_OAUTH_REFRESH_TOKEN": runtime_config.smtp_oauth_refresh_token,
        "SMTP_FROM_NAME": runtime_config.smtp_from_name,
        "SMTP_FROM_EMAIL": runtime_config.smtp_from_email,
        "SMTP_TEST_RECIPIENT": runtime_config.smtp_test_recipient,
        "SMS_ENABLED": runtime_config.sms_enabled,
        "SMS_PROVIDER": runtime_config.sms_provider,
        "SMS_PROVIDER_RANK": runtime_config.sms_provider_rank,
        "SMS_USERNAME": runtime_config.sms_username,
        "SMS_PASSWORD": runtime_config.sms_password,
        "SMS_API_TOKEN": runtime_config.sms_api_token,
        "SMS_API_URL": runtime_config.sms_api_url,
        "SMS_SENDER_ID": runtime_config.sms_sender_id,
        "SMS_TEST_RECIPIENT": runtime_config.sms_test_recipient,
        "SMS_TEST_MESSAGE": runtime_config.sms_test_message,
        "SMS_PRIORITY": runtime_config.sms_priority,
        "SMS_AWS_REGION": runtime_config.sms_aws_region,
        "SMS_AWS_ACCESS_KEY_ID": runtime_config.sms_aws_access_key_id,
        "SMS_AWS_SECRET_ACCESS_KEY": runtime_config.sms_aws_secret_access_key,
        "SMS_INFOBIP_BASE_URL": runtime_config.sms_infobip_base_url,
        "OPTICAL_RX_WARNING_THRESHOLD": str(runtime_config.optical_rx_warning_threshold),
        "OPTICAL_RX_CRITICAL_THRESHOLD": str(runtime_config.optical_rx_critical_threshold),
        "OPTICAL_THRESHOLDS_BY_DISTANCE": parse_distance_thresholds(
            runtime_config.optical_thresholds_by_distance
        ),
        "BACKUP_AUTO_ENABLED": False,
        "BACKUP_FREQUENCY": "weekly",
        "BACKUP_RETENTION_DAYS": "30",
        "BACKUP_CLOUD_UPLOAD": False,
        "BACKUP_CLOUD_PROVIDER": "google_drive",
        "BACKUP_CLOUD_PATH": "/backups/provemaps",
    }


def get_configuration() -> dict[str, Any]:
    """Valores atuais do .env, com fallback na configuração da base; booleanos já convertidos."""
    current_values = env_manager.read_values(EDITABLE_KEYS)
    fallback = _fallback_values(current_values)

    config_data: dict[str, Any] = {}
    for key in EDITABLE_KEYS:
        if key in DB_AUTHORITATIVE_KEYS:
            value = fallback.get(key, "")  # a base ganha sempre ao .env
        else:
            value = current_values.get(key, "")
            if value == "":
                value = fallback.get(key, "")
        if key in BOOL_KEYS:
            if isinstance(value, bool):
                config_data[key] = value
            else:
                config_data[key] = str(value).lower() == "true" if value else False
        else:
            config_data[key] = value or ""

    oauth_token = env_manager.read_values(["GDRIVE_OAUTH_REFRESH_TOKEN"]).get(
        "GDRIVE_OAUTH_REFRESH_TOKEN", ""
    )
    config_data["GDRIVE_OAUTH_CONNECTED"] = bool(oauth_token)
    return config_data


def export_configuration(exported_by: str) -> dict[str, Any]:
    """Configuração para ficheiro JSON, com os segredos redigidos."""
    config_data = env_manager.read_values(EXPORT_KEYS)
    for key in SENSITIVE_KEYS:
        if config_data.get(key):
            config_data[key] = REDACTED
    return {
        "version": "1.0",
        "exported_by": exported_by,
        "exported_at": datetime.now().isoformat(),
        "configuration": config_data,
    }


def import_configuration(content: str) -> list[str]:
    """Escreve no .env as chaves de um export (ignora vazias e redigidas); devolve as importadas."""
    import_data = json.loads(content)
    if not isinstance(import_data, dict) or "configuration" not in import_data:
        raise ConfigError("Invalid configuration file format")
    config = import_data["configuration"]
    filtered = {k: v for k, v in config.items() if v and v != REDACTED}
    env_manager.write_values(filtered)
    return list(filtered.keys())


def get_audit_history(limit: int = 50, section: str = "") -> list[dict[str, Any]]:
    queryset = ConfigurationAudit.objects.all()
    if section:
        queryset = queryset.filter(section=section)
    return [
        {
            "id": audit.id,
            "user": audit.user.username if audit.user else "Anonymous",
            "action": audit.get_action_display(),
            "section": audit.section,
            "field_name": audit.field_name,
            "old_value": audit.old_value,
            "new_value": audit.new_value,
            "success": audit.success,
            "error_message": audit.error_message,
            "timestamp": audit.timestamp.isoformat(),
            "ip_address": audit.ip_address,
        }
        for audit in queryset[:limit]
    ]


# ── update_configuration ─────────────────────────────────────────────────────


def _str(data: dict[str, Any], key: str, default: str = "") -> str:
    return str(data.get(key, default) or "").strip()


def _flag(data: dict[str, Any], key: str, default: bool) -> str:
    return "True" if to_bool(data.get(key, default)) else "False"


def _parse_float_str(value: Any, default: float) -> str:
    try:
        return str(float(str(value).strip()))
    except Exception:
        return str(default)


def _clamp_int(raw: str, default: int, low: int, high: int) -> int:
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(low, min(value, high))


def build_configuration_payload(
    data: dict[str, Any], runtime_config, backup_zip_password: str
) -> dict[str, str]:
    """Normaliza o pedido do ecrã para o mapa de chaves do .env/base (strings)."""
    ftp_port_raw = _str(data, "FTP_PORT")
    try:
        ftp_port_value = int(ftp_port_raw) if ftp_port_raw else 21
    except ValueError:
        ftp_port_value = 21

    sms_rank = _clamp_int(_str(data, "SMS_PROVIDER_RANK"), 1, 1, 5)

    # Segredos: o ecrã manda vazio quando não muda → mantém-se o da base
    def _keep(key: str, existing: str) -> str:
        return data.get(key, "") or (existing or "")

    payload = {
        "SECRET_KEY": data.get("SECRET_KEY") or runtime_config.secret_key or "",
        "DEBUG": _flag(data, "DEBUG", False),
        "ZABBIX_API_URL": data.get("ZABBIX_API_URL") or runtime_config.zabbix_api_url or "",
        "ZABBIX_API_USER": data.get("ZABBIX_API_USER") or runtime_config.zabbix_api_user or "",
        "ZABBIX_API_PASSWORD": data.get("ZABBIX_API_PASSWORD")
        or runtime_config.zabbix_api_password
        or "",
        "ZABBIX_API_KEY": _str(data, "ZABBIX_API_KEY"),
        "GOOGLE_MAPS_API_KEY": _str(data, "GOOGLE_MAPS_API_KEY"),
        "MAP_PROVIDER": _str(data, "MAP_PROVIDER", "google") or "google",
        "MAPBOX_TOKEN": _str(data, "MAPBOX_TOKEN"),
        "MAP_DEFAULT_ZOOM": _str(data, "MAP_DEFAULT_ZOOM", "12") or "12",
        "MAP_DEFAULT_LAT": _str(data, "MAP_DEFAULT_LAT", "-15.7801") or "-15.7801",
        "MAP_DEFAULT_LNG": _str(data, "MAP_DEFAULT_LNG", "-47.9292") or "-47.9292",
        "MAP_TYPE": _str(data, "MAP_TYPE", "terrain") or "terrain",
        "MAP_STYLES": _str(data, "MAP_STYLES"),
        "ENABLE_STREET_VIEW": _flag(data, "ENABLE_STREET_VIEW", True),
        "ENABLE_TRAFFIC": _flag(data, "ENABLE_TRAFFIC", False),
        "MAPBOX_STYLE": _str(data, "MAPBOX_STYLE", "mapbox://styles/mapbox/streets-v12")
        or "mapbox://styles/mapbox/streets-v12",
        "MAPBOX_CUSTOM_STYLE": _str(data, "MAPBOX_CUSTOM_STYLE"),
        "MAPBOX_ENABLE_3D": _flag(data, "MAPBOX_ENABLE_3D", False),
        "ESRI_API_KEY": _str(data, "ESRI_API_KEY"),
        "ESRI_BASEMAP": _str(data, "ESRI_BASEMAP", "streets") or "streets",
        "MAP_LANGUAGE": _str(data, "MAP_LANGUAGE", "pt-BR") or "pt-BR",
        "MAP_THEME": _str(data, "MAP_THEME", "light") or "light",
        "ENABLE_MAP_CLUSTERING": _flag(data, "ENABLE_MAP_CLUSTERING", True),
        "ENABLE_DRAWING_TOOLS": _flag(data, "ENABLE_DRAWING_TOOLS", True),
        "ENABLE_FULLSCREEN": _flag(data, "ENABLE_FULLSCREEN", True),
        "ALLOWED_HOSTS": data.get("ALLOWED_HOSTS") or runtime_config.allowed_hosts or "",
        "CSRF_TRUSTED_ORIGINS": _str(data, "CSRF_TRUSTED_ORIGINS"),
        "ENABLE_DIAGNOSTIC_ENDPOINTS": _flag(data, "ENABLE_DIAGNOSTIC_ENDPOINTS", False),
        "DB_HOST": data.get("DB_HOST") or runtime_config.db_host or "",
        "DB_PORT": data.get("DB_PORT") or runtime_config.db_port or "",
        "DB_NAME": data.get("DB_NAME") or runtime_config.db_name or "",
        "DB_USER": data.get("DB_USER") or runtime_config.db_user or "",
        "DB_PASSWORD": data.get("DB_PASSWORD") or runtime_config.db_password or "",
        "REDIS_URL": _str(data, "REDIS_URL"),
        "REDIS_PASSWORD": _str(data, "REDIS_PASSWORD"),
        "DOMAIN_NAME": _str(data, "DOMAIN_NAME"),
        "CERTBOT_EMAIL": _str(data, "CERTBOT_EMAIL"),
        "SENTRY_DSN": _str(data, "SENTRY_DSN"),
        "SERVICE_RESTART_COMMANDS": _str(data, "SERVICE_RESTART_COMMANDS"),
        "BACKUP_ZIP_PASSWORD": backup_zip_password,
        "FTP_ENABLED": _flag(data, "FTP_ENABLED", False),
        "FTP_HOST": _str(data, "FTP_HOST"),
        "FTP_PORT": str(ftp_port_value),
        "FTP_USER": _str(data, "FTP_USER"),
        "FTP_PASSWORD": _str(data, "FTP_PASSWORD"),
        "FTP_PATH": _str(data, "FTP_PATH") or "/backups/",
        "GDRIVE_ENABLED": _flag(data, "GDRIVE_ENABLED", False),
        "GDRIVE_AUTH_MODE": _str(data, "GDRIVE_AUTH_MODE") or "service_account",
        "GDRIVE_CREDENTIALS_JSON": _str(data, "GDRIVE_CREDENTIALS_JSON"),
        "GDRIVE_FOLDER_ID": _str(data, "GDRIVE_FOLDER_ID"),
        "GDRIVE_SHARED_DRIVE_ID": _str(data, "GDRIVE_SHARED_DRIVE_ID"),
        "GDRIVE_OAUTH_CLIENT_ID": _str(data, "GDRIVE_OAUTH_CLIENT_ID")
        or (runtime_config.gdrive_oauth_client_id or ""),
        "GDRIVE_OAUTH_CLIENT_SECRET": _str(data, "GDRIVE_OAUTH_CLIENT_SECRET")
        or (runtime_config.gdrive_oauth_client_secret or ""),
        "GDRIVE_OAUTH_REFRESH_TOKEN": runtime_config.gdrive_oauth_refresh_token or "",
        "GDRIVE_OAUTH_USER_EMAIL": runtime_config.gdrive_oauth_user_email or "",
        "SMTP_ENABLED": _flag(data, "SMTP_ENABLED", False),
        "SMTP_HOST": _str(data, "SMTP_HOST"),
        "SMTP_PORT": _str(data, "SMTP_PORT"),
        "SMTP_SECURITY": _str(data, "SMTP_SECURITY"),
        "SMTP_USER": _str(data, "SMTP_USER"),
        "SMTP_PASSWORD": _keep("SMTP_PASSWORD", runtime_config.smtp_password),
        "SMTP_AUTH_MODE": _str(data, "SMTP_AUTH_MODE")
        or (runtime_config.smtp_auth_mode or "password"),
        "SMTP_OAUTH_CLIENT_ID": _str(data, "SMTP_OAUTH_CLIENT_ID")
        or (runtime_config.smtp_oauth_client_id or ""),
        "SMTP_OAUTH_CLIENT_SECRET": _str(data, "SMTP_OAUTH_CLIENT_SECRET")
        or (runtime_config.smtp_oauth_client_secret or ""),
        "SMTP_OAUTH_REFRESH_TOKEN": _str(data, "SMTP_OAUTH_REFRESH_TOKEN")
        or (runtime_config.smtp_oauth_refresh_token or ""),
        "SMTP_FROM_NAME": _str(data, "SMTP_FROM_NAME"),
        "SMTP_FROM_EMAIL": _str(data, "SMTP_FROM_EMAIL"),
        "SMTP_TEST_RECIPIENT": _str(data, "SMTP_TEST_RECIPIENT"),
        "SMS_ENABLED": _flag(data, "SMS_ENABLED", False),
        "SMS_PROVIDER": _str(data, "SMS_PROVIDER") or "smsnet",
        "SMS_PROVIDER_RANK": str(sms_rank),
        "SMS_USERNAME": _str(data, "SMS_USERNAME"),
        "SMS_PASSWORD": _keep("SMS_PASSWORD", runtime_config.sms_password),
        "SMS_API_TOKEN": _keep("SMS_API_TOKEN", runtime_config.sms_api_token),
        "SMS_API_URL": _str(data, "SMS_API_URL"),
        "SMS_SENDER_ID": _str(data, "SMS_SENDER_ID"),
        "SMS_TEST_RECIPIENT": _str(data, "SMS_TEST_RECIPIENT"),
        "SMS_TEST_MESSAGE": _str(data, "SMS_TEST_MESSAGE"),
        "SMS_PRIORITY": _str(data, "SMS_PRIORITY"),
        "SMS_AWS_REGION": _str(data, "SMS_AWS_REGION"),
        "SMS_AWS_ACCESS_KEY_ID": _str(data, "SMS_AWS_ACCESS_KEY_ID"),
        "SMS_AWS_SECRET_ACCESS_KEY": _keep(
            "SMS_AWS_SECRET_ACCESS_KEY", runtime_config.sms_aws_secret_access_key
        ),
        "SMS_INFOBIP_BASE_URL": _str(data, "SMS_INFOBIP_BASE_URL"),
        "OPTICAL_RX_WARNING_THRESHOLD": _parse_float_str(
            data.get("OPTICAL_RX_WARNING_THRESHOLD", "-24"), -24
        ),
        "OPTICAL_RX_CRITICAL_THRESHOLD": _parse_float_str(
            data.get("OPTICAL_RX_CRITICAL_THRESHOLD", "-27"), -27
        ),
        "OPTICAL_THRESHOLDS_BY_DISTANCE": json.dumps(
            parse_distance_thresholds(data.get("OPTICAL_THRESHOLDS_BY_DISTANCE"))
        ),
    }

    # E-mail: o backend SMTP do Django segue a secção SMTP
    if to_bool(payload["SMTP_ENABLED"]):
        security = (payload["SMTP_SECURITY"] or "").lower()
        from_email = payload["SMTP_FROM_EMAIL"] or payload["SMTP_USER"]
        payload.update(
            {
                "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
                "EMAIL_HOST": payload["SMTP_HOST"],
                "EMAIL_PORT": payload["SMTP_PORT"] or "587",
                "EMAIL_HOST_USER": payload["SMTP_USER"],
                "EMAIL_HOST_PASSWORD": payload["SMTP_PASSWORD"],
                "EMAIL_USE_TLS": "True" if security == "tls" else "False",
                "EMAIL_USE_SSL": "True" if security == "ssl" else "False",
                "DEFAULT_FROM_EMAIL": from_email,
                "SERVER_EMAIL": from_email,
            }
        )
    else:
        payload.update(
            {
                "EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend",
                "EMAIL_HOST": "",
                "EMAIL_PORT": "",
                "EMAIL_HOST_USER": "",
                "EMAIL_HOST_PASSWORD": "",
                "EMAIL_USE_TLS": "False",
                "EMAIL_USE_SSL": "False",
            }
        )
    return payload


def _apply_runtime_overrides(payload: dict[str, str]) -> None:
    """Efeito imediato, sem reiniciar: thresholds, e-mail e comandos de restart."""
    os.environ["OPTICAL_RX_WARNING_THRESHOLD"] = payload["OPTICAL_RX_WARNING_THRESHOLD"]
    os.environ["OPTICAL_RX_CRITICAL_THRESHOLD"] = payload["OPTICAL_RX_CRITICAL_THRESHOLD"]
    os.environ["SERVICE_RESTART_COMMANDS"] = payload["SERVICE_RESTART_COMMANDS"]
    settings.EMAIL_BACKEND = payload.get("EMAIL_BACKEND", settings.EMAIL_BACKEND)
    settings.EMAIL_HOST = payload.get("EMAIL_HOST", settings.EMAIL_HOST)
    settings.EMAIL_PORT = (
        int(payload["EMAIL_PORT"]) if payload.get("EMAIL_PORT") else settings.EMAIL_PORT
    )
    settings.EMAIL_HOST_USER = payload.get("EMAIL_HOST_USER", settings.EMAIL_HOST_USER)
    settings.EMAIL_HOST_PASSWORD = payload.get("EMAIL_HOST_PASSWORD", settings.EMAIL_HOST_PASSWORD)
    settings.EMAIL_USE_TLS = payload.get("EMAIL_USE_TLS", "False").lower() == "true"
    settings.EMAIL_USE_SSL = payload.get("EMAIL_USE_SSL", "False").lower() == "true"
    settings.DEFAULT_FROM_EMAIL = payload.get("DEFAULT_FROM_EMAIL", settings.DEFAULT_FROM_EMAIL)
    settings.SERVER_EMAIL = payload.get("SERVER_EMAIL", settings.SERVER_EMAIL)
    for key, default in (
        ("OPTICAL_RX_WARNING_THRESHOLD", -24.0),
        ("OPTICAL_RX_CRITICAL_THRESHOLD", -27.0),
    ):
        try:
            setattr(settings, key, float(payload[key]))
        except (TypeError, ValueError):
            setattr(settings, key, default)
    distance = parse_distance_thresholds(payload.get("OPTICAL_THRESHOLDS_BY_DISTANCE"))
    os.environ["OPTICAL_THRESHOLDS_BY_DISTANCE"] = json.dumps(distance)
    settings.OPTICAL_THRESHOLDS_BY_DISTANCE = distance


def _purge_stale_env_keys() -> None:
    """Código antigo escrevia no .env defaults das chaves que hoje só a base governa; se lá
    continuarem, um arranque limpo lê-os antes da base. Esvazia-os (uma vez, se existirem)."""
    stale = DB_AUTHORITATIVE_KEYS & env_manager.read_env().keys()
    if stale:
        env_manager.write_values({key: "" for key in stale})


def _persist_configuration(payload: dict[str, str]) -> None:
    """Grava na base (`FirstTimeSetup`); o .env é só modelo e não é escrito aqui."""
    FirstTimeSetup.objects.update_or_create(
        configured=True,
        defaults={
            "company_name": "MapsproveFiber",
            "zabbix_url": payload["ZABBIX_API_URL"],
            "auth_type": "token" if payload["ZABBIX_API_KEY"] else "login",
            "zabbix_api_key": payload["ZABBIX_API_KEY"] or None,
            "zabbix_user": payload["ZABBIX_API_USER"] or None,
            "zabbix_password": payload["ZABBIX_API_PASSWORD"] or None,
            "maps_api_key": payload["GOOGLE_MAPS_API_KEY"],
            "map_provider": payload["MAP_PROVIDER"],
            "mapbox_token": payload["MAPBOX_TOKEN"],
            "map_default_zoom": int(payload.get("MAP_DEFAULT_ZOOM", 12)),
            "map_default_lat": float(payload.get("MAP_DEFAULT_LAT", -15.7801)),
            "map_default_lng": float(payload.get("MAP_DEFAULT_LNG", -47.9292)),
            "map_type": payload.get("MAP_TYPE", "terrain"),
            "map_styles": payload.get("MAP_STYLES", ""),
            "enable_street_view": to_bool(payload.get("ENABLE_STREET_VIEW", True)),
            "enable_traffic": to_bool(payload.get("ENABLE_TRAFFIC", False)),
            "mapbox_style": payload.get("MAPBOX_STYLE", "mapbox://styles/mapbox/streets-v12"),
            "mapbox_custom_style": payload.get("MAPBOX_CUSTOM_STYLE", ""),
            "mapbox_enable_3d": to_bool(payload.get("MAPBOX_ENABLE_3D", False)),
            "esri_api_key": payload.get("ESRI_API_KEY", ""),
            "esri_basemap": payload.get("ESRI_BASEMAP", "streets"),
            "map_language": payload.get("MAP_LANGUAGE", "pt-BR"),
            "map_theme": payload.get("MAP_THEME", "light"),
            "enable_map_clustering": to_bool(payload.get("ENABLE_MAP_CLUSTERING", True)),
            "enable_drawing_tools": to_bool(payload.get("ENABLE_DRAWING_TOOLS", True)),
            "enable_fullscreen": to_bool(payload.get("ENABLE_FULLSCREEN", True)),
            "db_host": payload["DB_HOST"],
            "db_port": payload["DB_PORT"],
            "db_name": payload["DB_NAME"],
            "db_user": payload["DB_USER"],
            "db_password": payload["DB_PASSWORD"],
            "redis_url": payload["REDIS_URL"],
            "ftp_enabled": to_bool(payload["FTP_ENABLED"]),
            "ftp_host": payload["FTP_HOST"],
            "ftp_port": int(payload["FTP_PORT"]),
            "ftp_user": payload["FTP_USER"],
            "ftp_password": payload["FTP_PASSWORD"],
            "ftp_path": payload["FTP_PATH"],
            "gdrive_enabled": to_bool(payload["GDRIVE_ENABLED"]),
            "gdrive_auth_mode": payload["GDRIVE_AUTH_MODE"],
            "gdrive_credentials_json": payload["GDRIVE_CREDENTIALS_JSON"],
            "gdrive_folder_id": payload["GDRIVE_FOLDER_ID"],
            "gdrive_shared_drive_id": payload["GDRIVE_SHARED_DRIVE_ID"],
            "gdrive_oauth_client_id": payload["GDRIVE_OAUTH_CLIENT_ID"],
            "gdrive_oauth_client_secret": payload["GDRIVE_OAUTH_CLIENT_SECRET"],
            "gdrive_oauth_refresh_token": payload["GDRIVE_OAUTH_REFRESH_TOKEN"],
            "gdrive_oauth_user_email": payload["GDRIVE_OAUTH_USER_EMAIL"],
            "smtp_enabled": to_bool(payload["SMTP_ENABLED"]),
            "smtp_host": payload["SMTP_HOST"],
            "smtp_port": payload["SMTP_PORT"],
            "smtp_security": payload["SMTP_SECURITY"],
            "smtp_user": payload["SMTP_USER"],
            "smtp_password": payload["SMTP_PASSWORD"],
            "smtp_auth_mode": payload["SMTP_AUTH_MODE"],
            "smtp_oauth_client_id": payload["SMTP_OAUTH_CLIENT_ID"],
            "smtp_oauth_client_secret": payload["SMTP_OAUTH_CLIENT_SECRET"],
            "smtp_oauth_refresh_token": payload["SMTP_OAUTH_REFRESH_TOKEN"],
            "smtp_from_name": payload["SMTP_FROM_NAME"],
            "smtp_from_email": payload["SMTP_FROM_EMAIL"],
            "smtp_test_recipient": payload["SMTP_TEST_RECIPIENT"],
            "sms_enabled": to_bool(payload["SMS_ENABLED"]),
            "sms_provider": payload["SMS_PROVIDER"],
            "sms_provider_rank": int(payload["SMS_PROVIDER_RANK"]),
            "sms_username": payload["SMS_USERNAME"],
            "sms_password": payload["SMS_PASSWORD"],
            "sms_api_token": payload["SMS_API_TOKEN"],
            "sms_api_url": payload["SMS_API_URL"],
            "sms_sender_id": payload["SMS_SENDER_ID"],
            "sms_test_recipient": payload["SMS_TEST_RECIPIENT"],
            "sms_test_message": payload["SMS_TEST_MESSAGE"],
            "sms_priority": payload["SMS_PRIORITY"],
            "sms_aws_region": payload["SMS_AWS_REGION"],
            "sms_aws_access_key_id": payload["SMS_AWS_ACCESS_KEY_ID"],
            "sms_aws_secret_access_key": payload["SMS_AWS_SECRET_ACCESS_KEY"],
            "sms_infobip_base_url": payload["SMS_INFOBIP_BASE_URL"],
        },
    )


def update_configuration(data: dict[str, Any]) -> dict[str, Any]:
    """Valida, normaliza, aplica em memória, grava na base, limpa caches e, se a senha
    de backup mudou, gera um backup. Devolve o que a view precisa para responder."""
    runtime_config = runtime_settings.get_runtime_config()
    existing_record = (
        FirstTimeSetup.objects.filter(configured=True).order_by("-configured_at").first()
    )
    existing_backup_password = (
        (getattr(existing_record, "backup_password", "") or "") if existing_record else ""
    )

    required = {
        "ZABBIX_API_URL": runtime_config.zabbix_api_url,
        "DB_HOST": runtime_config.db_host,
        "DB_PORT": runtime_config.db_port,
        "DB_NAME": runtime_config.db_name,
        "DB_USER": runtime_config.db_user,
    }
    missing = [key for key, existing in required.items() if not _str(data, key) and not existing]
    if missing:
        raise MissingRequiredFields(missing)

    backup_zip_password = _str(data, "BACKUP_ZIP_PASSWORD") or existing_backup_password
    if backup_zip_password and len(backup_zip_password) < MIN_BACKUP_PASSWORD_LEN:
        raise ConfigError("A senha do backup precisa ter pelo menos 8 caracteres.")

    payload = build_configuration_payload(data, runtime_config, backup_zip_password)

    _apply_runtime_overrides(payload)
    _persist_configuration(payload)
    _purge_stale_env_keys()

    clear_runtime_config_cache()
    runtime_settings.reload_config()
    from integrations.zabbix.zabbix_service import clear_token_cache

    clear_token_cache()
    reload_diagnostics_flag_cache()

    restart_triggered = bool(payload["SERVICE_RESTART_COMMANDS"]) and bool(trigger_restart())

    result: dict[str, Any] = {
        "restart_triggered": restart_triggered,
        "backup_created": False,
        "backup_filename": "",
        "gdrive_upload": {},
        "ftp_upload": {},
        "backup_error": "",
    }
    if backup_zip_password != existing_backup_password:
        try:
            filename = call_command("make_backup") or ""
            result["backup_created"] = True
            result["backup_filename"] = filename
            result["gdrive_upload"] = (
                upload_backup_if_enabled(
                    filename,
                    enabled=to_bool(payload["GDRIVE_ENABLED"]),
                    auth_mode=payload["GDRIVE_AUTH_MODE"],
                    credentials_json=payload["GDRIVE_CREDENTIALS_JSON"],
                    folder_id=payload["GDRIVE_FOLDER_ID"],
                    shared_drive_id=payload["GDRIVE_SHARED_DRIVE_ID"],
                    oauth_client_id=payload["GDRIVE_OAUTH_CLIENT_ID"],
                    oauth_client_secret=payload["GDRIVE_OAUTH_CLIENT_SECRET"],
                    oauth_refresh_token=payload["GDRIVE_OAUTH_REFRESH_TOKEN"],
                )
                or {}
            )
            result["ftp_upload"] = (
                upload_backup_via_ftp(
                    filename,
                    {
                        "enabled": to_bool(payload["FTP_ENABLED"]),
                        "host": payload["FTP_HOST"],
                        "port": payload["FTP_PORT"],
                        "user": payload["FTP_USER"],
                        "password": payload["FTP_PASSWORD"],
                        "path": payload["FTP_PATH"],
                    },
                )
                or {}
            )
        except Exception as exc:  # o backup é melhor-esforço; a configuração já está gravada
            result["backup_error"] = str(exc)
    return result
