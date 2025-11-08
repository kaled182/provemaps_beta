"""Compatibility shim for legacy routes_builder task views."""

from __future__ import annotations

from inventory.api import routes as inventory_routes_api

enqueue_build_route = inventory_routes_api.enqueue_build_route
enqueue_build_routes_batch = inventory_routes_api.enqueue_build_routes_batch
enqueue_import_route = inventory_routes_api.enqueue_import_route
enqueue_invalidate_route_cache = (
    inventory_routes_api.enqueue_invalidate_route_cache
)
enqueue_health_check = inventory_routes_api.enqueue_health_check
task_status = inventory_routes_api.task_status
enqueue_bulk_operations = inventory_routes_api.enqueue_bulk_operations

