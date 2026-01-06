from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from django.conf import settings

from setup_app.models import FirstTimeSetup


@dataclass
class RuntimeConfig:
    zabbix_api_url: str
    zabbix_api_user: str
    zabbix_api_password: str
    zabbix_api_key: str
    google_maps_api_key: str
    map_provider: str
    mapbox_token: str
    db_host: str
    db_port: str
    db_name: str
    db_user: str
    db_password: str
    redis_url: str
    allowed_hosts: list[str]
    diagnostics_enabled: bool


def _fallback_config() -> RuntimeConfig:
    db_settings = settings.DATABASES.get("default", {})
    redis_url = getattr(settings, "REDIS_URL", "")
    allowed_hosts = settings.ALLOWED_HOSTS if isinstance(settings.ALLOWED_HOSTS, (list, tuple)) else []
    return RuntimeConfig(
        zabbix_api_url=getattr(settings, "ZABBIX_API_URL", ""),
        zabbix_api_user=getattr(settings, "ZABBIX_API_USER", ""),
        zabbix_api_password=getattr(settings, "ZABBIX_API_PASSWORD", ""),
        zabbix_api_key=getattr(settings, "ZABBIX_API_KEY", ""),
        google_maps_api_key=getattr(settings, "GOOGLE_MAPS_API_KEY", ""),
        map_provider=getattr(settings, "MAP_PROVIDER", "google"),
        mapbox_token=getattr(settings, "MAPBOX_TOKEN", ""),
        db_host=db_settings.get("HOST", ""),
        db_port=str(db_settings.get("PORT", "")),
        db_name=db_settings.get("NAME", ""),
        db_user=db_settings.get("USER", ""),
        db_password=db_settings.get("PASSWORD", ""),
        redis_url=redis_url,
        allowed_hosts=list(allowed_hosts),
        diagnostics_enabled=getattr(settings, "ENABLE_DIAGNOSTIC_ENDPOINTS", False),
    )


@lru_cache(maxsize=1)
def get_runtime_config() -> RuntimeConfig:
    record = FirstTimeSetup.objects.filter(configured=True).order_by("-configured_at").first()
    if not record:
        return _fallback_config()

    allowed_hosts_env = settings.ALLOWED_HOSTS if isinstance(settings.ALLOWED_HOSTS, (list, tuple)) else []
    db_settings = settings.DATABASES.get("default", {})
    return RuntimeConfig(
        zabbix_api_url=record.zabbix_url or getattr(settings, "ZABBIX_API_URL", ""),
        zabbix_api_user=record.zabbix_user or getattr(settings, "ZABBIX_API_USER", ""),
        zabbix_api_password=record.zabbix_password or getattr(settings, "ZABBIX_API_PASSWORD", ""),
        zabbix_api_key=record.zabbix_api_key or getattr(settings, "ZABBIX_API_KEY", ""),
        google_maps_api_key=record.maps_api_key or getattr(settings, "GOOGLE_MAPS_API_KEY", ""),
        map_provider=record.map_provider or getattr(settings, "MAP_PROVIDER", "google"),
        mapbox_token=record.mapbox_token or getattr(settings, "MAPBOX_TOKEN", ""),
        db_host=record.db_host or db_settings.get("HOST", ""),
        db_port=record.db_port or str(db_settings.get("PORT", "")),
        db_name=record.db_name or db_settings.get("NAME", ""),
        db_user=record.db_user or db_settings.get("USER", ""),
        db_password=record.db_password or db_settings.get("PASSWORD", ""),
        redis_url=record.redis_url or getattr(settings, "REDIS_URL", ""),
        allowed_hosts=list(allowed_hosts_env),
        diagnostics_enabled=getattr(settings, "ENABLE_DIAGNOSTIC_ENDPOINTS", False),
    )


def reload_config() -> None:
    get_runtime_config.cache_clear()
