from __future__ import annotations

import subprocess

import psutil

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


def _service_status(name: str, check_cmd: list[str]) -> dict:
    """Run a check command; return online/offline based on exit code."""
    try:
        result = subprocess.run(
            check_cmd,
            capture_output=True,
            timeout=5,
        )
        online = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        online = False
    return {"name": name, "online": online}


def _services() -> list[dict]:
    checks = [
        ("Gunicorn", ["pgrep", "-f", "gunicorn"]),
        ("Celery", ["pgrep", "-f", "celery"]),
        ("Nginx", ["pgrep", "-x", "nginx"]),
        ("Redis", ["pgrep", "-x", "redis-server"]),
        ("PostgreSQL", ["pgrep", "-x", "postgres"]),
    ]
    return [_service_status(name, cmd) for name, cmd in checks]


@require_http_methods(["GET"])
@login_required
def api_server_stats(request):
    return JsonResponse({
        "cpu": _cpu(),
        "memory": _memory(),
        "disk": _disk(),
        "services": _services(),
    })
