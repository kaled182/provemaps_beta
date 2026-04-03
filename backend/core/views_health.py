import logging
import os
import platform
import shutil
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict

import django
from django.core.cache import caches
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import cache_page

logger = logging.getLogger(__name__)


class TimeoutException(Exception):
    """Raised when the timed context exceeds the configured limit."""


@contextmanager
def timeout(seconds: int):
    """
    Abort the wrapped operation after ``seconds`` on Unix platforms.

    Windows lacks ``SIGALRM`` support, so the context becomes a no-op in that
    environment and relies on external safeguards.
    """

    if seconds <= 0 or platform.system() == "Windows":
        yield
        return

    import signal

    def _raise_timeout(signum, frame):  # pragma: no cover
        raise TimeoutException(f"Operation timed out after {seconds} seconds")

    previous_handler = signal.signal(signal.SIGALRM, _raise_timeout)
    try:
        # Use ``ITIMER_REAL`` so the timer is cancelled once the context exits
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        # Cancel the timer and restore the original handler
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def _storage_check(checks: Dict[str, Any]) -> None:
    """Add disk usage information to the health payload."""

    try:
        stat = shutil.disk_usage("/")
        free_gb = stat.free / (1024**3)
        threshold = float(os.getenv("HEALTHCHECK_DISK_THRESHOLD_GB", "1"))
        checks["storage"] = {
            "ok": free_gb > threshold,
            "free_gb": round(free_gb, 2),
            "threshold_gb": threshold,
        }
    except Exception as exc:  # pragma: no cover - defensive
        checks["storage"] = {"ok": False, "error": str(exc)[:200]}


def _add_system_metrics(checks: Dict[str, Any]) -> None:
    """Collect lightweight system metrics without affecting the result."""

    try:
        import psutil  # type: ignore

        checks["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "process_memory_mb": round(
                psutil.Process().memory_info().rss / 1024 / 1024, 2
            ),
        }
    except ImportError:
        checks["system"] = {"error": "psutil not available"}
    except Exception as exc:  # pragma: no cover - defensive
        checks["system"] = {"error": str(exc)[:200]}


def healthz(request: HttpRequest):
    """
    Comprehensive health check endpoint (/healthz).

    Provides DB, cache, and optional storage/system metrics along with
    application metadata. Returns HTTP 200 when all critical checks pass and
    503 otherwise.
    """

    started = time.time()
    checks: Dict[str, Any] = {}
    debug_mode = os.getenv("HEALTHCHECK_DEBUG", "false").lower() == "true"
    strict_mode = os.getenv("HEALTHCHECK_STRICT", "true").lower() == "true"
    ignore_cache = os.getenv(
        "HEALTHCHECK_IGNORE_CACHE", "false"
    ).lower() == "true"

    # Database connectivity check with optional timeout
    try:
        db_timeout = int(os.getenv("HEALTHCHECK_DB_TIMEOUT", "5"))
        is_main_thread = threading.current_thread() is threading.main_thread()
        use_timeout = (
            db_timeout > 0 and platform.system() != "Windows" and is_main_thread
        )

        with connection.cursor() as cursor:
            if use_timeout:
                with timeout(db_timeout):
                    cursor.execute("SELECT 1")
                    row = cursor.fetchone()
            else:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()

            if not is_main_thread and db_timeout > 0:
                logger.debug(
                    "Health DB check running outside main thread; timeout skipped"
                )

        checks["db"] = {
            "ok": bool(row and (row[0] == 1)),
            "type": connection.vendor,
            "timeout_seconds": db_timeout,
            "thread_main": is_main_thread,
        }
    except TimeoutException:
        checks["db"] = {"ok": False, "error": "Database query timeout"}
    except Exception as exc:
        checks["db"] = {"ok": False, "error": str(exc)[:200]}

    # Cache backend check using a unique probe key
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
                "ok": cache.get(probe_key) == "ok",
                "backend": str(type(cache).__name__),
                "ignored": False,
            }
    except Exception as exc:
        if ignore_cache:
            checks["cache"] = {
                "ok": True,
                "ignored": True,
                "error": str(exc)[:200],
                "reason": "exception but ignored",
            }
        else:
            checks["cache"] = {"ok": False, "error": str(exc)[:200]}

    # Optional checks controlled via environment flags
    if os.getenv("HEALTHCHECK_STORAGE", "true").lower() == "true":
        _storage_check(checks)

    if os.getenv("HEALTHCHECK_SYSTEM_METRICS", "false").lower() == "true":
        _add_system_metrics(checks)

    if strict_mode:
        overall_ok = all(value.get("ok") for value in checks.values())
    else:
        overall_ok = checks.get("db", {}).get("ok", False)
    latency_ms = round((time.time() - started) * 1000, 2)

    if not overall_ok or debug_mode:
        message = (
            "Health check degraded" if not overall_ok else "Health check debug"
        )
        logger.warning(
            message, extra={"checks": checks, "latency_ms": latency_ms}
        )

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
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def healthz_ready(request: HttpRequest):
    """
    Readiness probe (/ready) that verifies light DB connectivity.

    Returns HTTP 200 when the application is ready to receive traffic and
    503 otherwise. Avoids heavy operations to keep the check fast.
    """

    started = time.time()
    db_ok = True
    db_timeout = 5
    db_timeout_env = os.getenv("HEALTHCHECK_DB_TIMEOUT", "5")
    force_no_timeout_env = os.getenv("HEALTHCHECK_FORCE_NO_TIMEOUT", "false")

    try:
        db_timeout = int(db_timeout_env)
        force_no_timeout = force_no_timeout_env.lower() == "true"
        is_main_thread = threading.current_thread() is threading.main_thread()
        use_timeout = (
            db_timeout > 0
            and platform.system() != "Windows"
            and not force_no_timeout
            and is_main_thread
        )

        with connection.cursor() as cursor:
            if use_timeout:
                with timeout(db_timeout):
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            else:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            if not is_main_thread and db_timeout > 0 and not force_no_timeout:
                logger.debug(
                    "Readiness DB check outside main thread; timeout skipped"
                )
    except TimeoutException:
        db_ok = False
        logger.warning(
            "Readiness DB check timeout", extra={"timeout_seconds": db_timeout}
        )
    except Exception:  # pragma: no cover - defensive
        db_ok = False
        logger.exception("Readiness DB check failed")

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
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def healthz_live(request: HttpRequest):
    """Liveness probe (/live) that confirms the process is running."""

    response = JsonResponse({"status": "alive"}, status=200)
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@cache_page(5)  # 5s cache to reduce latency under frequent scraping
def celery_status(request: HttpRequest):
    """
    Celery worker status endpoint (/celery/status).

    Triggers a lightweight ping followed by optional queue statistics. Results
    are cached for five seconds and returned as JSON.
    """

    started = time.time()
    timeout_seconds = float(os.getenv("CELERY_STATUS_TIMEOUT", "3"))
    ping_timeout = float(os.getenv("CELERY_PING_TIMEOUT", "2"))
    payload: Dict[str, Any] = {
        "timestamp": time.time(),
        "latency_ms": None,
        "status": "degraded",  # assume degraded until proven otherwise
        "worker": {
            "available": False,
            "error": None,
            "stats": None,
        },
    }

    try:
        from core.celery import get_queue_stats  # type: ignore
    except Exception as exc:  # pragma: no cover - defensive
        payload["worker"]["error"] = f"ImportError: {exc}"[:200]
        payload["latency_ms"] = round((time.time() - started) * 1000, 2)
        return JsonResponse(payload, status=503)

    # First send a ping so queue stats do not mark the worker as down
    ping_ok = False
    try:
        from core.celery import ping  # type: ignore

        pong_res = ping.delay()  # type: ignore[attr-defined]
        pong_val = pong_res.get(timeout=ping_timeout)
        ping_ok = pong_val == "pong"
    except Exception as exc:  # pragma: no cover - defensive
        payload["worker"]["error"] = f"PingError: {exc}"[:200]

    # If the ping succeeded, attempt to fetch statistics without failing status
    stats_error = None
    stats = None
    if ping_ok:
        try:
            async_res = get_queue_stats.delay()  # type: ignore[attr-defined]
            stats = async_res.get(timeout=timeout_seconds)
        except Exception as exc:  # pragma: no cover - defensive
            stats_error = str(exc)[:200]

    payload["worker"]["available"] = ping_ok
    if stats is not None:
        payload["worker"]["stats"] = stats
    if stats_error and not payload["worker"].get("error"):
        payload["worker"]["error"] = stats_error

    if ping_ok and isinstance(stats, dict) and "error" not in stats:
        payload["status"] = "ok"
    elif ping_ok:
        payload["status"] = "degraded"
    else:
        payload["status"] = "degraded"

    payload["latency_ms"] = round((time.time() - started) * 1000, 2)

    try:  # pragma: no cover - defensive
        from core.metrics_celery import update_metrics  # type: ignore

        update_metrics(payload)
    except Exception:
        pass

    code = 200 if payload["status"] == "ok" else 503
    response = JsonResponse(payload, status=code)
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response
