"""
API Views for frontend configuration
"""
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_GET


@require_GET
def frontend_config(request):
    """
    Returns frontend configuration including API keys.
    
    This endpoint is safe because:
    1. Google Maps API key can be restricted by domain/IP in Google Console
    2. The key is already exposed in the HTML meta tag
    3. It's needed for client-side navigation in the SPA
    """
    return JsonResponse({
        'googleMapsApiKey': settings.GOOGLE_MAPS_API_KEY,
        'debug': settings.DEBUG,
    })
