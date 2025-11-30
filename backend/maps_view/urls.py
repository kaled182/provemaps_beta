from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'maps_view'

urlpatterns = [
    path(
        'dashboard/',
        views.dashboard_view,
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
]
