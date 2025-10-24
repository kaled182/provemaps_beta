# core/views.py
import os
import time
import platform
import logging
import django
from django.http import JsonResponse
from django.db import connection
from django.core.cache import caches
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

logger = logging.getLogger(__name__)


@login_required
def zabbix_lookup_page(request):
    """
    Render the Zabbix lookup integration page.
    The frontend consumes the REST endpoints from the zabbix_api app.
    """
    return render(request, "zabbix/lookup.html")


def healthz(request):
    """
    Comprehensive health check endpoint (/healthz)
    - Checks: DB, Cache, Storage
    - Returns: Status, versions, latency, detailed checks
    - HTTP 200 if healthy, 503 if degraded
    """
    started = time.time()
    checks = {}

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
        checks["db"] = {
            "ok": bool(row and (row[0] == 1)),
            "type": connection.vendor  # postgresql, mysql, etc
        }
    except Exception as e:
        checks["db"] = {"ok": False, "error": str(e)[:200]}

    # Cache check
    try:
        cache = caches["default"]
        probe_key = "healthz_probe"
        cache.set(probe_key, "ok", 5)
        checks["cache"] = {"ok": (cache.get(probe_key) == "ok")}
    except Exception as e:
        checks["cache"] = {"ok": False, "error": str(e)[:200]}

    # Storage check (optional)
    try:
        import shutil
        stat = shutil.disk_usage("/")
        free_gb = stat.free / (1024**3)
        checks["storage"] = {
            "ok": free_gb > 1,
            "free_gb": round(free_gb, 2),
            "threshold": 1.0
        }
    except Exception as e:
        checks["storage"] = {"ok": False, "error": str(e)[:200]}

    overall_ok = all(v.get("ok") for v in checks.values())
    latency_ms = round((time.time() - started) * 1000, 2)

    # Log if degraded
    if not overall_ok:
        logger.warning(
            "Health check degraded",
            extra={"checks": checks, "latency_ms": latency_ms}
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

    return JsonResponse(payload, status=200 if overall_ok else 503)