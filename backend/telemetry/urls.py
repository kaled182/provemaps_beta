from django.urls import path
from . import views

app_name = "telemetry"

urlpatterns = [
    # Receiver — accepts pings from remote installations (no auth)
    path("ping/", views.api_telemetry_ping, name="ping"),
    # Stats — authenticated, used by SystemPanel
    path("stats/", views.api_telemetry_stats, name="stats"),
]
