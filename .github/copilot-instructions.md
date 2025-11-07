## Copilot Instructions — MapsProveFiber
Concise, project-specific guidance for AI code agents. Focus on CURRENT patterns (not aspirations) so you can act safely and fast.

### Core Architecture
- Django 5 multi-app; `core` is the spine (settings, URLs, metrics, ASGI/WSGI, Channels routing).
- Primary domains: `inventory` (authoritative Site/Device/Port), `maps_view` (real-time dashboard), `routes_builder` (fiber/KML + power calc), `setup_app` (runtime credentials), Zabbix integration via `integrations/zabbix` + `monitoring/usecases.py`.
- Async: Celery workers (`celery -A core worker` / beat) plus Channels websocket at `ws/dashboard/status/` (see `core/routing.py`).
- Persistence: MySQL/MariaDB (prod) or SQLite (local). Redis optional; code must degrade gracefully if absent.

### Observability & Health
- Prometheus via `django_prometheus`; metrics endpoint `/metrics/` (may redirect to `/metrics/metrics`). Custom static version metric in `core/metrics_static_version.py`.
- Health checks in `core/views_health.py`; Makefile wrappers: `make health`, `make ready`, `make live`.
- When adding endpoints respect settings flags in `settings/base.py` (`ENABLE_DIAGNOSTIC_ENDPOINTS`, `HEALTHCHECK_*`).

### Service Layer Pattern
- Keep business logic in each app's `services.py`; views stay thin (see `maps_view/views.py` and `routes_builder/views.py`).
- Routes Builder returns dataclasses (`RouteBuildContext`, `RouteBuildResult`) from `routes_builder/services.py`—preserve these shapes.
- Dashboard data retrieval uses SWR cache helper `maps_view.cache_swr.get_dashboard_cached`; refresh via Celery `refresh_dashboard_cache_task.delay`.

### Zabbix Integration
- Never direct `requests`; use `integrations.zabbix.zabbix_service` helpers (`zabbix_request`, safe cache wrappers). Client resiliency lives in `integrations/zabbix/client.py` (retry, circuit breaker, Prom metrics).
- Combine inventory + Zabbix status in `monitoring/usecases.py` (also re-exported by `maps_view/services.py` for backwards compatibility).

### Runtime Config & Secrets
- Dynamic credentials handled by `setup_app/services/runtime_settings.py` (`FirstTimeSetup`). Call `reload_config()` after updates.
- Don’t log secrets; rely on provided context processors + encrypted storage (Fernet).

### Static Assets & Templates
- Append `?v={{ STATIC_ASSET_VERSION }}` (from `setup_app.context_processors.static_version`) to `{% static %}` references—enforces cache busting. Keep ManifestStaticFilesStorage assumptions intact.

### Caching & Redis Absence
- Use `safe_cache_*` (in `integrations/zabbix/zabbix_service.py`) instead of assuming Redis present. If adding new caches, mirror existing graceful degradation style.
- Reuse existing cache key constants (`CACHE_KEY_*`) when invalidating route builder or dashboard data.

### Tests & Quality Workflow
- Run with `pytest -q`; domain-specific tests under `routes_builder/tests` and root `tests/`. Use fixtures from `routes_builder/tests/conftest.py` for inventory object creation.
- Formatting: `make fmt` (ruff+black+isort); lint: `make lint`. Maintain dataclass field order for stable tests.

### Adding APIs / Features
- Place new endpoints in the owning app’s `urls.py`; include them via `core/urls.py` namespace. Keep response shaping consistent with existing serializers.
- For real-time features, broadcast via `maps_view.realtime.publisher.broadcast_dashboard_status`—ensure `CHANNEL_LAYER_URL` configured for non-local fan-out.

### Example Safe Extension
- To add a cached dashboard metric: implement fetch in `maps_view/services.py`, wrap with SWR in `cache_swr.py`, expose via a thin view, and refresh through Celery task.

### Quick Dev Commands
- `make run` (dev server), `make up` (Compose), `make migrate`, `make superuser`, `celery -A core worker`, `celery -A core beat`, `make fmt`, `make lint`.

Feedback: Tell us if any section is unclear or missing (e.g., deployment quirks, data model edges) so we can iterate.
