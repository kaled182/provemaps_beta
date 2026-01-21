# AI Agent Playbook — MapsProveFiber
Fiber network management stack using Django 5, Celery, Channels, Vue 3, and Zabbix.

## Architecture & Boundaries
- [backend/inventory](backend/inventory) owns authoritative models and domain rules; add new flows under [backend/inventory/usecases](backend/inventory/usecases) or [backend/inventory/services](backend/inventory/services) and keep adapters in [backend/inventory/viewsets.py](backend/inventory/viewsets.py) thin.
- [backend/monitoring](backend/monitoring) enriches inventory payloads with live health; reuse its usecases when surfacing combined status in REST or websockets.
- [backend/integrations/zabbix](backend/integrations/zabbix) is the only gateway to Zabbix; call helpers in [backend/integrations/zabbix/zabbix_service.py](backend/integrations/zabbix/zabbix_service.py) so retries, token caching, and metrics stay consistent.
- [backend/maps_view](backend/maps_view) serves the dashboard; rely on [backend/maps_view/cache_swr.py](backend/maps_view/cache_swr.py) for stale-while-revalidate data and [backend/maps_view/realtime/publisher.py](backend/maps_view/realtime/publisher.py) for websocket fanout.
- Frontend lives in [frontend/src](frontend/src) (Vite + Pinia); mutate through [frontend/src/composables/useApi.js](frontend/src/composables/useApi.js) to ensure CSRF headers and uniform error handling.

## Code & Data Patterns
- Business logic returns DTO-style dicts from usecases; serializers map them without rearranging keys (order-sensitive tests cover this).
- Fiber payloads are cached via [backend/inventory/cache/fibers.py](backend/inventory/cache/fibers.py); call invalidate_fiber_cache whenever cables, ports, or routes change.
- Background tasks belong in app tasks.py and are wired through [backend/core/celery.py](backend/core/celery.py); choose queues default, maps, or zabbix to match load profiles.
- Optical telemetry flows through inventory.domain.optical and [backend/inventory/tasks.py](backend/inventory/tasks.py); reuse fetch_port_optical_snapshot instead of direct Zabbix calls.
- Dashboard payloads should be assembled with helpers in [backend/maps_view/realtime/events.py](backend/maps_view/realtime/events.py) before broadcasting.

## Workflows
- Start the stack with make up (wraps docker compose up); run the Django server through docker compose exec web python manage.py runserver 0.0.0.0:8000 for parity with production.
- Backend tests execute from repo root; pytest (configured via [pytest.ini](pytest.ini)) loads settings.test and enables Celery eager mode, so brokers are optional during CI.
- Focused suites live under [backend/inventory/tests](backend/inventory/tests) plus root API checks like [test_ports_endpoint.py](test_ports_endpoint.py) and [test_fiber_modal_data_flow.py](test_fiber_modal_data_flow.py).
- Format with make fmt (black, isort, ruff --fix) and lint with make lint; frontend dev runs npm run dev and unit tests via npm run test:unit inside frontend.

## Integrations & Caching
- Always fetch live monitoring data with zabbix_service.zabbix_request; token rotation, retries, and Prometheus counters are handled there.
- After mutating inventory entities, clear both invalidate_fiber_cache and maps_view.cache_swr.invalidate_dashboard_cache so dashboards refresh immediately.
- Celery beat schedules for caches, optical snapshots, and Zabbix sync live in backend/core/celery.py; extend that map when adding recurring work.
- Redis outages are tolerated by safe_cache_* wrappers—lean on them instead of touching django.core.cache directly in integration code.

## Frontend Notes
- Pinia stores in [frontend/src/stores](frontend/src/stores) expect SWR-friendly API responses; refetch detail payloads right before editing modals to avoid stale state.
- Websocket consumers rely on [frontend/src/composables/useWebSocket.js](frontend/src/composables/useWebSocket.js); payload contracts should mirror publisher outputs to keep dashboards stable.

## References
- Architecture deep dives: [doc/architecture](doc/architecture); process guardrails: [doc/process/AGENTS.md](doc/process/AGENTS.md); release changes: [doc/releases/v2.0.0](doc/releases/v2.0.0).
