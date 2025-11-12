# Observability Guide - MapsProveFiber

**Version**: v2.0.0  
**Last Updated**: 2025-11-10  
**Target Audience**: DevOps, SRE, Developers

---

## 📖 Overview

MapsProveFiber provides comprehensive observability through health checks, Prometheus metrics, structured logging, and distributed tracing. This guide covers monitoring setup, metrics collection, and operational dashboards.

---

## 🩺 Health Check Endpoints

### Available Endpoints

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `/healthz` | Overall health status | General monitoring |
| `/ready` | Readiness probe | Kubernetes readiness |
| `/live` | Liveness probe | Kubernetes liveness |
| `/celery/status` | Celery worker status | Task queue monitoring |

### `/healthz` - Overall Health

Comprehensive health check covering all system components.

**Request:**
```powershell
Invoke-WebRequest http://localhost:8000/healthz
```

**Response (Healthy):**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-10T10:30:00Z",
  "version": "2.0.0",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "storage": "ok",
    "celery": "ok"
  }
}
```

**Response (Unhealthy):**
```json
{
  "status": "unhealthy",
  "timestamp": "2025-11-10T10:30:00Z",
  "checks": {
    "database": "error: connection refused",
    "cache": "degraded",
    "storage": "ok"
  }
}
```

### `/ready` - Readiness Probe

Indicates if the application is ready to accept traffic.

**Request:**
```powershell
curl http://localhost:8000/ready
```

**Response:**
- `200 OK`: Ready to serve traffic
- `503 Service Unavailable`: Not ready (database unavailable, migrations pending)

### `/live` - Liveness Probe

Indicates if the application process is alive.

**Request:**
```powershell
curl http://localhost:8000/live
```

**Response:**
- `200 OK`: Process is alive
- `5xx`: Process is deadlocked or crashed

### `/celery/status` - Celery Worker Status

Reports Celery worker health and queue status.

**Request:**
```powershell
curl http://localhost:8000/celery/status
```

**Response:**
```json
{
  "workers": 2,
  "active_tasks": 5,
  "queued_tasks": 12,
  "status": "healthy"
}
```

---

## 📊 Prometheus Metrics

### Metrics Endpoint

**URL**: `/metrics/` or `/metrics/metrics`  
**Format**: Prometheus exposition format

**Request:**
```powershell
Invoke-WebRequest http://localhost:8000/metrics/metrics
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
# Current static asset version
mapsprovefiber_static_asset_version_info{version="20251110_103000"} 1
```

#### Celery Task Metrics
```prometheus
# Task execution count
celery_task_total{task="refresh_dashboard_cache_task",state="SUCCESS"} 123
celery_task_total{task="refresh_dashboard_cache_task",state="FAILURE"} 2

# Task duration
celery_task_duration_seconds{task="refresh_dashboard_cache_task",quantile="0.95"} 2.5
```

#### Zabbix Integration Metrics
```prometheus
# API call metrics
zabbix_api_calls_total{method="host.get",status="success"} 456
zabbix_api_calls_total{method="host.get",status="failure"} 3

# Circuit breaker state
zabbix_circuit_breaker_state{state="closed"} 1
zabbix_circuit_breaker_state{state="open"} 0

# Cache performance
zabbix_cache_hits_total 890
zabbix_cache_misses_total 110
```

---

## 📝 Structured Logging

### Log Files

```
backend/logs/
├── application.log       # General application logs
├── django.log           # Django framework logs
├── celery.log           # Celery worker logs
└── access.log           # HTTP access logs
```

### Log Format

```json
{
  "timestamp": "2025-11-10T10:30:00.123Z",
  "level": "INFO",
  "logger": "inventory.services",
  "message": "Site created successfully",
  "context": {
    "site_id": 123,
    "user_id": 45,
    "request_id": "abc-123-def"
  }
}
```

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

```powershell
# Tail application logs
tail -f backend/logs/application.log

# View Django logs
tail -f backend/logs/django.log

# Filter by level
grep ERROR backend/logs/application.log

# Docker logs
docker compose logs -f web
```

---

## 📈 Grafana Dashboards

### Setup Grafana

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards

volumes:
  prometheus_data:
  grafana_data:
```

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'mapsprovefiber'
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
# monitoring/alerts.yml
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
        expr: celery_workers_count == 0
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

Every request gets a unique ID for tracing:

```python
# middleware/request_id.py
import uuid

class RequestIDMiddleware:
    def __call__(self, request):
        request.request_id = str(uuid.uuid4())
        response = self.get_response(request)
        response['X-Request-ID'] = request.request_id
        return response
```

### Usage in Logs

```python
logger.info(
    "Database query executed",
    extra={"request_id": request.request_id, "duration_ms": 45}
)
```

### Query Logs by Request ID

```powershell
grep "request_id=abc-123-def" backend/logs/application.log
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
- [Deployment Guide](../operations/DEPLOYMENT.md)
- [Troubleshooting Guide](../operations/TROUBLESHOOTING.md)

---

**Last Updated**: 2025-11-10  
**Maintainers**: SRE Team, DevOps
