"""
API Views for frontend configuration
"""
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_GET

from setup_app.services import runtime_settings


@require_GET
def frontend_config(request):
    """
    Returns frontend configuration including API keys and map provider settings.

    Requires an authenticated session (EV-0002). The SPA only reaches this
    endpoint after login, and the map API keys must never be served to an
    anonymous visitor — domain restrictions in the providers' consoles are a
    second line of defence, not the first. The check lives here as well as in
    ``AuthRequiredMiddleware`` so the endpoint stays closed even if the
    middleware is disabled in some settings module.
    """
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return JsonResponse({'detail': 'Authentication required.'}, status=401)

    # Load configuration from database first
    config = runtime_settings.get_runtime_config()
    
    return JsonResponse({
        # Map provider configuration
        'mapProvider': config.map_provider,  # 'google', 'mapbox', 'osm', 'esri'
        'googleMapsApiKey': config.google_maps_api_key,
        'mapboxToken': config.mapbox_token,
        'esriApiKey': config.esri_api_key,
        
        # Map display settings
        'mapDefaultZoom': config.map_default_zoom,
        'mapDefaultLat': float(config.map_default_lat) if config.map_default_lat else -15.7801,
        'mapDefaultLng': float(config.map_default_lng) if config.map_default_lng else -47.9292,
        'mapType': config.map_type,
        'mapLanguage': config.map_language,
        'mapTheme': config.map_theme,
        
        # Google Maps specific
        'enableStreetView': config.enable_street_view,
        'enableTraffic': config.enable_traffic,
        'mapStyles': config.map_styles,
        
        # Mapbox specific
        'mapboxStyle': config.mapbox_style,
        'mapboxCustomStyle': config.mapbox_custom_style,
        'mapboxEnable3d': config.mapbox_enable_3d,
        
        # Esri specific
        'esriBasemap': config.esri_basemap,
        
        # Map features
        'enableMapClustering': config.enable_map_clustering,
        'enableDrawingTools': config.enable_drawing_tools,
        'enableFullscreen': config.enable_fullscreen,
        
        # Debug flag
        'debug': settings.DEBUG,
    })
