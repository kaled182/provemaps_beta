# pyright: reportConstantRedefinition=false

"""
Resilient Zabbix client with retry, backoff, circuit breaker, and metrics.

Features:
- ✅ Automatic retries with exponential backoff
- ✅ Circuit breaker for consecutive failures
- ✅ Request batching (multiple calls per HTTP request)
- ✅ Prometheus metrics (latency, errors, circuit breaker state)
- ✅ Configurable timeout via environment variable
- ✅ Structured logging
- ✅ Authentication cache (5 minutes)
- ✅ Compatible with API key or username/password

Usage:
    from integrations.zabbix.client import resilient_client

    # Simple call
    hosts = resilient_client.call("host.get", {"output": ["hostid", "name"]})

    # Batching (multiple calls in one request)
    results = resilient_client.batch([
        ("host.get", {"output": ["hostid"]}),
        ("hostgroup.get", {"output": ["groupid"]}),
    ])

    # Check circuit breaker state
    if resilient_client.circuit_breaker.is_open:
        print("Circuit breaker open! Waiting for recovery...")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, cast

import environ  # type: ignore[import]
import requests
from django.conf import settings
from django.core.cache import cache

from setup_app.services import runtime_settings

try:
    from core.metrics_custom import record_zabbix_call as _record_zabbix_call
except Exception:  # pragma: no cover - metrics helper optional at runtime
    _record_zabbix_call = None

logger = logging.getLogger(__name__)

# Initialize environ to read environment variables
env = environ.Env()


def _env_int(name: str, default: int) -> int:
    """Typed helper that retrieves an integer environment value."""
    raw_value: Any = env.int(name, default=default)  # type: ignore[arg-type]
    return cast(int, raw_value)


def _env_float(name: str, default: float) -> float:
    """Typed helper that retrieves a float environment value."""
    raw_value: Any = env.float(name, default=default)  # type: ignore[arg-type]
    return cast(float, raw_value)


# ==============================================================================
# Configuration via environment variables
# ==============================================================================

ZABBIX_REQUEST_TIMEOUT: int = _env_int("ZABBIX_REQUEST_TIMEOUT", 15)
ZABBIX_RETRY_MAX_ATTEMPTS: int = _env_int("ZABBIX_RETRY_MAX_ATTEMPTS", 3)
# Allows developers to clamp retries during investigations
# without changing the source code.
ZABBIX_RETRY_MAX_ATTEMPTS_DEBUG: int = _env_int(
    "ZABBIX_RETRY_MAX_ATTEMPTS_DEBUG",
    0,
)
ZABBIX_RETRY_BACKOFF_FACTOR: float = _env_float(
    "ZABBIX_RETRY_BACKOFF_FACTOR", 2.0
)
ZABBIX_CIRCUIT_BREAKER_THRESHOLD: int = _env_int(
    "ZABBIX_CIRCUIT_BREAKER_THRESHOLD", 5
)
ZABBIX_CIRCUIT_BREAKER_TIMEOUT: int = _env_int(
    "ZABBIX_CIRCUIT_BREAKER_TIMEOUT", 60
)
ZABBIX_BATCH_SIZE: int = _env_int("ZABBIX_BATCH_SIZE", 10)
API_KEY_BACKOFF_SECONDS: int = _env_int("ZABBIX_API_KEY_BACKOFF", 1800)

TOKEN_CACHE_TIME = 300  # 5 minutes
TOKEN_CACHE_KEY = "zabbix_client_resilient_token"
WARNED_MISSING_API_KEY = False

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

UNAUTHENTICATED_METHODS = {"user.login", "apiinfo.version"}


def _sanitize_params(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return params with sensitive keys masked for debug logging."""
    if not isinstance(value, dict):
        return {}
    masked: Dict[str, Any] = {}
    for key, val in value.items():
        if key and key.lower() in {"password", "auth", "token"}:
            masked[key] = "***"
        else:
            masked[key] = val
    return masked


def _is_api_key(token: Optional[str]) -> bool:
    """Check if token is a Zabbix API Key (64 hex chars) vs session token.
    
    Zabbix 7.x+ API Keys are 64-character hex strings that must be sent
    via Authorization: Bearer header, not in the 'auth' field.
    """
    if not token or not isinstance(token, str):
        return False
    # Zabbix API Keys are exactly 64 hex characters
    return len(token) == 64 and all(c in '0123456789abcdef' for c in token.lower())


# ==============================================================================
# Prometheus metrics (with fallback when not installed)
# ==============================================================================

try:
    from prometheus_client import Counter, Gauge, Histogram

    METRICS_ENABLED = True

    zabbix_requests_total = Counter(
        "zabbix_requests_total",
        "Total requests to the Zabbix API",
        ["method", "status"],
    )
    zabbix_request_duration_seconds = Histogram(
        "zabbix_request_duration_seconds",
        "Duration of requests to the Zabbix API",
        ["method"],
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0),
    )
    zabbix_circuit_breaker_state = Gauge(
        "zabbix_circuit_breaker_state",
        "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    )
    zabbix_retry_attempts = Counter(
        "zabbix_retry_attempts_total",
        "Total retry attempts",
        ["method"],
    )
except ImportError:
    METRICS_ENABLED = False
    logger.info(
        "prometheus_client not installed; Zabbix metrics disabled"
    )


# ==============================================================================
# Circuit Breaker
# ==============================================================================


class CircuitState(Enum):
    CLOSED = 0  # Operating normally
    OPEN = 1  # Too many failures, blocking calls
    HALF_OPEN = 2  # Testing recovery


@dataclass
class CircuitBreaker:
    """
    Circuit Breaker to avoid overloading Zabbix when failures occur.

    - CLOSED: Normal operation
    - OPEN: After X consecutive failures, block calls for Y seconds
    - HALF_OPEN: After the timeout, allow a single probe attempt
    """

    failure_threshold: int = ZABBIX_CIRCUIT_BREAKER_THRESHOLD
    timeout: int = ZABBIX_CIRCUIT_BREAKER_TIMEOUT
    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    last_failure_time: float = field(default=0.0)

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def record_success(self) -> None:
        """Reset the circuit breaker after a successful call."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        if METRICS_ENABLED:
            zabbix_circuit_breaker_state.set(CircuitState.CLOSED.value)

    def record_failure(self) -> None:
        """Register a failure and open the circuit when needed."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            if METRICS_ENABLED:
                zabbix_circuit_breaker_state.set(CircuitState.OPEN.value)
            logger.warning(
                "Circuit breaker OPENED after %d consecutive failures",
                self.failure_count,
            )

    def can_attempt(self) -> bool:
        """Return True when a request attempt is allowed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check whether the timeout elapsed to move into half-open
            if (time.time() - self.last_failure_time) >= self.timeout:
                self.state = CircuitState.HALF_OPEN
                if METRICS_ENABLED:
                    zabbix_circuit_breaker_state.set(
                        CircuitState.HALF_OPEN.value
                    )
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False

        # HALF_OPEN: allow a single retry attempt
        return True


# ==============================================================================
# Resilient client
# ==============================================================================


@dataclass
class ZabbixConfig:
    """Zabbix API configuration container."""

    url: str
    user: str
    password: str
    api_key: str


class ResilientZabbixClient:
    """Zabbix client with retry, backoff, circuit breaker, and metrics.

    Features:
    - Automatic retry with exponential backoff
    - Circuit breaker for consecutive failures
    - Request batching
    - Prometheus metrics
    - Authentication cache (5 minutes)
    """

    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self._cached_token: Optional[str] = None
        self._token_timestamp: float = 0.0
        self._last_api_key_used: Optional[str] = None
        self._failed_api_key: Optional[str] = None
        self._api_key_backoff_until: float = 0.0

    # --------------------------------------------------------------------------
    # Configuration and authentication
    # --------------------------------------------------------------------------

    def _get_config(self) -> ZabbixConfig:
        """Return Zabbix configuration from runtime or static settings."""
        config = runtime_settings.get_runtime_config()
        base_url = config.zabbix_api_url or settings.ZABBIX_API_URL
        return ZabbixConfig(
            url=self._normalize_url(base_url),
            user=config.zabbix_api_user or settings.ZABBIX_API_USER,
            password=(
                config.zabbix_api_password or settings.ZABBIX_API_PASSWORD
            ),
            api_key=config.zabbix_api_key or settings.ZABBIX_API_KEY,
        )

    def get_current_config(self) -> ZabbixConfig:
        """Return the current configuration (legacy compatibility)."""
        return self._get_config()

    def normalize_url(self, url: str) -> str:
        """Normalize the URL via the internal helper (public API)."""
        return self._normalize_url(url)

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize the Zabbix API endpoint URL."""
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

    def _get_token(self) -> Optional[str]:
        """Return an authentication token (from cache or login)."""
        config = self._get_config()
        configured_api_key = (config.api_key or "").strip()

        # Check the in-memory cache first
        time_diff = time.time() - self._token_timestamp
        if self._cached_token:
            if configured_api_key and self._cached_token == configured_api_key:
                return self._cached_token
            if time_diff < TOKEN_CACHE_TIME:
                return self._cached_token

        # Attempt to reuse the Django cache
        cached = cache.get(TOKEN_CACHE_KEY)
        if cached:
            self._cached_token = cached
            self._token_timestamp = time.time()
            if configured_api_key and cached == configured_api_key:
                self._last_api_key_used = configured_api_key
            else:
                self._last_api_key_used = None
            return cached

        # Perform login when cache is empty
        api_key = configured_api_key
        credentials_available = bool(
            (config.user or "").strip()
            and (config.password or "").strip()
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
                cache.set(TOKEN_CACHE_KEY, api_key, timeout=None)
                return api_key

        # User/password login fallback
        global WARNED_MISSING_API_KEY
        if (
            not api_key
            and credentials_available
            and not WARNED_MISSING_API_KEY
        ):
            logger.warning(
                "ZABBIX_API_KEY not configured; falling back to user.login "
                "which is slower and less stable",
            )
            WARNED_MISSING_API_KEY = True

        payload: Dict[str, Any] = {}
        payload["jsonrpc"] = "2.0"
        payload["method"] = "user.login"
        payload["params"] = {
            "username": config.user,
            "password": config.password,
        }
        payload["id"] = 1

        try:
            response = requests.post(
                config.url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=ZABBIX_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.error("Zabbix login failed: %s", data["error"])
                return None

            token = data.get("result")
            if token:
                self._cached_token = token
                self._token_timestamp = time.time()
                self._last_api_key_used = None
                cache.set(TOKEN_CACHE_KEY, token, TOKEN_CACHE_TIME)
            return token

        except requests.RequestException as exc:
            logger.error("Zabbix login request failed: %s", exc)
            return None

    def login(self) -> Optional[str]:
        """Compatibility helper returning the current authenticated token."""
        return self._get_token()

    def clear_token_cache(self) -> None:
        """Clear every authentication cache entry."""
        self._cached_token = None
        self._token_timestamp = 0.0
        self._last_api_key_used = None
        self._failed_api_key = None
        self._api_key_backoff_until = 0.0
        cache.delete(TOKEN_CACHE_KEY)

    # --------------------------------------------------------------------------
    # API calls
    # --------------------------------------------------------------------------

    def call(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        retry: bool = True,
    ) -> Optional[Any]:
        """Execute a Zabbix API call with retry and circuit breaker."""
        # Guard read-only deployments
        read_only = getattr(settings, "ZABBIX_READ_ONLY", True)
        if read_only and method not in READ_ONLY_SAFE_METHODS:
            logger.warning(
                "Blocked unsafe method in READ_ONLY mode: %s", method
            )
            return None

        # Circuit breaker guardrail
        if not self.circuit_breaker.can_attempt():
            logger.warning(
                "Circuit breaker OPEN, skipping call to %s", method
            )
            if METRICS_ENABLED:
                zabbix_requests_total.labels(
                    method=method, status="circuit_open"
                ).inc()
            return None

        max_attempts = ZABBIX_RETRY_MAX_ATTEMPTS if retry else 1
        if ZABBIX_RETRY_MAX_ATTEMPTS_DEBUG > 0:
            max_attempts = min(
                max_attempts,
                max(1, ZABBIX_RETRY_MAX_ATTEMPTS_DEBUG),
            )
        if ZABBIX_RETRY_MAX_ATTEMPTS_DEBUG > 0:
            max_attempts = min(
                max_attempts,
                max(1, ZABBIX_RETRY_MAX_ATTEMPTS_DEBUG),
            )

        for attempt in range(1, max_attempts + 1):
            try:
                result = self._execute_request(method, params, attempt)

                # Success resets the circuit breaker
                self.circuit_breaker.record_success()
                if METRICS_ENABLED:
                    zabbix_requests_total.labels(
                        method=method, status="success"
                    ).inc()

                return result

            except requests.RequestException as exc:
                logger.warning(
                    "Zabbix call %s failed (attempt %d/%d): %s",
                    method,
                    attempt,
                    max_attempts,
                    exc,
                )

                if attempt < max_attempts:
                    # Exponential backoff
                    backoff_time = ZABBIX_RETRY_BACKOFF_FACTOR ** (attempt - 1)
                    logger.debug("Retrying in %.1f seconds...", backoff_time)
                    time.sleep(backoff_time)

                    if METRICS_ENABLED:
                        zabbix_retry_attempts.labels(method=method).inc()
                else:
                    # Permanent failure
                    self.circuit_breaker.record_failure()
                    if METRICS_ENABLED:
                        zabbix_requests_total.labels(
                            method=method, status="failure"
                        ).inc()

        return None

    def _execute_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]],
        attempt: int,
        *,
        retry_without_auth: bool = False,
        token_retry: bool = False,
    ) -> Optional[Any]:
        """Execute the HTTP request destined for the Zabbix API."""
        config = self._get_config()

        # Authentication
        include_auth = method not in UNAUTHENTICATED_METHODS
        token = None
        if include_auth:
            token = self._get_token()
            if not token:
                raise requests.RequestException("Failed to obtain auth token")

        # Payload
        payload: Dict[str, Any] = {}
        payload["jsonrpc"] = "2.0"
        payload["method"] = method
        payload["id"] = attempt
        if params is not None:
            payload["params"] = cast(Any, params)
        
        # Detectar se é API Key (Zabbix 7.x) ou session token (Zabbix 6.x)
        use_bearer_header = False
        if include_auth and token:
            if _is_api_key(token) or retry_without_auth:
                # API Keys (Zabbix 7.x+) DEVEM usar Authorization Bearer
                use_bearer_header = True
            else:
                # Session tokens (login tradicional) usam campo 'auth'
                payload["auth"] = token

        headers = {"Content-Type": "application/json"}
        if use_bearer_header:
            headers["Authorization"] = f"Bearer {token}"

        # Metrics: start timer
        start_time = time.perf_counter()

        try:
            response = requests.post(
                config.url,
                json=payload,
                headers=headers,
                timeout=ZABBIX_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = cast(Dict[str, Any], response.json())
        except requests.RequestException as exc:
            duration_seconds = time.perf_counter() - start_time
            if METRICS_ENABLED:
                zabbix_request_duration_seconds.labels(
                    method=method
                ).observe(duration_seconds)

            logger.debug(
                "Zabbix call %s (attempt %d) completed in %.3f seconds",
                method,
                attempt,
                duration_seconds,
            )

            if _record_zabbix_call:
                _record_zabbix_call(
                    method,
                    duration_seconds,
                    False,
                    error_type=exc.__class__.__name__,
                )
            raise
        else:
            duration_seconds = time.perf_counter() - start_time
            if METRICS_ENABLED:
                zabbix_request_duration_seconds.labels(
                    method=method
                ).observe(duration_seconds)

            logger.debug(
                "Zabbix call %s (attempt %d) completed in %.3f seconds",
                method,
                attempt,
                duration_seconds,
            )

    # Inspect Zabbix error responses
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
                return self._execute_request(
                    method,
                    params,
                    attempt,
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
                return self._execute_request(
                    method,
                    params,
                    attempt,
                    retry_without_auth=False,
                    token_retry=True,
                )

            if error.get("code") in (-32602, -32500) or token_expired:
                logger.error(
                    "Zabbix session issue for %s (attempt %d): %s",
                    method,
                    attempt,
                    error,
                )
                logger.error(
                    "Zabbix session context params=%s include_auth=%s "
                    "retry_without_auth=%s token_retry=%s",
                    _sanitize_params(params),
                    include_auth,
                    retry_without_auth,
                    token_retry,
                )
            else:
                logger.warning("Zabbix API error for %s: %s", method, error)
            if error.get("code") in (-32602, -32500):
                self.clear_token_cache()
            if _record_zabbix_call:
                error_code = error.get("code")
                coded = (
                    f"zabbix_error_{error_code}"
                    if error_code is not None
                    else "zabbix_error"
                )
                _record_zabbix_call(
                    method,
                    duration_seconds,
                    False,
                    error_type=coded,
                )
            return None

        if _record_zabbix_call:
            _record_zabbix_call(
                method,
                duration_seconds,
                True,
                error_type=None,
            )
        return data.get("result")

    # --------------------------------------------------------------------------
    # Batching
    # --------------------------------------------------------------------------

    def batch(
        self,
        calls: List[Tuple[str, Optional[Dict[str, Any]]]],
        retry: bool = True,
    ) -> List[Optional[Any]]:
        """Execute multiple calls within a single HTTP request.

        Args:
            calls: List of tuples ``(method, params)``
            retry: When True, retry automatically on failures

        Returns:
            List of results in the same order as the provided calls.

        Example:
            results = client.batch([
                ("host.get", {"output": ["hostid"]}),
                ("hostgroup.get", {"output": ["groupid"]}),
            ])
        """
        if not calls:
            return []

        # Split into smaller chunks when exceeding the maximum size
        if len(calls) > ZABBIX_BATCH_SIZE:
            logger.debug(
                "Batching %d calls in chunks of %d",
                len(calls),
                ZABBIX_BATCH_SIZE,
            )
            results: List[Optional[Any]] = []
            for i in range(0, len(calls), ZABBIX_BATCH_SIZE):
                chunk = calls[i:i + ZABBIX_BATCH_SIZE]
                results.extend(self.batch(chunk, retry=retry))
            return results

    # Circuit breaker guardrail for batches
        if not self.circuit_breaker.can_attempt():
            logger.warning("Circuit breaker OPEN, skipping batch call")
            return [None] * len(calls)

        max_attempts = ZABBIX_RETRY_MAX_ATTEMPTS if retry else 1

        for attempt in range(1, max_attempts + 1):
            try:
                results = self._execute_batch(calls, attempt)
                self.circuit_breaker.record_success()
                if METRICS_ENABLED:
                    zabbix_requests_total.labels(
                        method="batch", status="success"
                    ).inc()
                return results

            except requests.RequestException as exc:
                logger.warning(
                    "Batch call failed (attempt %d/%d): %s",
                    attempt,
                    max_attempts,
                    exc,
                )

                if attempt < max_attempts:
                    backoff_time = ZABBIX_RETRY_BACKOFF_FACTOR ** (attempt - 1)
                    time.sleep(backoff_time)
                else:
                    self.circuit_breaker.record_failure()
                    if METRICS_ENABLED:
                        zabbix_requests_total.labels(
                            method="batch", status="failure"
                        ).inc()

        return [None] * len(calls)

    def _execute_batch(
        self,
        calls: List[Tuple[str, Optional[Dict[str, Any]]]],
        attempt: int,
    ) -> List[Optional[Any]]:
        """Execute a batch of requests."""
        config = self._get_config()
        token = self._get_token()

    # Build individual payloads
        # Note: Batch API no Zabbix ainda usa 'auth' field mesmo com API Keys
        # pois o header Authorization não é suportado em requests batch
        payloads: List[Dict[str, Any]] = []
        for idx, (method, params) in enumerate(calls):
            payload: Dict[str, Any] = {
                "jsonrpc": "2.0",
                "method": method,
                "id": idx + 1,
            }
            if params is not None:
                payload["params"] = cast(Any, params)
            if method not in UNAUTHENTICATED_METHODS and token:
                # Batch ainda usa auth field (limitação do Zabbix batch API)
                payload["auth"] = token
            payloads.append(payload)

        start_time = time.perf_counter()

        raw_data: Any
        try:
            # Zabbix supports batches by sending an array of payloads
            batch_timeout = ZABBIX_REQUEST_TIMEOUT * 2
            response = requests.post(
                config.url,
                json=payloads,
                headers={"Content-Type": "application/json"},
                timeout=batch_timeout,
            )
            response.raise_for_status()
            raw_data = response.json()

        finally:
            duration_seconds = time.perf_counter() - start_time
            if METRICS_ENABLED:
                zabbix_request_duration_seconds.labels(
                    method="batch"
                ).observe(duration_seconds)

            logger.debug(
                "Batch call with %d requests (attempt %d) completed in %.3f "
                "seconds",
                len(calls),
                attempt,
                duration_seconds,
            )

        # Process results
        if not isinstance(raw_data, list):
            logger.error(
                "Batch response is not a list: %s",
                type(raw_data).__name__,
            )
            return [None] * len(calls)

        data_list = cast(List[Dict[str, Any]], raw_data)

        results: List[Optional[Any]] = []
        for data in data_list:
            if "error" in data:
                error_blob = " ".join(
                    part
                    for part in [
                        str(data["error"].get("message", "")),
                        str(data["error"].get("data", "")),
                    ]
                    if part
                ).lower()
                if (
                    "token expired" in error_blob
                    or "session terminated" in error_blob
                ):
                    self._mark_token_as_expired()
                    raise requests.RequestException(
                        "Token expired during batch"
                    )
                logger.warning("Batch item error: %s", data["error"])
                results.append(None)
            else:
                results.append(data.get("result"))

        return results

    # --------------------------------------------------------------------------
    # Utilities
    # --------------------------------------------------------------------------

    def reset_circuit_breaker(self) -> None:
        """Manually reset the circuit breaker (handy for tests)."""
        self.circuit_breaker.record_success()
        logger.info("Circuit breaker manually reset")

    def get_metrics(self) -> Dict[str, Any]:
        """Return the current client metrics snapshot."""
        return {
            "circuit_breaker_state": self.circuit_breaker.state.name,
            "circuit_breaker_failure_count": (
                self.circuit_breaker.failure_count
            ),
            "token_cached": self._cached_token is not None,
            "failed_api_key": self._failed_api_key,
            "api_key_backoff_seconds_remaining": max(
                0.0,
                self._api_key_backoff_until - time.time(),
            ),
            "metrics_enabled": METRICS_ENABLED,
            "config": {
                "timeout": ZABBIX_REQUEST_TIMEOUT,
                "max_attempts": ZABBIX_RETRY_MAX_ATTEMPTS,
                "backoff_factor": ZABBIX_RETRY_BACKOFF_FACTOR,
                "circuit_breaker_threshold": ZABBIX_CIRCUIT_BREAKER_THRESHOLD,
                "circuit_breaker_timeout": ZABBIX_CIRCUIT_BREAKER_TIMEOUT,
                "batch_size": ZABBIX_BATCH_SIZE,
                "api_key_backoff": API_KEY_BACKOFF_SECONDS,
            },
        }

    def _reset_cached_token(self) -> None:
        self._cached_token = None
        self._token_timestamp = 0.0
        self._last_api_key_used = None

    def _mark_token_as_expired(self) -> None:
        failed_key = self._last_api_key_used
        configured_api_key = (self._get_config().api_key or "").strip()

        if (
            failed_key
            and configured_api_key
            and failed_key == configured_api_key
        ):
            self._cached_token = configured_api_key
            self._token_timestamp = time.time()
            self._last_api_key_used = configured_api_key
            self._failed_api_key = None
            self._api_key_backoff_until = 0.0
            cache.set(TOKEN_CACHE_KEY, configured_api_key, timeout=None)
            logger.debug(
                "Preserved configured Zabbix API key after expiry notice"
            )
            return

        self._reset_cached_token()
        cache.delete(TOKEN_CACHE_KEY)
        if failed_key:
            self._failed_api_key = failed_key
            self._api_key_backoff_until = (
                time.time() + API_KEY_BACKOFF_SECONDS
            )
            logger.debug(
                "Applied backoff to Zabbix API key; retry after %.0fs",
                API_KEY_BACKOFF_SECONDS,
            )
        else:
            self._failed_api_key = None
            self._api_key_backoff_until = 0.0
            logger.debug("Cleared cached Zabbix token without API key backoff")


# ==============================================================================
# Global singleton instance
# ==============================================================================

resilient_client = ResilientZabbixClient()


# ==============================================================================
# Convenience functions (legacy compatibility)
# ==============================================================================


def zabbix_call(
    method: str, params: Optional[Dict[str, Any]] = None
) -> Optional[Any]:
    """Wrapper around a single Zabbix API call."""
    return resilient_client.call(method, params)


def zabbix_batch(
    calls: List[Tuple[str, Optional[Dict[str, Any]]]]
) -> List[Optional[Any]]:
    """Wrapper around batching multiple Zabbix API calls."""
    return resilient_client.batch(calls)


__all__ = [
    "ResilientZabbixClient",
    "resilient_client",
    "zabbix_call",
    "zabbix_batch",
    "CircuitState",
]
