"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

# HTML views routed through core/views.py
from core import views as core_views
# Health endpoints separados em core/views_health.py
from core import views_health as health_views


def redirect_to_maps_view(request):
    if request.method == 'GET':
        return redirect('maps_view/dashboard')
    else:
        return redirect('maps_view/dashboard')


urlpatterns = [
    path('', redirect_to_maps_view),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # auth (login/logout/password views)
    path('metrics/', include('django_prometheus.urls')),

    # Apps
    path('zabbix_api/', include('zabbix_api.urls')),
    path('maps_view/', include('maps_view.urls')),
    path('setup_app/', include('setup_app.urls')),
    path('routes_builder/', include('routes_builder.urls')),

    # HTML page for Zabbix lookup (rendered via core/views.py)
    path('zabbix/lookup/', core_views.zabbix_lookup_page, name='zabbix_lookup'),

    # Health checks
    path('healthz', health_views.healthz, name='healthz'),               # comprehensive (strict/non-strict, ignore cache support)
    path('ready', health_views.healthz_ready, name='healthz_ready'),     # readiness probe
    path('live', health_views.healthz_live, name='healthz_live'),        # liveness probe

    # Favicon
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True)),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'maps_view' / 'static')
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)