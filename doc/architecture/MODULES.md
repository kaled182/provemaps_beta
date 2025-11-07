# Django Apps Module Structure

**MapsProveFiber** — Detailed documentation of all Django apps and their responsibilities.

**Last Updated**: 2025-11-07  
**Architecture Version**: v2.0.0

---

## 📦 Module Overview

| App | Purpose | Models | Primary APIs | Status |
|-----|---------|--------|--------------|--------|
| **core** | Configuration spine, metrics, health checks | None | `/health/`, `/metrics/` | ✅ Active |
| **inventory** | Network infrastructure (Sites, Devices, Ports) | Site, Device, Port, FiberCable, Route | `/api/v1/inventory/*` | ✅ Active |
| **maps_view** | Real-time dashboard and visualizations | None (view-only) | `/maps_view/dashboard/` | ✅ Active |
| **routes_builder** | Optical route calculation, KML import | None (legacy Route migrated) | `/routes_builder/fiber-route-builder/` | ⚠️ Legacy (Phase 4) |
| **setup_app** | Runtime config, credentials, docs viewer | FirstTimeSetup | `/setup_app/dashboard/` | ✅ Active |
| **monitoring** | Zabbix integration use cases | None | N/A (service layer) | ✅ Active |
| **integrations/zabbix** | Resilient Zabbix API client | None | N/A (library) | ✅ Active |
| **dwdm** | DWDM (Dense Wavelength Division Multiplexing) | Placeholder | N/A | 🚧 Future |
| **gpon** | GPON (Gigabit Passive Optical Network) | Placeholder | N/A | 🚧 Future |
| **service_accounts** | Service account management | Placeholder | N/A | 🚧 Future |

---

## 🎯 Core Apps (Production Active)

### 1. `core` — Configuration Spine

**Location**: `core/`  
**App Config**: `CoreConfig`  
**Purpose**: Central Django configuration, URL routing, middleware, metrics initialization

#### Key Files
- `settings/base.py`, `settings/dev.py`, `settings/production.py` — Django settings
- `urls.py` — Root URL dispatcher
- `asgi.py` / `wsgi.py` — ASGI/WSGI application entry points
- `celery.py` / `celery_app.py` — Celery application configuration
- `routing.py` — Channels routing (WebSocket support)
- `views_health.py` — Health check endpoints
- `metrics_*.py` — Prometheus metrics initialization

#### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health/` | GET | Overall application health (database, Redis, Celery) |
| `/health/ready/` | GET | Readiness probe (ready to serve traffic) |
| `/health/live/` | GET | Liveness probe (process is alive) |
| `/celery/status/` | GET | Celery worker/beat status |
| `/metrics/` | GET | Prometheus metrics endpoint |

#### Dependencies
- Django 5.x
- `django-prometheus` (metrics)
- Channels (WebSocket)
- Celery (task queue)

#### Notes
- No models (pure configuration)
- Initializes Prometheus custom metrics on `ready()`
- Handles root redirect to `/maps_view/dashboard/`

---

### 2. `inventory` — Network Infrastructure

**Location**: `inventory/`  
**App Config**: `InventoryConfig`  
**Purpose**: Authoritative source for network inventory (Sites, Devices, Ports, Fiber Cables, Routes)

#### Models
| Model | Table Name | Purpose |
|-------|------------|---------|
| **Site** | `zabbix_api_site` | Physical locations (name, city, lat/lon) |
| **Device** | `zabbix_api_device` | Network devices at sites (router, switch, OLT) |
| **Port** | `zabbix_api_port` | Device ports (fiber connections) |
| **FiberCable** | `zabbix_api_fibercable` | Physical fiber cables between ports |
| **Route** | `inventory_route` | Optical routes (migrated from `routes_builder` in Phase 3) |

> **Note**: Table names prefixed with `zabbix_api_*` for historical reasons (migration from `zabbix_api` app). See `BREAKING_CHANGES_v2.0.0.md` for details.

#### Key Features
- **Authoritative Inventory**: Single source of truth for network topology
- **Zabbix Sync**: Periodic sync from Zabbix API via Celery tasks
- **API Endpoints**: RESTful API at `/api/v1/inventory/*`
- **CRUD Operations**: Create, Read, Update, Delete via Django admin or API
- **Route Management**: Optical route calculations and metadata

#### Services (`inventory/services/`)
- `device_service.py` — Device CRUD and queries
- `site_service.py` — Site management
- `port_service.py` — Port and fiber cable management
- `route_service.py` — Route calculations and caching

#### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/inventory/sites/` | GET | List all sites |
| `/api/v1/inventory/devices/` | GET | List all devices |
| `/api/v1/inventory/ports/` | GET | List all ports |
| `/api/v1/inventory/fibers/` | GET | List fiber cables |
| `/api/v1/inventory/routes/` | GET | List optical routes |
| `/api/v1/inventory/fibers/oper-status/` | GET | Real-time fiber operational status |

#### Celery Tasks (`inventory/tasks.py`)
- `sync_devices_from_zabbix` — Sync devices from Zabbix API
- `update_device_status` — Update device operational status
- `recalculate_routes` — Recalculate optical routes

#### Dependencies
- Django ORM
- `integrations.zabbix` (Zabbix API client)
- Celery (periodic sync)

---

### 3. `maps_view` — Dashboard & Visualization

**Location**: `maps_view/`  
**App Config**: `MapsViewConfig`  
**Purpose**: Real-time network dashboard with maps visualization and monitoring metrics

#### Key Features
- **Real-Time Dashboard**: Live network status via WebSocket
- **Google Maps Integration**: Visual map of sites and fiber routes
- **SWR Caching**: Stale-While-Revalidate pattern for dashboard data
- **Prometheus Integration**: Metrics display and monitoring

#### Models
- None (view-only app; data fetched from `inventory` and `monitoring`)

#### Services (`maps_view/services.py`)
- `get_dashboard_data()` — Aggregate dashboard metrics
- `get_device_status()` — Device health status
- `get_fiber_status()` — Fiber operational status
- Re-exports `monitoring.usecases` for backwards compatibility

#### Caching (`maps_view/cache_swr.py`)
- `get_dashboard_cached()` — SWR cache for dashboard data
- `CACHE_KEY_DASHBOARD_DATA` — Cache key constant
- Refresh interval: `DASHBOARD_CACHE_REFRESH_INTERVAL` (default: 60s)

#### Celery Tasks (`maps_view/tasks.py`)
- `refresh_dashboard_cache_task` — Background refresh of dashboard cache
- `broadcast_dashboard_update` — WebSocket broadcast to connected clients

#### Real-Time (`maps_view/realtime/`)
- `consumers.py` — Channels WebSocket consumer
- `publisher.py` — Broadcast helper for dashboard updates
- WebSocket URL: `ws://localhost:8000/ws/dashboard/status/`

#### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/maps_view/dashboard/` | GET | Main dashboard view (HTML) |
| `/maps_view/metrics/` | GET | Metrics dashboard |
| `/maps_view/api/hosts-status/` | GET | JSON API for host status |

#### Dependencies
- Django Channels (WebSocket)
- `inventory` models
- `monitoring.usecases` (Zabbix integration)
- Redis (cache + Channels layer)

---

### 4. `routes_builder` — Optical Route Calculation

**Location**: `routes_builder/`  
**App Config**: `RoutesBuilderConfig`  
**Purpose**: Optical route planning, power budget calculations, KML import/export

#### Status
⚠️ **Legacy App** (Phase 4 cleanup pending)
- Route model migrated to `inventory` app in Phase 3
- Remaining functionality: UI views, Celery tasks, KML import
- **Planned Removal**: After Phase 4 completion (migration dependency resolved)

#### Models
- None (Route model migrated to `inventory.models.Route`)

#### Key Features
- **Route Builder UI**: Interactive fiber route builder
- **Power Budget Calculation**: Optical loss calculations
- **KML Import/Export**: Import routes from KML files, export to Google Earth
- **Celery Task Queue**: Async route building and validation

#### Services (`routes_builder/services.py`)
- `RouteBuildContext` (dataclass) — Route building context
- `RouteBuildResult` (dataclass) — Route building result
- `build_route()` — Calculate optical route
- `import_kml_route()` — Import route from KML
- `validate_route()` — Validate route integrity

#### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/routes_builder/fiber-route-builder/` | GET | Route builder UI |
| `/routes_builder/tasks/build/` | POST | Enqueue route build task |
| `/routes_builder/tasks/import/` | POST | Enqueue KML import task |
| `/routes_builder/tasks/status/<task_id>/` | GET | Task status check |

#### Celery Tasks (`routes_builder/tasks.py`)
- `build_route_task` — Async route building
- `import_kml_task` — Async KML import
- `validate_route_task` — Async route validation

#### Dependencies
- `inventory.models.Route` (migrated model)
- Celery (async processing)
- Google Maps API (geocoding, distance calculations)

---

### 5. `setup_app` — Runtime Configuration

**Location**: `setup_app/`  
**App Config**: `SetupAppConfig`  
**Purpose**: Secure runtime configuration, credential management, documentation viewer

#### Models
| Model | Purpose |
|-------|---------|
| **FirstTimeSetup** | Encrypted runtime configuration (Zabbix, DB, Redis credentials) |

#### Key Features
- **Encrypted Credentials**: Fernet encryption for sensitive data
- **Runtime Config**: Dynamic settings loaded from database
- **Docs Viewer**: Markdown documentation viewer at `/setup_app/docs/`
- **Environment Management**: GUI for `.env` file editing (optional)

#### Services (`setup_app/services/`)
- `runtime_settings.py` — Load runtime config from `FirstTimeSetup`
- `config_loader.py` — Cache and reload runtime config
- `service_reloader.py` — Trigger service restarts after config changes

#### Fields (EncryptedCharField)
- `zabbix_url`, `zabbix_api_key`, `zabbix_user`, `zabbix_password`
- `maps_api_key`, `unique_licence`
- `db_host`, `db_port`, `db_name`, `db_user`, `db_password`
- `redis_url`

#### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/setup_app/dashboard/` | GET | Setup dashboard |
| `/setup_app/first_time/` | GET/POST | First-time setup wizard |
| `/setup_app/config/` | GET/POST | Runtime config editor |
| `/setup_app/docs/` | GET | Documentation index |
| `/setup_app/docs/<path>/` | GET | View specific documentation |

#### Context Processors (`setup_app/context_processors.py`)
- `setup_logo` — Expose company logo to all templates
- `static_version` — Expose `STATIC_ASSET_VERSION` for cache busting

#### Dependencies
- `cryptography` (Fernet encryption)
- Markdown (docs rendering)
- Django admin (optional GUI)

---

### 6. `monitoring` — Zabbix Use Cases

**Location**: `monitoring/`  
**App Config**: `MonitoringConfig`  
**Purpose**: High-level Zabbix integration use cases (combine inventory + Zabbix status)

#### Models
- None (service layer only)

#### Key Features
- **Status Aggregation**: Combine `inventory` models with Zabbix real-time status
- **Use Case Layer**: Business logic for dashboard and monitoring views
- **Backwards Compatibility**: Re-exported by `maps_view.services` for legacy code

#### Use Cases (`monitoring/usecases.py`)
- `get_device_with_zabbix_status()` — Device + Zabbix status
- `get_fiber_operational_status()` — Fiber cable status from Zabbix
- `get_sites_with_devices()` — Sites with device counts and health
- `aggregate_network_metrics()` — Overall network health metrics

#### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/monitoring/devices/status/` | GET | Device status (inventory + Zabbix) |
| `/monitoring/fibers/status/` | GET | Fiber operational status |

#### Celery Tasks (`monitoring/tasks.py`)
- `refresh_device_status` — Periodic status refresh
- `check_fiber_health` — Fiber health monitoring

#### Dependencies
- `inventory` models
- `integrations.zabbix` (Zabbix API client)
- Celery (periodic tasks)

---

### 7. `integrations/zabbix` — Resilient Zabbix Client

**Location**: `integrations/zabbix/`  
**Purpose**: Resilient Zabbix API client with retry logic, circuit breaker, and metrics

#### Key Features
- **Retry Logic**: Exponential backoff for transient failures
- **Circuit Breaker**: Prevent cascading failures (opens after N consecutive errors)
- **Request Batching**: Multiple API calls in single HTTP request
- **Prometheus Metrics**: Latency, errors, circuit breaker state
- **Authentication Cache**: 5-minute auth token cache
- **Configurable Timeout**: `ZABBIX_API_TIMEOUT` env variable

#### Main Client (`integrations/zabbix/client.py`)
- `resilient_client` — Singleton Zabbix client
- `call(method, params)` — Single API call
- `batch(calls)` — Batched API calls
- `is_open` — Circuit breaker state

#### Circuit Breaker States
| State | Description |
|-------|-------------|
| **CLOSED** | Normal operation (requests allowed) |
| **OPEN** | Circuit open (requests blocked, waiting for recovery) |
| **HALF_OPEN** | Testing recovery (limited requests allowed) |

#### Service Helpers (`integrations/zabbix/zabbix_service.py`)
- `zabbix_request(method, params)` — Safe wrapper with cache
- `get_zabbix_hosts()` — Cached host list
- `get_zabbix_items()` — Cached item list
- `safe_cache_get()` / `safe_cache_set()` — Redis-optional cache helpers

#### Prometheus Metrics
- `zabbix_api_requests_total` — Total requests by method and status
- `zabbix_api_duration_seconds` — Request latency histogram
- `zabbix_circuit_breaker_state` — Circuit breaker state gauge

#### Configuration
```python
# Environment variables
ZABBIX_API_URL = "https://zabbix.example.com/api_jsonrpc.php"
ZABBIX_API_TOKEN = "your-api-token"  # OR
ZABBIX_API_USER = "admin"
ZABBIX_API_PASSWORD = "password"
ZABBIX_API_TIMEOUT = 30  # seconds (default: 30)
```

#### Dependencies
- `requests` (HTTP client)
- `django-environ` (environment variables)
- `setup_app.services.runtime_settings` (dynamic config)

---

## 🚧 Future Apps (Placeholder)

### 8. `dwdm` — Dense Wavelength Division Multiplexing

**Status**: 🚧 Placeholder (not yet implemented)  
**Purpose**: DWDM optical transport planning and monitoring

### 9. `gpon` — Gigabit Passive Optical Network

**Status**: 🚧 Placeholder (not yet implemented)  
**Purpose**: GPON topology management and monitoring

### 10. `service_accounts` — Service Account Management

**Status**: 🚧 Placeholder (not yet implemented)  
**Purpose**: API service account management and permissions

---

## 📊 App Dependency Graph

```
core (root)
  ├── inventory (models)
  │     └── integrations/zabbix (API client)
  │
  ├── maps_view (dashboard)
  │     ├── inventory (data)
  │     ├── monitoring (use cases)
  │     └── integrations/zabbix (status)
  │
  ├── routes_builder (legacy)
  │     └── inventory.models.Route (migrated)
  │
  ├── monitoring (use cases)
  │     ├── inventory (models)
  │     └── integrations/zabbix (API)
  │
  └── setup_app (config)
        └── (provides runtime settings to all apps)
```

---

## 🔄 Migration History

### Phase 3 (Completed)
- ✅ Migrated `Route` model from `routes_builder` → `inventory`
- ✅ ContentType migration (`routes_builder.route` → `inventory.route`)
- ✅ Preserved table name: `routes_builder_route` → `inventory_route`

### Phase 4 (In Progress)
- ⏳ Remove `zabbix_api` app entirely
- ⏳ Consolidate `routes_builder` functionality into `inventory`
- ⏳ Final cleanup: remove legacy imports and shims

---

## 📚 Related Documentation

- [OVERVIEW.md](./OVERVIEW.md) — Architecture overview
- [DATA_FLOW.md](./DATA_FLOW.md) — Data flow and integration patterns
- [../api/ENDPOINTS.md](../api/ENDPOINTS.md) — Complete API reference
- [../operations/DEPLOYMENT.md](../operations/DEPLOYMENT.md) — Production deployment
- [../releases/BREAKING_CHANGES_v2.0.0.md](../releases/BREAKING_CHANGES_v2.0.0.md) — Migration guide

---

**MapsProveFiber** — Module Structure Documentation  
**Version**: v2.0.0 | **Last Updated**: 2025-11-07
