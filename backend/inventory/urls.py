from django.urls import path

from . import api_views, views
from . import api_custom_maps

app_name = "inventory"

urlpatterns = [
    # HTML view
    path(
        "",
        views.fiber_route_builder,
        name="network_design",
    ),

    # REST API endpoints used by the React-free UI
    path("api/sites/", api_views.list_sites, name="api_list_sites"),
    path("api/routes/", api_views.list_routes, name="api_list_routes"),
    path(
        "api/routes/calculate/",
        api_views.calculate_route,
        name="api_calculate_route",
    ),
    path(
        "api/routes/save/",
        api_views.save_route,
        name="api_save_route",
    ),
    
    # Custom Maps API
    path(
        "api/v1/maps/custom/",
        api_custom_maps.custom_maps_list,
        name="custom_maps_list",
    ),
    path(
        "api/v1/maps/custom/<int:map_id>/",
        api_custom_maps.custom_map_detail,
        name="custom_map_detail",
    ),
    path(
        "api/v1/maps/custom/<int:map_id>/items/",
        api_custom_maps.save_map_items,
        name="save_map_items",
    ),
    path(
        "api/v1/maps/devices-location/",
        api_custom_maps.map_devices_with_location,
        name="map_devices_location",
    ),
    path(
        "api/v1/maps/cables-location/",
        api_custom_maps.map_cables_with_location,
        name="map_cables_location",
    ),
]
