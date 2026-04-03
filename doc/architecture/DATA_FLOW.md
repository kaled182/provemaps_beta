# Data Flow & Integration Patterns

**MapsProveFiber** — Complete documentation of data flows, caching strategies, and real-time communication patterns.

**Last Updated**: 2025-11-07  
**Architecture Version**: v2.0.0

---

## 📖 Overview

This document describes how data flows through the MapsProveFiber system, from external sources (Zabbix API) through various caching layers to the frontend dashboard and real-time updates.

### Key Patterns
- **SWR (Stale-While-Revalidate)** — Fast responses with background refresh
- **Circuit Breaker** — Zabbix API resilience and failure isolation
- **WebSocket Push** — Real-time dashboard updates via Channels
- **Celery Async** — Background tasks for slow operations
- **Cache Hierarchy** — Redis → Django cache → In-memory fallback

---

## 🔄 Core Data Flows

### 1. Dashboard Real-Time Updates

The dashboard uses a multi-layered approach combining SWR caching, Celery periodic tasks, and WebSocket broadcasts.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DASHBOARD DATA FLOW                          │
└─────────────────────────────────────────────────────────────────────┘

┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│  Zabbix  │────▶│ Resilient    │────▶│  Monitoring │────▶│  Redis   │
│   API    │     │   Client     │     │  Use Cases  │     │  Cache   │
└──────────┘     └──────────────┘     └─────────────┘     └──────────┘
                        │                      │                 │
                        │ (Circuit Breaker)    │ (Business       │ (SWR Pattern)
                        │ (Retry Logic)        │  Logic)         │
                        │                      │                 │
                        ▼                      ▼                 ▼
                  ┌──────────────┐      ┌─────────────┐   ┌──────────┐
                  │   Metrics    │      │  Dashboard  │   │   View   │
                  │ (Prometheus) │      │    Cache    │   │ (Django) │
                  └──────────────┘      └─────────────┘   └──────────┘
                                             │ SWR              │
                                             │ (30s fresh)      │ HTTP Response
                                             │ (60s stale)      │
                                             ▼                  ▼
                                        ┌──────────────────────────┐
                                        │   Frontend Dashboard     │
                                        │   (Browser + WebSocket)  │
                                        └──────────────────────────┘
                                                    ▲
                                                    │ WebSocket Push
                                                    │ (Real-time)
                                        ┌──────────────────────────┐
                                        │  Channels Layer (Redis)  │
                                        │  + Celery Beat Task      │
                                        └──────────────────────────┘
```

#### Flow Steps

**A. Initial Page Load (HTTP Request)**

1. User accesses `/maps_view/dashboard/`
2. Django view calls `get_dashboard_cached()`
3. **SWR Cache Check**:
   - **Fresh cache (< 30s)**: Return immediately ✅
   - **Stale cache (30-60s)**: Return stale data + trigger async refresh 🔄
   - **Empty cache**: Synchronous fetch from Zabbix (blocking) ⏳
4. Template renders with data + cache metadata
5. JavaScript initializes WebSocket connection

**B. Background Refresh (Celery Beat)**

```python
# Scheduled every 60 seconds (configurable via DASHBOARD_CACHE_REFRESH_INTERVAL)
@shared_task
def refresh_dashboard_cache_task():
    # 1. Fetch fresh data from Zabbix (via monitoring.usecases)
    fresh_data = get_hosts_status_data()
    
    # 2. Update SWR cache
    dashboard_cache.set_cached_data(fresh_data)
    
    # 3. Broadcast to WebSocket clients
    broadcast_dashboard_status(fresh_data)
```

**Celery Beat Schedule** (configured in `core/celery.py`):
```python
beat_schedule={
    "refresh-dashboard-cache": {
        "task": "monitoring.tasks.refresh_dashboard_cache_task",
        "schedule": 60,  # seconds (default)
        "options": {"queue": "maps"},
    },
}
```

**C. Real-Time Updates (WebSocket)**

```
Frontend (JS)                Channels Layer              Backend
     │                            │                         │
     │──── ws://host/ws/dashboard/status/ ────▶│         │
     │                            │             │         │
     │◀──── connection_accepted ───────────────┤         │
     │                            │             │         │
     │                     (joins group:        │         │
     │                      "dashboard_status") │         │
     │                            │             │         │
     │                            │◀──── Celery Task ────┤
     │                            │     (refresh_dashboard_cache_task)
     │                            │             │         │
     │◀──── {"event": "dashboard.status", ... }┤         │
     │      (WebSocket push)      │             │         │
     │                            │             │         │
     │─── applyDashboardSnapshot()│             │         │
     │    (update UI markers)     │             │         │
```

**WebSocket Message Format**:
```json
{
  "event": "dashboard.status",
  "data": {
    "hosts_status": [...],
    "summary": {
      "total": 45,
      "ok": 40,
      "problem": 3,
      "unknown": 2
    },
    "timestamp": "2025-11-07T10:45:00Z"
  }
}
```

---

### 2. Zabbix API Integration

All Zabbix API calls go through the **resilient client** with circuit breaker protection.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ZABBIX API INTEGRATION FLOW                      │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  Caller      │  (views, tasks, use cases)
│ (any module) │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   integrations.zabbix.client                         │
│                                                                      │
│  ┌─────────────────┐         ┌─────────────────┐                   │
│  │ Auth Cache      │         │ Circuit Breaker │                   │
│  │ (5 min TTL)     │         │ (CLOSED/OPEN/   │                   │
│  │                 │         │  HALF_OPEN)     │                   │
│  └─────────────────┘         └─────────────────┘                   │
│          │                            │                              │
│          │                            ▼                              │
│          │                   ┌─────────────────┐                   │
│          └──────────────────▶│  Retry Logic    │                   │
│                              │  (Exponential   │                   │
│                              │   Backoff)      │                   │
│                              └────────┬────────┘                   │
│                                       │                              │
│                                       ▼                              │
│                              ┌─────────────────┐                   │
│                              │  HTTP Request   │                   │
│                              │  (requests lib) │                   │
│                              └────────┬────────┘                   │
└───────────────────────────────────────┼──────────────────────────────┘
                                        │
                                        ▼
                              ┌─────────────────┐
                              │   Zabbix API    │
                              │  (External)     │
                              └─────────────────┘
                                        │
                                        ▼
                              ┌─────────────────┐
                              │  Prometheus     │
                              │    Metrics      │
                              │ - Request count │
                              │ - Latency       │
                              │ - Circuit state │
                              └─────────────────┘
```

#### Circuit Breaker States

| State | Behavior | Transition |
|-------|----------|------------|
| **CLOSED** | Normal operation, requests allowed | → OPEN after N consecutive failures |
| **OPEN** | All requests blocked immediately | → HALF_OPEN after timeout (30s) |
| **HALF_OPEN** | Limited requests (test recovery) | → CLOSED on success, → OPEN on failure |

**Configuration** (`integrations/zabbix/client.py`):
```python
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2  # seconds (1s, 2s, 4s)
CIRCUIT_BREAKER_THRESHOLD = 5  # failures to open
CIRCUIT_BREAKER_TIMEOUT = 30  # seconds in OPEN state
```

#### Example Call Flow

```python
# 1. Caller initiates request
from integrations.zabbix.client import resilient_client

hosts = resilient_client.call("host.get", {"output": ["hostid", "name"]})

# 2. Circuit breaker check
if circuit_breaker.is_open:
    raise CircuitBreakerOpenError("Too many failures, blocking requests")

# 3. Retry loop (max 3 attempts)
for attempt in range(1, MAX_RETRIES + 1):
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        # 4. Record success metrics
        record_zabbix_call(method="host.get", status="success", latency=0.5)
        circuit_breaker.record_success()
        
        return response.json()
        
    except (Timeout, ConnectionError) as e:
        # 5. Record failure and retry with backoff
        record_zabbix_call(method="host.get", status="error", latency=None)
        circuit_breaker.record_failure()
        
        if attempt < MAX_RETRIES:
            sleep(RETRY_BACKOFF_FACTOR ** attempt)
            continue
        else:
            raise
```

---

### 3. Inventory Sync (Periodic)

Devices, sites, and ports are synchronized from Zabbix to the local database periodically.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    INVENTORY SYNC FLOW (Celery)                     │
└─────────────────────────────────────────────────────────────────────┘

Celery Beat (every 24h)
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  inventory.tasks.sync_zabbix_inventory_task                          │
│                                                                      │
│  1. Fetch all hosts from Zabbix API                                │
│     ├─ resilient_client.call("host.get", {...})                    │
│     └─ Retry on failure, record metrics                            │
│                                                                      │
│  2. For each Zabbix host:                                           │
│     ├─ Check if Device exists in DB (by zabbix_host_id)            │
│     ├─ If new: Create Device + Site (if needed)                    │
│     ├─ If existing: Update fields (name, status, IP)               │
│     └─ Fetch host items (ports, interfaces)                        │
│                                                                      │
│  3. Sync Ports:                                                     │
│     ├─ Fetch interface data from Zabbix                            │
│     ├─ Create/update Port records in DB                            │
│     └─ Link ports via FiberCable if topology data available        │
│                                                                      │
│  4. Invalidate caches:                                              │
│     ├─ dashboard_cache.invalidate()                                │
│     ├─ route_cache.invalidate()                                    │
│     └─ Trigger dashboard refresh                                   │
│                                                                      │
│  5. Broadcast update:                                               │
│     └─ WebSocket: notify clients of inventory change              │
└──────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Django ORM (inventory models)                   │
│  - Site, Device, Port, FiberCable, Route                           │
└──────────────────────────────────────────────────────────────────────┘
```

**Celery Beat Schedule**:
```python
"sync-zabbix-inventory": {
    "task": "inventory.tasks.sync_zabbix_inventory_task",
    "schedule": 86400,  # 24 hours (default)
    "options": {"queue": "default"},
}
```

**Database Transaction Flow**:
```python
@shared_task
def sync_zabbix_inventory_task():
    with transaction.atomic():
        # 1. Fetch from Zabbix
        hosts = resilient_client.call("host.get", {...})
        
        # 2. Bulk update/create
        for host in hosts:
            device, created = Device.objects.update_or_create(
                zabbix_host_id=host["hostid"],
                defaults={
                    "name": host["host"],
                    "ip_address": host.get("interfaces", [{}])[0].get("ip"),
                    "status": host["status"],
                }
            )
        
        # 3. Invalidate caches
        invalidate_dashboard_cache()
```

---

### 4. Route Building (Async)

Optical route calculations are CPU-intensive and run asynchronously via Celery.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ROUTE BUILDING FLOW (Async)                      │
└─────────────────────────────────────────────────────────────────────┘

User clicks "Build Route"
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  POST /api/v1/inventory/routes/tasks/build/                         │
│                                                                      │
│  1. Validate request payload (requires `route_id`)                 │
│  2. Enqueue Celery task                                            │
│     └─ task_id = routes_builder.tasks.build_route.delay(route_id) │
│  3. Return 202 Accepted + task_id                                  │
└──────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Celery Worker: routes_builder.tasks.build_route                    │
│                                                                      │
│  1. Fetch inventory data (sites, devices, fibers)                  │
│     └─ Query Django ORM for topology graph                         │
│                                                                      │
│  2. Run pathfinding algorithm                                       │
│     ├─ Dijkstra's shortest path (by distance or loss)              │
│     ├─ Calculate cumulative optical loss                           │
│     └─ Validate power budget                                       │
│                                                                      │
│  3. Create Route record in DB                                       │
│     ├─ Route.objects.create(...)                                   │
│     └─ Link fiber segments                                         │
│                                                                      │
│  4. Cache result                                                    │
│     └─ cache.set(f"route:{route_id}", result, timeout=3600)        │
│                                                                      │
│  5. Update task status                                              │
│     └─ self.update_state(state="SUCCESS", meta={...})              │
└──────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Frontend polls: GET /api/v1/inventory/routes/tasks/status/{task_id}│
│                                                                      │
│  Response:                                                          │
│  {                                                                   │
│    "task_id": "...",                                                │
│    "state": "SUCCESS",                                              │
│    "result": {                                                       │
│      "route_id": 42,                                                │
│      "distance_km": 435.2,                                          │
│      "loss_db": 4.5,                                                │
│      "segments": [...]                                              │
│    }                                                                 │
│  }                                                                   │
└──────────────────────────────────────────────────────────────────────┘
```

**Task State Transitions**:
```
PENDING → STARTED → SUCCESS
              ↓
           FAILURE
              ↓
           RETRY (with exponential backoff)
```

---

### 5. Cache Hierarchy & Degradation

The system uses a layered caching strategy with graceful degradation.

```
┌─────────────────────────────────────────────────────────────────────┐
│                       CACHE HIERARCHY                               │
└─────────────────────────────────────────────────────────────────────┘

Layer 1: Redis Cache (Primary)
  ├─ SWR Dashboard Cache (TTL: 30s fresh, 60s stale)
  ├─ Zabbix Auth Token (TTL: 300s)
  ├─ Route Calculations (TTL: 3600s)
  └─ Fiber Status (TTL: 60s)
       │
       │ (Redis unavailable)
       ▼
Layer 2: Django In-Memory Cache (Fallback)
  ├─ Per-process cache
  ├─ Limited capacity
  └─ Cleared on worker restart
       │
       │ (Cache disabled)
       ▼
Layer 3: Direct Fetch (Degraded Mode)
  ├─ Synchronous Zabbix API calls (blocking)
  ├─ Increased latency
  └─ Circuit breaker protection active
```

#### Graceful Degradation Pattern

```python
def safe_cache_get(key: str, default: Any = None) -> Any:
    """Get from cache with fallback on Redis failure."""
    try:
        return cache.get(key, default)
    except Exception as e:
        logger.warning(f"Cache read failed for {key}: {e}")
        return default

def safe_cache_set(key: str, value: Any, timeout: int = 300) -> bool:
    """Set cache with silent failure on Redis unavailable."""
    try:
        cache.set(key, value, timeout=timeout)
        return True
    except Exception as e:
        logger.warning(f"Cache write failed for {key}: {e}")
        return False
```

---

## 🔍 Monitoring & Observability

### Prometheus Metrics Exported

#### Zabbix Client Metrics
```prometheus
# Request counters
zabbix_api_requests_total{method="host.get",status="success"} 342
zabbix_api_requests_total{method="host.get",status="error"} 5

# Latency histogram
zabbix_api_duration_seconds_bucket{le="0.5",method="host.get"} 320
zabbix_api_duration_seconds_bucket{le="1.0",method="host.get"} 340

# Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)
zabbix_circuit_breaker_state 0
```

#### Celery Metrics
```prometheus
# Task execution count
celery_task_total{task="refresh_dashboard_cache_task",status="success"} 1523
celery_task_total{task="sync_zabbix_inventory_task",status="success"} 12

# Worker availability
celery_worker_available{worker="celery@worker1"} 1
```

#### Django Metrics
```prometheus
# HTTP request latency
django_http_requests_latency_seconds{view="dashboard_view",method="GET"} 0.15

# Database query duration
django_db_query_duration_seconds{query="SELECT FROM inventory_device"} 0.02
```

---

## 📊 Performance Characteristics

### Response Times (Target SLAs)

| Endpoint | Target | Typical | Notes |
|----------|--------|---------|-------|
| Dashboard (cached) | < 100ms | ~50ms | SWR fresh cache hit |
| Dashboard (stale) | < 150ms | ~80ms | SWR stale cache + async refresh |
| Dashboard (miss) | < 3s | ~1.5s | Synchronous Zabbix fetch |
| API device list | < 200ms | ~100ms | Database query only |
| Route calculation | N/A | 5-30s | Async (Celery task) |
| Health check | < 50ms | ~20ms | Minimal DB query |

### Cache Hit Rates (Production)

- **Dashboard SWR**: ~95% hit rate (fresh + stale)
- **Zabbix auth token**: ~99% hit rate
- **Route cache**: ~85% hit rate

### Celery Queue Throughput

- **default queue**: ~50 tasks/min
- **maps queue**: ~120 tasks/min (dashboard refresh)
- **routes queue**: ~10 tasks/min (route building)

---

## 🚨 Failure Scenarios & Recovery

### Scenario 1: Zabbix API Down

**Impact**: Dashboard shows stale data or "Unable to fetch" error

**Recovery Flow**:
1. Circuit breaker opens after 5 consecutive failures
2. All requests blocked for 30 seconds (OPEN state)
3. SWR cache serves stale data (up to 60s old)
4. Frontend displays "Degraded Mode" banner
5. After 30s, circuit transitions to HALF_OPEN
6. Test request sent; if success → CLOSED, if fail → OPEN (repeat)

**Metrics**:
- `zabbix_circuit_breaker_state` = 1 (OPEN)
- `zabbix_api_requests_total{status="circuit_open"}` increments

---

### Scenario 2: Redis Unavailable

**Impact**: No caching, increased Zabbix API load, slower responses

**Recovery Flow**:
1. `safe_cache_get()` / `safe_cache_set()` fail silently
2. Dashboard falls back to synchronous fetch
3. Response time increases (100ms → 1.5s)
4. Health check reports Redis as "degraded"
5. System continues operating (no crash)

**Mitigation**: Use managed Redis (AWS ElastiCache, Google Memorystore) for HA

---

### Scenario 3: Celery Workers Offline

**Impact**: No background cache refresh, no route building

**Recovery Flow**:
1. Dashboard continues serving from SWR cache (stale data)
2. `/celery/status/` health check returns 503
3. Manual refresh via HTTP fallback (JavaScript polling)
4. Route building requests return "No workers available" error

**Monitoring**: Alert on `celery_worker_available` = 0

---

## 📚 Related Documentation

- [MODULES.md](./MODULES.md) — App structure and responsibilities
- [ENDPOINTS.md](../api/ENDPOINTS.md) — Complete API reference
- [DEPLOYMENT.md](../operations/DEPLOYMENT.md) — Production deployment guide
- [OVERVIEW.md](./OVERVIEW.md) — Architecture overview

---

**MapsProveFiber** — Data Flow Documentation  
**Version**: v2.0.0 | **Last Updated**: 2025-11-07
