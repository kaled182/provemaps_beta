from django.urls import path
from . import views
from . import views_docs  # Import docs_index and docs_view endpoints

app_name = 'setup_app'

urlpatterns = [
    path('dashboard/', views.setup_dashboard, name='setup_dashboard'),
    path('first_time/', views.first_time_setup, name='first_time_setup'),
    path('config/', views.manage_environment, name='manage_environment'),

    # Documentation endpoints
    path("docs/", views_docs.docs_index, name="docs_index"),
    path("docs/<path:filename>/", views_docs.docs_view, name="docs_view"),
]
