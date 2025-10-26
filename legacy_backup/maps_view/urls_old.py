from django.urls import path
from . import views

app_name = 'maps_view'

urlpatterns = [
    # =========================
    # TEST HELPERS
    # =========================
    path('api/test/cable-up/<int:cable_id>/', views.test_set_cable_up, name='test_set_cable_up'),
    path('api/test/cable-down/<int:cable_id>/', views.test_set_cable_down, name='test_set_cable_down'),
    path('api/test/cable-unknown/<int:cable_id>/', views.test_set_cable_unknown, name='test_set_cable_unknown'),

    # =========================
    # CABOS DE FIBRA
    # =========================
    path('api/fibers/', views.api_fiber_cables, name='api_fiber_cables'),
    path('api/fiber/<int:cable_id>/', views.api_fiber_detail, name='api_fiber_detail'),
    path('api/fiber/live-status/<int:cable_id>/', views.api_fiber_live_status, name='api_fiber_live_status'),
    path('api/fibers/live-status/', views.api_fibers_live_status_all, name='api_fibers_live_status_all'),
    path('api/fibers/refresh-status/', views.api_fibers_refresh_status, name='api_fibers_refresh_status'),
    path('api/fiber/value-mapping-status/<int:cable_id>/', views.api_cable_value_mapping_status, name='api_cable_value_mapping_status'),

    # =========================
    # IMPORTA??O KML E BUILDER
    # =========================
    path('api/import-fiber-kml/', views.api_import_fiber_kml, name='api_import_fiber_kml'),
    path('fiber-route-builder/', views.fiber_route_builder_view, name='fiber_route_builder'),
    path('import-kml-modal/', views.import_kml_modal, name='import_kml_modal'),

    # =========================
    # ZABBIX INTEGRA??O
    # =========================
    path('api/update-cable-oper-status/<int:cable_id>/', views.api_update_cable_oper_status, name='api_update_cable_oper_status'),
    path('api/device-ports/<int:device_id>/', views.api_device_ports, name='api_device_ports'),
    path('api/add-device-from-zabbix/', views.api_add_device_from_zabbix, name='api_add_device_from_zabbix'),
    path('api/zabbix/discover-hosts/', views.api_zabbix_discover_hosts, name='api_zabbix_discover_hosts'),

    # =========================
    # INVENT?RIO EM LOTE
    # =========================
    path('api/bulk-create-inventory/', views.api_bulk_create_inventory, name='api_bulk_create_inventory'),

    # =========================
    # SITES E DEVICES
    # =========================
    path('api/sites/', views.api_sites, name='api_sites'),

    # =========================
    # DASHBOARD PRINCIPAL
    # =========================
    path('dashboard/', views.dashboard_view, name='dashboard_view'),
]
