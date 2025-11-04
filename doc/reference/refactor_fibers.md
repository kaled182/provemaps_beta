# Fiber and Inventory Flow Refactor

## Iteration 1 (completed)
- Optical helper moved to `zabbix_api/domain/optical.py`.
- Geographic and Haversine calculations moved to `zabbix_api/domain/geometry.py`.
- Primary use case in `zabbix_api/usecases/fibers.py` now covers KML import, manual creation, live status, and bulk refresh.
- Fiber views (`zabbix_api/inventory_fibers.py`) translate `HttpRequest` to JSON responses by delegating to use cases.
- Standardised error handling via `FiberValidationError` and `FiberUseCaseError`.

## Iteration 2 (inventory) in progress
- `zabbix_api/usecases/inventory.py` centralises device, port, and site discovery plus history operations with typed errors (`InventoryNotFound`, `InventoryValidationError`).
- Inventory views (`api_device_*`, `api_sites`, `api_port_traffic_history`, `api_add_device_from_zabbix`) are thin wrappers on top of the use cases.
- Tasks and management commands (`zabbix_api/tasks.py`, `management/commands/warm_optical_cache.py`) reuse `_fetch_port_optical_snapshot` from the domain layer.
- `zabbix_api/inventory.py` kept backward compatibility (aliases for `combine_cable_status`, `zabbix_request`) and applies `staff_guard` only where required.

## Planned follow-up work
1. Extract `api_update_cable_oper_status` into a use case inside `zabbix_api/usecases/fibers.py`, reducing direct model access in views.
2. Review `api_zabbix_discover_hosts` and `api_bulk_create_inventory` for granular validation, partial feedback, and structured logging.
3. Add unit tests targeting `usecases/fibers.py` and `usecases/inventory.py` (error scenarios, incremental traffic mode, discovery without items).
4. Continue modularising `zabbix_service` by splitting geolocation and ping responsibilities into dedicated modules as scheduled in the roadmap.
