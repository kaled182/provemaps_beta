from __future__ import annotations

import os
import platform
import sys

import django
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


def _read_version() -> str:
    # Search for VERSION file: try /app/VERSION (Docker), then walk up from this file
    candidates = [
        "/app/VERSION",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "VERSION"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "VERSION"),
    ]
    for path in candidates:
        try:
            with open(os.path.normpath(path)) as f:
                version = f.read().strip()
                if version:
                    return version
        except (FileNotFoundError, OSError):
            continue
    return "unknown"


@require_http_methods(["GET"])
@login_required
def api_system_info(request):
    """
    Returns basic system/version information.
    Designed to be extended into a full server-admin panel in the future.
    """
    version = _read_version()

    return JsonResponse(
        {
            "version": version,
            "django_version": ".".join(str(x) for x in django.VERSION[:3]),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.system(),
            "environment": os.environ.get(
                "DJANGO_ENV", "development" if settings.DEBUG else "production"
            ),
            "hostname": os.environ.get("HOSTNAME", platform.node() or "unknown"),
            # Future: list of managed servers, resource usage, etc.
            "servers": [],
        }
    )
