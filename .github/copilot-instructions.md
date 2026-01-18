# AI Agent Playbook — MapsProveFiber
Fiber optic network management platform using Django 5 backend, Vue 3 SPA, Channels, Celery, and Zabbix.

## Architecture
- [backend/inventory](backend/inventory) is the authoritative inventory (Site, Device, Port, FiberCable, Route); expose new behaviour via [backend/inventory/usecases](backend/inventory/usecases) or [backend/inventory/services](backend/inventory/services) and keep DRF viewsets thin in [backend/inventory/viewsets.py](backend/inventory/viewsets.py).
- [backend/monitoring](backend/monitoring) enriches inventory data with live Zabbix health; reuse its fetchers when surfacing status in APIs.
- [backend/integrations/zabbix](backend/integrations/zabbix) wraps all Zabbix JSON-RPC traffic with retry, circuit breaker, and Prometheus metrics—call `zabbix_service.zabbix_request()` instead of raw HTTP.
- [backend/maps_view](backend/maps_view) powers the real-time dashboard (Channels consumers, SWR caching, Celery cache warmers) and publishes websocket updates through [backend/maps_view/realtime/publisher.py](backend/maps_view/realtime/publisher.py).
- [frontend/src](frontend/src) is a Vite SPA with Pinia stores; all mutating requests must go through the `useApi` composable for automatic CSRF handling.

## Workflow
- Stand up dependencies through Docker: `cd docker && docker compose up -d`, then run app code via `docker compose exec web python manage.py runserver 0.0.0.0:8000` when needed.
- Local shortcuts live in the root Makefile: `make up`, `make down`, `make migrate`, `make test`, `make fmt`, `make lint`.
- Frontend iterates with `npm install` and `npm run dev` inside `frontend`; build artifacts land in `backend/staticfiles/vue-spa`.
- Use PostGIS-enabled containers; SQLite fixtures exist for quick tests but skip spatial features.

## Patterns & Conventions
- Keep business rules inside usecases/services and return DTOs; serializers simply map DTOs without reordering fields (tests assert key order).
- After inventory mutations, invalidate caches via helpers like [backend/inventory/cache](backend/inventory/cache) and [backend/inventory/routes/services.py](backend/inventory/routes/services.py); SWR caches require explicit invalidation.
- Spatial data expects SRID 4326 LineString geometries; helpers in [backend/inventory/spatial.py](backend/inventory/spatial.py) compute lengths and bounds.
- Device import and syncing flows reuse regex-based rules in [backend/inventory/usecases/devices.py](backend/inventory/usecases/devices.py); follow existing priority logic when extending.
- When exposing metrics or background work, register Celery tasks in app `tasks.py` and scheduler entries in [backend/core/celery.py](backend/core/celery.py) with the proper queue (`default`, `maps`, `zabbix`).
- Vue components rely on SWR patterns; fetch fresh detail payloads before opening edit modals to avoid stale state.

## Testing & Quality
- Fast backend suite: `make test`; full PostGIS run: `docker compose exec web pytest`.
- Frontend unit tests: `npm run test:unit`; Playwright E2E: `npm run test:e2e`.
- Formatting and linting enforced by `make fmt` (black, ruff --fix, isort) and `make lint`.

## Real-Time & Integrations
- Dashboard data is cached through [backend/maps_view/cache_swr.py](backend/maps_view/cache_swr.py); long-running refresh jobs live in [backend/monitoring/tasks.py](backend/monitoring/tasks.py).
- Use publisher helpers to fan out websocket events after any device/fiber mutation; do not touch Channels layers directly.
- Zabbix sync tasks populate monitoring state; avoid direct DB writes—let usecases orchestrate sync and validation.

## Security & Configuration
- Secrets and runtime overrides are stored via [backend/setup_app/services/runtime_settings.py](backend/setup_app/services/runtime_settings.py); never hardcode credentials.
- Respect environment flags defined in [docker/docker-compose.yml](docker/docker-compose.yml) (e.g., `USE_VUE_DASHBOARD`, rollout percentages) when adding feature toggles.

## Docs & Further Reading
- Architecture deep dives live in [doc/architecture](doc/architecture); workflow/process guidance in [doc/process/AGENTS.md](doc/process/AGENTS.md).
- API specifics and breaking changes are tracked under [doc/api](doc/api) and [doc/releases/v2.0.0](doc/releases/v2.0.0).
