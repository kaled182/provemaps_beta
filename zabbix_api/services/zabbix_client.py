from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, cast

import requests

from django.conf import settings

from setup_app.services import runtime_settings

logger = logging.getLogger(__name__)

READ_ONLY_SAFE_METHODS = {
    "apiinfo.version",
    "user.login",
    "host.get",
    "item.get",
    "history.get",
    "problem.get",
    "event.get",
    "trigger.get",
    "graph.get",
    "hostgroup.get",
    "template.get",
    "map.get",
    "application.get",
    "hostinterface.get",
}

TOKEN_CACHE_TIME = 300  # 5 minutes
API_KEY_BACKOFF_SECONDS = 1800  # wait 30 minutes before reusing a bad API key
UNAUTHENTICATED_METHODS = {"user.login", "apiinfo.version"}


@dataclass
class ZabbixConfig:
    url: str
    raw: Any


class ZabbixClient:
    def __init__(self) -> None:
        self._cached_token: Optional[str] = None
        self._token_timestamp: float = 0.0
        self._last_api_key_used: Optional[str] = None
        self._failed_api_key: Optional[str] = None
        self._api_key_backoff_until: float = 0.0

    # ------------------------------------------------------------------ #
    # Public helpers                                                     #
    # ------------------------------------------------------------------ #
    @staticmethod
    def normalize_url(url: str) -> str:
        if not url:
            return url
        trimmed = url.strip()
        if trimmed.endswith("/api_jsonrpc.php/"):
            trimmed = trimmed[:-1]
        if not trimmed.endswith("api_jsonrpc.php"):
            suffix = (
                "api_jsonrpc.php"
                if trimmed.endswith("/")
                else "/api_jsonrpc.php"
            )
            trimmed = trimmed + suffix
        return trimmed

    def get_current_config(self) -> ZabbixConfig:
        config = runtime_settings.get_runtime_config()
        base_url = getattr(settings, "ZABBIX_API_URL", "")
        assembled = config.zabbix_api_url or base_url
        url = self.normalize_url(assembled)
        return ZabbixConfig(url=url, raw=config)

    def clear_token_cache(self) -> None:
        self._cached_token = None
        self._token_timestamp = 0.0
        self._last_api_key_used = None
        self._failed_api_key = None
        self._api_key_backoff_until = 0.0

    # ------------------------------------------------------------------ #
    # Authentication                                                     #
    # ------------------------------------------------------------------ #
    def _token_valid(self) -> bool:
        if not self._cached_token:
            return False
        return (time.time() - self._token_timestamp) < TOKEN_CACHE_TIME

    def login(self) -> Optional[str]:
        if self._token_valid():
            return self._cached_token

        config = self.get_current_config().raw
        api_key = (config.zabbix_api_key or "").strip()
        credentials_available = bool(
            (config.zabbix_api_user or "").strip()
            and (config.zabbix_api_password or "").strip()
        )
        now = time.time()

        if api_key:
            skip_api_key = (
                self._failed_api_key
                and api_key == self._failed_api_key
                and now < self._api_key_backoff_until
            )
            if skip_api_key and not credentials_available:
                logger.debug(
                    "Stored API key is in backoff but no fallback credentials "
                    "are configured; reusing key",
                )
                self._failed_api_key = None
                self._api_key_backoff_until = 0.0
                skip_api_key = False

            if skip_api_key:
                logger.debug(
                    "Skipping stored Zabbix API key; backoff ends in %.0fs",
                    self._api_key_backoff_until - now,
                )
            else:
                self._cached_token = api_key
                self._token_timestamp = now
                self._last_api_key_used = api_key
                return api_key

        payload = cast(
            Dict[str, Any],
            {
                "jsonrpc": "2.0",
                "method": "user.login",
                "params": {
                    "username": config.zabbix_api_user,
                    "password": config.zabbix_api_password,
                },
                "id": 1,
            },
        )

        try:
            response = requests.post(
                self.get_current_config().url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            data: Dict[str, Any] = response.json()
        except requests.RequestException as exc:
            logger.warning("Failed to authenticate with Zabbix: %s", exc)
            self._reset_cached_token()
            return None
        except Exception:
            logger.exception(
                "Unexpected error while parsing Zabbix login response"
            )
            self._reset_cached_token()
            return None

        if "error" in data:
            logger.warning("Zabbix login returned error: %s", data["error"])
            self._reset_cached_token()
            return None

        token = data.get("result")
        if token:
            self._cached_token = token
            self._token_timestamp = now
            self._last_api_key_used = None
        return token

    # ------------------------------------------------------------------ #
    # JSON-RPC request                                                   #
    # ------------------------------------------------------------------ #
    def request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        retry_without_auth: bool = False,
        token_retry: bool = False,
    ) -> Optional[Any]:
        read_only = getattr(settings, "ZABBIX_READ_ONLY", True)
        if read_only and method not in READ_ONLY_SAFE_METHODS:
            logger.debug(
                "Blocked potentially unsafe Zabbix method while in READ_ONLY: "
                "%s",
                method,
            )
            return None

        include_auth = method not in UNAUTHENTICATED_METHODS

        token: Optional[str] = None
        if include_auth:
            token = self.login()
            if not token:
                return None

        payload = cast(
            Dict[str, Any],
            {"jsonrpc": "2.0", "method": method, "id": 1},
        )
        if params is not None:
            payload["params"] = params
        if include_auth and not retry_without_auth and token:
            payload["auth"] = token

        headers = {"Content-Type": "application/json"}
        if include_auth and retry_without_auth and token:
            headers["Authorization"] = f"Bearer {token}"

        start_time = time.perf_counter()
        response = None

        try:
            config = self.get_current_config()
            response = requests.post(
                config.url,
                json=payload,
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            data: Dict[str, Any] = response.json()
        except requests.RequestException as exc:
            logger.warning("Zabbix call %s failed: %s", method, exc)
            return None
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            status_code = getattr(response, "status_code", "n/a")
            logger.debug(
                "Zabbix call %s (retry=%s auth=%s) completed in %.1f ms "
                "(status=%s)",
                method,
                retry_without_auth,
                include_auth,
                duration_ms,
                status_code,
            )

        if "error" in data:
            error = data["error"]
            if (
                include_auth
                and not retry_without_auth
                and error.get("code") in (-32602, -32500)
            ):
                logger.debug(
                    "Zabbix call %s returned error code %s; retrying with "
                    "Authorization header",
                    method,
                    error.get("code"),
                )
                return self.request(
                    method,
                    params=params,
                    retry_without_auth=True,
                    token_retry=token_retry,
                )

            error_blob = " ".join(
                part
                for part in [
                    str(error.get("message", "")),
                    str(error.get("data", "")),
                ]
                if part
            ).lower()
            token_expired = (
                "token expired" in error_blob
                or "session terminated" in error_blob
            )

            if include_auth and not token_retry and token_expired:
                logger.info(
                    "Zabbix token expired while calling %s; retrying "
                    "authentication",
                    method,
                )
                self._mark_token_as_expired()
                return self.request(
                    method,
                    params=params,
                    retry_without_auth=False,
                    token_retry=True,
                )

            logger.warning("Zabbix call %s returned error: %s", method, error)
            return None

        return data.get("result")

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    def _reset_cached_token(self) -> None:
        self._cached_token = None
        self._token_timestamp = 0.0
        self._last_api_key_used = None

    def _mark_token_as_expired(self) -> None:
        failed_key = self._last_api_key_used
        self._reset_cached_token()
        if failed_key:
            self._failed_api_key = failed_key
            self._api_key_backoff_until = time.time() + API_KEY_BACKOFF_SECONDS
        else:
            self._failed_api_key = None
            self._api_key_backoff_until = 0.0


client = ZabbixClient()


def normalize_zabbix_url(url: str) -> str:
    return client.normalize_url(url)


def get_current_config() -> Tuple[str, Any]:
    cfg = client.get_current_config()
    return cfg.url, cfg.raw


def clear_token_cache() -> None:
    client.clear_token_cache()


def zabbix_login() -> Optional[str]:
    return client.login()


def zabbix_request(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    retry_without_auth: bool = False,
) -> Optional[Any]:
    return client.request(
        method,
        params=params,
        retry_without_auth=retry_without_auth,
    )


__all__ = [
    "READ_ONLY_SAFE_METHODS",
    "TOKEN_CACHE_TIME",
    "normalize_zabbix_url",
    "get_current_config",
    "clear_token_cache",
    "zabbix_login",
    "zabbix_request",
    "client",
]
