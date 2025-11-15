"""URL routes for monitoring HTML endpoints and APIs."""

from typing import Any

from django.urls import path
from django.views.generic import RedirectView

from monitoring import views
from maps_view.views import dashboard_view

app_name = "monitoring"

urlpatterns: list[Any] = [
    path(
        "",
        RedirectView.as_view(
            pattern_name="monitoring:monitoring_overview",
            permanent=False,
        ),
        name="monitoring_root",
    ),
    path(
        "backbone/",
        dashboard_view,
        name="backbone_dashboard",
    ),
    path(
        "monitoring-all/",
        dashboard_view,
        name="monitoring_overview",
    ),
    path(
        "gpon/",
        dashboard_view,
        name="gpon_dashboard",
    ),
    path(
        "dwdm/",
        dashboard_view,
        name="dwdm_dashboard",
    ),
    path(
        "api/v1/monitoring/hosts/status/",
        views.api_hosts_status,
        name="api_hosts_status",
    ),
    path(
        "api/v1/monitoring/dashboard/snapshot/",
        views.api_dashboard_snapshot,
        name="api_dashboard_snapshot",
    ),
]
