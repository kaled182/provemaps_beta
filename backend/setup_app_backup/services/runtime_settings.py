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
    ftp_enabled: bool
    ftp_host: str
    ftp_port: str
    ftp_user: str
    ftp_password: str
    ftp_path: str
    gdrive_enabled: bool
    gdrive_credentials_json: str
    gdrive_folder_id: str
    gdrive_shared_drive_id: str
    gdrive_auth_mode: str
    gdrive_oauth_client_id: str
    gdrive_oauth_client_secret: str
    gdrive_oauth_refresh_token: str
    gdrive_oauth_user_email: str
    smtp_enabled: bool
    smtp_host: str
    smtp_port: str
    smtp_security: str
    smtp_user: str
    smtp_password: str
    smtp_auth_mode: str
    smtp_oauth_client_id: str
    smtp_oauth_client_secret: str
    smtp_oauth_refresh_token: str
    smtp_from_name: str
    smtp_from_email: str
    smtp_test_recipient: str
    sms_enabled: bool
    sms_provider: str
    sms_provider_rank: str
    sms_username: str
    sms_password: str
    sms_api_token: str
    sms_api_url: str
    sms_sender_id: str
    sms_test_recipient: str
    sms_test_message: str
    sms_priority: str
    sms_aws_region: str
    sms_aws_access_key_id: str
    sms_aws_secret_access_key: str
    sms_infobip_base_url: str
    map_default_zoom: int
    map_default_lat: str
    map_default_lng: str
    map_type: str
    map_styles: str
    enable_street_view: bool
    enable_traffic: bool
    mapbox_style: str
    mapbox_custom_style: str
    mapbox_enable_3d: bool
    esri_api_key: str
    esri_basemap: str
    map_language: str
    map_theme: str
    enable_map_clustering: bool
    enable_drawing_tools: bool
    enable_fullscreen: bool
    optical_rx_warning_threshold: float
    optical_rx_critical_threshold: float


def _float_setting(name: str, default: float) -> float:
    try:
        return float(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


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
        ftp_enabled=getattr(settings, "FTP_ENABLED", False),
        ftp_host=getattr(settings, "FTP_HOST", ""),
        ftp_port=str(getattr(settings, "FTP_PORT", "")),
        ftp_user=getattr(settings, "FTP_USER", ""),
        ftp_password=getattr(settings, "FTP_PASSWORD", ""),
        ftp_path=getattr(settings, "FTP_PATH", ""),
        gdrive_enabled=getattr(settings, "GDRIVE_ENABLED", False),
        gdrive_credentials_json=getattr(settings, "GDRIVE_CREDENTIALS_JSON", ""),
        gdrive_folder_id=getattr(settings, "GDRIVE_FOLDER_ID", ""),
        gdrive_shared_drive_id=getattr(settings, "GDRIVE_SHARED_DRIVE_ID", ""),
        gdrive_auth_mode=getattr(settings, "GDRIVE_AUTH_MODE", "service_account"),
        gdrive_oauth_client_id=getattr(settings, "GDRIVE_OAUTH_CLIENT_ID", ""),
        gdrive_oauth_client_secret=getattr(settings, "GDRIVE_OAUTH_CLIENT_SECRET", ""),
        gdrive_oauth_refresh_token=getattr(settings, "GDRIVE_OAUTH_REFRESH_TOKEN", ""),
        gdrive_oauth_user_email=getattr(settings, "GDRIVE_OAUTH_USER_EMAIL", ""),
        smtp_enabled=getattr(settings, "SMTP_ENABLED", False),
        smtp_host=getattr(settings, "SMTP_HOST", ""),
        smtp_port=str(getattr(settings, "SMTP_PORT", "")),
        smtp_security=getattr(settings, "SMTP_SECURITY", ""),
        smtp_user=getattr(settings, "SMTP_USER", ""),
        smtp_password=getattr(settings, "SMTP_PASSWORD", ""),
        smtp_auth_mode=getattr(settings, "SMTP_AUTH_MODE", "password"),
        smtp_oauth_client_id=getattr(settings, "SMTP_OAUTH_CLIENT_ID", ""),
        smtp_oauth_client_secret=getattr(settings, "SMTP_OAUTH_CLIENT_SECRET", ""),
        smtp_oauth_refresh_token=getattr(settings, "SMTP_OAUTH_REFRESH_TOKEN", ""),
        smtp_from_name=getattr(settings, "SMTP_FROM_NAME", ""),
        smtp_from_email=getattr(settings, "SMTP_FROM_EMAIL", ""),
        smtp_test_recipient=getattr(settings, "SMTP_TEST_RECIPIENT", ""),
        sms_enabled=getattr(settings, "SMS_ENABLED", False),
        sms_provider=getattr(settings, "SMS_PROVIDER", "smsnet"),
        sms_provider_rank=str(getattr(settings, "SMS_PROVIDER_RANK", "1")),
        sms_username=getattr(settings, "SMS_USERNAME", ""),
        sms_password=getattr(settings, "SMS_PASSWORD", ""),
        sms_api_token=getattr(settings, "SMS_API_TOKEN", ""),
        sms_api_url=getattr(settings, "SMS_API_URL", ""),
        sms_sender_id=getattr(settings, "SMS_SENDER_ID", ""),
        sms_test_recipient=getattr(settings, "SMS_TEST_RECIPIENT", ""),
        sms_test_message=getattr(settings, "SMS_TEST_MESSAGE", ""),
        sms_priority=getattr(settings, "SMS_PRIORITY", ""),
        sms_aws_region=getattr(settings, "SMS_AWS_REGION", ""),
        sms_aws_access_key_id=getattr(settings, "SMS_AWS_ACCESS_KEY_ID", ""),
        sms_aws_secret_access_key=getattr(settings, "SMS_AWS_SECRET_ACCESS_KEY", ""),
        sms_infobip_base_url=getattr(settings, "SMS_INFOBIP_BASE_URL", ""),
        map_default_zoom=int(getattr(settings, "MAP_DEFAULT_ZOOM", 12)),
        map_default_lat=str(getattr(settings, "MAP_DEFAULT_LAT", "-15.7801")),
        map_default_lng=str(getattr(settings, "MAP_DEFAULT_LNG", "-47.9292")),
        map_type=getattr(settings, "MAP_TYPE", "terrain"),
        map_styles=getattr(settings, "MAP_STYLES", ""),
        enable_street_view=getattr(settings, "ENABLE_STREET_VIEW", True),
        enable_traffic=getattr(settings, "ENABLE_TRAFFIC", False),
        mapbox_style=getattr(settings, "MAPBOX_STYLE", "streets-v12"),
        mapbox_custom_style=getattr(settings, "MAPBOX_CUSTOM_STYLE", ""),
        mapbox_enable_3d=getattr(settings, "MAPBOX_ENABLE_3D", False),
        esri_api_key=getattr(settings, "ESRI_API_KEY", ""),
        esri_basemap=getattr(settings, "ESRI_BASEMAP", "topo-vector"),
        map_language=getattr(settings, "MAP_LANGUAGE", "pt-BR"),
        map_theme=getattr(settings, "MAP_THEME", "light"),
        enable_map_clustering=getattr(settings, "ENABLE_MAP_CLUSTERING", True),
        enable_drawing_tools=getattr(settings, "ENABLE_DRAWING_TOOLS", True),
        enable_fullscreen=getattr(settings, "ENABLE_FULLSCREEN", True),
        optical_rx_warning_threshold=_float_setting("OPTICAL_RX_WARNING_THRESHOLD", -24.0),
        optical_rx_critical_threshold=_float_setting("OPTICAL_RX_CRITICAL_THRESHOLD", -27.0),
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
        ftp_enabled=record.ftp_enabled if record.ftp_enabled is not None else getattr(settings, "FTP_ENABLED", False),
        ftp_host=record.ftp_host or getattr(settings, "FTP_HOST", ""),
        ftp_port=str(record.ftp_port or getattr(settings, "FTP_PORT", "")),
        ftp_user=record.ftp_user or getattr(settings, "FTP_USER", ""),
        ftp_password=record.ftp_password or getattr(settings, "FTP_PASSWORD", ""),
        ftp_path=record.ftp_path or getattr(settings, "FTP_PATH", ""),
        gdrive_enabled=record.gdrive_enabled if record.gdrive_enabled is not None else getattr(settings, "GDRIVE_ENABLED", False),
        gdrive_credentials_json=record.gdrive_credentials_json or getattr(settings, "GDRIVE_CREDENTIALS_JSON", ""),
        gdrive_folder_id=record.gdrive_folder_id or getattr(settings, "GDRIVE_FOLDER_ID", ""),
        gdrive_shared_drive_id=record.gdrive_shared_drive_id or getattr(settings, "GDRIVE_SHARED_DRIVE_ID", ""),
        gdrive_auth_mode=record.gdrive_auth_mode or getattr(settings, "GDRIVE_AUTH_MODE", "service_account"),
        gdrive_oauth_client_id=record.gdrive_oauth_client_id or getattr(settings, "GDRIVE_OAUTH_CLIENT_ID", ""),
        gdrive_oauth_client_secret=record.gdrive_oauth_client_secret or getattr(settings, "GDRIVE_OAUTH_CLIENT_SECRET", ""),
        gdrive_oauth_refresh_token=record.gdrive_oauth_refresh_token or getattr(settings, "GDRIVE_OAUTH_REFRESH_TOKEN", ""),
        gdrive_oauth_user_email=record.gdrive_oauth_user_email or getattr(settings, "GDRIVE_OAUTH_USER_EMAIL", ""),
        smtp_enabled=record.smtp_enabled if record.smtp_enabled is not None else getattr(settings, "SMTP_ENABLED", False),
        smtp_host=record.smtp_host or getattr(settings, "SMTP_HOST", ""),
        smtp_port=record.smtp_port or str(getattr(settings, "SMTP_PORT", "")),
        smtp_security=record.smtp_security or getattr(settings, "SMTP_SECURITY", ""),
        smtp_user=record.smtp_user or getattr(settings, "SMTP_USER", ""),
        smtp_password=record.smtp_password or getattr(settings, "SMTP_PASSWORD", ""),
        smtp_auth_mode=record.smtp_auth_mode or getattr(settings, "SMTP_AUTH_MODE", "password"),
        smtp_oauth_client_id=record.smtp_oauth_client_id or getattr(settings, "SMTP_OAUTH_CLIENT_ID", ""),
        smtp_oauth_client_secret=record.smtp_oauth_client_secret or getattr(settings, "SMTP_OAUTH_CLIENT_SECRET", ""),
        smtp_oauth_refresh_token=record.smtp_oauth_refresh_token or getattr(settings, "SMTP_OAUTH_REFRESH_TOKEN", ""),
        smtp_from_name=record.smtp_from_name or getattr(settings, "SMTP_FROM_NAME", ""),
        smtp_from_email=record.smtp_from_email or getattr(settings, "SMTP_FROM_EMAIL", ""),
        smtp_test_recipient=record.smtp_test_recipient or getattr(settings, "SMTP_TEST_RECIPIENT", ""),
        sms_enabled=record.sms_enabled if record.sms_enabled is not None else getattr(settings, "SMS_ENABLED", False),
        sms_provider=record.sms_provider or getattr(settings, "SMS_PROVIDER", "smsnet"),
        sms_provider_rank=str(record.sms_provider_rank or getattr(settings, "SMS_PROVIDER_RANK", "1")),
        sms_username=record.sms_username or getattr(settings, "SMS_USERNAME", ""),
        sms_password=record.sms_password or getattr(settings, "SMS_PASSWORD", ""),
        sms_api_token=record.sms_api_token or getattr(settings, "SMS_API_TOKEN", ""),
        sms_api_url=record.sms_api_url or getattr(settings, "SMS_API_URL", ""),
        sms_sender_id=record.sms_sender_id or getattr(settings, "SMS_SENDER_ID", ""),
        sms_test_recipient=record.sms_test_recipient or getattr(settings, "SMS_TEST_RECIPIENT", ""),
        sms_test_message=record.sms_test_message or getattr(settings, "SMS_TEST_MESSAGE", ""),
        sms_priority=record.sms_priority or getattr(settings, "SMS_PRIORITY", ""),
        sms_aws_region=record.sms_aws_region or getattr(settings, "SMS_AWS_REGION", ""),
        sms_aws_access_key_id=record.sms_aws_access_key_id or getattr(settings, "SMS_AWS_ACCESS_KEY_ID", ""),
        sms_aws_secret_access_key=record.sms_aws_secret_access_key or getattr(settings, "SMS_AWS_SECRET_ACCESS_KEY", ""),
        sms_infobip_base_url=record.sms_infobip_base_url or getattr(settings, "SMS_INFOBIP_BASE_URL", ""),
        map_default_zoom=record.map_default_zoom if record.map_default_zoom is not None else int(getattr(settings, "MAP_DEFAULT_ZOOM", 12)),
        map_default_lat=str(record.map_default_lat) if record.map_default_lat is not None else str(getattr(settings, "MAP_DEFAULT_LAT", "-15.7801")),
        map_default_lng=str(record.map_default_lng) if record.map_default_lng is not None else str(getattr(settings, "MAP_DEFAULT_LNG", "-47.9292")),
        map_type=record.map_type or getattr(settings, "MAP_TYPE", "terrain"),
        map_styles=record.map_styles or getattr(settings, "MAP_STYLES", ""),
        enable_street_view=record.enable_street_view if record.enable_street_view is not None else getattr(settings, "ENABLE_STREET_VIEW", True),
        enable_traffic=record.enable_traffic if record.enable_traffic is not None else getattr(settings, "ENABLE_TRAFFIC", False),
        mapbox_style=record.mapbox_style or getattr(settings, "MAPBOX_STYLE", "streets-v12"),
        mapbox_custom_style=record.mapbox_custom_style or getattr(settings, "MAPBOX_CUSTOM_STYLE", ""),
        mapbox_enable_3d=record.mapbox_enable_3d if record.mapbox_enable_3d is not None else getattr(settings, "MAPBOX_ENABLE_3D", False),
        esri_api_key=record.esri_api_key or getattr(settings, "ESRI_API_KEY", ""),
        esri_basemap=record.esri_basemap or getattr(settings, "ESRI_BASEMAP", "topo-vector"),
        map_language=record.map_language or getattr(settings, "MAP_LANGUAGE", "pt-BR"),
        map_theme=record.map_theme or getattr(settings, "MAP_THEME", "light"),
        enable_map_clustering=record.enable_map_clustering if record.enable_map_clustering is not None else getattr(settings, "ENABLE_MAP_CLUSTERING", True),
        enable_drawing_tools=record.enable_drawing_tools if record.enable_drawing_tools is not None else getattr(settings, "ENABLE_DRAWING_TOOLS", True),
        enable_fullscreen=record.enable_fullscreen if record.enable_fullscreen is not None else getattr(settings, "ENABLE_FULLSCREEN", True),
        optical_rx_warning_threshold=_float_setting("OPTICAL_RX_WARNING_THRESHOLD", -24.0),
        optical_rx_critical_threshold=_float_setting("OPTICAL_RX_CRITICAL_THRESHOLD", -27.0),
    )


def reload_config() -> None:
    get_runtime_config.cache_clear()
