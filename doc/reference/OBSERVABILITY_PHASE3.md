# Observability Enhancements - Phase 3

## Overview
This document describes the observability improvements implemented in Phase 3:
- Custom Prometheus metrics for application monitoring
- Structured logging with structlog for better log analysis
- Request ID tracking for distributed tracing

## Custom Prometheus Metrics

### Location
- **Module**: `core/metrics_custom.py`
- **Initialization**: `core/apps.py` (CoreConfig.ready())
- **Endpoint**: `/metrics/` (django-prometheus)

### Available Metrics

#### Zabbix API Metrics
- `zabbix_api_latency_seconds` (Histogram): API call duration
  - Labels: `endpoint`, `status`
  - Buckets: 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0s

- `zabbix_api_calls_total` (Counter): Total API calls
  - Labels: `endpoint`, `status`, `error_type`

#### Celery Task Metrics
- `celery_queue_depth` (Gauge): Pending tasks in queue
  - Labels: `queue`

- `celery_task_duration_seconds` (Histogram): Task execution time
  - Labels: `task_name`, `status`
  - Buckets: 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0s

#### Cache Metrics
- `cache_operations_total` (Counter): Cache operations
  - Labels: `cache_name`, `operation`, `result`

- `cache_size_bytes` (Gauge): Current cache size
  - Labels: `cache_name`

#### Database Metrics
- `db_query_duration_seconds` (Histogram): Query execution time
  - Labels: `query_type`, `model`, `operation`
  - Buckets: 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0s

- `db_slow_queries_total` (Counter): Slow queries (>1s)
  - Labels: `model`, `operation`

#### Application Info
- `mapspro_application` (Info): Version and environment
  - Labels: `version`, `environment`, `debug`

### Usage Examples

#### Recording Zabbix API Calls
```python
from core.metrics_custom import record_zabbix_call
import time

start = time.time()
try:
    response = zabbix_client.host.get(hostids=[10001])
    record_zabbix_call('host.get', time.time() - start, True)
except ZabbixAPIException as e:
    record_zabbix_call('host.get', time.time() - start, False, 'timeout')
```

#### Recording Cache Operations
```python
from core.metrics_custom import record_cache_operation

# Cache hit
data = cache.get('device_123')
if data:
    record_cache_operation('device_cache', 'get', True)
else:
    record_cache_operation('device_cache', 'get', False)
```

#### Recording Database Queries
```python
from core.metrics_custom import record_db_query
import time

start = time.time()
devices = Device.objects.filter(status='active')
duration = time.time() - start
record_db_query('SELECT', 'Device', 'filter', duration)
```

#### Updating Celery Queue Metrics
```python
from core.metrics_custom import update_celery_queue_metrics
from celery import current_app

# Get queue depth from Redis
inspector = current_app.control.inspect()
active = inspector.active()
if active:
    for worker, tasks in active.items():
        update_celery_queue_metrics('default', len(tasks))
```

## Structured Logging (Structlog)

### Configuration
- **Module**: `settings/prod.py`
- **Dependency**: `structlog==24.4.0`
- **Format**: JSON (configurable via `LOG_FORMAT` env var)

### Features
1. **Structured Output**: Logs as JSON for easy parsing
2. **Context Variables**: Automatic context binding (request_id, etc.)
3. **Timestamps**: ISO format with timezone
4. **Stack Traces**: Automatic exception formatting

### Configuration in settings/prod.py
```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### Usage Examples

#### Basic Logging
```python
import structlog

logger = structlog.get_logger(__name__)

# Simple message
logger.info("user_login", username="admin", ip="192.168.1.1")

# With structured data
logger.warning(
    "high_memory_usage",
    memory_percent=85.3,
    threshold=80.0,
    host="web-01"
)

# Error with exception
try:
    result = risky_operation()
except Exception as e:
    logger.error(
        "operation_failed",
        operation="risky_operation",
        error=str(e),
        exc_info=True
    )
```

#### Output (JSON format)
```json
{
  "event": "user_login",
  "username": "admin",
  "ip": "192.168.1.1",
  "level": "info",
  "timestamp": "2025-10-27T15:30:45.123456Z",
  "logger": "maps_view.views",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Request ID Tracking

### Middleware
- **Location**: `core/middleware/request_id.py`
- **Class**: `RequestIDMiddleware`
- **Purpose**: Track requests across logs and services

### Features
1. **Automatic Generation**: UUID for each request
2. **Header Support**: Accepts `X-Request-ID` from clients
3. **Context Binding**: Available in all structlog logs
4. **Response Header**: Returns `X-Request-ID` to client

### Configuration
Add to `MIDDLEWARE` in `settings/prod.py`:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'core.middleware.request_id.RequestIDMiddleware',  # Add here
    'django.contrib.sessions.middleware.SessionMiddleware',
    ...
]
```

### Usage
```python
import structlog

logger = structlog.get_logger(__name__)

def my_view(request):
    # request_id automatically included in logs
    logger.info("processing_request", user_id=request.user.id)
    
    # Access request ID if needed
    request_id = request.request_id
    
    return JsonResponse({"status": "ok"})
```

### Log Output
```json
{
  "event": "processing_request",
  "user_id": 42,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "request_method": "POST",
  "request_path": "/api/cables/",
  "remote_addr": "192.168.1.100",
  "level": "info",
  "timestamp": "2025-10-27T15:30:45.123456Z"
}
```

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Update Production Settings
The structlog configuration is already in `settings/prod.py`.

### 3. Add Middleware
Already added to production settings (verify in your deployment).

### 4. Environment Variables
Optional configuration:
```bash
# Logging
LOG_LEVEL=INFO                    # Default: INFO
DJANGO_LOG_LEVEL=WARNING          # Default: WARNING
LOG_FORMAT=json                   # Default: simple (use json in prod)

# Prometheus
PROMETHEUS_METRICS_ENABLED=true   # Default: true
```

## Grafana Dashboard Queries

### Zabbix API Latency (P95)
```promql
histogram_quantile(0.95, 
  sum(rate(zabbix_api_latency_seconds_bucket[5m])) by (le, endpoint)
)
```

### Cache Hit Rate
```promql
sum(rate(cache_operations_total{result="hit"}[5m])) 
/ 
sum(rate(cache_operations_total[5m]))
```

### Slow Database Queries
```promql
sum(rate(db_slow_queries_total[5m])) by (model, operation)
```

### Celery Queue Depth
```promql
celery_queue_depth{queue="default"}
```

### Request Rate by Endpoint
```promql
sum(rate(django_http_requests_total_by_view_transport_method_total[5m])) 
by (view)
```

## Troubleshooting

### Metrics Not Appearing
1. Check if prometheus_client is installed: `pip show prometheus-client`
2. Verify metrics endpoint: `curl http://localhost:8000/metrics/`
3. Check CoreConfig.ready() is being called (see logs on startup)

### Structlog Not Working
1. Verify installation: `pip show structlog`
2. Check import in settings/prod.py
3. Verify LOG_FORMAT environment variable

### Request ID Missing
1. Check middleware order in settings
2. Verify RequestIDMiddleware is before other custom middleware
3. Check logs for middleware initialization errors

## Next Steps

### Recommended Additions
1. **Celery Beat Task**: Periodically update queue metrics
2. **Database Middleware**: Auto-instrument all queries
3. **Alert Rules**: Define Prometheus alerts for critical metrics
4. **Log Aggregation**: Send JSON logs to ELK/Loki/CloudWatch

### Example Celery Task for Metrics
```python
from celery import shared_task
from core.metrics_custom import update_celery_queue_metrics
from celery import current_app

@shared_task
def update_queue_metrics():
    """Periodic task to update Celery queue metrics."""
    inspector = current_app.control.inspect()
    reserved = inspector.reserved()
    
    if reserved:
        for worker, tasks in reserved.items():
            queue_name = worker.split('@')[0]
            update_celery_queue_metrics(queue_name, len(tasks))
```

## References
- [Prometheus Best Practices](https://prometheus.io/./practices/)
- [Structlog Documentation](https://www.structlog.org/)
- [Django Prometheus](https://github.com/korfuri/django-prometheus)
- [12-Factor App Logging](https://12factor.net/logs)
