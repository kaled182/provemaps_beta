import os
import time
import platform
import logging
import shutil
from contextlib import contextmanager
from typing import Any, Dict

import django
from django.http import JsonResponse
from django.db import connection
from django.core.cache import caches

logger = logging.getLogger(__name__)


class TimeoutException(Exception):
    pass


@contextmanager
def timeout(seconds: int):
    """No-op de timeout (placeholder)."""
    yield


def _storage_check(checks: Dict[str, Any]) -> None:
    """Verifica espaço em disco (opcional, não fatal)."""
    try:
        stat = shutil.disk_usage("/")
        free_gb = stat.free / (1024**3)
        threshold = float(os.getenv("HEALTHCHECK_DISK_THRESHOLD_GB", "1"))
        checks["storage"] = {
            "ok": free_gb > threshold,
            "free_gb": round(free_gb, 2),
            "threshold_gb": threshold,
        }
    except Exception as e:
        checks["storage"] = {"ok": False, "error": str(e)[:200]}


def _add_system_metrics(checks: Dict[str, Any]) -> None:
    """Adiciona métricas do sistema sem afetar o status geral"""
    try:
        import psutil
        checks["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "process_memory_mb": round(
                psutil.Process().memory_info().rss / 1024 / 1024, 2
            ),
        }
    except ImportError:
        checks["system"] = {"error": "psutil not available"}
    except Exception as e:
        checks["system"] = {"error": str(e)[:200]}


from django.http import HttpRequest


def healthz(request: HttpRequest):
    """
    Comprehensive health check endpoint (/healthz)
    - Checks: DB, Cache, Storage (opcional)
    - Returns: Status, versions, latency, detailed checks
    - HTTP 200 if healthy, 503 if degraded
    """
    started = time.time()
    checks: Dict[str, Any] = {}
    debug_mode = os.getenv("HEALTHCHECK_DEBUG", "false").lower() == "true"
    strict_mode = os.getenv("HEALTHCHECK_STRICT", "true").lower() == "true"
    ignore_cache = os.getenv(
        "HEALTHCHECK_IGNORE_CACHE", "false"
    ).lower() == "true"

    # Database check com timeout
    try:
        db_timeout = int(os.getenv("HEALTHCHECK_DB_TIMEOUT", "5"))
        with connection.cursor() as cursor:
            if platform.system() != "Windows":  # ambiente não-Windows
                with timeout(db_timeout):
                    cursor.execute("SELECT 1")
                    row = cursor.fetchone()
            else:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
        
        checks["db"] = {
            "ok": bool(row and (row[0] == 1)),
            "type": connection.vendor,  # postgresql, mysql, etc
            "timeout_seconds": db_timeout,
        }
    except TimeoutException:
        checks["db"] = {"ok": False, "error": "Database query timeout"}
    except Exception as e:
        checks["db"] = {"ok": False, "error": str(e)[:200]}

    # Cache check com chave única e identificação do backend
    try:
        if ignore_cache:
            checks["cache"] = {
                "ok": True,
                "ignored": True,
                "reason": "ignored by HEALTHCHECK_IGNORE_CACHE",
            }
        else:
            cache = caches["default"]
            probe_key = "healthz_probe_" + str(int(time.time()))
            cache.set(probe_key, "ok", 5)
            checks["cache"] = {
                "ok": (cache.get(probe_key) == "ok"),
                "backend": str(type(cache).__name__),
                "ignored": False,
            }
    except Exception as e:
        if ignore_cache:
            checks["cache"] = {
                "ok": True,
                "ignored": True,
                "error": str(e)[:200],
                "reason": "exception but ignored",
            }
        else:
            checks["cache"] = {"ok": False, "error": str(e)[:200]}

    # Storage check (opcional; controlado por env)
    if os.getenv("HEALTHCHECK_STORAGE", "true").lower() == "true":
        _storage_check(checks)

    # System metrics (opcional)
    if os.getenv("HEALTHCHECK_SYSTEM_METRICS", "false").lower() == "true":
        _add_system_metrics(checks)

    if strict_mode:
        overall_ok = all(v.get("ok") for v in checks.values())
    else:
        # Em modo não estrito consideramos apenas DB crítico
        overall_ok = checks.get("db", {}).get("ok", False)
    latency_ms = round((time.time() - started) * 1000, 2)

    # Log somente se degradado ou em modo debug
    if not overall_ok or debug_mode:
        msg = (
            "Health check degraded"
            if not overall_ok
            else "Health check debug"
        )
        logger.warning(msg, extra={"checks": checks, "latency_ms": latency_ms})

    payload: Dict[str, Any] = {
        "status": "ok" if overall_ok else "degraded",
        "timestamp": time.time(),
        "settings": os.getenv("DJANGO_SETTINGS_MODULE", ""),
        "version": os.getenv("APP_VERSION", "dev"),
        "django": django.get_version(),
        "python": platform.python_version(),
        "checks": checks,
        "latency_ms": latency_ms,
        "strict_mode": strict_mode,
        "ignore_cache": ignore_cache,
    }

    response = JsonResponse(payload, status=200 if overall_ok else 503)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


def healthz_ready(request: HttpRequest):
    """
    Readiness probe (/ready)
    - Verificação leve de conectividade com DB (sem payloads pesados).
    - Retorna 200 quando a app está pronta para receber tráfego.
    """
    started = time.time()
    db_ok = True
    try:
        db_timeout = int(os.getenv("HEALTHCHECK_DB_TIMEOUT", "5"))
        with connection.cursor() as cursor:
            if platform.system() != "Windows":
                with timeout(db_timeout):
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            else:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except TimeoutException:
        db_ok = False
    except Exception:
        db_ok = False

    status_code = 200 if db_ok else 503
    response = JsonResponse(
        {
            "status": "ready" if db_ok else "not_ready",
            "timestamp": time.time(),
            "check": "ready",
            "db_connected": db_ok,
            "latency_ms": round((time.time() - started) * 1000, 2),
        },
        status=status_code,
    )
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


def healthz_live(request: HttpRequest):
    """
    Liveness probe (/live)
    - Responde 200 se o processo está vivo (sem checar dependências externas).
    """
    response = JsonResponse({"status": "alive"}, status=200)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


def celery_status(request: HttpRequest):
    """Endpoint de status do Celery (/celery/status)
    - Dispara a task get_queue_stats
    - Timeout curto (default 3s via env CELERY_STATUS_TIMEOUT)
    - Resposta sempre JSON com status geral
    """
    started = time.time()
    timeout_seconds = float(os.getenv("CELERY_STATUS_TIMEOUT", "3"))
    ping_timeout = float(os.getenv("CELERY_PING_TIMEOUT", "2"))
    payload: dict[str, Any] = {
        "timestamp": time.time(),
        "latency_ms": None,
        "status": "degraded",  # assume degradado até provar o contrário
        "worker": {
            "available": False,
            "error": None,
            "stats": None,
        },
    }

    try:
        from core.celery import get_queue_stats  # type: ignore
    except Exception as e:  # pragma: no cover
        payload["worker"]["error"] = f"ImportError: {e}"[:200]
        payload["latency_ms"] = round((time.time() - started) * 1000, 2)
        return JsonResponse(payload, status=503)

    # Primeiro faz ping leve para não degradar por timeout de estatísticas
    ping_ok = False
    try:
        from core.celery import ping  # type: ignore
        pong_res = ping.delay()  # type: ignore[attr-defined]
        pong_val = pong_res.get(timeout=ping_timeout)
        ping_ok = pong_val == "pong"
    except Exception as e:  # pragma: no cover
        payload["worker"]["error"] = f"PingError: {e}"[:200]

    # Se ping funcionou, tenta estatísticas com timeout maior sem falhar o status geral
    stats_error = None
    stats = None
    if ping_ok:
        try:
            async_res = get_queue_stats.delay()  # type: ignore[attr-defined]
            stats = async_res.get(timeout=timeout_seconds)
        except Exception as e:  # pragma: no cover
            stats_error = str(e)[:200]

    payload["worker"]["available"] = ping_ok
    if stats is not None:
        payload["worker"]["stats"] = stats
    if stats_error and not payload["worker"].get("error"):
        payload["worker"]["error"] = stats_error

    # Define status final
    if ping_ok and isinstance(stats, dict) and (stats is None or "error" not in stats):
        payload["status"] = "ok"
    elif ping_ok:
        # Worker responde mas estatísticas falharam
        payload["status"] = "degraded"
    else:
        payload["status"] = "degraded"

    payload["latency_ms"] = round((time.time() - started) * 1000, 2)

    # Atualiza métricas Prometheus (silencioso em caso de erro ou se desabilitado)
    try:  # pragma: no cover - defensivo
        from core.metrics_celery import update_metrics  # type: ignore
        update_metrics(payload)
    except Exception:
        pass

    code = 200 if payload["status"] == "ok" else 503
    response = JsonResponse(payload, status=code)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response
