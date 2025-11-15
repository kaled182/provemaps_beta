from django.urls import path

from . import api_views, views

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
]
