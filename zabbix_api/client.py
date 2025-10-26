"""
Cliente Zabbix Resiliente com Retry, Backoff, Circuit Breaker e Métricas.

Features:
- ✅ Retry automático com exponential backoff
- ✅ Circuit breaker para falhas consecutivas
- ✅ Batching de requests (múltiplas chamadas em uma única requisição)
- ✅ Métricas Prometheus (latência, erros, circuit breaker state)
- ✅ Timeout configurável por variável de ambiente
- ✅ Logging estruturado
- ✅ Cache de autenticação (5 min)
- ✅ Compatível com API key ou username/password

Usage:
    from zabbix_api.client import resilient_client

    # Chamada simples
    hosts = resilient_client.call("host.get", {"output": ["hostid", "name"]})

    # Batching (múltiplas chamadas em uma requisição)
    results = resilient_client.batch([
        ("host.get", {"output": ["hostid"]}),
        ("hostgroup.get", {"output": ["groupid"]}),
    ])

    # Verificar estado do circuit breaker
    if resilient_client.circuit_breaker.is_open:
        print("Circuit breaker aberto! Aguardando recuperação...")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import environ
import requests
from django.conf import settings
from django.core.cache import cache

from setup_app.services import runtime_settings

logger = logging.getLogger(__name__)

# Inicializa environ para ler variáveis
env = environ.Env()

# ==============================================================================
# Configuração via variáveis de ambiente
# ==============================================================================

ZABBIX_REQUEST_TIMEOUT = env.int("ZABBIX_REQUEST_TIMEOUT", default=15)
ZABBIX_RETRY_MAX_ATTEMPTS = env.int("ZABBIX_RETRY_MAX_ATTEMPTS", default=3)
ZABBIX_RETRY_BACKOFF_FACTOR = env.float(
    "ZABBIX_RETRY_BACKOFF_FACTOR", default=2.0
)
ZABBIX_CIRCUIT_BREAKER_THRESHOLD = env.int(
    "ZABBIX_CIRCUIT_BREAKER_THRESHOLD", default=5
)
ZABBIX_CIRCUIT_BREAKER_TIMEOUT = env.int(
    "ZABBIX_CIRCUIT_BREAKER_TIMEOUT", default=60
)
ZABBIX_BATCH_SIZE = env.int("ZABBIX_BATCH_SIZE", default=10)

TOKEN_CACHE_TIME = 300  # 5 minutos
TOKEN_CACHE_KEY = "zabbix_client_resilient_token"

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

# ==============================================================================
# Métricas Prometheus (com fallback se não instalado)
# ==============================================================================

try:
    from prometheus_client import Counter, Gauge, Histogram

    METRICS_ENABLED = True

    zabbix_requests_total = Counter(
        "zabbix_requests_total",
        "Total de requisições ao Zabbix API",
        ["method", "status"],
    )
    zabbix_request_duration_seconds = Histogram(
        "zabbix_request_duration_seconds",
        "Duração das requisições ao Zabbix API",
        ["method"],
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0),
    )
    zabbix_circuit_breaker_state = Gauge(
        "zabbix_circuit_breaker_state",
        "Estado do circuit breaker (0=closed, 1=open, 2=half_open)",
    )
    zabbix_retry_attempts = Counter(
        "zabbix_retry_attempts_total",
        "Total de tentativas de retry",
        ["method"],
    )
except ImportError:
    METRICS_ENABLED = False
    logger.info(
        "prometheus_client não instalado; métricas Zabbix desabilitadas"
    )


# ==============================================================================
# Circuit Breaker
# ==============================================================================


class CircuitState(Enum):
    CLOSED = 0  # Funcionando normalmente
    OPEN = 1  # Muitas falhas, bloqueando chamadas
    HALF_OPEN = 2  # Testando recuperação


@dataclass
class CircuitBreaker:
    """
    Circuit Breaker para evitar sobrecarga do Zabbix em caso de falhas.

    - CLOSED: Funcionamento normal
    - OPEN: Após X falhas consecutivas, bloqueia chamadas por Y segundos
    - HALF_OPEN: Após timeout, permite 1 tentativa de teste
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
        """Reseta circuit breaker após sucesso."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        if METRICS_ENABLED:
            zabbix_circuit_breaker_state.set(CircuitState.CLOSED.value)

    def record_failure(self) -> None:
        """Registra falha e abre circuit se necessário."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            if METRICS_ENABLED:
                zabbix_circuit_breaker_state.set(CircuitState.OPEN.value)
            logger.warning(
                "Circuit breaker OPENED após %d falhas consecutivas",
                self.failure_count,
            )

    def can_attempt(self) -> bool:
        """Verifica se pode tentar chamada."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Verifica se passou o timeout para tentar half-open
            if (time.time() - self.last_failure_time) >= self.timeout:
                self.state = CircuitState.HALF_OPEN
                if METRICS_ENABLED:
                    zabbix_circuit_breaker_state.set(
                        CircuitState.HALF_OPEN.value
                    )
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False

        # HALF_OPEN: permite 1 tentativa
        return True


# ==============================================================================
# Cliente Resiliente
# ==============================================================================


@dataclass
class ZabbixConfig:
    """Configuração do Zabbix API."""

    url: str
    user: str
    password: str
    api_key: str


class ResilientZabbixClient:
    """
    Cliente Zabbix com retry, backoff, circuit breaker e métricas.

    Features:
    - Retry automático com exponential backoff
    - Circuit breaker para falhas consecutivas
    - Batching de requests
    - Métricas Prometheus
    - Cache de autenticação (5 min)
    """

    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self._cached_token: Optional[str] = None
        self._token_timestamp: float = 0.0

    # --------------------------------------------------------------------------
    # Configuração e Autenticação
    # --------------------------------------------------------------------------

    def _get_config(self) -> ZabbixConfig:
        """Obtém configuração do Zabbix (runtime ou settings)."""
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

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normaliza URL do Zabbix API."""
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
        """Obtém token de autenticação (cache ou login)."""
        # Verifica cache em memória
        time_diff = time.time() - self._token_timestamp
        if self._cached_token and time_diff < TOKEN_CACHE_TIME:
            return self._cached_token

        # Tenta cache do Django
        cached = cache.get(TOKEN_CACHE_KEY)
        if cached:
            self._cached_token = cached
            self._token_timestamp = time.time()
            return cached

        # Faz login
        config = self._get_config()

        # Se tiver API key, usa diretamente
        if config.api_key:
            self._cached_token = config.api_key
            self._token_timestamp = time.time()
            cache.set(TOKEN_CACHE_KEY, config.api_key, TOKEN_CACHE_TIME)
            return config.api_key

        # Login com user/password
        payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {"username": config.user, "password": config.password},
            "id": 1,
        }

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
                cache.set(TOKEN_CACHE_KEY, token, TOKEN_CACHE_TIME)
            return token

        except requests.RequestException as exc:
            logger.error("Zabbix login request failed: %s", exc)
            return None

    def clear_token_cache(self) -> None:
        """Limpa cache de autenticação."""
        self._cached_token = None
        self._token_timestamp = 0.0
        cache.delete(TOKEN_CACHE_KEY)

    # --------------------------------------------------------------------------
    # Chamadas API
    # --------------------------------------------------------------------------

    def call(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        retry: bool = True,
    ) -> Optional[Any]:
        """
        Executa chamada ao Zabbix API com retry e circuit breaker.

        Args:
            method: Método da API (ex: "host.get")
            params: Parâmetros da chamada
            retry: Se True, faz retry automático em caso de falha

        Returns:
            Resultado da API ou None em caso de erro
        """
        # Verifica READ_ONLY
        read_only = getattr(settings, "ZABBIX_READ_ONLY", True)
        if read_only and method not in READ_ONLY_SAFE_METHODS:
            logger.warning(
                "Blocked unsafe method in READ_ONLY mode: %s", method
            )
            return None

        # Verifica circuit breaker
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

        for attempt in range(1, max_attempts + 1):
            try:
                result = self._execute_request(method, params, attempt)

                # Sucesso: reseta circuit breaker
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
                    # Falha definitiva
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
    ) -> Optional[Any]:
        """Executa requisição HTTP ao Zabbix API."""
        config = self._get_config()

        # Autenticação
        include_auth = method not in UNAUTHENTICATED_METHODS
        token = None
        if include_auth:
            token = self._get_token()
            if not token:
                raise requests.RequestException("Failed to obtain auth token")

        # Payload
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "id": attempt,
        }
        if params is not None:
            payload["params"] = params
        if include_auth and token:
            payload["auth"] = token

        headers = {"Content-Type": "application/json"}

        # Métricas: início
        start_time = time.perf_counter()

        try:
            response = requests.post(
                config.url,
                json=payload,
                headers=headers,
                timeout=ZABBIX_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

        finally:
            # Métricas: fim
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

        # Verifica erros do Zabbix
        if "error" in data:
            error = data["error"]
            logger.warning("Zabbix API error for %s: %s", method, error)
            # Limpa cache de token se erro de autenticação
            if error.get("code") in (-32602, -32500):
                self.clear_token_cache()
            return None

        return data.get("result")

    # --------------------------------------------------------------------------
    # Batching
    # --------------------------------------------------------------------------

    def batch(
        self,
        calls: List[Tuple[str, Optional[Dict[str, Any]]]],
        retry: bool = True,
    ) -> List[Optional[Any]]:
        """
        Executa múltiplas chamadas em uma única requisição HTTP.

        Args:
            calls: Lista de tuplas (method, params)
            retry: Se True, faz retry automático em caso de falha

        Returns:
            Lista de resultados (mesma ordem das chamadas)

        Example:
            results = client.batch([
                ("host.get", {"output": ["hostid"]}),
                ("hostgroup.get", {"output": ["groupid"]}),
            ])
        """
        if not calls:
            return []

        # Divide em chunks se exceder tamanho máximo
        if len(calls) > ZABBIX_BATCH_SIZE:
            logger.debug(
                "Batching %d calls in chunks of %d",
                len(calls),
                ZABBIX_BATCH_SIZE,
            )
            results = []
            for i in range(0, len(calls), ZABBIX_BATCH_SIZE):
                chunk = calls[i:i + ZABBIX_BATCH_SIZE]
                results.extend(self.batch(chunk, retry=retry))
            return results

        # Verifica circuit breaker
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
        """Executa batch de requisições."""
        config = self._get_config()
        token = self._get_token()

        # Monta payloads individuais
        payloads = []
        for idx, (method, params) in enumerate(calls):
            payload: Dict[str, Any] = {
                "jsonrpc": "2.0",
                "method": method,
                "id": idx + 1,
            }
            if params is not None:
                payload["params"] = params
            if method not in UNAUTHENTICATED_METHODS and token:
                payload["auth"] = token
            payloads.append(payload)

        start_time = time.perf_counter()

        try:
            # Zabbix suporta batch enviando array de payloads
            batch_timeout = ZABBIX_REQUEST_TIMEOUT * 2
            response = requests.post(
                config.url,
                json=payloads,
                headers={"Content-Type": "application/json"},
                timeout=batch_timeout,
            )
            response.raise_for_status()
            data_list = response.json()

        finally:
            duration_seconds = time.perf_counter() - start_time
            if METRICS_ENABLED:
                zabbix_request_duration_seconds.labels(
                    method="batch"
                ).observe(duration_seconds)

            logger.debug(
                "Batch call with %d requests (attempt %d) completed in %.3f seconds",
                len(calls),
                attempt,
                duration_seconds,
            )

        # Processa resultados
        if not isinstance(data_list, list):
            logger.error("Batch response não é lista: %s", type(data_list))
            return [None] * len(calls)

        results = []
        for data in data_list:
            if "error" in data:
                logger.warning("Batch item error: %s", data["error"])
                results.append(None)
            else:
                results.append(data.get("result"))

        return results

    # --------------------------------------------------------------------------
    # Utilitários
    # --------------------------------------------------------------------------

    def reset_circuit_breaker(self) -> None:
        """Reseta circuit breaker manualmente (útil para testes)."""
        self.circuit_breaker.record_success()
        logger.info("Circuit breaker resetado manualmente")

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas atuais do cliente."""
        return {
            "circuit_breaker_state": self.circuit_breaker.state.name,
            "circuit_breaker_failure_count": self.circuit_breaker.failure_count,
            "token_cached": self._cached_token is not None,
            "metrics_enabled": METRICS_ENABLED,
            "config": {
                "timeout": ZABBIX_REQUEST_TIMEOUT,
                "max_attempts": ZABBIX_RETRY_MAX_ATTEMPTS,
                "backoff_factor": ZABBIX_RETRY_BACKOFF_FACTOR,
                "circuit_breaker_threshold": ZABBIX_CIRCUIT_BREAKER_THRESHOLD,
                "circuit_breaker_timeout": ZABBIX_CIRCUIT_BREAKER_TIMEOUT,
                "batch_size": ZABBIX_BATCH_SIZE,
            },
        }


# ==============================================================================
# Instância global (singleton)
# ==============================================================================

resilient_client = ResilientZabbixClient()


# ==============================================================================
# Funções de conveniência (compatibilidade com código existente)
# ==============================================================================


def zabbix_call(method: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """Wrapper para chamada simples ao Zabbix API."""
    return resilient_client.call(method, params)


def zabbix_batch(calls: List[Tuple[str, Optional[Dict[str, Any]]]]) -> List[Optional[Any]]:
    """Wrapper para batch de chamadas ao Zabbix API."""
    return resilient_client.batch(calls)


__all__ = [
    "ResilientZabbixClient",
    "resilient_client",
    "zabbix_call",
    "zabbix_batch",
    "CircuitState",
]
