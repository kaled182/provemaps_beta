"""
SPA Views - Serve the Vue.js Single Page Application with proper context
"""
from django.views.generic import TemplateView
from django.conf import settings


class SPAView(TemplateView):
    """
    Serves the Vue SPA with Django context variables.
    
    Injects:
    - GOOGLE_MAPS_API_KEY
    - STATIC_ASSET_VERSION
    - Any other settings needed by the frontend
    """
    template_name = "spa.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Inject Google Maps API Key
        context['GOOGLE_MAPS_API_KEY'] = settings.GOOGLE_MAPS_API_KEY
        
        # Inject Static Asset Version for cache busting
        context['STATIC_ASSET_VERSION'] = getattr(
            settings,
            'STATIC_ASSET_VERSION',
            'nosha-dev'
        )
        
        # Add debug flag
        context['DEBUG'] = settings.DEBUG
        
        return context
