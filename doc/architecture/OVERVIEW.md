# Architecture Documentation - v2.0.0 Modular Design

**Project**: MapsProveFiber  
**Version**: v2.0.0  
**Architecture**: Modular Django Multi-App  
**Last Updated**: 2025-01-07

---

## 🎯 Overview

MapsProveFiber v2.0.0 introduces a **modular architecture** that separates concerns into distinct Django apps, each with a well-defined responsibility. This design improves maintainability, testability, and scalability while enabling independent evolution of each module.

### Design Principles

1. **Separation of Concerns**: Each app owns a specific domain (inventory, monitoring, integrations)
2. **Single Source of Truth**: Inventory app is the authoritative source for Sites, Devices, Ports, Routes
3. **Resilient Integrations**: Zabbix client isolated with circuit breaker, retry logic, metrics
4. **Service Layer Pattern**: Business logic in `services.py`, views stay thin
5. **API-First**: REST endpoints at `/api/v1/inventory/*` for all data access
6. **Graceful Degradation**: Redis cache optional, system continues without it

---

## 📦 Module Architecture

### High-Level Structure

```mermaid
graph TD
    subgraph "External Systems"
        Z[Zabbix API]
        R[Redis Cache]
        DB[(MySQL/MariaDB)]
    end
    
    subgraph "MapsProveFiber v2.0.0"
        subgraph "Core Layer"
            C[core/]
            C --> S[settings]
            C --> U[urls]
            C --> M[metrics]
            C --> H[health checks]
        end
        
        subgraph "Domain Layer"
            I[inventory/]
            MO[monitoring/]
            RB[routes_builder/]
        end
        
        subgraph "Integration Layer"
            IZ[integrations/zabbix/]
        end
        
        subgraph "Infrastructure Layer"
            SA[setup_app/]
            CE[Celery Workers]
            CH[Channels WebSocket]
        end
    end
    
    subgraph "Clients"
        FE[Frontend<br/>Dashboard & Maps]
        API_CLIENT[API Clients]
        PROM[Prometheus]
    end
    
    FE -->|HTTP| C
    API_CLIENT -->|REST| I
    PROM -->|/metrics/| M
    
    I -->|models| DB
    I -->|cache| R
    MO -->|combine| I
    MO -->|fetch| IZ
    IZ -->|API calls| Z
    RB -->|Celery tasks| CE
    CE -->|read/write| DB
    CH -->|real-time| FE
    SA -->|runtime config| C
    
    style I fill:#4CAF50,color:#fff
    style MO fill:#2196F3,color:#fff
    style IZ fill:#FF9800,color:#fff
    style C fill:#9C27B0,color:#fff
    style RB fill:#FFC107,color:#000
```

### Module Responsibilities

| Module | Responsibility | Key Components | Status |
|--------|---------------|----------------|--------|
| **`core/`** | Django configuration, URL routing, metrics, health checks | settings, urls, ASGI, WSGI, Celery, middleware | ✅ Stable |
| **`inventory/`** | Authoritative data for Sites, Devices, Ports, Routes | models, API, services, usecases, cache | ✅ v2.0.0 |
| **`monitoring/`** | Health checks, combined Zabbix + inventory status | usecases, tasks, views | ✅ v2.0.0 |
| **`integrations/zabbix/`** | Resilient Zabbix API client | client, zabbix_service, circuit breaker | ✅ v2.0.0 |
| **`maps_view/`** | Real-time dashboard, WebSocket publisher | views, realtime, cache_swr, tasks | ✅ Stable |
| **`routes_builder/`** | Fiber route calculation (KML import, power calc) | services, tasks, views | ⚠️ Deprecated |
| **`setup_app/`** | Runtime settings, credential management | FirstTimeSetup, encryption | ✅ Stable |
| **`gpon/`** | GPON topology (future) | models | ⏳ Scaffolding |
| **`dwdm/`** | DWDM equipment (future) | models | ⏳ Scaffolding |

---

## 🗂️ Detailed Module Design

### 1. `inventory/` — Authoritative Data Layer

**Purpose**: Single source of truth for network inventory

```
inventory/
├── models.py                    # Site, Device, Port, Route (Django ORM)
├── urls_api.py                  # URL routing for /api/v1/inventory/*
├── api/
│   ├── devices.py              # GET /api/v1/inventory/devices/
│   ├── fibers.py               # GET /api/v1/inventory/fibers/
│   └── routes.py               # Route CRUD endpoints
├── cache/
│   ├── fibers.py               # invalidate_fiber_cache, helpers
│   └── device_status.py        # Status caching logic
├── domain/
│   ├── geometry.py             # sanitize_path_points, calculate_length
│   └── optical.py              # fetch_port_optical_snapshot
├── services/
│   ├── fiber_status.py         # get_oper_status_from_zabbix
│   ├── site_service.py         # SiteService (future)
│   └── device_service.py       # DeviceService (future)
├── usecases/
│   ├── devices.py              # bulk_create_inventory, add_device_from_zabbix
│   ├── fibers.py               # create_fiber_from_kml, live_status
│   └── ports.py                # device_ports, optical_snapshots
└── tests/
    ├── conftest.py             # Fixtures (create_test_site, etc.)
    └── test_*.py               # Unit & integration tests
```

**Key Patterns**:
- **Models**: Django ORM models (`Site`, `Device`, `Port`, `Route`)
- **API**: Thin controllers → delegate to usecases
- **Services**: Reusable helpers (fetch Zabbix data, compute status)
- **Usecases**: Complex workflows (bulk import, KML parsing)
- **Cache**: Redis-optional caching with graceful degradation

**Data Flow**:
```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as inventory/api/fibers.py
    participant UC as inventory/usecases/fibers.py
    participant SRV as inventory/services/fiber_status.py
    participant ZAB as integrations/zabbix/
    participant DB as Database
    
    FE->>API: GET /api/v1/inventory/fibers/oper-status/
    API->>UC: get_fibers_operational_status()
    UC->>DB: SELECT * FROM inventory_port
    DB-->>UC: ports data
    UC->>SRV: get_oper_status_from_zabbix(port)
    SRV->>ZAB: zabbix_request("item.get", {...})
    ZAB-->>SRV: Zabbix item value
    SRV-->>UC: "up" | "down" | "unknown"
    UC-->>API: fibers_status_list
    API-->>FE: JSON response
```

---

### 2. `monitoring/` — Observability Layer

**Purpose**: Health checks, combined status from inventory + Zabbix

```
monitoring/
├── usecases.py          # HostStatusProcessor (combine Zabbix + inventory)
├── tasks.py             # Celery tasks for periodic checks
├── views.py             # Health endpoint views
└── tests/
    └── test_*.py
```

**Key Components**:
- **`HostStatusProcessor`**: Combines Zabbix availability with inventory device data
- **Tasks**: Periodic health checks, status aggregation (Celery beat)
- **Views**: `/healthz/`, `/ready/`, `/live/` endpoints

**Integration Pattern**:
```python
# monitoring/usecases.py
class HostStatusProcessor:
    @classmethod
    def get_combined_status(cls, device):
        # Fetch from inventory
        device_data = Device.objects.get(id=device.id)
        
        # Fetch from Zabbix
        zabbix_status = zabbix_request("host.get", {
            "hostids": device.zabbix_host_id,
            "output": ["available", "status"]
        })
        
        # Combine
        return {
            "device": device_data,
            "zabbix_available": zabbix_status[0]["available"],
            "combined_status": cls._evaluate_status(device_data, zabbix_status)
        }
```

---

### 3. `integrations/zabbix/` — External API Client

**Purpose**: Resilient, observable Zabbix API client

```
integrations/
└── zabbix/
    ├── client.py              # ResilientZabbixClient (circuit breaker, retry)
    ├── zabbix_service.py      # zabbix_request, safe_cache_* helpers
    └── README.md              # Client usage documentation
```

**Features**:
- ✅ **Automatic Retries**: Exponential backoff (3 attempts)
- ✅ **Circuit Breaker**: Opens after 5 consecutive failures
- ✅ **Request Batching**: Multiple calls in single HTTP request
- ✅ **Prometheus Metrics**: Latency, errors, circuit state
- ✅ **Authentication Cache**: 5-minute auth token cache
- ✅ **Graceful Degradation**: Returns fallback data on failure

**Client Usage**:
```python
from integrations.zabbix.client import resilient_client
from integrations.zabbix.zabbix_service import zabbix_request

# Method 1: Direct client (advanced)
hosts = resilient_client.call("host.get", {"output": ["hostid", "name"]})

# Method 2: Helper function (recommended)
hosts = zabbix_request("host.get", {"output": ["hostid", "name"]})
```

**Circuit Breaker State Machine**:
```mermaid
stateDiagram-v2
    [*] --> Closed
    Closed --> Open: 5 consecutive failures
    Open --> HalfOpen: 60s timeout
    HalfOpen --> Closed: Success
    HalfOpen --> Open: Failure
    
    note right of Closed
        Normal operation
        Requests allowed
    end note
    
    note right of Open
        All requests blocked
        Return fallback data
    end note
    
    note right of HalfOpen
        Test request allowed
        Evaluate recovery
    end note
```

---

### 4. `core/` — Configuration & Infrastructure

**Purpose**: Django configuration, URL routing, observability

```
core/
├── settings/
│   ├── base.py              # Common settings
│   ├── development.py       # Dev overrides
│   ├── production.py        # Prod overrides
│   └── test.py              # Test settings
├── urls.py                  # Root URLConf
├── asgi.py                  # ASGI entry point
├── wsgi.py                  # WSGI entry point
├── celery_app.py            # Celery configuration
├── routing.py               # Channels WebSocket routing
├── metrics_*.py             # Prometheus metrics
├── views_health.py          # /healthz/, /ready/, /live/
└── middleware/
    └── request_id.py        # Request ID tracking
```

**URL Structure**:
```python
# core/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/inventory/', include('inventory.urls_api')),  # ✅ v2.0.0
    path('monitoring/', include('monitoring.urls')),
    path('routes/', include('routes_builder.urls')),  # ⚠️ Deprecated
    path('healthz/', health_check),
    path('ready/', readiness_check),
    path('live/', liveness_check),
    path('metrics/', include('django_prometheus.urls')),
]
```

---

### 5. `maps_view/` — Real-Time Dashboard

**Purpose**: WebSocket-powered network dashboard

```
maps_view/
├── views.py                 # Dashboard rendering
├── cache_swr.py             # Stale-while-revalidate cache
├── realtime/
│   └── publisher.py         # broadcast_dashboard_status()
├── tasks.py                 # refresh_dashboard_cache_task
└── static/
    └── maps_view/
        └── js/
            └── fiber_status_manager.js  # Real-time status updates
```

**WebSocket Flow**:
```mermaid
sequenceDiagram
    participant FE as Frontend (WebSocket)
    participant CH as Channels Consumer
    participant PUB as realtime/publisher.py
    participant CACHE as Redis (Cache)
    participant DB as Database
    
    FE->>CH: ws://domain/ws/dashboard/status/
    CH->>FE: WebSocket connected
    
    Note over DB,CACHE: Background task (Celery beat)
    DB->>CACHE: Update cached dashboard data
    CACHE->>PUB: broadcast_dashboard_status(data)
    PUB->>CH: Publish to channel layer
    CH->>FE: WebSocket message (new status)
    FE->>FE: Update UI without refresh
```

---

## 🔄 Data Flow Patterns

### Pattern 1: API Request → Database

**Use Case**: Fetch device list

```mermaid
graph LR
    A[GET /api/v1/inventory/devices/] --> B[inventory/api/devices.py]
    B --> C[Django ORM Query]
    C --> D[(MySQL)]
    D --> E[Serialize to JSON]
    E --> F[HTTP 200 Response]
```

### Pattern 2: API Request → Zabbix → Cache → Database

**Use Case**: Fetch fiber operational status

```mermaid
graph LR
    A[GET /api/v1/inventory/fibers/oper-status/] --> B[inventory/api/fibers.py]
    B --> C[inventory/usecases/fibers.py]
    C --> D{Cache hit?}
    D -->|Yes| E[Return cached]
    D -->|No| F[integrations/zabbix/]
    F --> G[Zabbix API]
    G --> H[Cache result]
    H --> I[Return to client]
```

### Pattern 3: Celery Task → Async Processing

**Use Case**: Route calculation (KML import)

```mermaid
graph TD
    A[POST /routes/tasks/build/] --> B[Enqueue Celery Task]
    B --> C{Celery Worker}
    C --> D[routes_builder/tasks.py]
    D --> E[Parse KML geometry]
    E --> F[Calculate path length]
    F --> G[Compute optical power]
    G --> H[Save to database]
    H --> I[Update cache]
    I --> J[Return task result]
```

---

## 🔐 Security Architecture

### Authentication & Authorization

```mermaid
graph TD
    A[HTTP Request] --> B{Authenticated?}
    B -->|No| C[Redirect to Login]
    B -->|Yes| D{Has Permission?}
    D -->|No| E[HTTP 403 Forbidden]
    D -->|Yes| F{Diagnostic Endpoint?}
    F -->|Yes| G{ENABLE_DIAGNOSTIC_ENDPOINTS?}
    G -->|No| E
    G -->|Yes| H{User is staff?}
    H -->|No| E
    H -->|Yes| I[Execute Request]
    F -->|No| I
```

### Credential Management

- **Runtime Credentials**: Stored in `setup_app.FirstTimeSetup` model (encrypted with Fernet)
- **Environment Variables**: `.env` file (gitignored, never committed)
- **Secrets Rotation**: Manual via Django admin (future: automated)

---

## 📊 Observability Stack

### Metrics (Prometheus)

**Endpoint**: `/metrics/`

**Custom Metrics**:
```python
# Zabbix Client
zabbix_api_requests_total          # Counter: total requests
zabbix_api_request_duration_seconds  # Histogram: latency
zabbix_api_errors_total            # Counter: failures
zabbix_circuit_breaker_state       # Gauge: 0=closed, 1=open, 2=half-open

# Static Version
mapsprovefib_static_version_info   # Info: git commit, build date
```

### Health Checks

| Endpoint | Purpose | Success Criteria |
|----------|---------|------------------|
| `/healthz/` | Full health check | DB + cache + storage all OK |
| `/ready/` | Readiness probe | App can serve traffic |
| `/live/` | Liveness probe | Process is alive |

**Health Check Response**:
```json
{
  "status": "ok",
  "timestamp": 1731109200.123,
  "checks": {
    "db": {"ok": true, "type": "mysql", "latency_ms": 5.2},
    "cache": {"ok": true, "backend": "RedisCache", "latency_ms": 1.3},
    "storage": {"ok": true, "free_gb": 42.3}
  },
  "latency_ms": 23.6
}
```

### Logging

**Structured Logging** (JSON format):
```python
logger.info(
    "Fiber status fetched",
    extra={
        "cable_id": cable.id,
        "status": "up",
        "latency_ms": 45.2,
        "request_id": request.META.get("X-Request-ID")
    }
)
```

---

## 🚀 Deployment Architecture

### Production Stack

```mermaid
graph TD
    subgraph "Load Balancer"
        LB[Nginx / ALB]
    end
    
    subgraph "Application Tier"
        A1[Django Instance 1<br/>Gunicorn]
        A2[Django Instance 2<br/>Gunicorn]
        A3[Django Instance N<br/>Gunicorn]
    end
    
    subgraph "Worker Tier"
        W1[Celery Worker 1]
        W2[Celery Worker 2]
        B[Celery Beat<br/>Scheduler]
    end
    
    subgraph "Data Tier"
        DB[(MySQL/MariaDB<br/>Primary)]
        DBS[(MySQL<br/>Replica)]
        REDIS[(Redis)]
    end
    
    subgraph "Monitoring"
        PROM[Prometheus]
        GRAF[Grafana]
        SENT[Sentry]
    end
    
    LB --> A1
    LB --> A2
    LB --> A3
    
    A1 --> DB
    A2 --> DB
    A3 --> DB
    A1 --> REDIS
    A2 --> REDIS
    A3 --> REDIS
    
    W1 --> DB
    W2 --> DB
    W1 --> REDIS
    W2 --> REDIS
    B --> REDIS
    
    DB --> DBS
    
    PROM -->|scrape /metrics/| A1
    PROM -->|scrape /metrics/| A2
    PROM -->|scrape /metrics/| A3
    GRAF -->|visualize| PROM
    A1 -->|errors| SENT
    A2 -->|errors| SENT
    A3 -->|errors| SENT
```

### Scaling Considerations

| Component | Horizontal Scaling | Vertical Scaling | Notes |
|-----------|-------------------|------------------|-------|
| **Django** | ✅ Yes | ✅ Yes | Stateless, add more Gunicorn workers |
| **Celery Workers** | ✅ Yes | ✅ Yes | Task-specific queues (high/low priority) |
| **MySQL** | ⚠️ Read replicas | ✅ Yes | Write bottleneck, consider sharding |
| **Redis** | ✅ Cluster mode | ✅ Yes | Optional for cache, mandatory for Channels |

---

## 🔄 Migration Path (v1.x → v2.0.0)

### Phase-by-Phase Evolution

```mermaid
graph TD
    V1[v1.x - Monolithic<br/>zabbix_api app]
    
    P0[Phase 0: Scaffolding<br/>Create inventory, monitoring, integrations]
    P1[Phase 1: Zabbix Isolation<br/>Move client to integrations/zabbix]
    P2[Phase 2: Monitoring Consolidation<br/>HostStatusProcessor]
    P3[Phase 3: Inventory Modularization<br/>API + services + usecases]
    P4[Phase 4: Legacy Removal<br/>Delete zabbix_api/]
    P5[Phase 5: Production Readiness<br/>Documentation + validation]
    
    V2[v2.0.0 - Modular<br/>inventory + monitoring + integrations]
    
    V1 --> P0
    P0 --> P1
    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    P5 --> V2
    
    style V1 fill:#f44336,color:#fff
    style V2 fill:#4CAF50,color:#fff
    style P4 fill:#FF9800,color:#fff
    style P5 fill:#2196F3,color:#fff
```

### Key Milestones

| Phase | Completion | Status | Breaking Changes |
|-------|------------|--------|------------------|
| **0** | ✅ 100% | Complete | None |
| **1** | ✅ 100% | Complete | None |
| **2** | ✅ 100% | Complete | None |
| **3** | ✅ 100% | Complete | None (shims maintained) |
| **4** | ✅ 100% | Complete | ❌ `zabbix_api` module removed |
| **5** | ⏳ 80% | In Progress | None (documentation only) |

---

## 📚 Related Documentation

- [BREAKING_CHANGES_v2.0.0.md](../releases/BREAKING_CHANGES_v2.0.0.md) — Migration guide
- [DEPLOYMENT.md](../operations/DEPLOYMENT.md) — **Production deployment** (unificado: setup, checklist, rollback)
- [MIGRATION_PRODUCTION_GUIDE.md](../operations/MIGRATION_PRODUCTION_GUIDE.md) — Database migration
- [API_DOCUMENTATION.md](../reference-root/API_DOCUMENTATION.md) — REST API reference
- [REFATORAR.md](../developer/REFATORAR.md) — Refactoring plan

---

**Last Updated**: 2025-01-07  
**Architecture Version**: v2.0.0  
**Author**: Don Jonhn  
**Review Status**: ✅ Approved for Production
