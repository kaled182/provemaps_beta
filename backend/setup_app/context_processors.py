from types import SimpleNamespace

from .models import CompanyProfile, FirstTimeSetup
from django.conf import settings
from pathlib import Path
import json

_vite_manifest_cache = {"mtime": None, "entry": None}


def _load_vite_entry():
    manifest_path = Path(settings.STATIC_ROOT) / "vue-spa" / ".vite" / "manifest.json"
    try:
        stat = manifest_path.stat()
    except FileNotFoundError:
        _vite_manifest_cache["mtime"] = None
        _vite_manifest_cache["entry"] = None
        return None

    if _vite_manifest_cache["mtime"] == stat.st_mtime:
        return _vite_manifest_cache["entry"]

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _vite_manifest_cache["mtime"] = stat.st_mtime
        _vite_manifest_cache["entry"] = None
        return None

    entry = data.get("index.html")
    if not entry or "file" not in entry:
        _vite_manifest_cache["mtime"] = stat.st_mtime
        _vite_manifest_cache["entry"] = None
        return None

    _vite_manifest_cache["mtime"] = stat.st_mtime
    _vite_manifest_cache["entry"] = {
        "file": entry["file"],
        "css": entry.get("css", []),
    }
    return _vite_manifest_cache["entry"]

def setup_logo(request):
    profile = CompanyProfile.objects.order_by("-updated_at").first()
    if profile and profile.assets_logo:
        return {"setup_logo": SimpleNamespace(logo=profile.assets_logo)}
    setup = FirstTimeSetup.objects.filter(configured=True).order_by("-configured_at").first()
    return {"setup_logo": setup}

def static_version(request):
    """Expose STATIC_ASSET_VERSION for cache bust in templates."""
    return {
        'STATIC_ASSET_VERSION': getattr(settings, 'STATIC_ASSET_VERSION', 'dev'),
        'VITE_ENTRY': _load_vite_entry(),
    }
