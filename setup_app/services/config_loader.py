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
