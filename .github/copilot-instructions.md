## Copilot Instructions — MapsProveFiber

> Concise, project-specific guidance for AI code agents.  
> **Focus on CURRENT patterns** so you can deliver safe changes fast.  
> See also: `doc/process/AGENTS.md`, `doc/architecture/MODULES.md`, `doc/architecture/DATA_FLOW.md`

---

### Documentation Standards (CRITICAL)

**File Organization Rules**:
- ❌ **NEVER create .md files in project root** (except README.md)
- ✅ **ALL documentation belongs in `doc/` directory**
- ✅ **Use existing subdirectories** or create new ones as needed:
  - `doc/troubleshooting/` — Bug fixes, problem resolutions, incident reports
  - `doc/reports/rollout/` — Deployment reports, rollout documentation
  - `doc/reports/fixes/` — Bug fix summaries, applied patches
  - `doc/reports/phases/` — Project phase completion reports
  - `doc/reports/` — General reports, sprint summaries
  - `doc/guides/testing/` — Testing guides, validation checklists
  - `doc/guides/` — How-to guides, tutorials
  - `doc/roadmap/` — Future plans, roadmap documents
  - `doc/operations/` — Deployment, monitoring, operations guides
  - `doc/architecture/` — System architecture documentation
  - `doc/developer/` — Developer guides, setup instructions
  - `doc/api/` — API documentation
  - `doc/security/` — Security policies, compliance
  - `doc/releases/` — Version changelogs, release notes

**When documenting work**:
1. Choose appropriate `doc/` subdirectory (create new one if needed)
2. Use descriptive filename: `COMPONENT_PURPOSE.md` (e.g., `DOCKER_CELERY_FIX.md`)
3. Never pollute project root with documentation files
4. Update existing docs when relevant instead of creating new files

---

### Environment & Infrastructure (CRITICAL)

**Windows Development - Docker-Only Architecture**:
- ❌ **NEVER run services directly on Windows** (no local PostgreSQL, MySQL, Redis, Celery)
- ✅ **ALL services run in Docker Compose** (`docker/docker-compose.yml`)
- 🐍 **Python venv on Windows**: ONLY for IDE/linting/autocomplete — NOT for running services
- 🐳 **Active containers** (when running `docker compose up`):
  - `docker-postgres-1`: PostgreSQL 16 + PostGIS 3.4 (host port `5433` → container port `5432`)
  - `docker-redis-1`: Redis 7 (host port `6379`)
  - `docker-web-1`: Django 5 + Gunicorn + Uvicorn workers
  - `docker-celery_worker-1`: Celery worker (queues: default, zabbix, maps)
  - `docker-celery_beat-1`: Celery beat scheduler

**Database access patterns**:
- From Windows host: `DB_HOST=localhost`, `DB_PORT=5433`, `DB_ENGINE=postgis`
- From inside Docker: `DB_HOST=postgres`, `DB_PORT=5432`, `DB_ENGINE=postgis`
- Credentials: `DB_USER=app`, `DB_PASSWORD=app`, `DB_NAME=app` (dev environment)
- **NEVER use SQLite in production** — spatial features require PostGIS

**Common Docker operations**:
```powershell
# Start all services
cd docker; docker compose up -d

# Run migrations (CORRECT way)
docker compose exec web python manage.py migrate

# Create superuser (CORRECT way)
docker compose exec web python manage.py createsuperuser

# Access Django shell
docker compose exec web python manage.py shell

# Run tests with real PostgreSQL
docker compose exec web pytest

# Check service status
docker compose ps

# View logs
docker compose logs -f web
docker compose logs -f celery_worker

# Stop all services
docker compose down

# CRITICAL: Rebuild after code changes
# When templates, Python code, or static files change:
docker compose down
docker compose build --no-cache web  # Rebuild web image
docker compose up -d

# Quick restart (for template-only changes with mounted volumes)
docker compose restart web

# IMPORTANT: Build location matters!
# ✅ CORRECT: cd docker; docker compose build
# ❌ WRONG: docker compose build (from project root without -f flag)
```

---

### Architecture & Apps

**Django 5 monolith** (v2.0.0 - modular refactor complete):
- Root: `backend/`; settings in `settings/{base,dev,prod,test}.py`; default `DJANGO_SETTINGS_MODULE=settings.dev`
- Database: **PostgreSQL 16 + PostGIS 3.4** (production & Docker dev); SQLite fallback for quick tests only
- Async stack: Celery (queues: `default`, `zabbix`, `maps`) + Redis broker; Django Channels for WebSockets
- ASGI/WSGI: Gunicorn with Uvicorn workers (`core.asgi:application`)

**Core apps** (active):
- `core/` — ASGI/WSGI, Celery config, Channels routing, health endpoints (`/healthz`, `/ready`, `/live`), Prometheus metrics (`/metrics/`)
- `inventory/` — Authoritative models (`Site`, `Device`, `Port`, `FiberCable`, `Route`, `RouteSegment`, `RouteEvent`); REST APIs at `/api/v1/inventory/*`; typed services in `inventory/routes/services.py` (`RouteBuildContext`, `RouteBuildResult`); spatial queries in `inventory/api/spatial.py`
- `maps_view/` — Network dashboard (Django templates + optional Vue 3 SPA); SWR cache pattern; WebSocket publisher helpers (`broadcast_dashboard_status`, `broadcast_cable_status_update`)
- `monitoring/` — Usecases joining inventory + Zabbix status (`monitoring/usecases.py`: `get_devices_with_zabbix`, `build_zabbix_map`, `HostStatusProcessor`)
- `integrations/zabbix/` — Resilient JSON-RPC client with circuit breaker, exponential backoff, connection pooling; **never bypass** `zabbix_request` or `safe_cache_*` helpers
- `setup_app/` — Runtime credential storage (Fernet-encrypted `FirstTimeSetup` model); access via `setup_app.services.runtime_settings.get_runtime_config()`

**Active specialized apps**:
- `service_accounts/` — Service account lifecycle management with token rotation, audit logging, webhook notifications
  - Models: `ServiceAccount`, `ServiceAccountToken`, `ServiceAccountAuditLog`
  - Auto-rotation: Celery task (`tasks.py`) enforces rotation policies based on `auto_rotate_days`
  - Webhooks: Notification system for pre-rotation warnings (`notify_before_days`)
  - Configured via: `SERVICE_ACCOUNT_ROTATION_INTERVAL_SECONDS`, `SERVICE_ACCOUNT_WEBHOOK_*_TIMEOUT`

**Archived/placeholder** apps:
- `routes_builder/` — **RETIRED** (Nov 2025); route logic migrated to `inventory.routes` and `inventory.models_routes`
- `dwdm/`, `gpon/` — Placeholder modules for future features; minimal or no active code


---

### Async, Realtime & Caching

**Celery** (`core/celery.py`):
- Queues: `default` (general), `zabbix` (external polling), `maps` (route/fiber computation)
- Run: `celery -A core worker -Q <queue> -l info` + `celery -A core beat -l info` (scheduled tasks)
- Test mode: `CELERY_TASK_ALWAYS_EAGER=True` in `settings.test`; new tasks must handle eager execution gracefully

**WebSocket** (`core/routing.py` → `maps_view/realtime/consumers.py`):
- Routes: `/ws/dashboard/status/` (group: `dashboard_status`), cable status (group: `cable_status`)
- **Always use publisher helpers**: `broadcast_dashboard_status(hosts_data)`, `broadcast_cable_status_update(cable_list)`
- Consumers expect authenticated Django sessions; no anonymous access

**SWR (Stale-While-Revalidate)** pattern (`maps_view/cache_swr.py`):
- Class: `SWRCache(key, fresh_ttl=30, stale_ttl=60)` — serves stale data immediately, triggers async refresh
- Dashboard: `get_dashboard_cached()` + `monitoring.tasks.refresh_dashboard_cache_task.delay()`
- Fiber lists: `inventory/cache/fibers.py` + `inventory.tasks.refresh_fiber_list_cache`
- **Prefer resilient helpers** (`safe_cache_get`, `safe_cache_set`) to tolerate missing Redis (falls back to locmem/dummy cache)

**Cache invalidation**:
- Fiber mutations → `inventory.cache.fibers.invalidate_fiber_cache()`
- Route mutations → `inventory.routes.services.invalidate_route_cache(route_id)` → Celery task on `maps` queue


---

### Data & Integration Boundaries

**Zabbix integration**:
- **Never use raw `requests`**; always call `integrations.zabbix.zabbix_service.zabbix_request(method, params)`
- Circuit breaker + retry logic built-in; Prometheus metrics track failures/latencies
- Cache helpers: `safe_cache_get`, `safe_cache_set` (handle Redis outages gracefully)
- Join with inventory: `monitoring.usecases.get_devices_with_zabbix()` fetches `Device` rows + live Zabbix status in single call

**Inventory workflows**:
- **Services layer**: `inventory/routes/services.py`, `inventory/usecases/fibers.py` — business logic lives here, NOT in views
- Typed DTOs: `RouteBuildContext`, `RouteBuildResult` (dataclasses with strict field order; tests assert on exact shapes)
- ViewSets are thin wrappers: `inventory/viewsets.py` → call usecases → return serialized responses

**Runtime secrets**:
- Stored in `setup_app.models.FirstTimeSetup` (Fernet-encrypted with `settings.FERNET_KEYS`)
- Access via `setup_app.services.runtime_settings.get_runtime_config()` (LRU-cached; call `reload_config()` after DB updates)
- Env vars in `settings/base.py` provide fallbacks; production requires real secrets

**Feature flags**:
- `USE_VUE_DASHBOARD` + `VUE_DASHBOARD_ROLLOUT_PERCENTAGE` — gate Vue 3 SPA in `maps_view/templates/spa.html`
  - **Current status (Nov 2025)**: Active canary rollout at 10% (configured in `.env` and `database/runtime.env`)
  - Development: 100% rollout (`settings/dev.py`)
  - Canary logic: User assignment based on MD5 hash of session ID for consistency
  - View logic: `maps_view/views.py::dashboard_view()` switches between `spa.html` (Vue) and `dashboard.html` (legacy)
- `ENABLE_DIAGNOSTIC_ENDPOINTS` — controls visibility of health/debug routes

**PostGIS spatial operations** (active since Phase 10):
- Models: `Site` (lat/lng), `FiberCable.path`, `RouteSegment.path` use `LineStringField` (SRID 4326/WGS84)
- Spatial queries: BBox filtering in `inventory/api/spatial.py` for viewport-based map loading
  - `Polygon.from_bbox((lng_min, lat_min, lng_max, lat_max))` for viewport queries
  - Lazy loading: Frontend requests only visible segments/cables within map bounds
- Utilities: `inventory/spatial.py` — `coords_to_linestring()`, `linestring_to_coords()`, `ensure_wgs84()`
- Graceful degradation: Falls back to JSON storage when GDAL/GEOS unavailable (CI/test environments)
- Migration: `0010_add_spatial_fields.py` + `0011_populate_spatial_fields.py` converted legacy JSON to PostGIS


---

### Developer Workflow

**CRITICAL - Docker-Only Environment (Windows)**:
- **ALL services run in Docker containers** (PostgreSQL, Redis, Celery, web server)
- **NEVER run database/redis directly on Windows** — always use `docker compose` commands
- Python virtual environment on Windows is ONLY for IDE tooling (linting, autocomplete)
- Database: PostgreSQL 16 + PostGIS 3.4 in `docker-postgres-1` container (port `5433` → `5432`)
- Redis: `docker-redis-1` container (port `6379`)
- Django migrations: Run inside Docker container or with Docker port forwarding
- Connection from Windows host: Use `localhost:5433` (PostgreSQL) or `localhost:6379` (Redis)

**Local development (Docker Compose)**:
1. Start full stack: `make up` or `cd docker; docker compose up -d`
2. View logs: `make logs` or `docker compose logs -f web`
3. Apply migrations: `docker compose exec web python manage.py migrate` (inside container)
4. Create superuser: `docker compose exec web python manage.py createsuperuser` (inside container)
5. Access shell: `docker compose exec web python manage.py shell`
6. Run tests: `docker compose exec web pytest` (inside container with PostgreSQL)
7. Stop stack: `make down` or `docker compose down`

**Direct Django development (bypassing Docker - AVOID for DB operations)**:
- Only use for frontend/template work that doesn't touch database
- If absolutely necessary, set `DB_ENGINE=sqlite` temporarily
- Remember: Production uses PostgreSQL + PostGIS — SQLite incompatible with spatial fields

**Testing**:
- Quick: `make test` (pytest -q) or `pytest -v <path/to/test.py>::TestClass::test_method`
- Coverage: `make test-coverage` (generates `htmlcov/index.html`)
- Markers: `@pytest.mark.django_db`, `@pytest.mark.slow` (skip unless `--slow`), `@pytest.mark.integration` (skip unless `--integration`)
- Settings: `settings.test` (SQLite by default; PostgreSQL available via Docker: `docker compose exec web pytest`)
- **Note**: `conftest.py` sets `CELERY_TASK_ALWAYS_EAGER=True`; tasks run synchronously in tests

**Code quality**:
- Format: `make fmt` (ruff --fix, black, isort)
- Lint: `make lint` (ruff check, black --check, isort --check-only)
- Style: Black (line-length=100), isort (profile=black), Ruff (Django-aware)
- Config: `backend/pyproject.toml`, `backend/pyrightconfig.json`

**Frontend** (Vue 3 SPA):
- Location: `frontend/` (Vite + Vue 3 + Pinia + Vue Router)
- Build: `npm run build` (outputs to `backend/staticfiles/vue-spa/`)
- Dev server: `npm run dev` (port 5173; proxies `/api` and `/ws` to Django)
- Static versioning: `{% static 'file.js' %}?v={{ STATIC_ASSET_VERSION }}` (auto-generated from Git SHA + timestamp in `settings/dev.py`)

**Docker Compose**:
- Commands: `make up|down|logs|build|restart`
- File: `docker/docker-compose.yml`
- Services: `web` (Django + Gunicorn + Uvicorn), `postgres` (PostgreSQL 16 + PostGIS 3.4), `redis`, `celery` (worker), `beat` (Celery beat)
- Resilience: Code falls back to SQLite + locmem cache when Redis/PostgreSQL are unavailable (dev only)


---

### Testing & Quality Signals

**Data shape stability**:
- Many tests assert on exact dataclass field order (e.g., `RouteBuildResult`, fiber payload dicts)
- **Never reorder fields** in DTOs without updating tests in `backend/tests/routes/`, `backend/tests/test_cache_swr.py`

**Celery in tests**:
- `CELERY_TASK_ALWAYS_EAGER=True` in `settings.test` → tasks run synchronously
- New tasks must skip external calls (Zabbix, Redis) when brokers are offline; use mocks/stubs

**Prometheus metrics**:
- Endpoint: `/metrics/` (django-prometheus + custom metrics)
- Custom: `core/metrics_static_version.py` (`static_asset_version_info`), `core/metrics_celery.py`
- Update: When adding observability, register metrics in `core/apps.py` (`CoreConfig.ready()`)

**WebSocket testing**:
- Consumers require authenticated sessions; use `django.test.Client` with logged-in users
- Publisher helpers (`broadcast_*`) tolerate missing channel layers (return `False` if unconfigured)


---

### When Extending

**Adding business logic**:
- Place in `<app>/services/` or `<app>/usecases/` modules; keep views/serializers thin
- Reuse existing DTOs (`RouteBuildResult`, fiber payload dicts) for consistency
- Example: `monitoring/usecases.py` (host status processing), `inventory/usecases/fibers.py` (fiber CRUD workflows)

**Adding Celery tasks**:
- Define in `<app>/tasks.py`; use `@shared_task(bind=True, name="namespace.task_name")`
- Register route in `core/celery.py` (`app.conf.task_routes`) and assign to correct queue (`default`, `zabbix`, `maps`)
- Add beat schedule if periodic (e.g., cache warmers in `app.conf.beat_schedule`)

**Adding REST endpoints**:
- Wire through app's `urls.py` (e.g., `inventory/urls_api.py`) → include in `core/urls.py`
- Use DRF viewsets/serializers; call usecases for business logic
- Respect `settings.ENABLE_DIAGNOSTIC_ENDPOINTS` for admin/debug routes

**Adding cache keys**:
- Use SWR pattern (`SWRCache`) or resilient helpers (`safe_cache_*`) to handle missing Redis
- Define invalidation logic (e.g., `invalidate_fiber_cache`, `invalidate_route_cache`) and call after mutations
- Namespace keys: `<app>:<entity>:<id>` (e.g., `monitoring:zabbix_hosts:<md5hash>`)

**Frontend changes**:
- Vue SPA: edit `frontend/src/`, rebuild with `npm run build`, commit `backend/staticfiles/vue-spa/` (or let CI rebuild)
- Django templates: edit `<app>/templates/`, ensure `{% static 'path' %}?v={{ STATIC_ASSET_VERSION }}` for cache busting
- Static assets: place in `<app>/static/`, run `make collectstatic` (ManifestStaticFilesStorage hashes filenames)

**Adding spatial features**:
- Use `LineStringField(srid=4326)` for paths/routes (WGS84 standard)
- Import helpers: `from inventory.spatial import coords_to_linestring, linestring_to_coords, ensure_wgs84`
- BBox queries: Follow pattern in `inventory/api/spatial.py` (parse bbox string → `Polygon.from_bbox` → filter)
- Always include fallback for non-GIS environments (see `inventory/models.py` `_FallbackLineStringField`)
- Migrations: Use `django.contrib.gis.db.models` for spatial fields, include data migration for existing records

**Adjusting Vue rollout**:
- Update `VUE_DASHBOARD_ROLLOUT_PERCENTAGE` in `.env` and `database/runtime.env` (0-100)
- Restart Docker containers: `cd docker; docker compose restart web`
- Monitor: Check `maps_view/views.py::dashboard_view()` logic, Prometheus metrics, user feedback
- Rollout path: 10% → 25% → 50% → 100% (gradual increase based on error rates)

---

### Common Pitfalls

- 🚫 **CRITICAL: Don't run services outside Docker** — Database, Redis, Celery must run in containers, not on Windows host
- 🚫 **Don't use SQLite for spatial features** — PostGIS fields require PostgreSQL; SQLite is only for quick non-spatial tests
- 🚫 **CRITICAL: Don't forget to rebuild Docker** — After changing templates, Python code, or migrations: `docker compose down && docker compose build --no-cache web && docker compose up -d`
- 🚫 **CRITICAL: Wrong working directory for Docker** — Always `cd docker` before running `docker compose` commands, or use `-f docker/docker-compose.yml` flag
- **Don't bypass Zabbix client**: Use `zabbix_request`, not `requests.post`
- **Don't use bare `cache.*` calls**: Use `safe_cache_*` or `SWRCache` to handle Redis outages
- **Don't reorder dataclass fields**: Tests assert on field order; changes break serialization
- **Don't skip cache invalidation**: Fiber/route mutations require explicit `invalidate_*` calls
- **Don't hardcode secrets**: Use `runtime_settings.get_runtime_config()` or env vars
- **Don't forget queue routing**: Celery tasks need correct queue assignment in `core/celery.py`
- **Don't omit migrations**: Run `docker compose exec web python manage.py makemigrations` after model changes, commit migration files

---

### Quick Reference

| Task | Command | Notes |
|------|---------|-------|
| Run dev server | `make run` | Django on `0.0.0.0:8000` |
| Run full stack | `make up` | Docker Compose (web, db, redis, celery) |
| Run tests | `make test` | Fast pytest (sqlite, locmem cache) |
| Format code | `make fmt` | Ruff, Black, isort |
| Check lint | `make lint` | Read-only checks |
| Apply migrations | `make migrate` | Uses `settings.dev` by default |
| Health checks | `make health\|ready\|live` | Curl `/healthz`, `/ready`, `/live` |
| Celery worker | `celery -A core worker -Q default,zabbix,maps -l info` | Multi-queue worker |
| Celery beat | `celery -A core beat -l info` | Scheduled tasks |
| Frontend build | `npm run build` (in `frontend/`) | Outputs to `backend/staticfiles/vue-spa/` |
| Docker build | `cd docker; docker compose build` | Build from correct directory |
| Docker logs | `cd docker; docker compose logs -f web` | View container logs |

---

### Questions to Resolve

- **Archived apps cleanup**: Confirm if `dwdm/` and `gpon/` placeholder apps can be removed or should remain for future development

**Feedback welcome**: Flag unclear areas in this doc so we can refine instructions collaboratively.
