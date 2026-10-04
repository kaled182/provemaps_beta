# Observability Guide - MapsProveFiber

**Versão do produto**: ver [VERSION](../../VERSION)  
**Last Updated**: 2026-10-04  
**Target Audience**: DevOps, SRE, Developers

---

## 📖 Overview

MapsProveFiber provides comprehensive observability through health checks, Prometheus metrics, structured logging, and distributed tracing. This guide covers monitoring setup, metrics collection, and operational dashboards.

---

## 🩺 Health Check Endpoints

### Available Endpoints

> Examples use port 8000 (`make run`). The Docker dev stack (`docker/docker-compose.yml`) publishes the web service on port **8100**.

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `/healthz` | Overall health status | General monitoring |
| `/ready` | Readiness probe | Kubernetes readiness |
| `/live` | Liveness probe | Kubernetes liveness |
| `/celery/status` | Celery worker status | Task queue monitoring |

### `/healthz` - Overall Health

Comprehensive health check covering all system components.

**Request:**
```bash
curl http://localhost:8000/healthz
```

**Response (Healthy):**
```json
{
  "status": "ok",
  "timestamp": 1762770600.0,
  "settings": "settings.dev",
  "version": "dev",
  "django": "5.2.7",
  "python": "3.12.x",
  "checks": {
    "db": {"ok": true},
    "cache": {"ok": true, "backend": "RedisCache", "ignored": false},
    "storage": {"ok": true}
  },
  "latency_ms": 12.3,
  "strict_mode": true,
  "ignore_cache": false
}
```

`version` comes from the `APP_VERSION` environment variable (default `dev`); the product version lives in the [VERSION](../../VERSION) file.

**Response (Unhealthy):**
HTTP `503` with `"status": "degraded"` and the failing check marked `"ok": false`:
```json
{
  "status": "degraded",
  "checks": {
    "db": {"ok": false, "error": "connection refused"},
    "cache": {"ok": true},
    "storage": {"ok": true}
  }
}
```

### `/ready` - Readiness Probe

Indicates if the application is ready to accept traffic.

**Request:**
```bash
curl http://localhost:8000/ready
```

**Response:**
- `200 OK`: Ready to serve traffic
- `503 Service Unavailable`: Not ready (database unavailable, migrations pending)

### `/live` - Liveness Probe

Indicates if the application process is alive.

**Request:**
```bash
curl http://localhost:8000/live
```

**Response:**
- `200 OK`: Process is alive
- `5xx`: Process is deadlocked or crashed

### `/celery/status` - Celery Worker Status

Reports Celery worker health and queue status.

**Request:**
```bash
curl http://localhost:8000/celery/status
```

**Response** (`200` when `status` is `ok`, `503` when `degraded`):
```json
{
  "timestamp": 1762770600.0,
  "latency_ms": 85.2,
  "status": "ok",
  "worker": {
    "available": true,
    "error": null,
    "stats": {}
  }
}
```

---

## 📊 Prometheus Metrics

### Metrics Endpoint

**URL**: `/metrics/` or `/metrics/metrics`  
**Format**: Prometheus exposition format

**Request:**
```bash
curl http://localhost:8000/metrics/metrics
```

### Standard Django Metrics

Provided by `django-prometheus`:

```prometheus
# HTTP Requests
django_http_requests_total_by_method_total{method="GET"} 1234
django_http_requests_total_by_view_total{view="dashboard"} 567
django_http_responses_total_by_status_total{status="200"} 890

# Response Times
django_http_requests_latency_seconds_by_view{view="dashboard",quantile="0.5"} 0.05
django_http_requests_latency_seconds_by_view{view="dashboard",quantile="0.95"} 0.15

# Database
django_db_query_duration_seconds_count 5678
django_db_connections_count{alias="default"} 5

# Cache
django_cache_get_total{backend="redis"} 1234
django_cache_hits_total{backend="redis"} 1100
django_cache_misses_total{backend="redis"} 134
```

### Custom Application Metrics

#### Static Asset Version
```prometheus
# Current static asset version (Info metric, `core/metrics_static_version.py`)
static_asset_version_info{version="20251110_103000"} 1
```

#### Celery Metrics
```prometheus
# Worker status (`core/metrics_celery.py`, updated by /celery/status)
celery_worker_available 1
celery_worker_count 2
celery_active_tasks 5

# Queue depth and task duration (`core/metrics_custom.py`)
celery_queue_depth{queue="default"} 12
celery_task_duration_seconds_bucket{task_name="refresh_dashboard_cache_task",status="success",le="2.5"} 120
```

#### Zabbix Integration Metrics
```prometheus
# Gateway/client metrics (`integrations/zabbix/client.py`)
zabbix_requests_total{...}
zabbix_request_duration_seconds_bucket{...}
zabbix_circuit_breaker_state{...}
zabbix_retry_attempts_total{...}

# Higher-level call metrics (`core/metrics_custom.py`)
integrations_zabbix_calls_total{endpoint="host.get",status="success",error_type=""} 456
integrations_zabbix_latency_seconds_bucket{...}
```

Inventory API metrics (`inventory_api_requests_total`, `inventory_api_duration_seconds`, `inventory_cache_operations_total`, ...) are defined in `backend/inventory/metrics.py`. Label sets above are indicative; check the metric definitions in code for the authoritative names and labels.

---

## 📝 Structured Logging

### Log Destinations

By default logs go to the console (stdout), which Docker collects (`docker compose -f docker/docker-compose.yml logs -f web`). An optional rotating file handler is available in non-debug settings:

```env
ENABLE_FILE_LOGGING=true
LOG_FILE=/var/log/django/app.log   # default
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
```

### Log Format

`LOG_FORMAT` selects `verbose` (default) or `simple`; `LOG_LEVEL` sets the level. The request ID (see below) is added to the structlog context when structlog is available.

### Log Levels

```python
# Python code
import logging
logger = logging.getLogger(__name__)

logger.debug("Detailed information for debugging")
logger.info("General informational messages")
logger.warning("Warning messages for attention")
logger.error("Error messages for failures")
logger.critical("Critical system failures")
```

### Viewing Logs

```bash
# Docker logs (dev stack)
docker compose -f docker/docker-compose.yml logs -f web
docker compose -f docker/docker-compose.yml logs -f celery

# Filter by level
docker compose -f docker/docker-compose.yml logs web | grep ERROR

# If ENABLE_FILE_LOGGING=true
tail -f /var/log/django/app.log
```

---

## 📈 Grafana Dashboards

### Setup Grafana

Prometheus and Grafana are services of the dev stack (`docker/docker-compose.yml`): Prometheus on http://localhost:9090, Grafana on http://localhost:3002 (credentials set in the compose file). In production they belong to the `monitoring` / `full` profiles of `docker/docker-compose.prod.yml` (see [`DEPLOY.md`](../../DEPLOY.md)).

```bash
docker compose -f docker/docker-compose.yml up -d prometheus grafana
```

Provisioned configuration lives in `docker/prometheus/` (config + `alerts/`) and `docker/grafana/` (datasources + dashboards); details in `docker/prometheus/README.md`.

### Prometheus Configuration

```yaml
# docker/prometheus/prometheus.yml (excerpt)
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'django'
    static_configs:
      - targets: ['web:8000']
    metrics_path: '/metrics/metrics'
```

### Pre-built Dashboards

1. **Application Overview**
   - Request rate, latency, error rate
   - Database connections
   - Cache hit rate

2. **Celery Monitoring**
   - Active workers
   - Task queue length
   - Task success/failure rate

3. **Zabbix Integration**
   - API call rate
   - Circuit breaker status
   - Cache performance

4. **Infrastructure**
   - CPU, memory, disk usage
   - Network I/O
   - Container health

---

## 🚨 Alerting

### Alert Rules

```yaml
# docker/prometheus/alerts/<name>.yml (example; the repo ships radius_search.yml)
groups:
  - name: application_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(django_http_responses_total_by_status_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
      
      - alert: DatabaseConnectionsHigh
        expr: django_db_connections_count > 50
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool near capacity"
      
      - alert: CeleryWorkerDown
        expr: celery_worker_available == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "No Celery workers available"
```

### Alert Channels

Configure in Grafana or Prometheus Alertmanager:
- Email notifications
- Slack webhooks
- PagerDuty integration
- Microsoft Teams
- Custom webhooks

---

## 🔍 Distributed Tracing

### Request ID Tracking

Every request gets a unique ID for tracing, added by `core.middleware.request_id.RequestIDMiddleware` (it honours an incoming `X-Request-ID` header, stores it in `request.META['HTTP_X_REQUEST_ID']`, binds it to the structlog context and returns it in the `X-Request-ID` response header).

### Usage in Logs

```python
logger.info(
    "Database query executed",
    extra={"request_id": request.request_id, "duration_ms": 45}
)
```

### Query Logs by Request ID

```bash
docker compose -f docker/docker-compose.yml logs web | grep "abc-123-def"
```

---

## ⚡ Performance Monitoring

### Slow Query Logging

```python
# settings/base.py
LOGGING = {
    'handlers': {
        'slow_queries': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'logs/slow_queries.log',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['slow_queries'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Log queries taking >500ms
LOGGING['loggers']['django.db.backends']['level'] = 'WARNING'
```

### Application Performance Monitoring (APM)

For production, consider:
- **New Relic**: Full-stack monitoring
- **Datadog**: Infrastructure + APM
- **Elastic APM**: Open-source alternative
- **Sentry**: Error tracking

---

## 📊 Key Metrics to Monitor

### Application Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Request latency (p95) | < 200ms | > 500ms |
| Error rate | < 1% | > 5% |
| Throughput | - | Drop >20% |
| Cache hit rate | > 80% | < 50% |

### Infrastructure Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| CPU usage | < 70% | > 85% |
| Memory usage | < 80% | > 90% |
| Disk usage | < 75% | > 85% |
| Database connections | < 50 | > 90 |

### Business Metrics

| Metric | Description |
|--------|-------------|
| Active devices | Number of monitored devices |
| Dashboard views | Daily dashboard access count |
| Routes created | Daily fiber route creations |
| API calls | API usage statistics |

---

## 🛠️ Operational Runbooks

### High Error Rate

1. Check `/healthz` endpoint
2. Review recent logs for errors
3. Check database connectivity
4. Verify external integrations (Zabbix)
5. Roll back if recent deployment

### High Latency

1. Check database query performance
2. Review cache hit rate
3. Check external API latency (Zabbix)
4. Scale workers if queue is backed up
5. Optimize slow queries

### Memory Leak

1. Monitor memory usage over time
2. Check for orphaned connections
3. Review Celery task memory usage
4. Restart workers periodically
5. Profile application with memory profiler

---

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Django Prometheus](https://github.com/korfuri/django-prometheus)
- [Deployment Guide](../../DEPLOY.md)
- [Monitoring Guide](../operations/MONITORING.md)
- [Troubleshooting notes](../troubleshooting/)

---

**Last Updated**: 2026-10-04  
**Maintainers**: SRE Team, DevOps
