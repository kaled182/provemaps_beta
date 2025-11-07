from django.urls import path
from . import views

app_name = 'maps_view'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard_view'),
    path('metrics/', views.metrics_dashboard, name='metrics_dashboard'),
]
