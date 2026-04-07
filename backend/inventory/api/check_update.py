from __future__ import annotations

import urllib.request
import urllib.error
import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .system_info import _read_version

logger = logging.getLogger(__name__)

GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/kaled182/provemaps_beta/main/version.json"
)
CACHE_KEY = "provemaps:version_check"
CACHE_TTL = 3600  # 1 hour — avoid hammering GitHub for every user click


def _fetch_remote_version() -> dict | None:
    """Fetch version.json from GitHub raw content. Cached in Redis for 1 hour."""
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    req = urllib.request.Request(
        GITHUB_RAW_URL,
        headers={"User-Agent": "provemaps-update-check/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            cache.set(CACHE_KEY, data, CACHE_TTL)
            return data
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as e:
        logger.warning("check_update: could not fetch remote version.json: %s", e)
        return None


def _parse_version(v: str) -> tuple[int, ...]:
    """Convert '1.4.2' or 'v1.4.2' to (1, 4, 2)."""
    try:
        return tuple(int(x) for x in v.lstrip("v").strip().split("."))
    except ValueError:
        return (0,)


@require_http_methods(["GET"])
@login_required
def api_check_update(request):
    current = _read_version()
    remote = _fetch_remote_version()

    if remote is None:
        return JsonResponse({
            "current_version": current,
            "latest_version": None,
            "update_available": False,
            "error": "Não foi possível verificar atualizações.",
        })

    latest = remote.get("version", "")
    update_available = _parse_version(latest) > _parse_version(current)

    return JsonResponse({
        "current_version": current,
        "latest_version": latest,
        "update_available": update_available,
        "release_date": remote.get("date", ""),
        "critical": remote.get("critical", False),
        "changelog": remote.get("changelog", ""),
    })
