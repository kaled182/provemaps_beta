"""Runtime configuration loader fed by the ``FirstTimeSetup`` table."""
from __future__ import annotations

import os
from typing import Dict

from django.core.cache import cache
from django.db import connection

from setup_app.models import FirstTimeSetup

_CONFIG_CACHE_KEY = "setup_app:runtime_config"
_CONFIG_CACHE_TTL = 300  # 5 minutos


def get_runtime_config() -> Dict[str, str]:
    """Return the runtime configuration from cache or the database."""
    # Prefer the cached snapshot
    cached = cache.get(_CONFIG_CACHE_KEY)
    if cached is not None:
        return cached

    # Fallback to the database if it is not cached
    config = _load_from_database()
    
    # Store the refreshed payload in cache
    if config:
        cache.set(_CONFIG_CACHE_KEY, config, _CONFIG_CACHE_TTL)
    
    return config


def _load_from_database() -> Dict[str, str]:
    """Fetch the most recent configuration row from the database."""
    config = {}
    record = (
        FirstTimeSetup.objects.filter(configured=True)
        .order_by("-configured_at")
        .first()
    )
    if not record:
        return config

    if record.zabbix_url:
        config["ZABBIX_API_URL"] = record.zabbix_url

    if record.auth_type == "token":
        if record.zabbix_api_key:
            config["ZABBIX_API_KEY"] = record.zabbix_api_key
    else:
        if record.zabbix_user:
            config["ZABBIX_API_USER"] = record.zabbix_user
        if record.zabbix_password:
            config["ZABBIX_API_PASSWORD"] = record.zabbix_password

    if record.maps_api_key:
        config["GOOGLE_MAPS_API_KEY"] = record.maps_api_key

    if record.db_host:
        config["DB_HOST"] = record.db_host
    if record.db_port:
        config["DB_PORT"] = record.db_port
    if record.db_name:
        config["DB_NAME"] = record.db_name
    if record.db_user:
        config["DB_USER"] = record.db_user
    if record.db_password:
        config["DB_PASSWORD"] = record.db_password
    if record.redis_url:
        config["REDIS_URL"] = record.redis_url
    if record.ftp_enabled is not None:
        config["FTP_ENABLED"] = record.ftp_enabled
    if record.ftp_host:
        config["FTP_HOST"] = record.ftp_host
    if record.ftp_port:
        config["FTP_PORT"] = str(record.ftp_port)
    if record.ftp_user:
        config["FTP_USER"] = record.ftp_user
    if record.ftp_password:
        config["FTP_PASSWORD"] = record.ftp_password
    if record.ftp_path:
        config["FTP_PATH"] = record.ftp_path
    if record.gdrive_enabled is not None:
        config["GDRIVE_ENABLED"] = record.gdrive_enabled
    if record.gdrive_credentials_json:
        config["GDRIVE_CREDENTIALS_JSON"] = record.gdrive_credentials_json
    if record.gdrive_folder_id:
        config["GDRIVE_FOLDER_ID"] = record.gdrive_folder_id
    if record.gdrive_shared_drive_id:
        config["GDRIVE_SHARED_DRIVE_ID"] = record.gdrive_shared_drive_id
    if record.gdrive_auth_mode:
        config["GDRIVE_AUTH_MODE"] = record.gdrive_auth_mode
    if record.gdrive_oauth_client_id:
        config["GDRIVE_OAUTH_CLIENT_ID"] = record.gdrive_oauth_client_id
    if record.gdrive_oauth_client_secret:
        config["GDRIVE_OAUTH_CLIENT_SECRET"] = record.gdrive_oauth_client_secret
    if record.gdrive_oauth_refresh_token:
        config["GDRIVE_OAUTH_REFRESH_TOKEN"] = record.gdrive_oauth_refresh_token
    if record.gdrive_oauth_user_email:
        config["GDRIVE_OAUTH_USER_EMAIL"] = record.gdrive_oauth_user_email
    if record.smtp_enabled is not None:
        config["SMTP_ENABLED"] = record.smtp_enabled
    if record.smtp_host:
        config["SMTP_HOST"] = record.smtp_host
    if record.smtp_port:
        config["SMTP_PORT"] = record.smtp_port
    if record.smtp_security:
        config["SMTP_SECURITY"] = record.smtp_security
    if record.smtp_user:
        config["SMTP_USER"] = record.smtp_user
    if record.smtp_password:
        config["SMTP_PASSWORD"] = record.smtp_password
    if record.smtp_auth_mode:
        config["SMTP_AUTH_MODE"] = record.smtp_auth_mode
    if record.smtp_oauth_client_id:
        config["SMTP_OAUTH_CLIENT_ID"] = record.smtp_oauth_client_id
    if record.smtp_oauth_client_secret:
        config["SMTP_OAUTH_CLIENT_SECRET"] = record.smtp_oauth_client_secret
    if record.smtp_oauth_refresh_token:
        config["SMTP_OAUTH_REFRESH_TOKEN"] = record.smtp_oauth_refresh_token
    if record.smtp_from_name:
        config["SMTP_FROM_NAME"] = record.smtp_from_name
    if record.smtp_from_email:
        config["SMTP_FROM_EMAIL"] = record.smtp_from_email
    if record.smtp_test_recipient:
        config["SMTP_TEST_RECIPIENT"] = record.smtp_test_recipient
    if record.sms_enabled is not None:
        config["SMS_ENABLED"] = record.sms_enabled
    if record.sms_provider:
        config["SMS_PROVIDER"] = record.sms_provider
    if record.sms_provider_rank:
        config["SMS_PROVIDER_RANK"] = str(record.sms_provider_rank)
    if record.sms_username:
        config["SMS_USERNAME"] = record.sms_username
    if record.sms_password:
        config["SMS_PASSWORD"] = record.sms_password
    if record.sms_api_token:
        config["SMS_API_TOKEN"] = record.sms_api_token
    if record.sms_api_url:
        config["SMS_API_URL"] = record.sms_api_url
    if record.sms_sender_id:
        config["SMS_SENDER_ID"] = record.sms_sender_id
    if record.sms_test_recipient:
        config["SMS_TEST_RECIPIENT"] = record.sms_test_recipient
    if record.sms_test_message:
        config["SMS_TEST_MESSAGE"] = record.sms_test_message
    if record.sms_priority:
        config["SMS_PRIORITY"] = record.sms_priority
    if record.sms_aws_region:
        config["SMS_AWS_REGION"] = record.sms_aws_region
    if record.sms_aws_access_key_id:
        config["SMS_AWS_ACCESS_KEY_ID"] = record.sms_aws_access_key_id
    if record.sms_aws_secret_access_key:
        config["SMS_AWS_SECRET_ACCESS_KEY"] = record.sms_aws_secret_access_key
    if record.sms_infobip_base_url:
        config["SMS_INFOBIP_BASE_URL"] = record.sms_infobip_base_url
    
    # Map configuration
    if record.map_provider:
        config["MAP_PROVIDER"] = record.map_provider
    if record.mapbox_token:
        config["MAPBOX_TOKEN"] = record.mapbox_token
    # Google Maps
    if record.map_default_zoom is not None:
        config["MAP_DEFAULT_ZOOM"] = str(record.map_default_zoom)
    if record.map_default_lat is not None:
        config["MAP_DEFAULT_LAT"] = str(record.map_default_lat)
    if record.map_default_lng is not None:
        config["MAP_DEFAULT_LNG"] = str(record.map_default_lng)
    if record.map_type:
        config["MAP_TYPE"] = record.map_type
    if record.map_styles:
        config["MAP_STYLES"] = record.map_styles
    if record.enable_street_view is not None:
        config["ENABLE_STREET_VIEW"] = record.enable_street_view
    if record.enable_traffic is not None:
        config["ENABLE_TRAFFIC"] = record.enable_traffic
    # Mapbox
    if record.mapbox_style:
        config["MAPBOX_STYLE"] = record.mapbox_style
    if record.mapbox_custom_style:
        config["MAPBOX_CUSTOM_STYLE"] = record.mapbox_custom_style
    if record.mapbox_enable_3d is not None:
        config["MAPBOX_ENABLE_3D"] = record.mapbox_enable_3d
    # Esri
    if record.esri_api_key:
        config["ESRI_API_KEY"] = record.esri_api_key
    if record.esri_basemap:
        config["ESRI_BASEMAP"] = record.esri_basemap
    # Common
    if record.map_language:
        config["MAP_LANGUAGE"] = record.map_language
    if record.map_theme:
        config["MAP_THEME"] = record.map_theme
    if record.enable_map_clustering is not None:
        config["ENABLE_MAP_CLUSTERING"] = record.enable_map_clustering
    if record.enable_drawing_tools is not None:
        config["ENABLE_DRAWING_TOOLS"] = record.enable_drawing_tools
    if record.enable_fullscreen is not None:
        config["ENABLE_FULLSCREEN"] = record.enable_fullscreen

    return config


def clear_runtime_config_cache():
    """Invalidate the runtime configuration cache entry."""
    cache.delete(_CONFIG_CACHE_KEY)


def get_config_value(key: str, default: str = "") -> str:
    """Return a specific config value honoring the precedence chain."""
    # 1. Environment variables
    env_value = os.getenv(key)
    if env_value:
        return env_value
    
    # 2. Database-backed runtime config
    runtime_config = get_runtime_config()
    return runtime_config.get(key, default)


def is_first_time_setup_needed() -> bool:
    """Check whether the initial setup still needs to run."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'setup_app_firsttimesetup'
            """)
            if not cursor.fetchone():
                return True

            cursor.execute("""
                SELECT COUNT(*)
                FROM setup_app_firsttimesetup
                WHERE configured = 1
            """)
            count = cursor.fetchone()[0]
            return count == 0
    except Exception:
        return True
