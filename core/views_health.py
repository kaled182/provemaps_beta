import os
import time
import platform
import logging
import shutil
import signal
from contextlib import contextmanager

import django
from django.http import JsonResponse
from django.db import connection
from django.core.cache import caches

logger = logging.getLogger(__name__)


class TimeoutException(Exception):
    pass


@contextmanager
def timeout(seconds):
    """Context manager for timeout handling (Unix/Linux only)"""
    def timeout_handler(signum, frame):
        raise TimeoutException("Operation timed out")
    
    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)


def _storage_check(checks: dict) -> None:
    """Verifica espaço em disco (opcional, não fatal)."""
    try:
        stat = shutil.disk_usage("/")
        free_gb = stat.free / (1024**3)
        checks["storage"] = {
            "ok": free_gb > float(os.getenv("HEALTHCHECK_DISK_THRESHOLD_GB", "1")),
            "free_gb": round(free_gb, 2),
            "threshold_gb": float(os.getenv("HEALTHCHECK_DISK_THRESHOLD_GB", "1")),
        }
    except Exception as e:
        checks["storage"] = {"ok": False, "error": str(e)[:200]}


def _add_system_metrics(checks: dict) -> None:
    """Adiciona métricas do sistema sem afetar o status geral"""
    try:
        import psutil
        checks["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "process_memory_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2)
        }
    except ImportError:
        checks["system"] = {"error": "psutil not available"}
    except Exception as e:
        checks["system"] = {"error": str(e)[:200]}


def healthz(request):
    """
    Comprehensive health check endpoint (/healthz)
    - Checks: DB, Cache, Storage (opcional)
    - Returns: Status, versions, latency, detailed checks
    - HTTP 200 if healthy, 503 if degraded
    """
    started = time.time()
    checks = {}
    debug_mode = os.getenv("HEALTHCHECK_DEBUG", "false").lower() == "true"

    # Database check com timeout
    try:
        db_timeout = int(os.getenv("HEALTHCHECK_DB_TIMEOUT", "5"))
        with connection.cursor() as cursor:
            if platform.system() != "Windows":  # signal.alarm não funciona no Windows
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
    except TimeoutException as e:
        checks["db"] = {"ok": False, "error": "Database query timeout"}
    except Exception as e:
        checks["db"] = {"ok": False, "error": str(e)[:200]}

    # Cache check com chave única e identificação do backend
    try:
        cache = caches["default"]
        probe_key = "healthz_probe_" + str(int(time.time()))
        cache.set(probe_key, "ok", 5)
        checks["cache"] = {
            "ok": (cache.get(probe_key) == "ok"),
            "backend": str(type(cache).__name__)
        }
    except Exception as e:
        checks["cache"] = {"ok": False, "error": str(e)[:200]}

    # Storage check (opcional; controlado por env)
    if os.getenv("HEALTHCHECK_STORAGE", "true").lower() == "true":
        _storage_check(checks)

    # System metrics (opcional)
    if os.getenv("HEALTHCHECK_SYSTEM_METRICS", "false").lower() == "true":
        _add_system_metrics(checks)

    overall_ok = all(v.get("ok") for v in checks.values())
    latency_ms = round((time.time() - started) * 1000, 2)

    # Log somente se degradado ou em modo debug
    if not overall_ok or debug_mode:
        logger.warning(
            "Health check degraded" if not overall_ok else "Health check debug",
            extra={"checks": checks, "latency_ms": latency_ms},
        )

    payload = {
        "status": "ok" if overall_ok else "degraded",
        "timestamp": time.time(),
        "settings": os.getenv("DJANGO_SETTINGS_MODULE", ""),
        "version": os.getenv("APP_VERSION", "dev"),
        "django": django.get_version(),
        "python": platform.python_version(),
        "checks": checks,
        "latency_ms": latency_ms,
    }

    response = JsonResponse(payload, status=200 if overall_ok else 503)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


def healthz_ready(request):
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


def healthz_live(request):
    """
    Liveness probe (/live)
    - Responde 200 se o processo está vivo (sem checar dependências externas).
    """
    response = JsonResponse({"status": "alive"}, status=200)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response