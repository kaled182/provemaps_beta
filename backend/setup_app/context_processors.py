from .models import FirstTimeSetup
from django.conf import settings

def setup_logo(request):
    setup = FirstTimeSetup.objects.filter(configured=True).order_by('-configured_at').first()
    return {'setup_logo': setup}

def static_version(request):
    """Expose STATIC_ASSET_VERSION for cache bust in templates."""
    return {
        'STATIC_ASSET_VERSION': getattr(settings, 'STATIC_ASSET_VERSION', 'dev')
    }
