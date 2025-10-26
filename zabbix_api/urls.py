from django.urls import path

from . import diagnostics, inventory, inventory_fibers, lookup, reports
from .services import zabbix_service

app_name = "zabbix_api"

urlpatterns = [
    # =========================================================================
    # ZABBIX - READ-ONLY DASHBOARD ENDPOINTS
    # =========================================================================
    path("hosts/", reports.zabbix_hosts, name="zabbix_hosts"),
    path("hosts/<int:hostid>/", reports.zabbix_host_detail, name="zabbix_host_detail"),
    path("hosts/<int:hostid>/items/", reports.zabbix_host_items, name="zabbix_host_items"),
    path("hosts/<int:hostid>/triggers/", reports.zabbix_host_triggers, name="zabbix_host_triggers"),
    path("hosts/<int:hostid>/graphs/", reports.zabbix_host_graphs, name="zabbix_host_graphs"),
    path("hosts/<int:hostid>/latest/", reports.zabbix_host_latest_data, name="zabbix_host_latest_data"),
    path(
        "items/<int:hostid>/<int:itemid>/history/",
        reports.zabbix_item_history,
        name="zabbix_item_history",
    ),
    path("problems/", reports.zabbix_problems, name="zabbix_problems"),
    path("problems/<int:hostid>/", reports.zabbix_host_problems, name="zabbix_host_problems"),
    path("events/", reports.zabbix_events, name="zabbix_events"),
    path("hostgroups/", reports.zabbix_hostgroups, name="zabbix_hostgroups"),
    path("templates/", reports.zabbix_templates, name="zabbix_templates"),
    path("status/", reports.zabbix_status, name="zabbix_status"),
    path("overview/", reports.zabbix_monitoring_overview, name="zabbix_monitoring_overview"),
    path("latest_all/", reports.zabbix_all_latest_data, name="zabbix_all_latest_data"),
    path("problems_summary/", reports.zabbix_problems_summary, name="zabbix_problems_summary"),
    path("problems_by_severity/", reports.zabbix_problems_by_severity, name="zabbix_problems_by_severity"),
    path("critical_problems/", reports.zabbix_critical_problems, name="zabbix_critical_problems"),
    path("recent_events/", reports.zabbix_recent_events, name="zabbix_recent_events"),
    path("events_summary/", reports.zabbix_events_summary, name="zabbix_events_summary"),
    path("hosts/network-info/", reports.zabbix_hosts_network_info, name="zabbix_hosts_network_info"),
    path("hosts/<int:hostid>/network-info/", reports.zabbix_host_network_info, name="zabbix_host_network_info"),
    path("test/", reports.zabbix_test, name="zabbix_test"),
    path("clear-cache/", reports.zabbix_clear_cache, name="zabbix_clear_cache"),

    # =========================================================================
    # LOOKUP (autocomplete endpoints consumed by the lookup.html template)
    # =========================================================================
    path("lookup/hosts/", lookup.lookup_hosts, name="lookup_hosts"),
    path(
        "lookup/hosts/<int:hostid>/interfaces/",
        lookup.lookup_host_interfaces,
        name="lookup_host_interfaces",
    ),
    path(
        "lookup/hosts/<int:hostid>/status/",
        lookup.lookup_host_status,
        name="lookup_host_status",
    ),
    path(
        "lookup/interfaces/<int:interfaceid>/details/",
        lookup.lookup_interface_details,
        name="lookup_interface_details",
    ),

    # =========================================================================
    # ZABBIX INTEGRATION WITH LOCAL INVENTORY
    # =========================================================================
    path(
        "api/add-device-from-zabbix/",
        inventory.api_add_device_from_zabbix,
        name="api_add_device_from_zabbix",
    ),
    path(
        "api/zabbix/discover-hosts/",
        inventory.api_zabbix_discover_hosts,
        name="api_zabbix_discover_hosts",
    ),
    path(
        "api/update-cable-oper-status/<int:cable_id>/",
        inventory.api_update_cable_oper_status,
        name="api_update_cable_oper_status",
    ),
    path("api/device-ports/<int:device_id>/", inventory.api_device_ports, name="api_device_ports"),
    path(
        "api/device-ports-optical/<int:device_id>/",
        inventory.api_device_ports_with_optical,
        name="api_device_ports_with_optical",
    ),
    path(
        "api/port-optical-status/<int:port_id>/",
        inventory.api_device_port_optical_status,
        name="api_device_port_optical_status",
    ),
    path(
        "api/port-traffic-history/<int:port_id>/",
        inventory.api_port_traffic_history,
        name="api_port_traffic_history",
    ),

    # =========================================================================
    # FIBER CABLES
    # =========================================================================
    path("api/fibers/", inventory.api_fiber_cables, name="api_fiber_cables"),
    path("api/fiber/<int:cable_id>/", inventory_fibers.api_fiber_detail, name="api_fiber_detail"),
    path(
        "api/fiber/live-status/<int:cable_id>/",
        inventory.api_fiber_live_status,
        name="api_fiber_live_status",
    ),
    path(
        "api/fibers/live-status/",
        inventory.api_fibers_live_status_all,
        name="api_fibers_live_status_all",
    ),
    path(
        "api/fibers/refresh-status/",
        inventory.api_fibers_refresh_status,
        name="api_fibers_refresh_status",
    ),
    path(
        "api/fiber/value-mapping-status/<int:cable_id>/",
        inventory.api_cable_value_mapping_status,
        name="api_cable_value_mapping_status",
    ),

    # =========================================================================
    # KML IMPORT / BUILDER
    # =========================================================================
    path("api/import-fiber-kml/", inventory.api_import_fiber_kml, name="api_import_fiber_kml"),
    path("api/fibers/manual-create/", inventory_fibers.api_create_manual_fiber, name="api_create_manual_fiber"),
    path("api/fibers/import-kml/", inventory_fibers.api_import_fiber_kml, name="api_import_fiber_kml_alt"),
    path("import-kml-modal/", inventory.import_kml_modal, name="import_kml_modal"),

    # =========================================================================
    # BULK INVENTORY / SITES
    # =========================================================================
    path("api/bulk-create-inventory/", inventory.api_bulk_create_inventory, name="api_bulk_create_inventory"),
    path("api/sites/", inventory.api_sites, name="api_sites"),

    # =========================================================================
    # TEST HELPERS (diagnostics and simulations)
    # =========================================================================
    path("api/test/cable-up/<int:cable_id>/", diagnostics.test_set_cable_up, name="test_set_cable_up"),
    path("api/test/cable-down/<int:cable_id>/", diagnostics.test_set_cable_down, name="test_set_cable_down"),
    path("api/test/cable-unknown/<int:cable_id>/", diagnostics.test_set_cable_unknown, name="test_set_cable_unknown"),

    # Legacy helper endpoints
    path("api/interfaces/", zabbix_service.get_interfaces, name="get_interfaces"),
    path("status/<int:itemid>/", zabbix_service.port_itemid_status, name="port_itemid_status"),

    # PING / TELNET
    path("api/test/telnet/", diagnostics.api_test_telnet, name="api_test_telnet"),
    path("api/test/ping/", diagnostics.api_test_ping, name="api_test_ping"),
    path("api/test/ping_telnet/", diagnostics.api_test_ping_telnet, name="api_test_ping_telnet"),
]
