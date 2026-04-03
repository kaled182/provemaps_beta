from __future__ import annotations

import os
import sys
import platform
import django

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.conf import settings

# Path: backend/inventory/api/system_info.py
# Base dir is three levels up: api/ → inventory/ → backend/ → project root
_BASE_DIR = os.path.dirname(  # project root
    os.path.dirname(           # backend/
        os.path.dirname(       # inventory/
            os.path.dirname(   # api/
                os.path.abspath(__file__)
            )
        )
    )
)


def _read_version() -> str:
    version_file = os.path.join(_BASE_DIR, "VERSION")
    try:
        with open(version_file) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"


@require_http_methods(["GET"])
@login_required
def api_system_info(request):
    """
    Returns basic system/version information.
    Designed to be extended into a full server-admin panel in the future.
    """
    version = _read_version()

    return JsonResponse({
        "version": version,
        "django_version": ".".join(str(x) for x in django.VERSION[:3]),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.system(),
        "environment": os.environ.get("DJANGO_ENV", "development" if settings.DEBUG else "production"),
        "hostname": os.environ.get("HOSTNAME", platform.node() or "unknown"),
        # Future: list of managed servers, resource usage, etc.
        "servers": [],
    })
