# API Endpoints Reference# API Documentation - MapsProveFiber v2.0.0



**MapsProveFiber** — Complete REST API documentation for all public and internal endpoints.This document describes every REST endpoint exposed by MapsProveFiber, including integration with Zabbix, the local inventory, fiber routes, Celery jobs, and health probes. The material is organized by module to emphasize clarity, security, and quick diagnostics.



**Last Updated**: 2025-11-07  > **⚠️ BREAKING CHANGES**: v2.0.0 introduces modular architecture. See [`BREAKING_CHANGES_v2.0.0.md`](../releases/BREAKING_CHANGES_v2.0.0.md) for migration guide.

**API Version**: v1  

**Base URL**: `http://localhost:8000`---



---## Module overview



## 📖 Overview| Module | Path | Primary responsibility | Status |

|--------|------|------------------------|--------|

This document provides a comprehensive reference for all HTTP endpoints in the MapsProveFiber application.| **Inventory API** | `api/v1/inventory/` | Devices, ports, fibers, routes, operational metadata | ✅ Active |

| **Monitoring** | `monitoring/` | Health checks, combined Zabbix + inventory status | ✅ Active |

### API Organization| **Integrations (Zabbix)** | `integrations/zabbix/` | Resilient Zabbix API client (circuit breaker, retry) | ✅ Active |

- **Inventory API** (`/api/v1/inventory/*`) — Network infrastructure CRUD| **Routes Builder** | `routes_builder/` | Celery tasks for route calculation (legacy) | ⚠️ Deprecated |

- **Monitoring API** (`/api/v1/monitoring/*`) — Real-time status and metrics  | **Setup App** | `setup_app/` | Runtime settings and credential management | ✅ Active |

- **Maps View** (`/maps_view/*`) — Dashboard and visualization| **Core** | `core/` | Django configuration, Celery, URLs, health probes | ✅ Active |

- **Routes Builder** (`/routes_builder/*`) — Optical route planning ⚠️ Legacy| **~~Zabbix API~~** | ~~`zabbix_api/`~~ | ~~Legacy integration module~~ | ❌ **REMOVED in v2.0.0** |

- **Setup App** (`/setup_app/*`) — Configuration and documentation

- **Health & Metrics** (`/health*`, `/metrics/`) — Observability---



### Authentication## Access and security

All endpoints require:

- ✅ **Authenticated user** (Django session or token)- Every endpoint requires a logged-in Django user.

- 🔒 **Staff user** (for administrative endpoints)- Administrative endpoints require a staff user.

- 🚨 **Diagnostic flag** (`ENABLE_DIAGNOSTIC_ENDPOINTS=true` for testing endpoints)- Diagnostic routes are guarded by the `ENABLE_DIAGNOSTIC_ENDPOINTS` flag:

  ```bash

---  ENABLE_DIAGNOSTIC_ENDPOINTS=true

  ```

## 🏥 Health & Observability  When the flag is `false`, the routes respond with **HTTP 403** without executing external actions.



### Health Checks---



| Endpoint | Method | Auth | Description | Response |## Base URLs

|----------|--------|------|-------------|----------|

| `/health/` | GET | No | Overall health status | JSON |- Public endpoints: `http://localhost:8000/`

| `/health/ready/` | GET | No | Readiness probe (K8s) | JSON |- **Inventory API (v2.0.0+)**: `http://localhost:8000/api/v1/inventory/` ✅

| `/health/live/` | GET | No | Liveness probe (K8s) | JSON |- ~~Zabbix integration (legacy)~~: ~~`http://localhost:8000/zabbix_api/`~~ ❌ **REMOVED**

| `/celery/status/` | GET | Yes | Celery worker/beat status | JSON |

> **Migration Note**: All `/zabbix_api/*` endpoints have been removed. Use `/api/v1/inventory/*` instead.  

#### Example: `/health/`> Replace `localhost` with the production domain in deployed environments.

```bash

curl http://localhost:8000/health/---

```

## Health and status

**Response** (200 OK):

```json| Endpoint | Method | Description |

{|----------|--------|-------------|

  "status": "healthy",| `/healthz/` | GET | Full system health check (database, cache, storage, runtime) |

  "timestamp": "2025-11-07T10:30:00Z",| `/ready/` | GET | Readiness probe - reports when the app can receive traffic |

  "database": "ok",| `/live/` | GET | Liveness probe - verifies that the process is alive |

  "redis": "ok",

  "celery_worker": "ok",Example response:

  "celery_beat": "ok"```json

}{

```  "status": "ok",

  "timestamp": 1731109200.123,

### Metrics  "checks": {

    "db": {"ok": true, "type": "mysql"},

| Endpoint | Method | Auth | Description | Format |    "cache": {"ok": true, "backend": "RedisCache"},

|----------|--------|------|-------------|--------|    "storage": {"ok": true, "free_gb": 42.3}

| `/metrics/` | GET | No | Prometheus metrics | Text |  },

  "latency_ms": 23.6

---```



## 📦 Inventory API (`/api/v1/inventory/*`)---



### Sites## ~~Zabbix API~~ (REMOVED in v2.0.0)



| Endpoint | Method | Auth | Description |> **⚠️ DEPRECATED**: All endpoints under `/zabbix_api/*` have been **removed** in v2.0.0.  

|----------|--------|------|-------------|> **Migration Required**: Use Inventory API (`/api/v1/inventory/*`) and Monitoring endpoints instead.  

| `/api/v1/inventory/sites/` | GET | Yes | List all sites |> **See**: [`BREAKING_CHANGES_v2.0.0.md`](../releases/BREAKING_CHANGES_v2.0.0.md) for migration guide.



### Devices### Legacy Endpoint Migration Map



| Endpoint | Method | Auth | Description || ❌ Removed Endpoint (v1.x) | ✅ New Endpoint (v2.0.0+) | Notes |

|----------|--------|------|-------------||----------------------------|---------------------------|-------|

| `/api/v1/inventory/devices/<device_id>/ports/` | GET | Yes | List device ports || `/zabbix_api/inventory/sites/` | `/api/v1/inventory/sites/` | Direct replacement |

| `/api/v1/inventory/devices/<device_id>/ports/optical/` | GET | Yes | Ports with optical status || `/zabbix_api/inventory/devices/` | `/api/v1/inventory/devices/` | Direct replacement |

| `/api/v1/inventory/devices/add-from-zabbix/` | POST | Staff | Import device from Zabbix || `/zabbix_api/inventory/fibers/` | `/api/v1/inventory/fibers/` | Direct replacement |

| `/api/v1/inventory/zabbix/discover-hosts/` | GET | Staff | Discover Zabbix hosts || `/zabbix_api/api/fibers/oper-status/` | `/api/v1/inventory/fibers/oper-status/` | Direct replacement |

| `/api/v1/inventory/bulk/` | POST | Staff | Bulk create inventory || `/zabbix_api/api/test/*` | `/api/v1/inventory/diagnostics/*` | Diagnostic endpoints moved |

| `/zabbix_api/status/` | Use `integrations.zabbix.zabbix_service.zabbix_request()` | Backend only |

### Ports| `/zabbix_api/monitoring/*` | Use `monitoring.usecases.HostStatusProcessor` | Backend only |



| Endpoint | Method | Auth | Description |### Status and monitoring

|----------|--------|------|-------------|

| `/api/v1/inventory/ports/<port_id>/optical/` | GET | Yes | Optical power levels |**STATUS**: ❌ **ALL ENDPOINTS REMOVED**

| `/api/v1/inventory/ports/<port_id>/traffic/` | GET | Yes | Traffic history (24h) |

Endpoints are grouped by category. Default prefix: ~~`/zabbix_api/`~~ **DELETED**

### Fiber Cables

| Endpoint | Method | Description | Status |

| Endpoint | Method | Auth | Description ||----------|--------|-------------|--------|

|----------|--------|------|-------------|| ~~`/status/`~~ | ~~GET~~ | ~~Overall health of the Zabbix environment~~ | ❌ Removed |

| `/api/v1/inventory/fibers/` | GET | Yes | List all fiber cables || ~~`/monitoring/overview/`~~ | ~~GET~~ | ~~Summary view of hosts and active issues~~ | ❌ Removed |

| `/api/v1/inventory/fibers/<cable_id>/` | GET | Yes | Fiber cable details || ~~`/monitoring/performance/`~~ | ~~GET~~ | ~~Aggregated metrics (CPU, memory, disk)~~ | ❌ Removed |

| `/api/v1/inventory/fibers/<cable_id>/oper-status/` | PUT | Staff | Update operational status || ~~`/monitoring/availability/`~~ | ~~GET~~ | ~~Uptime percentages~~ | ❌ Removed |

| `/api/v1/inventory/fibers/oper-status/` | GET | Yes | All fiber operational status || ~~`/monitoring/latest_all/`~~ | ~~GET~~ | ~~Latest values for all tracked hosts~~ | ❌ Removed |

| `/api/v1/inventory/fibers/<cable_id>/live-status/` | GET | Yes | Real-time fiber status from Zabbix |

| `/api/v1/inventory/fibers/live-status/` | GET | Yes | All fibers live status |**Migration**: Use `monitoring.usecases.HostStatusProcessor` for backend integration.

| `/api/v1/inventory/fibers/refresh-status/` | POST | Yes | Trigger status refresh (Celery) |

| `/api/v1/inventory/fibers/import-kml/` | POST | Staff | Import fibers from KML |---

| `/api/v1/inventory/fibers/manual-create/` | POST | Staff | Manually create fiber |

| `/api/v1/inventory/fibers/<cable_id>/value-mapping/` | GET | Yes | Zabbix value mapping status |### Hosts and items



### Routes (Optical Path Planning)**STATUS**: ❌ **ALL ENDPOINTS REMOVED**



| Endpoint | Method | Auth | Description || Endpoint | Method | Description | Status |

|----------|--------|------|-------------||----------|--------|-------------|--------|

| `/api/v1/inventory/routes/tasks/build/` | POST | Staff | Build/calculate route (async) || ~~`/hosts/`~~ | ~~GET~~ | ~~List hosts with basic metadata~~ | ❌ Removed |

| `/api/v1/inventory/routes/tasks/batch/` | POST | Staff | Batch build routes || ~~`/hosts/{id}/`~~ | ~~GET~~ | ~~Detailed information for a host~~ | ❌ Removed |

| `/api/v1/inventory/routes/tasks/import/` | POST | Staff | Import route from KML || ~~`/hosts/{id}/items/`~~ | ~~GET~~ | ~~Items grouped by category~~ | ❌ Removed |

| `/api/v1/inventory/routes/tasks/invalidate/` | POST | Staff | Clear route cache || ~~`/hosts/{id}/triggers/`~~ | ~~GET~~ | ~~Triggers grouped by severity~~ | ❌ Removed |

| `/api/v1/inventory/routes/tasks/health/` | GET | Staff | Route service health check || ~~`/hosts/{id}/graphs/`~~ | ~~GET~~ | ~~Available graphs~~ | ❌ Removed |

| `/api/v1/inventory/routes/tasks/status/<task_id>/` | GET | Yes | Check async task status || ~~`/hosts/{id}/latest/`~~ | ~~GET~~ | ~~Latest metrics for the host~~ | ❌ Removed |

| `/api/v1/inventory/routes/tasks/bulk/` | POST | Staff | Bulk route operations || ~~`/hosts/{id}/performance/`~~ | ~~GET~~ | ~~CPU, memory, and disk performance~~ | ❌ Removed |

| ~~`/items/{hostid}/{itemid}/history/`~~ | ~~GET~~ | ~~24 hour history for the item~~ | ❌ Removed |

### Diagnostics (Testing Only)

**Migration**: Use `integrations.zabbix.client.resilient_client.call()` for direct Zabbix API access.

⚠️ **Requires** `ENABLE_DIAGNOSTIC_ENDPOINTS=true`

---

| Endpoint | Method | Auth | Description |

|----------|--------|------|-------------|### Problems and events

| `/api/v1/inventory/diagnostics/telnet/` | POST | Staff | Test telnet connectivity |

| `/api/v1/inventory/diagnostics/ping/` | POST | Staff | Test ICMP ping |**STATUS**: ❌ **ALL ENDPOINTS REMOVED**

| `/api/v1/inventory/diagnostics/ping-telnet/` | POST | Staff | Combined ping + telnet test |**STATUS**: ❌ **ALL ENDPOINTS REMOVED**

| `/api/v1/inventory/diagnostics/cables/<cable_id>/up/` | POST | Staff | Simulate cable UP state |

| `/api/v1/inventory/diagnostics/cables/<cable_id>/down/` | POST | Staff | Simulate cable DOWN state || Endpoint | Method | Description | Status |

| `/api/v1/inventory/diagnostics/cables/<cable_id>/unknown/` | POST | Staff | Reset cable state to unknown ||----------|--------|-------------|--------|

| ~~`/problems/`~~ | ~~GET~~ | ~~Active problems~~ | ❌ Removed |

---| ~~`/problems/summary/`~~ | ~~GET~~ | ~~Breakdown by severity~~ | ❌ Removed |

| ~~`/problems/by-severity/`~~ | ~~GET~~ | ~~Count by severity level~~ | ❌ Removed |

## 📊 Monitoring API (`/api/v1/monitoring/*`)| ~~`/problems/critical/`~~ | ~~GET~~ | ~~Critical incidents only~~ | ❌ Removed |

| ~~`/events/recent/`~~ | ~~GET~~ | ~~Condensed chronological feed~~ | ❌ Removed |

| Endpoint | Method | Auth | Description || ~~`/events/summary/`~~ | ~~GET~~ | ~~Distribution by status and severity~~ | ❌ Removed |

|----------|--------|------|-------------|

| `/api/v1/monitoring/hosts/status/` | GET | Yes | Zabbix host status summary |---

| `/api/v1/monitoring/dashboard/snapshot/` | GET | Yes | Dashboard snapshot (cached) |

### Network and inventory bridge (legacy)

---

**STATUS**: ❌ **REMOVED** — Inventory-related endpoints now live exclusively under `/api/v1/inventory/`.

## 🗺️ Maps View (`/maps_view/*`)

The `/zabbix_api/` versions have been **permanently removed** in v2.0.0. Update all client code to use the new inventory namespace.

| Endpoint | Method | Auth | Description |

|----------|--------|------|-------------|---

| `/maps_view/dashboard/` | GET | Yes | Main dashboard (HTML) |

| `/maps_view/metrics/` | GET | Yes | Metrics dashboard (HTML) |### Diagnostic tools

| `/maps_view/api/hosts-status/` | GET | Yes | Real-time host status (JSON) |

**STATUS**: ⚠️ **MOVED** to `/api/v1/inventory/diagnostics/`

---

**STATUS**: ⚠️ **MOVED** to `/api/v1/inventory/diagnostics/`

## 🛠️ Routes Builder (`/routes_builder/*`)

Prefix: `/api/v1/inventory/diagnostics/` (updated in v2.0.0)

⚠️ **Legacy** — Being consolidated into `inventory` API (Phase 4)

> Available only when `ENABLE_DIAGNOSTIC_ENDPOINTS=true` and the user has the staff flag.

| Endpoint | Method | Auth | Description |

|----------|--------|------|-------------|| Endpoint | Method | Description | Status |

| `/routes_builder/fiber-route-builder/` | GET | Yes | Route builder UI (HTML) ||----------|--------|-------------|--------|

| `/routes_builder/tasks/build/` | POST | Staff | Build route (Celery task) || `/ping/` | GET | Remote ping test | ✅ Active |

| `/routes_builder/tasks/import/` | POST | Staff | Import KML route || `/telnet/` | GET | Port check via Telnet | ✅ Active |

| `/routes_builder/tasks/status/<task_id>/` | GET | Yes | Task status || `/ping-telnet/` | GET | Combined ping and Telnet checks | ✅ Active |

| `/cables/{id}/up/` | POST | Mark fiber cable as active | ✅ Active |

---| `/cables/{id}/down/` | POST | Mark fiber cable as inactive | ✅ Active |

| `/cables/{id}/unknown/` | POST | Mark fiber cable as unknown | ✅ Active |

## ⚙️ Setup App (`/setup_app/*`)

~~Legacy diagnostic routes under `/zabbix_api/api/test/*` have been removed~~; all integrations must use the inventory diagnostic endpoints.

| Endpoint | Method | Auth | Description |

|----------|--------|------|-------------|---

| `/setup_app/dashboard/` | GET | Yes | Setup dashboard (HTML) |

| `/setup_app/first_time/` | GET/POST | Staff | First-time setup wizard |### Lookup endpoints

| `/setup_app/config/` | GET/POST | Staff | Runtime config editor |

| `/setup_app/docs/` | GET | Yes | Documentation index |Used by autocomplete widgets and interactive UI components.

| `/setup_app/docs/<path>/` | GET | Yes | View specific documentation |

| Endpoint | Method | Description |

---|----------|--------|-------------|

| `/lookup/hosts/` | GET | Lightweight host search |

## 📚 Related Documentation| `/lookup/hosts/{id}/interfaces/` | GET | Interfaces for a host |

| `/lookup/interfaces/{id}/details/` | GET | Interface details |

- [MODULES.md](../architecture/MODULES.md) — App structure and responsibilities

- [DATA_FLOW.md](../architecture/DATA_FLOW.md) — Data flow patterns---

- [DEPLOYMENT.md](../operations/DEPLOYMENT.md) — Production deployment guide

## Inventory API

---

Prefix: `/api/v1/inventory/`

**MapsProveFiber** — API Endpoints Reference  

**Version**: v1 | **Last Updated**: 2025-11-07### Sites and devices


| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sites/` | GET | List sites in the inventory |
| `/devices/add-from-zabbix/` | POST | Create a device populated from Zabbix |
| `/zabbix/discover-hosts/` | GET | Preview hosts available for import |
| `/bulk/` | POST | Bulk device and port ingestion |

### Ports and telemetry

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/devices/<device_id>/ports/` | GET | Ports registered for a device |
| `/devices/<device_id>/ports/optical/` | GET | Ports with optical telemetry |
| `/ports/<port_id>/optical/` | GET | Optical measurements for a port |
| `/ports/<port_id>/traffic/` | GET | Historical RX/TX series for a port |

### Fibers and routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/fibers/` | GET | List fiber cables with metadata |
| `/fibers/<cable_id>/` | GET/PUT/DELETE | Retrieve, update, or remove a cable |
| `/fibers/manual-create/` | POST | Create a cable manually |
| `/fibers/import-kml/` | POST | Import fiber geometry from a KML file |
| `/fibers/import-kml/modal/` | GET | Render the HTML modal for KML imports |

### Fiber status and diagnostics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/fibers/<cable_id>/oper-status/` | GET | Refresh operational status for a cable |
| `/fibers/<cable_id>/live-status/` | GET | Live status for a single cable |
| `/fibers/live-status/` | GET | Live status snapshot for all cables |
| `/fibers/refresh-status/` | GET | Force a refresh for cached fiber statuses |
| `/fibers/<cable_id>/value-mapping/` | GET | Zabbix value mapping for a cable |

---

## Routes Builder task API

Prefix: `/routes/tasks/`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tasks/build/` | POST | Enqueue a route calculation |
| `/tasks/batch/` | POST | Enqueue multiple routes |
| `/tasks/invalidate/` | POST | Invalidate the cached route |
| `/tasks/health/` | GET | Worker health check |
| `/tasks/status/{task_id}/` | GET | Task status lookup |
| `/tasks/bulk/` | POST | Batch operations (build plus invalidate) |

Example request:
```json
{
  "route_id": 12,
  "force": true,
  "options": {"recalc_topology": true}
}
```
Example response:
```json
{
  "status": "enqueued",
  "task_id": "a23b9cfa-22bb-44c8-8c1f-bcd56f0",
  "queue": "maps"
}
```

---

## Standard error structure

| Code | Type | Description |
|------|------|-------------|
| **400** | `Bad Request` | Invalid JSON payload or missing parameters |
| **401** | `Unauthorized` | User is not authenticated |
| **403** | `Forbidden` | Permission denied or diagnostics disabled |
| **404** | `Not Found` | Resource not found |
| **409** | `Conflict` | Route locked by another process |
| **500** | `Server Error` | Internal failure - check Celery and Django logs |

---

## Best practices

- Return `HTTP 202` for asynchronous operations.
- Always validate the `task_id` before polling the status endpoint.
- Set `DEBUG=false` in production.
- Monitor workers with:
  ```bash
  celery -A core.celery_app inspect active
  ```
