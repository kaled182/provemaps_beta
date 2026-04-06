from __future__ import annotations

import urllib.request
import urllib.error
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .system_info import _read_version

GITHUB_REPO = "kaled182/provemaps_beta"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _fetch_latest_release() -> dict | None:
    req = urllib.request.Request(
        GITHUB_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "provemaps-update-check/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return None


def _parse_version(v: str) -> tuple[int, ...]:
    """Convert '1.4.2' or 'v1.4.2' to (1, 4, 2)."""
    v = v.lstrip("v").strip()
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


@require_http_methods(["GET"])
@login_required
def api_check_update(request):
    current = _read_version()
    release = _fetch_latest_release()

    if release is None:
        return JsonResponse({
            "current_version": current,
            "latest_version": None,
            "update_available": False,
            "error": "Não foi possível verificar atualizações. Verifique a conexão com a internet.",
        })

    latest_tag = release.get("tag_name", "")
    latest_version = latest_tag.lstrip("v").strip()
    release_url = release.get("html_url", "")
    release_name = release.get("name", latest_version)
    release_notes = release.get("body", "")

    update_available = _parse_version(latest_version) > _parse_version(current)

    return JsonResponse({
        "current_version": current,
        "latest_version": latest_version,
        "update_available": update_available,
        "release_url": release_url,
        "release_name": release_name,
        "release_notes": release_notes,
    })
