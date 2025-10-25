from django.urls import path
from . import views
from . import views_docs  # Importa o módulo que contém docs_index e docs_view

app_name = 'setup_app'

urlpatterns = [
    path('dashboard/', views.setup_dashboard, name='setup_dashboard'),
    path('first_time/', views.first_time_setup, name='first_time_setup'),
    path('config/', views.manage_environment, name='manage_environment'),

    # Documentação
    path("docs/", views_docs.docs_index, name="docs_index"),
    path("docs/<str:filename>/", views_docs.docs_view, name="docs_view"),
]
