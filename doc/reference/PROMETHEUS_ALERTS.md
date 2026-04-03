# Prometheus Alerts For Celery

This reference contains example alert rules (Prometheus Alertmanager) and PromQL queries that use the metrics exposed by `/celery/status`.

## Available Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `celery_worker_available` | Gauge | 1 when the worker replied to the ping, otherwise 0 |
| `celery_status_latency_ms` | Gauge | Latency of the last status check (ms) |
| `celery_worker_count` | Gauge | Number of active workers |
| `celery_active_tasks` | Gauge | Total tasks currently processing |
| `celery_scheduled_tasks` | Gauge | Total tasks scheduled with ETA |
| `celery_reserved_tasks` | Gauge | Total reserved tasks |

## Recommended Alert Rules

### Zabbix Client: Circuit Breaker Open

```yaml
      - alert: ZabbixCircuitBreakerOpen
        expr: zabbix_circuit_breaker_state > 0
        for: 1m
        labels:
          severity: critical
          component: zabbix
        annotations:
          summary: "Zabbix circuit breaker opened"
          description: "Circuit breaker remains open for more than 60 seconds on method {{ $labels.method }}."
```

### Zabbix Client: Retry Burst

```yaml
      - alert: ZabbixRetryBurst
        expr: increase(zabbix_retry_attempts_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
          component: zabbix
        annotations:
          summary: "Excessive retry attempts in the Zabbix client"
          description: "More than 10 retry attempts in 5 minutes. Check backend availability."
```

### 1. Worker Unavailable

Triggers when no worker replies for longer than three minutes.

```yaml
# prometheus/alerts/celery.yml
groups:
  - name: celery_alerts
    interval: 30s
    rules:
      - alert: CeleryWorkerDown
        expr: celery_worker_available == 0
        for: 3m
        labels:
          severity: critical
          component: celery
        annotations:
          summary: "Celery workers unavailable"
          description: "No Celery worker acknowledged the ping during the last 3 minutes. Check logs and container status."
```

Recommended response:
- Inspect logs: `docker compose logs celery --tail=100`
- Restart workers: `docker compose restart celery beat`
- Verify Redis connectivity: `docker compose logs redis`

---

### 2. Elevated Latency

Fires when the status call exceeds five seconds for an extended period.

```yaml
      - alert: CeleryHighLatency
        expr: celery_status_latency_ms > 5000
        for: 5m
        labels:
          severity: warning
          component: celery
        annotations:
          summary: "High Celery status latency"
          description: "Status latency has been above 5 seconds for more than 5 minutes. Broker overload or slow workers suspected."
```

Recommended response:
- Check CPU and memory usage: `docker stats celery`
- Review backlog via `/celery/status` and `active_tasks`
- Consider increasing concurrency (`-c` flag in `docker-compose.yml`)

---

### 3. No Active Workers

Triggers when the worker count drops to zero.

```yaml
      - alert: CeleryNoWorkersActive
        expr: celery_worker_count == 0
        for: 2m
        labels:
          severity: critical
          component: celery
        annotations:
          summary: "No Celery workers active"
          description: "Celery worker count is zero. Asynchronous tasks will not execute."
```

Recommended response:
- Confirm containers: `docker compose ps`
- Restart services: `docker compose up -d celery beat`
- Review startup errors: `docker compose logs celery`

---

### 4. Active Task Accumulation

Signals a possible bottleneck when many tasks run concurrently for long periods.

```yaml
      - alert: CeleryHighActiveTasks
        expr: celery_active_tasks > 50
        for: 10m
        labels:
          severity: warning
          component: celery
        annotations:
          summary: "High number of active Celery tasks"
          description: "{{ $value }} tasks have been active for more than 10 minutes. Investigate slow or blocked jobs."
```

Recommended response:
- Inspect `/celery/status` for slow tasks
- Search logs for errors: `docker compose logs celery | Select-String "ERROR"`
- Adjust task time limits (`CELERY_TASK_TIME_LIMIT`)

---

### 5. Scheduled Task Backlog

Highlights growth in the scheduled queue that might indicate insufficient capacity.

```yaml
      - alert: CeleryScheduledTasksGrowing
        expr: rate(celery_scheduled_tasks[5m]) > 5
        for: 5m
        labels:
          severity: warning
          component: celery
        annotations:
          summary: "Scheduled task backlog increasing"
          description: "Scheduled tasks are increasing at {{ $value }} per minute. Workers might be overloaded."
```

Recommended response:
- Scale workers horizontally: `docker compose up -d --scale celery=3`
- Review task arrival rate
- Tweak `CELERY_WORKER_PREFETCH_MULTIPLIER`

---

## Useful PromQL Queries

### Availability Rate (Last 24h)

```promql
avg_over_time(celery_worker_available[24h]) * 100
```

### Average Latency (Last Hour)

```promql
avg_over_time(celery_status_latency_ms[1h])
```

### Active Task Peak (Last 6h)

```promql
max_over_time(celery_active_tasks[6h])
```

### Reserved Task Growth Rate

```promql
rate(celery_reserved_tasks[5m])
```

### Worker Count Over Time

```promql
celery_worker_count
```

---

## Grafana Dashboards

### Basic Monitoring Panel

```json
{
  "dashboard": {
    "title": "Celery Monitoring",
    "panels": [
      {
        "title": "Worker Availability",
        "targets": [{"expr": "celery_worker_available"}],
        "type": "stat"
      },
      {
        "title": "Active Tasks",
        "targets": [{"expr": "celery_active_tasks"}],
        "type": "graph"
      },
      {
        "title": "Latency (ms)",
        "targets": [{"expr": "celery_status_latency_ms"}],
        "type": "graph"
      },
      {
        "title": "Worker Count",
        "targets": [{"expr": "celery_worker_count"}],
        "type": "stat"
      }
    ]
  }
}
```

### Quick Import Steps

1. Grafana -> Dashboards -> Import.
2. Paste the JSON above or create the panels manually.
3. Select the Prometheus datasource.
4. Adjust time ranges as needed.

---

### Zabbix Resilient Client Panel

Dashboard JSON lives at `doc/reference/grafana/zabbix_resilient_client_dashboard.json`.

Featured panels:
- p95 latency (`histogram_quantile(0.95, sum(rate(zabbix_request_duration_seconds_bucket[5m])) by (le, method))`)
- Request volume (`sum(rate(zabbix_requests_total[5m])) by (method, status)`)
- Current circuit breaker state (`zabbix_circuit_breaker_state`)
- Recent retries (`increase(zabbix_retry_attempts_total[5m])`)
- Requests within the last minute (`sum(increase(zabbix_api_calls_total[1m]))`)

Import the JSON to enable the Stage 3 dashboard.

---

## Alertmanager Configuration

### Alert Routing

```yaml
# alertmanager.yml
route:
  group_by: ['component']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'celery-team'
  routes:
    - match:
        severity: critical
        component: celery
      receiver: 'celery-oncall'
      continue: true

receivers:
  - name: 'celery-team'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK'
        channel: '#celery-alerts'
        title: 'Celery Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'celery-oncall'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

---

## CI/CD Integration

### Pre-Deploy Validation

Check whether metrics are present before deployment:

```powershell
# scripts/validate_metrics.ps1

$MetricsUrl = "http://localhost:8000/metrics"
$RequiredMetrics = @(
  "celery_worker_available",
  "celery_status_latency_ms",
  "celery_worker_count"
)

$metricsContent = (Invoke-WebRequest -Uri $MetricsUrl -UseBasicParsing).Content

foreach ($metric in $RequiredMetrics) {
  if (-not $metricsContent.Contains($metric)) {
    Write-Host "Metric missing: $metric" -ForegroundColor Red
    exit 1
  }
}

Write-Host "All Celery metrics detected" -ForegroundColor Green
```

### Kubernetes Health Checks

```yaml
# k8s/deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mapsprovefiber
spec:
  template:
    spec:
      containers:
      - name: web
        livenessProbe:
          httpGet:
            path: /live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /celery/status
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
```

---

## Troubleshooting

### Metrics Not Updating

**Symptom:** Values look stale or missing.

**Checks:**
```powershell
docker compose exec celery celery -A core inspect scheduled
docker compose logs beat --tail=50 | Select-String "update_celery_metrics_task"
```

**Resolution:**
```powershell
docker compose restart beat
docker compose exec web python -c "import os; print(os.getenv('CELERY_METRICS_ENABLED', 'true'))"
```

---

### Frequent False Positives

**Symptom:** Alerts fire often without real incidents.

**Adjustments:**
- Increase the `for` duration (for example from 3m to 5m).
- Raise thresholds (for example, latency from 5s to 8s).
- Review endpoint timeouts (`CELERY_STATUS_TIMEOUT`).

---

## Best Practices

1. **Separate environments**: apply Prometheus labels such as `environment=prod` vs `environment=staging`.
2. **Retention planning**: keep at least 30 days of metrics to analyse trends and regressions.
3. **Aggregation**: rely on functions such as `sum()`, `avg()`, and `max()` when querying multiple workers.
4. **Runbooks**: document response steps for each alert so on-call engineers can react quickly.
5. **Testing**: simulate failures (for example stopping workers) to validate alert rules before production rollout.

---

## References

- [Prometheus Alerting](https://prometheus.io/./alerting/latest/overview/)
- [Alert Manager Configuration](https://prometheus.io/./alerting/latest/configuration/)
- [Grafana Dashboard Best Practices](https://grafana.com/./grafana/latest/best-practices/)
- [Celery Monitoring Guide](https://docs.celeryproject.org/en/stable/userguide/monitoring.html)

---

**Last updated:** 26 October 2025  
**Author:** Automated development system
