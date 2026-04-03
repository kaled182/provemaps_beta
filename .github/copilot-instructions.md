# AI Agent Playbook — MapsProveFiber
Django 5 platform for fiber optic network infrastructure with real-time Zabbix monitoring and geospatial route planning.

## Architecture & Boundaries
**[backend/inventory](backend/inventory)** — Authoritative source for all domain models (Site, Device, Port, FiberCable, Route). Business logic flows through **usecases/** (domain operations) and **services/** (cross-boundary coordination). Adapters in **viewsets.py** stay thin—delegate to usecases. Never bypass the inventory layer when creating/modifying network entities. REST APIs exposed at `/api/v1/inventory/*`.

**[backend/monitoring](backend/monitoring)** — Enriches inventory entities with Zabbix health status. Use `get_devices_with_zabbix()` and `build_zabbix_map()` usecases to combine inventory + monitoring data instead of directly calling Zabbix APIs.

**[backend/integrations/zabbix](backend/integrations/zabbix)** — Single gateway to Zabbix API. Always use `zabbix_service.zabbix_request()` for API calls—provides token caching, circuit breaker, retries, and Prometheus metrics. Use `safe_cache_get/set/delete` wrappers to tolerate Redis outages gracefully.

**[backend/maps_view](backend/maps_view)** — Dashboard views and WebSocket publisher. Cache strategy: [cache_swr.py](backend/maps_view/cache_swr.py) implements stale-while-revalidate pattern (30s fresh, 60s stale). Real-time updates flow through [realtime/publisher.py](backend/maps_view/realtime/publisher.py) using `broadcast_dashboard_status()` and Channels groups.

**[backend/core](backend/core)** — Foundation layer with settings, root URLs, ASGI/WSGI configs, Channels routing, middleware, and health checks. Django settings split into [settings/dev.py](backend/settings/dev.py), [settings/prod.py](backend/settings/prod.py), [settings/test.py](backend/settings/test.py) using `django-environ` for secrets.

**[frontend/src](frontend/src)** — Vue 3 + Vite + Pinia SPA. Always mutate via [composables/useApi.js](frontend/src/composables/useApi.js) to ensure CSRF tokens and error handling. Stores in [stores/](frontend/src/stores) expect SWR-compatible payloads with `data`/`timestamp`/`is_stale` keys.

## Code & Data Patterns
**Usecase pattern** — Business logic lives in `inventory/usecases/*.py` and returns plain dicts (DTOs). Serializers in `serializers.py` map these 1:1 without rearranging keys (order-sensitive tests validate field order). Example: `usecases/fibers.py::fiber_to_payload()` returns structured dict consumed by `FiberCableSerializer`.

**Cache invalidation** — After mutating inventory entities (cables, ports, routes), always call both:
1. `inventory.cache.fibers.invalidate_fiber_cache()` — Clears fiber list cache
2. `maps_view.cache_swr.invalidate_dashboard_cache()` — Clears dashboard SWR cache  
Available cache modules: [cache/fibers.py](backend/inventory/cache/fibers.py), [cache/radius_search.py](backend/inventory/cache/radius_search.py) with Prometheus metrics for cache operations.

**Background tasks** — Celery tasks live in app-level `tasks.py` files and register via [core/celery.py](backend/core/celery.py). Choose queues: `default` (general), `maps` (dashboard refresh), `zabbix` (monitoring sync). Configure periodic tasks in `beat_schedule` dict in celery.py. Current schedules: dashboard (60s), fiber list (180s), cable status (120s), optical levels (300s), inventory sync (24h), service account rotation (1h).

**Optical telemetry** — Fetch port optical power via `inventory.tasks.fetch_port_optical_snapshot()` (queues Celery task) or `inventory.domain.optical` helpers—never call Zabbix directly. Data flows: Zabbix → task → inventory cache → dashboard.

**WebSocket payloads** — Assemble messages using [maps_view/realtime/events.py](backend/maps_view/realtime/events.py) helpers like `build_dashboard_payload()` before broadcasting via `publisher.broadcast_dashboard_status()`. Payloads must include `timestamp` and mirror REST API structure. Frontend connects via `/ws/dashboard/status/` (Channels consumer).

## Workflows
**Development setup** — Run `docker compose -f docker/docker-compose.yml up` or `make up` to start all services (web, postgres, redis, celery). For local Django dev without Docker: `python backend/manage.py runserver 0.0.0.0:8000` after setting `DJANGO_SETTINGS_MODULE=settings.dev`. Requires `.env` file with Zabbix credentials (see `.env.example`).

**Testing** — Execute from **repo root** (not backend/): `pytest -q` (fast) or `pytest -v` (verbose). Config in [pytest.ini](pytest.ini) sets `pythonpath = . backend` and loads `settings.test` (SQLite default, set `TEST_DB_ENGINE=mysql` for MariaDB). Celery eager mode enabled in test settings—no broker needed. Run specific suites: `pytest backend/inventory/tests/test_usecases.py -v`. Use markers: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.zabbix`, `@pytest.mark.api`, `@pytest.mark.celery`.

**Test organization** — Focused suites in [backend/inventory/tests](backend/inventory/tests), integration tests at root like [test_fiber_modal_data_flow.py](test_fiber_modal_data_flow.py). Conftest at [backend/conftest.py](backend/conftest.py) provides fixtures. Coverage: `pytest --cov --cov-report=html` or `make test-coverage`.

**Code quality** — Format: `make fmt` (black line-length=100, isort profile=black, ruff --fix). Lint: `make lint`. Pre-commit hooks run automatically (black, ruff, isort, shellcheck, hadolint). Frontend: `npm run dev` in frontend/, tests via `npm run test:unit`. Static assets: `make collectstatic` for production.

**Migrations** — `make migrate` or `python backend/manage.py migrate`. Generate: `make makemigrations`. Database reset (Docker): `make resetdb` (drops DB, re-migrates, creates admin user). Always run migrations from repo root to ensure proper path resolution.

## Integrations & Caching
**Zabbix API** — Use `zabbix_service.zabbix_request(method, params)` for all API calls. Features: automatic token rotation, exponential backoff retries, connection pooling, circuit breaker, Prometheus metrics (`zabbix_api_requests_total`, `zabbix_api_failures_total`). Token cached 1 hour via `safe_cache_set()`.

**SWR caching** — Dashboard data uses stale-while-revalidate: fresh for 30s, serves stale for 60s while background Celery task refreshes. See [maps_view/cache_swr.py](backend/maps_view/cache_swr.py) `SWRCache` class. Frontend displays "stale data" banner when `is_stale: true`.

**Redis resilience** — Use `safe_cache_get/set/delete` wrappers from `integrations/zabbix/zabbix_service.py` to gracefully handle Redis outages. App remains functional with degraded caching instead of crashing.

**Periodic tasks** — Defined in `CELERYBEAT_SCHEDULE` dict in [core/celery.py](backend/core/celery.py). Existing schedules: dashboard refresh (60s), optical snapshots (5m), Zabbix inventory sync (24h), service account rotation (1h). Add new tasks here.

## Frontend Notes
**State management** — Pinia stores in [frontend/src/stores](frontend/src/stores). Always refetch detail payloads before opening edit modals (`await api.get(/api/v1/inventory/fibers/${id}/)`). SWR pattern: store `{ data, timestamp, is_stale }` and display staleness indicators.

**WebSockets** — Connect via [composables/useWebSocket.js](frontend/src/composables/useWebSocket.js) to `/ws/dashboard/status/` (Channels consumer). Message types: `dashboard.status` (full state), `cable.status` (incremental updates). Payload structure must match publisher outputs in [maps_view/realtime/publisher.py](backend/maps_view/realtime/publisher.py).

**CSRF tokens** — `useApi()` composable handles CSRF headers automatically via `getCsrfToken()` (reads `window.CSRF_TOKEN` or `csrftoken` cookie). Never use raw `fetch()` for mutations—always use `api.post/put/patch/delete`.

## References
**Architecture** — [doc/architecture/README.md](doc/architecture/README.md) for system design, [doc/process/AGENTS.md](doc/process/AGENTS.md) for development workflows.
**Release notes** — [doc/releases/v2.0.0](doc/releases/v2.0.0) covers modular refactor migration.
**Troubleshooting** — [doc/troubleshooting](doc/troubleshooting) for common issues, [doc/operations](doc/operations) for deployment.
