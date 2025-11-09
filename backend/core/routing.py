from __future__ import annotations

from django.urls import path

from maps_view.realtime import consumers as maps_view_consumers

websocket_urlpatterns = [
    path("ws/dashboard/status/", maps_view_consumers.DashboardStatusConsumer.as_asgi()),
    path("maps_view/ws/dashboard/status/", maps_view_consumers.DashboardStatusConsumer.as_asgi()),
]
