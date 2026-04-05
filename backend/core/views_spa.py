"""
SPA Views - Serve the Vue.js Single Page Application with proper context
"""
import json
import os

from django.views.generic import TemplateView
from django.conf import settings
from django.contrib.staticfiles.finders import find as static_find


def _load_vite_entry():
    """
    Read Vite manifest.json and return the entry data for index.html.
    Returns None if manifest is not found (falls back to hardcoded filenames).
    """
    # Try manifest path relative to STATICFILES_DIRS or STATIC_ROOT
    candidates = [
        os.path.join(settings.STATIC_ROOT or '', 'vue-spa', '.vite', 'manifest.json'),
        os.path.join(settings.BASE_DIR, 'staticfiles', 'vue-spa', '.vite', 'manifest.json'),
        os.path.join(settings.BASE_DIR, 'backend', 'staticfiles', 'vue-spa', '.vite', 'manifest.json'),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    manifest = json.load(f)
                # Vite manifest key is the input file path
                return manifest.get('index.html')
            except (OSError, json.JSONDecodeError, KeyError):
                pass
    return None


class SPAView(TemplateView):
    """
    Serves the Vue SPA with Django context variables.

    Injects:
    - GOOGLE_MAPS_API_KEY
    - STATIC_ASSET_VERSION
    - VITE_ENTRY: manifest entry so template uses hashed filenames
    """
    template_name = "spa.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['GOOGLE_MAPS_API_KEY'] = settings.GOOGLE_MAPS_API_KEY
        context['STATIC_ASSET_VERSION'] = getattr(settings, 'STATIC_ASSET_VERSION', 'nosha-dev')
        context['DEBUG'] = settings.DEBUG
        context['VITE_ENTRY'] = _load_vite_entry()
        return context
