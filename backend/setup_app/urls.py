from django.urls import path
from . import views
from . import views_docs  # Import docs_index and docs_view endpoints
from . import api_views  # Import API endpoints for testing and management

app_name = 'setup_app'

urlpatterns = [
    path('dashboard/', views.setup_dashboard, name='setup_dashboard'),
    path('first_time/', views.first_time_setup, name='first_time_setup'),
    path('config/', views.manage_environment, name='manage_environment'),

    # API endpoints for configuration management
    path('api/test-zabbix/', api_views.test_zabbix_connection, name='test_zabbix'),
    path('api/test-database/', api_views.test_database_connection, name='test_database'),
    path('api/test-redis/', api_views.test_redis_connection, name='test_redis'),
    path('api/export/', api_views.export_configuration, name='export_config'),
    path('api/import/', api_views.import_configuration, name='import_config'),
    path('api/audit-history/', api_views.get_audit_history, name='audit_history'),
    path('api/config/', api_views.get_configuration, name='get_config'),
    path('api/config/update/', api_views.update_configuration, name='update_config'),
    path('api/env/', api_views.get_env_file, name='get_env'),
    path('api/env/update/', api_views.update_env_file, name='update_env'),
    path('api/backups/', api_views.backups_manager, name='backups_manager'),
    path('api/backups/restore/', api_views.restore_backup, name='restore_backup'),

    # Documentation endpoints
    path("docs/", views_docs.docs_index, name="docs_index"),
    path("docs/<path:filename>/", views_docs.docs_view, name="docs_view"),
]
