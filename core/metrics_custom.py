"""
Custom Prometheus Metrics for MapsProveFiber

Application-specific metrics for monitoring:
- Zabbix API latency and reliability
- Celery task queue depth and worker health
- Cache hit rates and efficiency
- Database query performance
- External service availability
"""
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, Info


# Zabbix API Metrics
zabbix_api_latency = Histogram(
    'zabbix_api_latency_seconds',
    'Latency of Zabbix API calls in seconds',
    labelnames=['endpoint', 'status'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

zabbix_api_calls_total = Counter(
    'zabbix_api_calls_total',
    'Total number of Zabbix API calls',
    labelnames=['endpoint', 'status', 'error_type']
)

# Celery Task Metrics
celery_queue_depth = Gauge(
    'celery_queue_depth',
    'Number of tasks waiting in Celery queue',
    labelnames=['queue']
)

celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Duration of Celery task execution in seconds',
    labelnames=['task_name', 'status'],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

# Cache Metrics
cache_operations_total = Counter(
    'cache_operations_total',
    'Total number of cache operations',
    labelnames=['cache_name', 'operation', 'result']
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Current size of cache in bytes',
    labelnames=['cache_name']
)

# Database Query Metrics
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Duration of database queries in seconds',
    labelnames=['query_type', 'model', 'operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

db_slow_queries_total = Counter(
    'db_slow_queries_total',
    'Total number of slow database queries (>1s)',
    labelnames=['model', 'operation']
)

# Application Info
application_info = Info(
    'mapspro_application',
    'Application version and environment information'
)


def init_metrics():
    """Initialize metrics with default values."""
    from django.conf import settings

    application_info.info({
        'version': getattr(settings, 'APP_VERSION', 'unknown'),
        'environment': getattr(
            settings, 'ENVIRONMENT', 'development'
        ),
        'debug': str(settings.DEBUG),
    })

    celery_queue_depth.labels(queue='default').set(0)
    celery_queue_depth.labels(queue='priority').set(0)


def record_zabbix_call(
    endpoint: str,
    duration: float,
    success: bool,
    error_type: Optional[str] = None
):
    """Record a Zabbix API call."""
    status = 'success' if success else 'error'
    zabbix_api_latency.labels(
        endpoint=endpoint, status=status
    ).observe(duration)
    zabbix_api_calls_total.labels(
        endpoint=endpoint,
        status=status,
        error_type=error_type or 'none'
    ).inc()


def record_cache_operation(
    cache_name: str, operation: str, hit: bool
):
    """Record a cache operation."""
    result = 'hit' if hit else 'miss'
    if operation == 'set':
        result = 'success' if hit else 'error'

    cache_operations_total.labels(
        cache_name=cache_name,
        operation=operation,
        result=result
    ).inc()


def record_db_query(
    query_type: str, model: str, operation: str, duration: float
):
    """Record a database query."""
    db_query_duration.labels(
        query_type=query_type,
        model=model,
        operation=operation
    ).observe(duration)

    if duration > 1.0:
        db_slow_queries_total.labels(
            model=model, operation=operation
        ).inc()


def update_celery_queue_metrics(queue_name: str, depth: int):
    """Update Celery queue depth."""
    celery_queue_depth.labels(queue=queue_name).set(depth)
