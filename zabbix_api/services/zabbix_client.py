from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from zabbix_api.client import (
    API_KEY_BACKOFF_SECONDS,
    READ_ONLY_SAFE_METHODS,
    TOKEN_CACHE_TIME,
    ResilientZabbixClient,
    resilient_client,
    zabbix_batch as _zabbix_batch,
    zabbix_call as _zabbix_call,
)

logger = logging.getLogger(__name__)

__all__ = [
    "READ_ONLY_SAFE_METHODS",
    "TOKEN_CACHE_TIME",
    "API_KEY_BACKOFF_SECONDS",
    "normalize_zabbix_url",
    "get_current_config",
    "clear_token_cache",
    "zabbix_login",
    "zabbix_request",
    "zabbix_batch",
    "zabbix_call",
    "client",
]

client: ResilientZabbixClient = resilient_client


def normalize_zabbix_url(url: str) -> str:
    """Keep compatibility with the legacy helper."""
    return resilient_client.normalize_url(url)


def get_current_config() -> Tuple[str, Any]:
    """Return the normalized URL plus the runtime configuration."""
    cfg = resilient_client.get_current_config()
    return cfg.url, cfg


def clear_token_cache() -> None:
    """Clear the cached token while preserving legacy API behavior."""
    resilient_client.clear_token_cache()


def zabbix_login() -> Optional[str]:
    """Return the current token (legacy API compatibility)."""
    return resilient_client.login()


def zabbix_request(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    retry_without_auth: bool = False,
) -> Optional[Any]:
    """Thin wrapper for JSON-RPC calls using the resilient client."""
    if retry_without_auth:
        logger.debug(
            "retry_without_auth flag ignored; the resilient client already "
            "performs the automatic fallback",
        )
    return resilient_client.call(method, params)


def zabbix_batch(
    calls: list[tuple[str, Optional[Dict[str, Any]]]]
) -> list[Optional[Any]]:
    """Compatibility wrapper for batch calls (legacy signature)."""
    return _zabbix_batch(calls)


def zabbix_call(
    method: str,
    params: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """Compatibility wrapper for single calls (legacy signature)."""
    return _zabbix_call(method, params)
