## Copilot Instructions — MapsProveFiber
Concise, project-specific guidance for AI code agents. Focus on CURRENT patterns so you can deliver safe changes fast.

### Architecture & Apps
- Django 5 project rooted in `backend/`; `settings/base.py` loads env defaults (MySQL/MariaDB with optional PostGIS, Redis optional) and defaults to `DJANGO_SETTINGS_MODULE=settings.dev`.
- `core/` hosts settings glue (ASGI/WSGI, Celery bootstrap, Prometheus metrics, health views, root URLs).
- `inventory/` owns canonical models (Site, Device, Port, FiberCable, Route, etc.) plus services like `inventory/routes/services.py`; the legacy routes-builder APIs now live under `inventory.routes`.
- `maps_view/` drives the dashboard (Django templates + optional Vue SPA) and real-time flows; business logic is sourced from `monitoring/usecases.py` via thin shims.
- `integrations/zabbix/` encapsulates JSON-RPC access and cache helpers; `setup_app/` persists runtime credentials with `FirstTimeSetup` records (`runtime_settings.get_runtime_config`).

### Async, Realtime & Caching
- Celery configured in `core/celery.py` (queues: `default`, `zabbix`, `maps`); run workers with `celery -A core worker -Q <queue>` and beat to execute cache warmers (`inventory.tasks.*`, `monitoring.tasks.refresh_dashboard_cache_task`).
- Channels routing defined in `core/routing.py`; use `maps_view.realtime.publisher.broadcast_dashboard_status` / `broadcast_cable_status_update` instead of direct `group_send`.
- Dashboard endpoints reuse SWR helpers in `maps_view/cache_swr.py`; pair `get_dashboard_cached` with `refresh_dashboard_cache_task.delay` to refresh data safely.
- Fiber listings follow the same pattern via `inventory/cache/fibers.py`; the Celery task `inventory.tasks.refresh_fiber_list_cache` populates cache + websocket updates.

### Data & Integration Boundaries
- Never call Zabbix with raw `requests`; reuse `integrations.zabbix.zabbix_service.zabbix_request` and `safe_cache_*`. `monitoring/usecases.py` is the canonical join between inventory rows and live Zabbix status.
- Fiber/route workflows rely on typed services (`RouteBuildContext`, `RouteBuildResult`) and usecases in `inventory/usecases/fibers.py`; invalidate caches via `invalidate_fiber_cache` or `invalidate_route_cache` when mutating data.
- Runtime secrets (Zabbix, Google Maps, DB overrides) flow through `setup_app.services.runtime_settings`; call `reload_config()` after persisting `FirstTimeSetup`.
- Feature flags: `USE_VUE_DASHBOARD` + `VUE_DASHBOARD_ROLLOUT_PERCENTAGE` gate the SPA; keep `{% static 'vue-spa/...' %}?v={{ STATIC_ASSET_VERSION }}` intact for cache busting.

### Developer Workflow
- Activate the venv and rely on Makefile exports; run server with `make run` (uses `settings.dev`).
- Key commands: `make migrate`, `make fmt`, `make lint`, `make test`, `make health|ready|live`.
- Tests run with `pytest -q` (`pyproject.toml` points to `settings.test` and strict markers); integration suites live under `backend/tests/` plus app-specific `tests/` folders.
- Celery worker/beat: `celery -A core worker -l info` and `celery -A core beat -l info`; queue selection matters (route/fiber jobs target `maps`, Zabbix polling on `zabbix`).
- Frontend lives in `frontend/` (Vite + Vue 3); `npm run build` outputs to `backend/static/vue-spa/`, consumed by `maps_view/templates/spa.html` behind the feature flag.
- Docker Compose (`make up`) runs the full stack; when Redis/MySQL are absent the code falls back to SQLite and locmem caches—ensure new features stay resilient.

### Testing & Quality Signals
- Preserve dataclass field order and payload shapes (numerous assertions in `backend/tests/routes` and SWR tests expect deterministic metadata).
- Celery runs eagerly in tests; new tasks must tolerate `CELERY_TASK_ALWAYS_EAGER=True` and skip external calls when brokers are offline.
- Prometheus metrics live at `/metrics/`; update via helpers in `core/metrics_*` (`metrics_static_version`, `metrics_celery`).
- WebSocket consumers in `maps_view/realtime/consumers.py` assume authenticated sessions; route new realtime data through publisher helpers so Channels groups stay consistent.

### When Extending
- Place business rules inside `services/` or `usecases/` modules and keep views/serializers thin; reuse existing DTOs like `RouteBuildResult` or fiber payload dicts.
- Prefer resilient cache helpers (`safe_cache_*`, `SWRCache`, `invalidate_*`) over bare `cache.*` calls to handle missing Redis.
- Update Celery routing/beat entries in `core/celery.py` when adding long-running or scheduled jobs and align queue choice with workload type.
- Wire new endpoints through the owning app’s `urls.py` and include them in `core/urls.py`; respect `settings.ENABLE_DIAGNOSTIC_ENDPOINTS` gates for health/diagnostic features.

Feedback: Flag unclear areas (e.g., PostGIS rollout, Vue SPA expectations) so we can extend these instructions.
