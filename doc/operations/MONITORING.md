# Monitoring Guide - MapsProveFiber

**Version**: v2.0.0  
**Last Updated**: 2025-11-10  
**Target Audience**: DevOps, SRE

---

## 📖 Overview

Comprehensive monitoring setup for MapsProveFiber, including Prometheus metrics, Celery monitoring, Redis high availability, and alerting strategies.

---

## 📊 Prometheus Metrics

### Endpoint

**URL**: `/metrics/metrics`  
**Format**: Prometheus exposition format  
**Update Frequency**: Real-time

### Custom Metrics

#### Static Asset Version
```prometheus
# Tracks deployed version and git commit
static_asset_version_info{version="20251110_103000",git_sha="abc123",timestamp="20251110103000"} 1
```

#### Celery Metrics
```prometheus
# Worker availability
celery_worker_available 1

# Status check latency
celery_status_latency_ms 45

# Worker and task counts
celery_worker_count 2
celery_active_tasks 5
celery_scheduled_tasks 12
celery_reserved_tasks 3
```

#### Zabbix Integration Metrics
```prometheus
# API calls
zabbix_api_calls_total{method="host.get",status="success"} 456

# Circuit breaker
zabbix_circuit_breaker_state{method="host.get"} 0

# Retry attempts
zabbix_retry_attempts_total{method="host.get"} 3
```

---

## 🔄 Celery Monitoring

### Status Endpoint

**URL**: `/celery/status`  
**Auth**: Staff required  
**Cache**: 5 seconds

**Response:**
```json
{
  "workers": 2,
  "active_tasks": 5,
  "scheduled_tasks": 12,
  "reserved_tasks": 3,
  "available": true,
  "latency_ms": 45
}
```

### Configuration

```env
# .env
CELERY_STATUS_TIMEOUT=6          # Status call timeout (seconds)
CELERY_PING_TIMEOUT=2            # Ping timeout (seconds)
CELERY_METRICS_ENABLED=true      # Enable Prometheus metrics
CELERY_METRICS_UPDATE_INTERVAL=30 # Update interval (seconds)
```

### Monitoring Script

**PowerShell:**
```powershell
# scripts/check_celery.ps1
$response = Invoke-WebRequest -Uri "http://localhost:8000/celery/status"
if ($response.StatusCode -eq 200) {
    $data = $response.Content | ConvertFrom-Json
    if ($data.available) {
        Write-Host "Celery OK: $($data.workers) workers, $($data.active_tasks) active tasks"
        exit 0
    }
}
Write-Host "Celery FAIL"
exit 1
```

**Bash:**
```bash
# scripts/check_celery.sh
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/celery/status)
if [ "$response" = "200" ]; then
    echo "Celery OK"
    exit 0
else
    echo "Celery FAIL"
    exit 1
fi
```

---

## 🚨 Alert Rules

### Celery Alerts

```yaml
# prometheus/alerts/celery.yml
groups:
  - name: celery_alerts
    rules:
      - alert: CeleryWorkerDown
        expr: celery_worker_available == 0
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "Celery workers unavailable"
      
      - alert: CeleryHighLatency
        expr: celery_status_latency_ms > 5000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High Celery status latency"
      
      - alert: CeleryNoWorkersActive
        expr: celery_worker_count == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "No active Celery workers"
      
      - alert: CeleryHighActiveTasks
        expr: celery_active_tasks > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High number of active tasks"
      
      - alert: CeleryScheduledTasksGrowing
        expr: increase(celery_scheduled_tasks[5m]) > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Scheduled tasks growing rapidly"
```

### Zabbix Integration Alerts

```yaml
# prometheus/alerts/zabbix.yml
groups:
  - name: zabbix_alerts
    rules:
      - alert: ZabbixCircuitBreakerOpen
        expr: zabbix_circuit_breaker_state > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Zabbix circuit breaker opened"
      
      - alert: ZabbixRetryBurst
        expr: increase(zabbix_retry_attempts_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Excessive retry attempts"
      
      - alert: ZabbixHighErrorRate
        expr: rate(zabbix_api_calls_total{status="failure"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High Zabbix API error rate"
```

---

## 🔴 Redis High Availability

### Production Architecture

**Option A: Managed Redis (Recommended)**
- AWS ElastiCache
- Google Cloud Memorystore
- Azure Cache for Redis

**Option B: Redis Sentinel**

```yaml
# docker-compose.prod.yml
services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
  
  redis-replica-1:
    image: redis:7-alpine
    command: redis-server --slaveof redis-master 6379 --requirepass ${REDIS_PASSWORD}
  
  redis-replica-2:
    image: redis:7-alpine
    command: redis-server --slaveof redis-master 6379 --requirepass ${REDIS_PASSWORD}
  
  sentinel-1:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
  
  sentinel-2:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
  
  sentinel-3:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
```

**Configuration:**
```env
REDIS_USE_SENTINEL=true
REDIS_SENTINELS=sentinel-1:26379,sentinel-2:26379,sentinel-3:26379
REDIS_MASTER_NAME=mymaster
REDIS_PASSWORD=secure-password
```

### Graceful Degradation

MapsProveFiber continues operating without Redis:
- Cache misses → direct database queries
- Celery → local execution (synchronous)
- WebSocket → polling fallback

---

## 📈 Grafana Dashboard

### Import Dashboard

```json
{
  "dashboard": {
    "title": "MapsProveFiber Monitoring",
    "panels": [
      {
        "title": "Celery Workers",
        "targets": [
          {"expr": "celery_worker_count"}
        ]
      },
      {
        "title": "Active Tasks",
        "targets": [
          {"expr": "celery_active_tasks"}
        ]
      },
      {
        "title": "Zabbix API Calls",
        "targets": [
          {"expr": "rate(zabbix_api_calls_total[5m])"}
        ]
      }
    ]
  }
}
```

### Key Panels

1. **System Health**
   - Request rate
   - Error rate
   - Response time (p50, p95, p99)

2. **Celery Performance**
   - Worker count
   - Task queue length
   - Task duration

3. **Zabbix Integration**
   - API call rate
   - Error rate
   - Circuit breaker state

4. **Infrastructure**
   - CPU usage
   - Memory usage
   - Database connections

---

## 🔍 Troubleshooting

### Celery Workers Not Responding

**Symptoms:**
- `celery_worker_available == 0`
- `/celery/status` returns errors

**Resolution:**
```powershell
# Check worker status
docker compose ps celery

# View logs
docker compose logs celery --tail=100

# Restart workers
docker compose restart celery beat

# Verify Redis connection
docker compose logs redis
```

### High Task Latency

**Symptoms:**
- `celery_status_latency_ms > 5000`
- Slow task execution

**Resolution:**
```powershell
# Check resource usage
docker compose stats celery

# Increase concurrency
# In docker-compose.yml:
# command: celery -A core worker -l info -c 4

# Check for stuck tasks
docker compose exec web python manage.py shell
>>> from celery import current_app
>>> inspect = current_app.control.inspect()
>>> inspect.active()
```

### Circuit Breaker Open

**Symptoms:**
- `zabbix_circuit_breaker_state > 0`
- Zabbix integration failing

**Resolution:**
```powershell
# Check Zabbix connectivity
curl http://zabbix-server/api_jsonrpc.php

# View integration logs
docker compose logs web | grep -i zabbix

# Reset circuit breaker (automatic after timeout)
# Or restart service
docker compose restart web
```

---

## 📚 Additional Resources

- [Observability Guide](../guides/OBSERVABILITY.md)
- [Redis HA Configuration](REDIS_HA.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

---

**Last Updated**: 2025-11-10  
**Maintainers**: SRE Team
