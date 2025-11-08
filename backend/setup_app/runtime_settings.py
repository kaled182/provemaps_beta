"""Helpers to override Django settings at runtime using persisted values."""
from __future__ import annotations

import functools
from typing import Any

from django.conf import settings as django_settings

from .services.config_loader import get_config_value, get_runtime_config


@functools.lru_cache(maxsize=1)
def _get_cached_config():
    """Return the cached runtime configuration snapshot."""
    return get_runtime_config()


class RuntimeSettings:
    """Map Django settings with a fallback to the database layer."""

    def __getattr__(self, name: str) -> Any:
        """Return a configuration value honoring the precedence order."""
        # First try to read from Django settings (environment variables)
        django_value = getattr(django_settings, name, None)
        if django_value:
            return django_value

        # If not defined in Django settings, fall back to the database
        runtime_config = _get_cached_config()
        return runtime_config.get(name)

    def reload_config(self):
        """Clear the local cache so the next call fetches fresh data."""
        _get_cached_config.cache_clear()


# Global instance available across the project
runtime_settings = RuntimeSettings()


# Helper shortcuts for specific configuration values
def get_zabbix_url() -> str:
    """Return the configured Zabbix base URL."""
    return get_config_value('ZABBIX_API_URL', '')


def get_zabbix_api_key() -> str:
    """Return the Zabbix API key (when ``auth_type='token'``)."""
    return get_config_value('ZABBIX_API_KEY', '')


def get_zabbix_user() -> str:
    """Return the Zabbix username (when ``auth_type='login'``)."""
    return get_config_value('ZABBIX_API_USER', '')


def get_zabbix_password() -> str:
    """Return the Zabbix password (when ``auth_type='login'``)."""
    return get_config_value('ZABBIX_API_PASSWORD', '')


def get_google_maps_api_key() -> str:
    """Return the Google Maps API key."""
    return get_config_value('GOOGLE_MAPS_API_KEY', '')
