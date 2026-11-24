from django.urls import path

from . import api

app_name = "switches"

urlpatterns = [
    path("", api.SwitchesOverviewView.as_view(), name="overview"),
]
