from __future__ import annotations

from django.urls import path
from django.core.exceptions import ImproperlyConfigured
import logging

from .api.splice_matrix import (
    SpliceBoxMatrixView,
    CreateFusionView,
    DeleteFusionView,
    BoxContextView,
)
from .api.cable_attachment import CableAttachmentViewSet

logger = logging.getLogger(__name__)

# GIS-dependent endpoints (require GDAL). In lightweight test environments we
# tolerate missing GDAL by skipping these routes instead of blowing up during
# URL import.
_GIS_ENDPOINTS_AVAILABLE = True
try:
    from .api.cable_split import CableSplitViewSet
    from .api.cable_split_v2 import CableSplitV2View
    from .api.attach_loose_end import AttachLooseEndView
    from .api.create_standalone_ceo import CreateStandaloneCEOView
    from .api.list_standalone_ceos import ListStandaloneCEOsView
    from .api.list_loose_ends import ListLooseEndsView
except ImproperlyConfigured:  # pragma: no cover - depends on GDAL availability
    _GIS_ENDPOINTS_AVAILABLE = False
    CableSplitViewSet = None  # type: ignore[assignment]
    CableSplitV2View = None  # type: ignore[assignment]
    AttachLooseEndView = None  # type: ignore[assignment]
    CreateStandaloneCEOView = None  # type: ignore[assignment]
    ListStandaloneCEOsView = None  # type: ignore[assignment]
    ListLooseEndsView = None  # type: ignore[assignment]
    logger.warning("GDAL not available; skipping GIS-dependent inventory APIs")

from inventory.api import devices as device_api
from inventory.api import fibers as fiber_api
from inventory.api.fibers import api_fiber_audit_log
from inventory.api.cable_photos import api_cable_photos, api_cable_photo_delete
from inventory.api.search import api_global_search
from inventory.api.cable_folders import (
    api_list_cable_folders,
    api_create_cable_folder,
    api_update_cable_folder,
    api_delete_cable_folder,
    api_move_cable_to_folder,
)
from inventory.api import routes as routes_api
from inventory.api import zabbix_lookup as zabbix_lookup_api
from inventory.api.cable_groups import (
    api_list_cable_groups,
    api_create_cable_group,
    api_update_cable_group,
    api_delete_cable_group,
)
from inventory.api.cable_types import (
    api_list_cable_types,
    api_create_cable_type,
    api_update_cable_type,
    api_delete_cable_type,
)
from inventory.api.responsibles import (
    api_list_responsibles,
    api_create_responsible,
)
from inventory.api.maintenance_alert import (
    api_maintenance_recipients,
    api_maintenance_send_alert,
)
from inventory.api.alarm_sources import api_alarm_config_sources
from inventory.api.system_info import api_system_info
from inventory.api.server_stats import api_server_stats
from inventory.api.check_update import api_check_update
from inventory.api.perform_update import api_perform_update
from inventory.api.trace_route import trace_fiber_route
from inventory.api.infrastructure import (
    api_create_infrastructure,
    api_update_infrastructure,
    api_delete_infrastructure,
)

_SPATIAL_ENDPOINTS_AVAILABLE = True
try:
    from inventory.api import spatial as spatial_api
except ImproperlyConfigured:  # pragma: no cover - depends on GDAL availability
    _SPATIAL_ENDPOINTS_AVAILABLE = False
    spatial_api = None  # type: ignore[assignment]
    logger.warning("GDAL not available; skipping spatial inventory APIs")

app_name = "inventory-api"

urlpatterns = [
    # System info / admin panel base
    path("system/info/", api_system_info, name="system-info"),
    path("system/stats/", api_server_stats, name="system-stats"),
    path("system/check-update/", api_check_update, name="system-check-update"),
    path("system/perform-update/", api_perform_update, name="system-perform-update"),
    # Global search
    path("search/", api_global_search, name="global-search"),
    # Cable folders
    path("cable-folders/", api_list_cable_folders, name="cable-folders-list"),
    path("cable-folders/create/", api_create_cable_folder, name="cable-folders-create"),
    path("cable-folders/<int:folder_id>/", api_update_cable_folder, name="cable-folders-update"),
    path("cable-folders/<int:folder_id>/delete/", api_delete_cable_folder, name="cable-folders-delete"),
    path("fibers/<int:cable_id>/move-folder/", api_move_cable_to_folder, name="fiber-move-folder"),
    # Cable Groups
    path(
        "cable-groups/",
        api_list_cable_groups,
        name="cable-groups-list",
    ),
    path(
        "cable-groups/create/",
        api_create_cable_group,
        name="cable-groups-create",
    ),
    path(
        "cable-groups/<int:group_id>/",
        api_update_cable_group,
        name="cable-groups-update",
    ),
    path(
        "cable-groups/<int:group_id>/delete/",
        api_delete_cable_group,
        name="cable-groups-delete",
    ),
    # Cable Types
    path("cable-types/", api_list_cable_types, name="cable-types-list"),
    path("cable-types/create/", api_create_cable_type, name="cable-types-create"),
    path("cable-types/<int:type_id>/", api_update_cable_type, name="cable-types-update"),
    path("cable-types/<int:type_id>/delete/", api_delete_cable_type, name="cable-types-delete"),
    # Responsibles
    path("responsibles/", api_list_responsibles, name="responsibles-list"),
    path("responsibles/create/", api_create_responsible, name="responsibles-create"),
    # Maintenance area notifications
    path("maintenance-alert/recipients/", api_maintenance_recipients, name="maintenance-alert-recipients"),
    path("maintenance-alert/send/", api_maintenance_send_alert, name="maintenance-alert-send"),
    # Alarm configuration sources (users, groups, contacts)
    path("alarm-config-sources/", api_alarm_config_sources, name="alarm-config-sources"),
    # Cable Attachments
    path(
        "cable-attachments/attach/",
        CableAttachmentViewSet.as_view({'post': 'attach'}),
        name="cable-attach",
    ),
    path(
        "cable-attachments/detach/",
        CableAttachmentViewSet.as_view({'post': 'detach'}),
        name="cable-detach",
    ),
    path(
        "devices/select-options/",
        device_api.api_device_select_options,
        name="device-select-options",
    ),
    path(
        "devices/autocomplete/",
        device_api.api_devices_autocomplete,
        name="devices-autocomplete",
    ),
    path(
        "devices/<int:device_id>/ports/",
        device_api.api_device_ports,
        name="device-ports",
    ),
    path(
        "devices/<int:device_id>/ports/live/",
        device_api.api_device_ports_live,
        name="device-ports-live",
    ),
    path(
        "devices/<int:device_id>/ports/optical/",
        device_api.api_device_ports_with_optical,
        name="device-ports-optical",
    ),
    path(
        "ports/<int:port_id>/optical/",
        device_api.api_device_port_optical_status,
        name="port-optical-status",
    ),
    path(
        "ports/<int:port_id>/traffic/",
        device_api.api_port_traffic_history,
        name="port-traffic-history",
    ),
    path(
        "devices/add-from-zabbix/",
        device_api.api_add_device_from_zabbix,
        name="add-device-from-zabbix",
    ),
    path(
        "zabbix/discover-hosts/",
        device_api.api_zabbix_discover_hosts,
        name="zabbix-discover-hosts",
    ),
    path(
        "zabbix/lookup/hosts/",
        zabbix_lookup_api.lookup_hosts,
        name="zabbix-lookup-hosts",
    ),
    path(
        "zabbix/lookup/hosts/grouped/",
        zabbix_lookup_api.lookup_hosts_grouped,
        name="zabbix-lookup-hosts-grouped",
    ),
    path(
        "zabbix/lookup/server-info/",
        zabbix_lookup_api.lookup_zabbix_server_info,
        name="zabbix-server-info",
    ),
    path(
        "zabbix/lookup/host-groups/",
        zabbix_lookup_api.lookup_host_groups,
        name="zabbix-lookup-host-groups",
    ),
    path(
        "zabbix/lookup/hosts/<str:hostid>/status/",
        zabbix_lookup_api.lookup_host_status,
        name="zabbix-lookup-host-status",
    ),
    path(
        "zabbix/lookup/hosts/<str:hostid>/interfaces/",
        zabbix_lookup_api.lookup_host_interfaces,
        name="zabbix-lookup-host-interfaces",
    ),
    path(
        "bulk/",
        device_api.api_bulk_create_inventory,
        name="bulk-create-inventory",
    ),
    path("sites/", device_api.api_sites, name="sites"),
    path(
        "fibers/<int:cable_id>/audit-log/",
        api_fiber_audit_log,
        name="fiber-audit-log",
    ),
    path(
        "fibers/<int:cable_id>/photos/",
        api_cable_photos,
        name="fiber-photos",
    ),
    path(
        "fibers/<int:cable_id>/photos/<int:photo_id>/",
        api_cable_photo_delete,
        name="fiber-photo-delete",
    ),
    path(
        "fibers/<int:cable_id>/oper-status/",
        device_api.api_update_cable_oper_status,
        name="fiber-oper-status",
    ),
    path(
        "fibers/<int:cable_id>/cached-status/",
        fiber_api.api_fiber_cached_optical_status,
        name="fiber-cached-optical-status",
    ),
    path(
        "fibers/<int:cable_id>/cached-live-status/",
        fiber_api.api_fiber_cached_live_status,
        name="fiber-cached-live-status",
    ),
    path(
        "fibers/oper-status/",
        fiber_api.api_fibers_oper_status,
        name="fibers-oper-status",
    ),
    path("fibers/", fiber_api.api_fiber_cables, name="fibers"),
    path(
        "fibers/<int:cable_id>/",
        fiber_api.api_fiber_detail,
        name="fiber-detail",
    ),
    path(
        "fibers/<int:cable_id>/force-delete/",
        fiber_api.api_force_delete_fiber,
        name="fiber-force-delete",
    ),
    path(
        "fibers/<int:cable_id>/live-status/",
        fiber_api.api_fiber_live_status,
        name="fiber-live-status",
    ),
    path(
        "fibers/live-status/",
        fiber_api.api_fibers_live_status_all,
        name="fibers-live-status-all",
    ),
    path(
        "fibers/refresh-status/",
        fiber_api.api_fibers_refresh_status,
        name="fibers-refresh-status",
    ),
    path(
        "fibers/<int:cable_id>/value-mapping/",
        fiber_api.api_cable_value_mapping_status,
        name="fiber-value-mapping-status",
    ),
    path(
        "fibers/import-kml/",
        fiber_api.api_import_fiber_kml,
        name="fibers-import-kml",
    ),
    path(
        "fibers/manual-create/",
        fiber_api.api_create_manual_fiber,
        name="fibers-manual-create",
    ),
    path(
        "fibers/delete-bulk/",
        fiber_api.api_delete_fibers_bulk,
        name="fibers-delete-bulk",
    ),
    path(
        "fibers/import-kml/modal/",
        fiber_api.import_kml_modal,
        name="fibers-import-kml-modal",
    ),
    path(
        "fibers/validate-port/",
        fiber_api.api_validate_port,
        name="fibers-validate-port",
    ),
    path(
        "fibers/validate-name/",
        fiber_api.api_validate_cable_name,
        name="fibers-validate-name",
    ),
    path(
        "fibers/validate-device-coords/",
        fiber_api.api_validate_device_coordinates,
        name="fibers-validate-device-coords",
    ),
    path(
        "fibers/validate-nearby/",
        fiber_api.api_validate_nearby_cables,
        name="fibers-validate-nearby",
    ),
    path(
        "diagnostics/telnet/",
        device_api.api_test_telnet,
        name="diagnostics-telnet",
    ),
    path(
        "diagnostics/ping/",
        device_api.api_test_ping,
        name="diagnostics-ping",
    ),
    path(
        "diagnostics/ping-telnet/",
        device_api.api_test_ping_telnet,
        name="diagnostics-ping-telnet",
    ),
    path(
        "diagnostics/cables/<int:cable_id>/up/",
        device_api.api_test_set_cable_up,
        name="diagnostics-cable-up",
    ),
    path(
        "diagnostics/cables/<int:cable_id>/down/",
        device_api.api_test_set_cable_down,
        name="diagnostics-cable-down",
    ),
    path(
        "diagnostics/cables/<int:cable_id>/unknown/",
        device_api.api_test_set_cable_unknown,
        name="diagnostics-cable-unknown",
    ),
    path(
        "routes/tasks/build/",
        routes_api.enqueue_build_route,
        name="routes-build",
    ),
    path(
        "routes/tasks/batch/",
        routes_api.enqueue_build_routes_batch,
        name="routes-build-batch",
    ),
    path(
        "routes/tasks/import/",
        routes_api.enqueue_import_route,
        name="routes-import",
    ),
    path(
        "routes/tasks/invalidate/",
        routes_api.enqueue_invalidate_route_cache,
        name="routes-invalidate-cache",
    ),
    path(
        "routes/tasks/health/",
        routes_api.enqueue_health_check,
        name="routes-health-check",
    ),
    path(
        "routes/tasks/status/<str:task_id_value>/",
        routes_api.task_status,
        name="routes-task-status",
    ),
    path(
        "routes/tasks/bulk/",
        routes_api.enqueue_bulk_operations,
        name="routes-bulk",
    ),
    # Phase 11 - Device Import System (Nov 2025)
    path(
        "devices/grouped/",
        device_api.api_inventory_grouped,
        name="inventory-grouped",
    ),
    path(
        "devices/zabbix-status/",
        device_api.api_devices_zabbix_status,
        name="devices-zabbix-status",
    ),
    path(
        "devices/import-batch/",
        device_api.api_import_batch,
        name="inventory-import-batch",
    ),
    path(
        "devices/<int:device_id>/",
        device_api.api_device_detail,
        name="device-detail",
    ),
    path(
        "infrastructure/",
        api_create_infrastructure,
        name="infrastructure-create",
    ),
    path(
        "infrastructure/<int:pk>/",
        api_update_infrastructure,
        name="infrastructure-update",
    ),
    path(
        "infrastructure/<int:pk>/delete/",
        api_delete_infrastructure,
        name="infrastructure-delete",
    ),
    path(
        'splice-boxes/<int:id>/matrix/',
        SpliceBoxMatrixView.as_view(),
        name='splice-box-matrix',
    ),
    path(
        'splice-boxes/<int:id>/context/',
        BoxContextView.as_view(),
        name='splice-box-context',
    ),
    path(
        'fusions/',
        CreateFusionView.as_view(),
        name='create-fusion',
    ),
    path(
        'fusions/<int:fiber_id>/',
        DeleteFusionView.as_view(),
        name='delete-fusion',
    ),
    # Trace Route - Optical path tracing (Phase 11.5)
    path(
        'trace-route/',
        trace_fiber_route,
        name='trace-route',
    ),
]

if _GIS_ENDPOINTS_AVAILABLE:
    urlpatterns += [
        # Cable Split
        path(
            "cables/split-at-ceo/",
            CableSplitViewSet.as_view({'post': 'split_at_ceo'}),
            name="cable-split-ceo",
        ),
        # Cable Split V2 (usando CableSegments)
        path(
            "cables/<int:pk>/split-at-ceo-v2/",
            CableSplitV2View.as_view(),
            name="cable-split-ceo-v2",
        ),
        # Attach Loose End (anexar ponta solta após rompimento)
        path(
            "infrastructure/<int:infrastructure_id>/attach-loose-end/",
            AttachLooseEndView.as_view(),
            name="attach-loose-end",
        ),
        # Create Standalone CEO (criar CEO independente, não anexada a cabo)
        path(
            "infrastructure/create-standalone-ceo/",
            CreateStandaloneCEOView.as_view(),
            name="create-standalone-ceo",
        ),
        # List Standalone CEOs (listar CEOs independentes)
        path(
            "infrastructure/standalone-ceos/",
            ListStandaloneCEOsView.as_view(),
            name="list-standalone-ceos",
        ),
        # List Loose Ends (listar pontas soltas de segmentos rompidos)
        path(
            "segments/loose-ends/",
            ListLooseEndsView.as_view(),
            name="list-loose-ends",
        ),
    ]

if _SPATIAL_ENDPOINTS_AVAILABLE:
    urlpatterns += [
        # Spatial queries (Phase 10 - PostGIS)
        path(
            "segments/",
            spatial_api.api_route_segments_bbox,
            name="segments-bbox",
        ),
        path(
            "fibers/bbox/",
            spatial_api.api_fiber_cables_bbox,
            name="fibers-bbox",
        ),
        # Phase 7 - Spatial radius search with ST_DWithin
        path(
            "sites/radius/",
            spatial_api.api_sites_within_radius,
            name="sites-radius",
        ),
    ]
