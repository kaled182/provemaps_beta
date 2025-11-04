# Celery Status Endpoint

## Overview

The `/celery/status` endpoint reports the real-time state of Celery workers and queue statistics.

## Technical Summary

- **URL**: `/celery/status`
- **Method**: `GET`
- **Authentication**: Not required by default (can be added later)
- **View**: `core.views_health.celery_status`
- **Default timeout**: 3 seconds (configurable via `CELERY_STATUS_TIMEOUT`)

## Configuration

```text
# Optional timeout override in .env
CELERY_STATUS_TIMEOUT=5  # seconds
```

## Behaviour

The view triggers the Celery task `get_queue_stats` defined in `core/celery.py` and waits for a response. If no worker is available or the timeout expires the endpoint returns a `degraded` status with HTTP 503.

### Resilience Strategy (Fallback)

To reduce false negatives the endpoint performs two sequential checks:

1. Run `ping.delay()` with a short timeout (`CELERY_PING_TIMEOUT`, default 2 seconds). A `pong` response marks the worker as available.
2. Request detailed statistics via `get_queue_stats.delay()` using `CELERY_STATUS_TIMEOUT` (default 3 seconds, recommended 5 to 8 in production). If this step times out or fails the overall status becomes `degraded`, but `worker.available` remains `true`.

Benefits:
- Avoids reporting a full outage when only queue inspection is slow.
- Provides better signals for orchestrators: HTTP 503 still indicates degradation but distinguishes missing workers from slow metrics.

Environment variables (`.env` file):
```text
CELERY_STATUS_TIMEOUT=6      # statistics timeout
CELERY_PING_TIMEOUT=2        # lightweight ping timeout
```

Environment variables (PowerShell):
```powershell
$env:CELERY_STATUS_TIMEOUT = '6'      # statistics timeout
$env:CELERY_PING_TIMEOUT = '2'        # lightweight ping timeout
```

Example degraded response (ping succeeded but stats timed out):
```json
{
  "timestamp": 1730000000.123,
  "latency_ms": 3044.52,
  "status": "degraded",
  "worker": {
    "available": true,
    "error": "The operation timed out.",
    "stats": null
  }
}
```

Example healthy response:
```json
{
  "timestamp": 1730000101.456,
  "latency_ms": 4021.11,
  "status": "ok",
  "worker": {
    "available": true,
    "error": null,
    "stats": {
      "workers": ["celery@hostname"],
      "active_tasks": {"celery@hostname": []},
      "scheduled_tasks": {"celery@hostname": []},
      "reserved_tasks": {"celery@hostname": []},
      "timestamp": 1730000101.0
    }
  }
}
```

### Execution Flow

1. Client calls `/celery/status`.
2. View dispatches `get_queue_stats.delay()` (after a preceding ping check).
3. Await the configured timeout.
4. Return JSON with the status and statistics.

## Response Examples

### Scenario 1: Worker Available

**HTTP Status**: `200 OK`

```json
{
  "timestamp": 1730000000.123,
  "latency_ms": 45.67,
  "status": "ok",
  "worker": {
    "available": true,
    "error": null,
    "stats": {
      "workers": ["celery@hostname"],
      "active_tasks": {
        "celery@hostname": []
      },
      "scheduled_tasks": {
        "celery@hostname": []
      },
      "reserved_tasks": {
        "celery@hostname": []
      },
      "timestamp": 1730000000.0
    }
  }
}
```

### Scenario 2: Worker Unavailable

**HTTP Status**: `503 Service Unavailable`

```json
{
  "timestamp": 1730000000.123,
  "latency_ms": 3005.45,
  "status": "degraded",
  "worker": {
    "available": false,
    "error": "Timeout: task did not complete within 3.0 seconds",
    "stats": null
  }
}
```

### Scenario 3: Import Error

**HTTP Status**: `503 Service Unavailable`

```json
{
  "timestamp": 1730000000.123,
  "latency_ms": 1.23,
  "status": "degraded",
  "worker": {
    "available": false,
    "error": "ImportError: No module named 'celery'",
    "stats": null
  }
}
```

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | float | Unix timestamp of the response |
| `latency_ms` | float | Total response time in milliseconds |
| `status` | string | Either `"ok"` or `"degraded"` |
| `worker.available` | boolean | Worker responded within the timeout |
| `worker.error` | string or null | Error message when available |
| `worker.stats` | object or null | Detailed queue statistics |

### `worker.stats` Structure

When populated the payload contains:

- `workers`: list of active worker names
- `active_tasks`: tasks currently executing per worker
- `scheduled_tasks`: tasks scheduled for future execution
- `reserved_tasks`: tasks reserved but not yet started
- `timestamp`: inspection timestamp

## Monitoring Guidance

### Prometheus and Grafana

```yaml
# prometheus.yml
scrape_configs:
  - job_name: "celery-status"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["app:8000"]
```

#### Exported Metrics

Calling `/celery/status` updates the Prometheus gauges defined in `core/metrics_celery.py`. The gauges are exposed through the global `/metrics` endpoint provided by `django-prometheus`. Prefer scraping `/metrics` directly instead of `/celery/status`.

Control flag (`.env` file):

```text
CELERY_METRICS_ENABLED=true
```

Control flag (PowerShell):

```powershell
$env:CELERY_METRICS_ENABLED = 'true'  # set to false to skip gauge updates
```

Available gauges:

| Metric | Description |
|--------|-------------|
| `celery_worker_available` | 1 if the ping call succeeded, else 0 |
| `celery_status_latency_ms` | Latency of the last `/celery/status` request in ms |
| `celery_worker_count` | Number of workers responding to inspection |
| `celery_active_tasks` | Total active tasks across all workers |
| `celery_scheduled_tasks` | Total scheduled (ETA) tasks |
| `celery_reserved_tasks` | Total reserved tasks |

Sample `/metrics` excerpt:

```
celery_worker_available 1
celery_status_latency_ms 87.12
celery_worker_count 1
celery_active_tasks 0
celery_scheduled_tasks 0
celery_reserved_tasks 0
```

Recommended practices:
- Pair with a Grafana dashboard to visualise availability and latency.
- Alert when `celery_worker_available == 0` for three minutes or when `increase(celery_status_latency_ms[5m]) > 5000`.
- If traffic is high, rely on the periodic task to refresh metrics and keep `/celery/status` cached.

### Docker Health Check

```yaml
# docker-compose.yml
healthcheck:
  test: ["CMD-SHELL", "python -c \"import urllib.request; exit(0 if urllib.request.urlopen('http://localhost:8000/celery/status').getcode() == 200 else 1)\""]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Bash Monitoring Script

```bash
#!/bin/bash
# check_celery.sh

RESPONSE=$(curl -s -w "%{http_code}" http://localhost:8000/celery/status)
HTTP_CODE="${RESPONSE: -3}"
BODY="${RESPONSE:0:-3}"

if [ "$HTTP_CODE" -eq 200 ]; then
  echo "Celery OK"
  exit 0
else
  echo "Celery degraded: $BODY"
  exit 1
fi
```

### PowerShell Monitoring Script

```powershell
# check_celery.ps1
$Url = "http://localhost:8000/celery/status"
$Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 8
$Json = $Response.Content | ConvertFrom-Json
if ($Response.StatusCode -eq 200 -and $Json.status -eq 'ok') {
  Write-Host "Celery OK (latency=$($Json.latency_ms)ms workers=$($Json.worker.stats.workers.Count))"
  exit 0
} elseif ($Json.worker.available -eq $true) {
  Write-Host "Celery degraded (worker reachable, stats unavailable)"; exit 1
} else {
  Write-Host "Celery unavailable (no worker)"; exit 2
}
```

## Tests

Unit tests live in `tests/test_celery_status.py`.

```powershell
& D:/provemaps_beta/venv/Scripts/python.exe -m pytest tests/test_celery_status.py -v
& D:/provemaps_beta/venv/Scripts/python.exe -m pytest tests/test_celery_status.py --cov=core.views_health --cov-report=term
```

## Management Command

The `celery_health` management command provides manual checks:

```powershell
python manage.py celery_health
python manage.py celery_health --pretty
python manage.py celery_health --timeout 10
```

## Troubleshooting

### Always Returns 503

**Cause**: Workers are down or cannot connect to the broker.

**Resolution**:
```powershell
docker compose logs redis
docker compose logs celery
docker compose exec celery celery -A core.celery_app inspect ping
```

### Timeout Too Aggressive

**Cause**: Workers are slow or under heavy load.

**Resolution**:
```powershell
$env:CELERY_STATUS_TIMEOUT = '10'
docker compose restart web
```

### ImportError In Production

**Cause**: Missing dependencies inside the container.

**Resolution**:
```powershell
docker compose build --no-cache web celery beat
docker compose up -d
```

## Security Considerations

The endpoint is unauthenticated by default. In production environments consider:

1. Adding authentication:
```python
from django.contrib.auth.decorators import login_required

@login_required
def celery_status(request: HttpRequest):
    ...
```

2. Adding caching or throttling:
```python
from django.views.decorators.cache import cache_page

@cache_page(10)  # cache for 10 seconds
def celery_status(request: HttpRequest):
    ...
```

3. Restricting access by IP at the proxy or middleware level.

## Relationship To Other Health Checks

- `/healthz` reports database, cache, and storage health.
- `/ready` verifies readiness (database connectivity).
- `/live` reports process liveness.
- `/celery/status` focuses on Celery worker availability.

## Changelog

### 26 Oct 2025
- Initial endpoint implementation
- Added unit tests
- Published documentation
- Integrated Prometheus metrics via `update_metrics`
- Added a five second cache layer to reduce latency
- Introduced the `update_celery_metrics_task` periodic beat task
- Published alert guidance in `PROMETHEUS_ALERTS.md`

---

**Author**: Automated development system  
**Last updated**: 26 October 2025
