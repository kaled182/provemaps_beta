# API Documentation - MapsProveFiber

This document describes every REST endpoint exposed by MapsProveFiber, including integration with Zabbix, the local inventory, fiber routes, Celery jobs, and health probes. The material is organized by module to emphasize clarity, security, and quick diagnostics.

---

## Module overview

| Module | Path | Primary responsibility |
|--------|------|------------------------|
| **Zabbix API** | `zabbix_api/` | Zabbix integration, diagnostics, and inventory sync |
| **Routes Builder** | `routes_builder/` | Celery tasks that calculate and cache routes |
| **Setup App** | `setup_app/` | `.env` management and runtime settings |
| **Core** | `core/` | Django configuration, Celery wiring, URLs, and health checks |

---

## Access and security

- Every endpoint requires a logged-in Django user.
- Administrative endpoints require a staff user.
- Diagnostic routes are guarded by the `ENABLE_DIAGNOSTIC_ENDPOINTS` flag:
  ```bash
  ENABLE_DIAGNOSTIC_ENDPOINTS=true
  ```
  When the flag is `false`, the routes respond with **HTTP 403** without executing external actions.

---

## Base URLs

- Public endpoints: `http://localhost:8000/`
- Zabbix integration: `http://localhost:8000/zabbix_api/`

> Replace `localhost` with the production domain in deployed environments.

---

## Health and status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz/` | GET | Full system health check (database, cache, storage, runtime) |
| `/ready/` | GET | Readiness probe - reports when the app can receive traffic |
| `/live/` | GET | Liveness probe - verifies that the process is alive |

Example response:
```json
{
  "status": "ok",
  "timestamp": 1731109200.123,
  "checks": {
    "db": {"ok": true, "type": "mysql"},
    "cache": {"ok": true, "backend": "RedisCache"},
    "storage": {"ok": true, "free_gb": 42.3}
  },
  "latency_ms": 23.6
}
```

---

## Zabbix API

Endpoints are grouped by category. Default prefix: `/zabbix_api/`

### Status and monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status/` | GET | Overall health of the Zabbix environment |
| `/monitoring/overview/` | GET | Summary view of hosts and active issues |
| `/monitoring/performance/` | GET | Aggregated metrics (CPU, memory, disk) |
| `/monitoring/availability/` | GET | Uptime percentages |
| `/monitoring/latest_all/` | GET | Latest values for all tracked hosts |

---

### Hosts and items

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hosts/` | GET | List hosts with basic metadata |
| `/hosts/{id}/` | GET | Detailed information for a host |
| `/hosts/{id}/items/` | GET | Items grouped by category |
| `/hosts/{id}/triggers/` | GET | Triggers grouped by severity |
| `/hosts/{id}/graphs/` | GET | Available graphs |
| `/hosts/{id}/latest/` | GET | Latest metrics for the host |
| `/hosts/{id}/performance/` | GET | CPU, memory, and disk performance |
| `/items/{hostid}/{itemid}/history/` | GET | 24 hour history for the item |

---

### Problems and events

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/problems/` | GET | Active problems |
| `/problems/summary/` | GET | Breakdown by severity |
| `/problems/by-severity/` | GET | Count by severity level |
| `/problems/critical/` | GET | Critical incidents only |
| `/events/` | GET | Recent events |
| `/events/recent/` | GET | Condensed chronological feed |
| `/events/summary/` | GET | Distribution by status and severity |

---

### Network and inventory

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hosts/network-info/` | GET | Interfaces and IP addresses for all hosts |
| `/hosts/{id}/network-info/` | GET | Interfaces for a specific host |
| `/api/add-device-from-zabbix/` | POST | Creates a local device based on Zabbix data |
| `/api/bulk-create-inventory/` | POST | Bulk device creation |
| `/api/device-ports/{device_id}/` | GET | Ports for a device |
| `/api/port-traffic-history/{port_id}/` | GET | Traffic history for the port |
| `/api/import-fiber-kml/` | POST | Imports fiber topology from a KML file |
| `/api/fiber/live-status/{cable_id}/` | GET | Current status for the cable |
| `/api/fiber/value-mapping-status/{cable_id}/` | GET | Status value mapping |

---

### Diagnostic tools

> Available only when `ENABLE_DIAGNOSTIC_ENDPOINTS=true` and the user has the staff flag.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/test/ping/` | GET | Remote ping test |
| `/api/test/telnet/` | GET | Port check via Telnet |
| `/api/test/ping_telnet/` | GET | Combined ping and Telnet checks |
| `/api/test/cable-up/{id}/` | POST | Marks a cable as active |
| `/api/test/cable-down/{id}/` | POST | Marks a cable as inactive |

---

### Lookup endpoints

Used by autocomplete widgets and interactive UI components.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/lookup/hosts/` | GET | Lightweight host search |
| `/lookup/hosts/{id}/interfaces/` | GET | Interfaces for a host |
| `/lookup/interfaces/{id}/details/` | GET | Interface details |

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
