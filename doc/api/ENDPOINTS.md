# API Documentation · MapsProveFiber v2.0.0

**MapsProveFiber** — Reference for every HTTP endpoint exposed by the platform, including inventory, monitoring, dashboard, setup, and observability surfaces.

**Last Updated**: 2025-11-08  
**API Version**: v1  
**Base URL**: `http://localhost:8000`

---

## Module Overview

| Module | Path Prefix | Primary Responsibility | Status |
|--------|-------------|-----------------------|--------|
| Inventory API | `/api/v1/inventory/` | Network sites, devices, ports, fiber cables, route orchestration | ✅ Active |
| Monitoring API | `/api/v1/monitoring/` | Inventory + Zabbix status aggregation, dashboard snapshots | ✅ Active |
| Maps View | `/maps_view/` | Real-time dashboard UI, metrics views | ✅ Active |
| Setup App | `/setup_app/` | Runtime credentials, configuration, documentation viewer | ✅ Active |
| Core | `/health*`, `/metrics/` | Health probes, Prometheus metrics, Celery status | ✅ Active |
| Integrations (Zabbix) | n/a (library) | Resilient Zabbix RPC client used by services | ✅ Active |
| ~~Routes Builder~~ | ~~`/routes_builder/*`~~ | ~~Legacy optical route planner~~ | ❌ Archived Nov 2025 |
| ~~Zabbix API~~ | ~~`/zabbix_api/*`~~ | ~~Legacy integration module~~ | ❌ Removed |

---

## Authentication & Access Control

- All HTTP endpoints require an authenticated Django user session or token.
- Mutating Inventory endpoints and diagnostics routes require staff privileges.
- Diagnostics endpoints are protected by the `ENABLE_DIAGNOSTIC_ENDPOINTS` flag in `settings/base.py`; disabled routes return **HTTP 403**.

---

## Health, Metrics & Core Probes

### Health Checks

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health/` | GET | No | Aggregate health report (database, cache, Celery, runtime) |
| `/health/ready/` | GET | No | Readiness probe |
| `/health/live/` | GET | No | Liveness probe |
| `/celery/status/` | GET | Staff | Celery worker and beat inspection |

### Metrics

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/metrics/` | GET | No | Prometheus metrics exporter |

---

## Inventory API (`/api/v1/inventory/`)

Single source of truth for the network topology and route orchestration. Responses are JSON unless noted.

### Sites & Devices

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/sites/` | GET | Yes | List inventory sites |
| `/devices/<int:device_id>/` | GET | Yes | Device detail (includes ports and Zabbix metadata) |
| `/devices/<int:device_id>/ports/` | GET | Yes | Ports for a device |
| `/devices/<int:device_id>/ports/optical/` | GET | Yes | Ports with optical telemetry |
| `/devices/add-from-zabbix/` | POST | Staff | Import device and ports from Zabbix |
| `/zabbix/discover-hosts/` | GET | Staff | Preview Zabbix hosts eligible for import |
| `/bulk/` | POST | Staff | Bulk ingest devices, ports, and fibers |

### Ports & Telemetry

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/ports/<int:port_id>/optical/` | GET | Yes | Optical power levels for a port |
| `/ports/<int:port_id>/traffic/` | GET | Yes | Historical RX/TX metrics |

### Fiber Cables

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/fibers/` | GET | Yes | List fiber cables |
| `/fibers/<int:cable_id>/` | GET | Yes | Cable detail |
| `/fibers/<int:cable_id>/oper-status/` | PUT | Staff | Update operational state |
| `/fibers/oper-status/` | GET | Yes | Aggregated operational state for all fibers |
| `/fibers/<int:cable_id>/live-status/` | GET | Yes | Real-time metrics for a cable |
| `/fibers/live-status/` | GET | Yes | Real-time metrics for all cables |
| `/fibers/refresh-status/` | POST | Staff | Trigger asynchronous refresh via Celery |
| `/fibers/import-kml/` | POST | Staff | Bulk import fiber geometry from KML |
| `/fibers/manual-create/` | POST | Staff | Manually register a fiber |
| `/fibers/<int:cable_id>/value-mapping/` | GET | Yes | Zabbix value mapping for a fiber |

### Routes & Task Orchestration

As of v2.0.0 all optical route build operations are consolidated here; the standalone `routes_builder` app is archived. Base path: `/api/v1/inventory/routes/tasks/`.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/inventory/routes/tasks/build/` | POST | Staff | Trigger calculation for a single route (Celery task) |
| `/api/v1/inventory/routes/tasks/batch/` | POST | Staff | Batch build multiple routes |
| `/api/v1/inventory/routes/tasks/bulk/` | POST | Staff | Composite operations (build + invalidate) for multiple routes |
| `/api/v1/inventory/routes/tasks/import/` | POST | Staff | Import route definition from KML |
| `/api/v1/inventory/routes/tasks/invalidate/` | POST | Staff | Clear cached route results |
| `/api/v1/inventory/routes/tasks/health/` | GET | Staff | Lightweight health probe for the route orchestration pipeline |
| `/api/v1/inventory/routes/tasks/status/<str:task_id_value>/` | GET | Yes | Poll Celery task state by ID |

### Diagnostics (Guarded)

All endpoints below require a staff user **and** `ENABLE_DIAGNOSTIC_ENDPOINTS=true`.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/diagnostics/telnet/` | POST | Staff | Execute a remote Telnet check |
| `/diagnostics/ping/` | POST | Staff | Execute an ICMP ping |
| `/diagnostics/ping-telnet/` | POST | Staff | Run ping followed by Telnet |
| `/diagnostics/cables/<int:cable_id>/up/` | POST | Staff | Simulate cable UP state |
| `/diagnostics/cables/<int:cable_id>/down/` | POST | Staff | Simulate cable DOWN state |
| `/diagnostics/cables/<int:cable_id>/unknown/` | POST | Staff | Reset cable state to unknown |

---

## Monitoring API (`/api/v1/monitoring/`)

Combines inventory data with Zabbix telemetry for dashboards and reporting.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hosts/status/` | GET | Yes | Aggregated device health and availability |
| `/dashboard/snapshot/` | GET | Yes | Cached dashboard payload used by Maps View |

---

## Maps View (`/maps_view/`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/dashboard/` | GET | Yes | Primary HTML dashboard |
| `/metrics/` | GET | Yes | Metrics overview page |
| `/api/hosts-status/` | GET | Yes | JSON feed consumed by the dashboard |
| `ws/dashboard/status/` | WS | Yes | Channels WebSocket endpoint for live updates |

---

## Setup App (`/setup_app/`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/dashboard/` | GET | Staff | Runtime configuration overview |
| `/first_time/` | GET/POST | Staff | First-time setup wizard |
| `/config/` | GET/POST | Staff | Edit runtime credentials |
| `/docs/` | GET | Staff | Documentation index |
| `/docs/<path>/` | GET | Staff | Render a specific documentation page |

---

## Archived / Removed Endpoints

- `routes_builder/*` — **Removed**; replace with `/api/v1/inventory/routes/tasks/*` endpoints above.
- `zabbix_api/*` — **Removed**; inventory and monitoring APIs now cover previous functionality.

Legacy documentation is retained under `doc/archive/` for historical reference but should not be used for active integrations.

---

## Related Documentation

- `doc/architecture/MODULES.md` — Application responsibilities and status.
- `doc/architecture/DATA_FLOW.md` — Data flow diagrams and integration points.
- `doc/releases/BREAKING_CHANGES_v2.0.0.md` — Migration guide for the v2.0.0 consolidation.
- `doc/operations/DEPLOYMENT.md` — Deployment checklist and operational considerations.

**MapsProveFiber** — API reference maintained by the Engineering team.
