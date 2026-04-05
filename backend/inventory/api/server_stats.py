from __future__ import annotations

import os
import socket
import subprocess

import psutil

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


def _cpu() -> dict:
    return {
        "percent": psutil.cpu_percent(interval=0.5),
        "count": psutil.cpu_count(logical=True),
    }


def _memory() -> dict:
    m = psutil.virtual_memory()
    return {
        "total_gb": round(m.total / 1024 ** 3, 1),
        "used_gb": round(m.used / 1024 ** 3, 1),
        "percent": m.percent,
    }


def _disk() -> dict:
    d = psutil.disk_usage("/")
    return {
        "total_gb": round(d.total / 1024 ** 3, 1),
        "used_gb": round(d.used / 1024 ** 3, 1),
        "percent": d.percent,
    }


def _tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if a TCP connection to host:port succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _pgrep(pattern: str) -> bool:
    """Return True if a process matching pattern exists in this container."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            timeout=3,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _http_check(url: str, timeout: float = 2.0) -> bool:
    """Return True if an HTTP GET to url returns any response."""
    import urllib.request
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def _services() -> list[dict]:
    # DB settings
    db_cfg = settings.DATABASES.get("default", {})
    db_host = db_cfg.get("HOST") or os.getenv("DB_HOST", "postgres")
    db_port = int(db_cfg.get("PORT") or os.getenv("DB_PORT", 5432))

    # Redis
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis_host = "redis"
    redis_port = 6379
    try:
        from urllib.parse import urlparse
        parsed = urlparse(redis_url)
        redis_host = parsed.hostname or "redis"
        redis_port = parsed.port or 6379
    except Exception:
        pass

    return [
        {"name": "Gunicorn",   "online": _pgrep("gunicorn")},
        {"name": "Celery",     "online": _pgrep("celery")},
        {"name": "Nginx",      "online": _tcp_check("nginx", 80)},
        {"name": "Redis",      "online": _tcp_check(redis_host, redis_port)},
        {"name": "PostgreSQL", "online": _tcp_check(db_host, db_port)},
    ]


@require_http_methods(["GET"])
@login_required
def api_server_stats(request):
    return JsonResponse({
        "cpu": _cpu(),
        "memory": _memory(),
        "disk": _disk(),
        "services": _services(),
    })
