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
    path('api/test-gdrive/', api_views.test_gdrive, name='test_gdrive'),
    path('api/test-ftp/', api_views.test_ftp_connection, name='test_ftp'),
    path('api/test-smtp/', api_views.test_smtp_connection, name='test_smtp'),
    path('api/test-sms/', api_views.test_sms_connection, name='test_sms'),
    path('api/gdrive/oauth/start/', api_views.start_gdrive_oauth, name='gdrive_oauth_start'),
    path('api/gdrive/oauth/callback/', api_views.gdrive_oauth_callback, name='gdrive_oauth_callback'),
    path('api/export/', api_views.export_configuration, name='export_config'),
    path('api/import/', api_views.import_configuration, name='import_config'),
    path('api/audit-history/', api_views.get_audit_history, name='audit_history'),
    path('api/config/', api_views.get_configuration, name='get_config'),
    path('api/config/update/', api_views.update_configuration, name='update_config'),
    path('api/company-profile/', api_views.get_company_profile, name='get_company_profile'),
    path('api/company-profile/update/', api_views.update_company_profile, name='update_company_profile'),
    path('api/monitoring-servers/', api_views.monitoring_servers, name='monitoring_servers'),
    path('api/monitoring-servers/<int:server_id>/', api_views.monitoring_server_detail, name='monitoring_server_detail'),
    path('api/gateways/', api_views.messaging_gateways, name='messaging_gateways'),
    path('api/gateways/<int:gateway_id>/', api_views.messaging_gateway_detail, name='messaging_gateway_detail'),
    path('api/gateways/<int:gateway_id>/video/preview/start/', api_views.start_video_gateway_preview, name='start_video_gateway_preview'),
    path('api/gateways/<int:gateway_id>/video/preview/stop/', api_views.stop_video_gateway_preview, name='stop_video_gateway_preview'),
    path('api/gateways/<int:gateway_id>/whatsapp/qr/', api_views.whatsapp_qr_start, name='whatsapp_qr_start'),
    path('api/gateways/<int:gateway_id>/whatsapp/qr/status/', api_views.whatsapp_qr_status, name='whatsapp_qr_status'),
    path('api/gateways/<int:gateway_id>/whatsapp/qr/disconnect/', api_views.whatsapp_qr_disconnect, name='whatsapp_qr_disconnect'),
    path('api/gateways/<int:gateway_id>/whatsapp/qr/reset/', api_views.whatsapp_qr_reset, name='whatsapp_qr_reset'),
    path('api/gateways/<int:gateway_id>/whatsapp/qr/test-message/', api_views.whatsapp_qr_test_message, name='whatsapp_qr_test_message'),
    path('api/env/', api_views.get_env_file, name='get_env'),
    path('api/env/update/', api_views.update_env_file, name='update_env'),
    path('api/env/import/', api_views.import_env_backup, name='import_env'),
    path('api/backups/', api_views.backups_manager, name='backups_manager'),
    path('api/backups/restore/', api_views.restore_backup, name='restore_backup'),
    path('api/backups/delete/', api_views.delete_backup, name='delete_backup'),
    path('api/backups/upload-cloud/', api_views.upload_backup_to_cloud, name='upload_backup_cloud'),
    path('api/backups/settings/', api_views.update_backup_settings, name='backup_settings'),
    path('api/backups/download/<path:filename>/', api_views.download_backup, name='download_backup'),

    # Documentation endpoints
    path("docs/", views_docs.docs_index, name="docs_index"),
    path("docs/<path:filename>/", views_docs.docs_view, name="docs_view"),
]
