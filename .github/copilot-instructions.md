# AI Agent Instructions — MapsProveFiber v2.0.0

**Fiber optic network infrastructure management platform** — Django 5.x + Vue 3 SPA + Zabbix integration with real-time WebSocket updates.

> 💡 **For detailed architecture**: `doc/architecture/{MODULES,DATA_FLOW}.md` | **Process docs**: `doc/process/AGENTS.md`

---

## 🏗️ Architecture Overview

### Django Apps (Modular)
- **`inventory/`** — Single source of truth (Site, Device, Port, FiberCable, Route models); domain logic in `usecases/` and `services/`
- **`monitoring/`** — Combines inventory + Zabbix status; business logic for health checks and device monitoring
- **`integrations/zabbix/`** — Resilient Zabbix API client with circuit breaker, retry logic, Prometheus metrics
- **`maps_view/`** — Real-time dashboard, WebSocket consumers, SWR cache pattern
- **`core/`** — Django spine (settings, URLs, Celery, health endpoints, middleware)
- **`setup_app/`** — Encrypted runtime config (Fernet), credentials management, docs viewer
- **`service_accounts/`** — Token rotation & webhooks (future)
- **`dwdm/`, `gpon/`** — Placeholder apps for future DWDM/GPON features

**Retired Apps**: ~~`routes_builder/`~~ (archived Nov 2025, use `inventory/routes/`), ~~`zabbix_api/`~~ (removed v2.0, use `integrations/zabbix/`)

### Tech Stack
- **Backend**: Django 5.x, PostgreSQL+PostGIS, Redis (optional), Celery workers
- **Frontend**: Vue 3 SPA (Vite), Pinia stores, Vue Router, Google Maps API
- **Real-time**: Django Channels (WebSocket), Celery Beat (periodic tasks)
- **Monitoring**: Prometheus metrics (`/metrics/`), Zabbix API integration, Sentry APM

---

## 🚀 Development Workflow

### Prerequisites
- **Python 3.12** (pyproject.toml target; 3.11+ compatible)
- **Node.js 18+** for frontend (Vite build)
- **Docker & Docker Compose** (required for PostgreSQL+PostGIS, Redis)

### Environment Setup (Docker Required)
```powershell
# ALWAYS use Docker for services (PostgreSQL+PostGIS, Redis, Celery)
cd docker
docker compose up -d                # Start all services
docker compose exec web python manage.py migrate
docker compose exec web pytest      # Run tests in Docker environment
docker compose logs -f web          # Tail logs
docker compose build --no-cache web # Rebuild after Python/migrations changes
docker compose down                 # Stop all services
```

**Database Access**: Host → `localhost:5433`; Container → `postgres:5432`

### Quick Commands (Makefile)
```bash
make up          # Start Docker stack
make down        # Stop Docker stack
make migrate     # Apply migrations
make test        # Run pytest (fast, may use SQLite)
make fmt         # Auto-format (black, ruff --fix, isort)
make lint        # Check formatting/style
make shell       # Django shell
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev      # Vite dev server (HMR) at http://localhost:5173
npm run build    # Build to backend/staticfiles/vue-spa/
npm run test:unit        # Vitest unit tests
npm run test:unit:watch  # Vitest watch mode
npm run test:e2e         # Playwright E2E tests
npm run lint             # ESLint check
```

**Frontend Structure**:
```
frontend/src/
├── components/      # Reusable Vue components
│   ├── DeviceImport/  # Device import modals and workflows
│   ├── Map/          # Google Maps integration
│   └── ...
├── composables/     # Reusable composition functions (useApi, etc.)
├── stores/          # Pinia state management
├── views/           # Page-level components
├── router/          # Vue Router configuration
└── utils/           # Utility functions
```

---

## 🧱 Core Patterns & Conventions

### 1. Service Layer Architecture
**CRITICAL**: Business logic lives in `services.py` / `usecases.py`, NOT in views/viewsets.

```python
# ✅ CORRECT - View delegates to service layer
from inventory.usecases import devices as device_uc

def device_list_view(request):
    devices = device_uc.list_devices_with_status()
    return render(request, "devices.html", {"devices": devices})

# ❌ WRONG - Business logic in view
def device_list_view(request):
    devices = Device.objects.select_related("site").all()
    # ... complex filtering, status enrichment, etc.
```

**Examples**: 
- `inventory/usecases/devices.py` — Device operations, Zabbix sync
- `inventory/usecases/fibers.py` — Fiber cable CRUD, status updates
- `inventory/routes/services.py` — Route building, cache invalidation
- `inventory/viewsets.py` — DRF ViewSets (SiteViewSet, DeviceViewSet, PortViewSet, FiberCableViewSet)
- `inventory/api/` — Additional API views (fusion.py, splice_matrix.py)

### 2. Zabbix Integration (Circuit Breaker)
**ALL Zabbix calls MUST go through** `integrations/zabbix/zabbix_service.zabbix_request()`:

```python
# ✅ CORRECT
from integrations.zabbix import zabbix_service
hosts = zabbix_service.zabbix_request("host.get", {"output": ["hostid", "name"]})

# ❌ WRONG - Direct HTTP to Zabbix (bypasses circuit breaker, metrics, retry)
import requests
response = requests.post(ZABBIX_URL, json={...})
```

**Circuit breaker** prevents cascading failures; monitors failure rate and opens after threshold.

### 3. Caching Strategy (SWR + Invalidation)
Use **SWR (Stale-While-Revalidate)** for dashboard data:

```python
from maps_view.cache_swr import SWRCache

cache = SWRCache(key="dashboard:hosts", fresh_ttl=30, stale_ttl=60)
data = cache.get_or_fetch(
    fetch_fn=lambda: get_hosts_status_data(),
    async_task=refresh_dashboard_cache_task.delay  # Celery background refresh
)
```

**Invalidation is MANDATORY** after mutations:
```python
from inventory.cache.fibers import invalidate_fiber_cache
from inventory.routes.services import invalidate_route_cache

# After creating/updating fiber
fiber.save()
invalidate_fiber_cache()

# After route changes
route.save()
invalidate_route_cache(route.id)
```

### 4. Spatial Operations (PostGIS)
All spatial data uses **SRID 4326** (WGS84) with LineString geometry:

```python
from django.contrib.gis.geos import LineString
from inventory.spatial import calculate_route_length

coords = [(-47.123, -23.456), (-47.234, -23.567)]
path = LineString(coords, srid=4326)
length_km = calculate_route_length(path)  # Returns Decimal
```

**Helpers**: `inventory/spatial.py` — distance calculations, bounding box queries, radius search

### 5. DTO Field Ordering
**CRITICAL**: Preserve exact field order in DTOs/serializers — tests assert ordering:

```python
# ✅ CORRECT - Field order matches expected structure
class RouteBuildResult(TypedDict):
    route_id: int
    status: str
    segments: list
    total_length_km: Decimal
    # ... exact order from original

# ❌ WRONG - Reordered fields will break tests
class RouteBuildResult(TypedDict):
    status: str  # Moved field breaks ordering assertions
    route_id: int
```

---

## 🧪 Testing

### Running Tests
```bash
make test                           # Fast (may use SQLite, skip spatial)
docker compose exec web pytest      # Full (PostGIS, production-like)
pytest -v tests/test_specific.py    # Specific test file
pytest --cov --cov-report=html      # Coverage report
```

**Test Configuration**: `backend/pytest.ini`, `backend/pyproject.toml` (pytest.ini_options)

### Celery Testing
```python
# Tests run with eager mode (synchronous)
# CELERY_TASK_ALWAYS_EAGER=True in settings.test

from inventory.tasks import sync_device_status
result = sync_device_status.delay(device_id=123)  # Runs immediately
assert result.successful()
```

### Code Quality
```bash
make fmt    # Auto-fix: ruff --fix, black, isort
make lint   # Check: ruff check, black --check, isort --check
```

**Tooling**: Ruff (linting), Black (formatting, line-length=100), isort (imports), configured in `backend/pyproject.toml`

---

## 🎨 Frontend Conventions

### CSRF Protection (MANDATORY)
All POST/PUT/PATCH/DELETE requests **MUST use `useApi` composable**:

```javascript
// ✅ CORRECT - Automatic CSRF token injection
import { useApi } from '@/composables/useApi';
const api = useApi();
await api.post('/api/v1/devices/', deviceData);

// ❌ WRONG - Missing CSRF token (403 Forbidden)
await fetch('/api/v1/devices/', {
  method: 'POST',
  body: JSON.stringify(deviceData)
});
```

**Token sources**: `window.CSRF_TOKEN` (injected in template) or `csrftoken` cookie

### Vue 3 Dashboard Rollout
Controlled via environment variables in `docker/docker-compose.yml`:

```yaml
USE_VUE_DASHBOARD: "true"
VUE_DASHBOARD_ROLLOUT_PERCENTAGE: "50"  # 0-100
```

**Selection logic**: `maps_view/views.py::dashboard_view()` checks percentage + user session hash

---

## 📡 API Patterns

### REST API Structure
```
/api/v1/inventory/        # Inventory CRUD (sites, devices, ports, fibers)
/api/v1/devices/          # Device operations (NOT /api/v1/inventory/devices/)
/api/v1/device-groups/    # Device groups (NOT /inventory/device-groups/)
/api/v1/import-rules/     # Import rules for device auto-association
/metrics/                 # Prometheus metrics
/health/, /ready/, /live/ # Health checks
```

**CRITICAL**: Device endpoints are at `/api/v1/devices/*`, not under inventory namespace.

### Adding New Endpoints
1. Create service/usecase in `<app>/usecases/` or `<app>/services/`
2. Create serializer in `<app>/serializers.py`
3. Create view/viewset in `<app>/api/` or `<app>/views.py`
4. Add route in `<app>/urls.py`
5. Include in `core/urls.py`

**Example**:
```python
# inventory/usecases/sites.py
def list_sites_with_devices():
    return Site.objects.prefetch_related("devices").all()

# inventory/serializers.py
class SiteSerializer(serializers.ModelSerializer):
    ...

# inventory/api/sites.py
class SiteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Site.objects.all()
    serializer_class = SiteSerializer

# inventory/urls_api.py
router.register("sites", SiteViewSet)
```

---

## 🔄 Real-Time Updates (WebSocket)

### Publishing Events
Use helper functions in `maps_view/realtime/publisher.py`:

```python
from maps_view.realtime.publisher import (
    broadcast_dashboard_status,
    broadcast_cable_status_update
)

# After device status changes
broadcast_dashboard_status(hosts_status_data)

# After fiber cable updates
broadcast_cable_status_update(cable_id, new_status)
```

### Celery Beat Schedule
Dashboard refresh task runs every 60s (configurable via `DASHBOARD_CACHE_REFRESH_INTERVAL`):

```python
# core/celery.py
beat_schedule = {
    "refresh-dashboard-cache": {
        "task": "monitoring.tasks.refresh_dashboard_cache_task",
        "schedule": 60,  # seconds
        "options": {"queue": "maps"}
    },
    "refresh-fiber-list-cache": {
        "task": "inventory.tasks.refresh_fiber_list_cache",
        "schedule": 180,  # 3 minutes
        "options": {"queue": "default"}
    },
    "refresh-cables-oper-status": {
        "task": "inventory.tasks.refresh_cables_oper_status",
        "schedule": 120,  # 2 minutes
        "options": {"queue": "zabbix"}
    },
    "update-all-port-optical-levels": {
        "task": "inventory.tasks.update_all_port_optical_levels",
        "schedule": 300,  # 5 minutes (RX/TX power)
        "options": {"queue": "zabbix"}
    }
}
```

**Adding Celery Tasks**:
1. Define in `<app>/tasks.py`
2. Add route in `core/celery.py`
3. Assign queue: `default`, `zabbix`, or `maps`

---

## 🔐 Security & Configuration

### Secrets Management
**NEVER hardcode credentials**. Use encrypted runtime config:

```python
from setup_app.services.runtime_settings import get_runtime_config, reload_config

config = get_runtime_config()  # Returns decrypted settings
zabbix_url = config.get("zabbix_url")

# After database config changes
reload_config()  # Clear cache, force reload
```

**Encryption**: Fernet (symmetric); keys in `FERNET_KEYS` env var

### Environment Variables
```bash
# Production checklist
SECRET_KEY=<secure-random-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
ZABBIX_API_URL=https://zabbix.example.com/api_jsonrpc.php
ZABBIX_API_KEY=<api-key>  # OR ZABBIX_API_USER + ZABBIX_API_PASSWORD
REDIS_URL=redis://localhost:6379/0
DB_ENGINE=postgis  # mysql, postgresql, or postgis
FERNET_KEYS=<base64-encoded-key>
```

---

## 🐞 Debugging & Diagnostics

### Viewing Logs
```powershell
# Docker logs (recent 5 minutes)
cd docker; docker compose logs web --since 5m

# Grep for specific patterns
docker compose logs web | Select-String -Pattern "Applied import rule"

# Follow live logs
docker compose logs -f web
```

### Django Shell (Testing Logic)
```bash
docker compose exec web python manage.py shell
>>> from inventory.services.import_rules import apply_import_rules
>>> apply_import_rules("Huawei - Switch Teste")
{'category': 'backbone', 'group_id': 42}
```

### Health Checks
```bash
curl http://localhost:8000/health/       # Database + Redis + Celery
curl http://localhost:8000/ready/        # Ready to serve traffic
curl http://localhost:8000/live/         # Process alive
curl http://localhost:8000/celery/status/ # Worker status
curl http://localhost:8000/metrics/      # Prometheus metrics
```

---

## 🚨 Common Pitfalls

### ❌ DON'T
- Start PostgreSQL/Redis directly on Windows (Docker only)
- Bypass service layer (business logic in views)
- Skip cache invalidation after mutations
- Reorder DTO fields (breaks ordering assertions)
- Use SQLite for spatial operations in production
- Make direct Zabbix HTTP requests (bypasses circuit breaker)
- Hardcode secrets in code

### ✅ DO
- Rebuild Docker image after Python dependency/migration changes
- Use publisher helpers for WebSocket broadcasts
- Define Celery tasks in `<app>/tasks.py` and route in `core/celery.py`
- Preserve exact field order in DTOs
- Invalidate caches explicitly after writes
- Use `useApi` composable for all mutating frontend requests

---

## 📚 Documentation

- **Architecture**: `doc/architecture/{MODULES,DATA_FLOW,OVERVIEW}.md`
- **API Reference**: `doc/api/ENDPOINTS.md`
- **Development**: `doc/guides/DEVELOPMENT.md`
- **Migration v1→v2**: `doc/releases/v2.0.0/BREAKING_CHANGES.md`
- **Process/Agents**: `doc/process/AGENTS.md`

---

## 🎯 Device Import Workflow (Complex Domain)

**Context**: Import devices from Zabbix with automatic category/group assignment via regex rules.

### Key Components
- **Frontend**: `frontend/src/components/DeviceImport/` (Vue modals, preview tabs)
- **Backend**: `inventory/usecases/devices.py` (business logic), `inventory/models.py` (ImportRule model)
- **Endpoints**: 
  - `POST /api/v1/inventory/devices/import-batch/` (batch import)
  - `GET /api/v1/devices/<id>/` (device details)
  - `POST /api/v1/devices/<id>/sync/` (re-sync from Zabbix)
  - `GET /api/v1/device-groups/` (list groups)
  - `GET /api/v1/import-rules/` (CRUD rules)

### Import Rules Logic
1. **Priority order** (lowest number = highest priority)
2. **Regex matching** on device name
3. **Auto-assignment** of category (`backbone`, `gpon`, `dwdm`) and group
4. **Applied during**:
   - New device import
   - Existing device sync (if still default category/no group)
   - Manual sync action via UI

**Validation**:
```powershell
# Check logs for rule applications
docker compose logs web --since 5m | Select-String "Applied import rule"

# Expected output:
# INFO ... devices Applied import rule #3 (GPON OLTs) to OLT-Centro: category=gpon, group_id=5
```

### Data Consistency Pattern
**Edit Modal**: Always fetches fresh data before opening:
```javascript
async openEditModal(device) {
  const fresh = await api.get(`/api/v1/devices/${device.id}/`);
  this.editingDevice = fresh;  // Use server state, not cached array
}
```

**Readonly Modal**: Uses dedicated endpoint with fallback:
```javascript
async viewDeviceDetails(device) {
  let fresh;
  try {
    fresh = await api.get(`/api/v1/devices/by-zabbix/${device.zabbix_id}/`);
  } catch {
    fresh = await api.get(`/api/v1/devices/${device.id}/`);
  }
  this.showDeviceModal(fresh, readOnly=true);
}
```

---

## 🔍 Trace Route - Optical Path Tracing (Phase 11.5)

**Context**: Bidirectional optical path tracing with power budget analysis, following physical fiber connections through DIOs, fusions, and switches.

### Architecture
**Backend**: Recursive graph traversal algorithm in `inventory/api/trace_route.py`
- Traces `FiberStrand.fused_to` relationships (fusion points in CEOs)
- Traces `FiberStrand.connected_device_port` relationships (DIO/Switch connections)
- Calculates power budget: fiber loss (0.35 dB/km) + fusion loss (0.1 dB) + connector loss (0.5 dB)

**Frontend**: Metro-style timeline visualization in `frontend/src/components/TraceRoute/`
- `TraceRouteView.vue` — Timeline display with power budget card
- `TraceRouteModal.vue` — Modal wrapper with loading states
- `useTraceRoute.js` — Composable for API calls and export

### Optical Path Flow
```
[Switch A Port 1] → [DIO Port 5] → [Fiber Strand 01] → [CEO Fusion] 
  → [Fiber Strand 02] → [DIO Port 3] → [Switch B Port 8]
```

### Key Endpoint
```
GET /api/v1/inventory/trace-route/?strand_id=123
```

**Response**:
```json
{
  "trace_id": "trace_123_1701234567",
  "source": { "device_name": "SW-Core-01", "port_name": "GigabitEthernet1/0/1" },
  "destination": { "device_name": "SW-Dist-05", "port_name": "SFP2" },
  "path": [
    { "step_number": 1, "type": "device_port", "name": "SW-Core-01 - Gig1/0/1", "loss_db": 0.5 },
    { "step_number": 2, "type": "fiber_strand", "name": "Cabo-Backbone-01 - Fibra 5", "loss_db": 0.875 },
    { "step_number": 3, "type": "fusion", "name": "Fusão em CEO-Planaltina", "loss_db": 0.1 }
  ],
  "total_distance_km": 2.5,
  "total_loss_db": 1.475,
  "fusion_count": 1,
  "connector_count": 2,
  "power_budget": {
    "tx_power_dbm": 0,
    "rx_sensitivity_dbm": -18,
    "available_margin_db": 16.525,
    "required_margin_db": 3,
    "is_viable": true,
    "status": "OK",
    "message": "Link viável com 16.53 dB de margem"
  }
}
```

### Usage Pattern
```javascript
import { useTraceRoute } from '@/composables/useTraceRoute';

const { traceFromStrand, loading, traceResult } = useTraceRoute();

// Trace from fiber strand
await traceFromStrand(strandId);

// Display in modal
<TraceRouteModal :strand-id="selectedStrand" :is-open="showTrace" @close="showTrace = false" />
```

### Power Budget Calculation
- **Fiber Loss**: 0.35 dB/km (SM fiber typical)
- **Fusion Loss**: 0.1 dB per fusion (typical splice)
- **Connector Loss**: 0.5 dB per connector (SC/LC/FC)
- **TX Power**: 0 dBm (typical SFP)
- **RX Sensitivity**: -18 dBm (typical SFP)
- **Required Margin**: 3 dB (safety factor)

**Viability Check**: `available_margin_db >= required_margin_db`

---

**Version**: 2024-11-30 (Updated for comprehensive AI agent onboarding)  
**Maintainer**: For questions/clarifications → `doc/contributing/README.md`
