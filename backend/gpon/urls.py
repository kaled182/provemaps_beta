"""Rotas de ``/api/v1/monitoring/gpon/`` (EV-0095)."""

from django.urls import path

from . import api

app_name = "gpon"

urlpatterns = [
    path("", api.GponOverviewView.as_view(), name="overview"),
    path("onus/<int:pk>/history/", api.OnuHistoryView.as_view(), name="onu_history"),
    path("events/", api.PonEventsView.as_view(), name="pon_events"),
    path("pon-trend/", api.PonTrendView.as_view(), name="pon_trend"),
]
