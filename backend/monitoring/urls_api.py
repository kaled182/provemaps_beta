"""API URL routes for monitoring endpoints (no UI pages)."""

from typing import Any

from django.urls import path

from monitoring import views

app_name = "monitoring_api"

urlpatterns: list[Any] = [
    path(
        "hosts/status/",
        views.api_hosts_status,
        name="api_hosts_status",
    ),
    path(
        "dashboard/snapshot/",
        views.api_dashboard_snapshot,
        name="api_dashboard_snapshot",
    ),
]
