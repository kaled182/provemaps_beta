"""
URL configuration for core project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from typing import Any

# Health endpoints
from core import views_health as health_views
from core import views_metrics as metrics_views
from core import views_docs as docs_views
# Views antigas
from core import views as core_views
# SPA views
from core.views_spa import SPAView
from core import views_auth
# API views
from core import views_api as api_views
from core import api_users
from setup_app import api_views as setup_api_views


# Customize Django Admin
admin.site.site_header = "SIMPLES INTERNET - Administração"
admin.site.site_title = "Maps Prove Fiber Admin"
admin.site.index_title = "Gerenciamento do Sistema"


# Define API, Admin e Health routes FIRST
urlpatterns: list[Any] = [
    path('admin/', admin.site.urls),
    path(
        'accounts/password_reset/',
        views_auth.RuntimeEmailPasswordResetView.as_view(),
        name='password_reset',
    ),
    path(
        'accounts/login/',
        views_auth.TwoStepLoginView.as_view(),
        name='login',
    ),
    path(
        'accounts/otp/',
        views_auth.RuntimeOtpView.as_view(),
        name='login_otp',
    ),
    path(
        'accounts/',
        include('django.contrib.auth.urls'),
    ),
    path(
        'metrics',
        RedirectView.as_view(url='/metrics/metrics', permanent=False),
        name='metrics_root_redirect',
    ),
    path('metrics/', include('django_prometheus.urls')),
    path(
        'api/metrics/health/',
        metrics_views.system_health_metrics,
        name='system_health_metrics'
    ),
    path('metrics/health', SPAView.as_view(), name='metrics_health_page'),

    # Documentation API
    path(
        'api/docs/<path:doc_path>',
        docs_views.serve_doc_file,
        name='serve_doc'
    ),
    path('docs', SPAView.as_view(), name='docs_page'),

    # User Management API
    path('api/users/', api_users.list_users, name='api_list_users'),
    path('api/users/create/', api_users.create_user, name='api_create_user'),
    path('api/users/<int:user_id>/', api_users.get_user, name='api_get_user'),
    path(
        'api/users/<int:user_id>/update/',
        api_users.update_user,
        name='api_update_user'
    ),
    path(
        'api/users/<int:user_id>/delete/',
        api_users.delete_user,
        name='api_delete_user'
    ),
    path('api/users/me/', api_users.me_user, name='api_me_user'),
    path('api/users/me/avatar/', api_users.me_avatar, name='api_me_avatar'),
    path('api/users/me/totp/', api_users.me_totp, name='api_me_totp'),
    path('api/users/me/totp/verify/', api_users.me_totp_verify, name='api_me_totp_verify'),
    path('api/users/me/totp/disable/', api_users.me_totp_disable, name='api_me_totp_disable'),
    path('api/groups/', api_users.list_groups, name='api_list_groups'),
    path('api/departments/', api_users.list_departments, name='api_list_departments'),
    path(
        'api/departments/<int:department_id>/',
        api_users.department_detail,
        name='api_department_detail'
    ),
    path(
        'api/departments/<int:department_id>/remove/',
        api_users.remove_department,
        name='api_remove_department'
    ),
    path('system/users', SPAView.as_view(), name='users_page'),

    # APIs
    path('api/v1/telemetry/', include('telemetry.urls')),
    path('api/v1/inventory/', include('inventory.urls_api')),
    path('api/v1/', include('inventory.urls_rest')),
    path('api/v1/monitoring/', include('monitoring.urls_api')),
    path('', include('inventory.urls')),  # Custom maps and legacy HTML views
    path('api/v1/cameras/', setup_api_views.video_cameras_list, name='api_video_cameras'),
    path('api/config/', api_views.frontend_config, name='frontend_config'),
    path('setup_app/', include('setup_app.urls')),
    path('maps_view/', include('maps_view.urls')),
    path('monitoring/', include('monitoring.urls')),

    # Health checks
    path('healthz', health_views.healthz, name='healthz'),
    path('ready', health_views.healthz_ready, name='healthz_ready'),
    path('live', health_views.healthz_live, name='healthz_live'),
    path(
        'celery/status',
        health_views.celery_status,
        name='celery_status'
    ),

    # Zabbix lookup page (if still needed)
    path(
        'zabbix/lookup/',
        core_views.zabbix_lookup_page,
        name='zabbix_lookup'
    ),

    # Favicon
    path(
        'favicon.ico',
        RedirectView.as_view(url='/static/favicon.ico', permanent=True)
    ),
]

# Django Debug Toolbar (dev only)
if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns.insert(0, path('__debug__/', include(debug_toolbar.urls)))

# Serve static and media files (dev only)
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

# Vue SPA Catch-All Route
# This MUST be the last route. It captures any URL not matched above
# (by API, Admin, or Static) and serves the Vue SPA.
# IMPORTANT: Must NOT match API routes (api/), admin routes (admin/), or static files
urlpatterns.append(
    re_path(
        r"^(?!api/)(?!admin/)(?!static/)(?!media/).*$",  # Negative lookahead to exclude API, admin, static, media
        SPAView.as_view(),
        name="spa",
    )
)
