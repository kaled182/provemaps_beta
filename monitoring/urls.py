"""URL routes for monitoring API endpoints."""

from typing import Any

from django.urls import path

from monitoring import views

app_name = "monitoring"

urlpatterns: list[Any] = [
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
