from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import mapbox_proxy
from . import views_bootstrap

app_name = 'maps_view'

urlpatterns = [
    # Endpoint agregado: tudo que o /monitoring/backbone/map precisa em 1 chamada
    path(
        'api/backbone/init/',
        views_bootstrap.backbone_init_api,
        name='backbone_init_api'
    ),
    path(
        'dashboard/',
        RedirectView.as_view(url='/', permanent=True),
        name='dashboard_view',
    ),
    path(
        'api/dashboard/data/',
        views.dashboard_data_api,
        name='dashboard_data_api'
    ),
    path(
        'api/dashboard/sites/',
        views.dashboard_sites_api,
        name='dashboard_sites_api'
    ),
    path('metrics/', views.metrics_dashboard, name='metrics_dashboard'),
    
    # Mapbox API Proxy (evita Mixed Content Security)
    path(
        'api/mapbox-proxy/styles/<path:style_id>',
        mapbox_proxy.proxy_mapbox_style,
        name='mapbox_proxy_style'
    ),
    path(
        'api/mapbox-proxy/tiles/<str:tileset>/<int:z>/<int:x>/<int:y>.vector.pbf',
        mapbox_proxy.proxy_mapbox_tiles,
        name='mapbox_proxy_tiles'
    ),
    path(
        'api/mapbox-proxy/sprites/<path:style_id>/<str:sprite_file>',
        mapbox_proxy.proxy_mapbox_sprites,
        name='mapbox_proxy_sprites'
    ),
    path(
        'api/mapbox-proxy/fonts/<path:font_stack>/<str:glyph_range>.pbf',
        mapbox_proxy.proxy_mapbox_glyphs,
        name='mapbox_proxy_glyphs'
    ),
]
