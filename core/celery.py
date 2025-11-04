"""
Celery application for the MapsProveFiber project.

- Reads Django settings (namespace CELERY_) and falls back to
    environment variables when needed.
- Defines queues/routes for different workloads (default, zabbix, maps).
- Applies sensible performance and safety defaults.
"""

import os
import time
from celery import Celery
from kombu import Queue, Exchange

# ---------------------------------------------------------------------
# Django settings bootstrap
# ---------------------------------------------------------------------
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "settings.dev"),
)

# Logical Celery app name (appears in logs/monitoring)
app = Celery("mapsprovefiber")

# Load Django configuration (uses CELERY_ prefix in settings)
app.config_from_object("django.conf:settings", namespace="CELERY")

# ---------------------------------------------------------------------
# Broker/backend fallbacks derived from environment variables
# ---------------------------------------------------------------------
# Priority: CELERY_BROKER_URL -> REDIS_URL -> local default
_broker_url = (
    os.getenv("CELERY_BROKER_URL")
    or os.getenv("REDIS_URL")
    or "redis://localhost:6379/1"
)
_result_backend = os.getenv("CELERY_RESULT_BACKEND") or _broker_url

# Default interval (seconds) for dashboard refresh via SWR
_dashboard_refresh_interval = float(
    os.getenv("DASHBOARD_CACHE_REFRESH_INTERVAL", "60")
)

# Default interval (seconds) for Zabbix inventory sync
_inventory_sync_interval = float(
    os.getenv("INVENTORY_SYNC_INTERVAL_SECONDS", "86400")
)

_service_account_rotation_interval = float(
    os.getenv("SERVICE_ACCOUNT_ROTATION_INTERVAL_SECONDS", "3600")
)

# ---------------------------------------------------------------------
# Default options (overridable via settings or environment)
# ---------------------------------------------------------------------
app.conf.update(
    broker_url=_broker_url,
    result_backend=_result_backend,

    # Serialization (avoid pickle for safety)
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone / clock
    timezone=os.getenv("TIME_ZONE", "UTC"),
    enable_utc=True,

    # Reliability / performance
    # Avoid losing a task if the worker crashes mid-execution
    task_acks_late=True,
    worker_prefetch_multiplier=int(
        os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1")
    ),
    worker_max_tasks_per_child=int(
        os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", "100")
    ),
    # 5 minutes
    task_soft_time_limit=int(
        os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "300")
    ),
    # 10 minutes
    task_time_limit=int(os.getenv("CELERY_TASK_TIME_LIMIT", "600")),
    # Example: "10/s"
    task_default_rate_limit=os.getenv(
        "CELERY_TASK_DEFAULT_RATE_LIMIT", None
    ),
    broker_connection_retry_on_startup=True,

    # Synchronous execution during tests (can be defined in env/test)
    task_always_eager=(
        os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
    ),
    task_eager_propagates=True,

    # Verbose logging
    worker_log_format=os.getenv(
        "CELERY_WORKER_LOG_FORMAT",
        "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    ),
    worker_task_log_format=os.getenv(
        "CELERY_TASK_LOG_FORMAT",
        (
            "[%(asctime)s: %(levelname)s/%(processName)s] "
            "[%(task_name)s(%(task_id)s)] %(message)s"
        ),
    ),
    worker_redirect_stdouts=False,

    # Retry policies
    task_publish_retry=True,
    task_publish_retry_policy={
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.2,
    },

    # Monitoring and observability
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Result expiration (avoid piling up stale records)
    result_expires=int(os.getenv("CELERY_RESULT_EXPIRES", "3600")),  # 1 hour

    # Dead letter queue behavior for repeatedly failing tasks
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=False,
    
    # Beat schedule for recurring tasks
    beat_schedule={
        "update-celery-metrics": {
            "task": "core.celery.update_celery_metrics_task",
            "schedule": float(
                os.getenv("CELERY_METRICS_UPDATE_INTERVAL", "30")
            ),
            "options": {"queue": "default"},
        },
        "refresh-dashboard-cache": {
            "task": "maps_view.tasks.refresh_dashboard_cache_task",
            "schedule": _dashboard_refresh_interval,
            "options": {"queue": "maps"},
        },
        "sync-zabbix-inventory": {
            "task": "inventory.tasks.sync_zabbix_inventory_task",
            "schedule": _inventory_sync_interval,
            "options": {"queue": "default"},
        },
        "service-account-rotation": {
            "task": "service_accounts.enforce_rotation_policies_task",
            "schedule": _service_account_rotation_interval,
            "options": {"queue": "default"},
        },
    },
)

# ---------------------------------------------------------------------
# Queues and routing
# ---------------------------------------------------------------------
_default_exchange_name = os.getenv("CELERY_DEFAULT_EXCHANGE", "mapsprovefiber")
_default_exchange = Exchange(_default_exchange_name, type="direct")

app.conf.task_queues = (
    Queue("default", _default_exchange, routing_key="default"),
    Queue("zabbix", _default_exchange, routing_key="zabbix"),
    Queue("maps", _default_exchange, routing_key="maps"),
)

app.conf.task_default_queue = os.getenv("CELERY_DEFAULT_QUEUE", "default")
app.conf.task_default_exchange = _default_exchange_name
app.conf.task_default_routing_key = app.conf.task_default_queue

# Routing rules grouped by task namespace
app.conf.task_routes = {
    # Tasks from the Zabbix app (e.g. zabbix_api/tasks.py -> @shared_task)
    "zabbix_api.tasks.*": {"queue": "zabbix", "routing_key": "zabbix"},

    # Fiber/route tasks (e.g. routes_builder/tasks.py)
    "routes_builder.tasks.*": {"queue": "maps", "routing_key": "maps"},

    # Dashboard/maps view tasks
    "maps_view.tasks.*": {"queue": "maps", "routing_key": "maps"},
}

# ---------------------------------------------------------------------
# Automatic task discovery across installed apps
# ---------------------------------------------------------------------
app.autodiscover_tasks()


# ---------------------------------------------------------------------
# Simple diagnostic task (used by worker health checks)
# ---------------------------------------------------------------------
@app.task(bind=True)
def ping(self):
    """Return "pong"; handy for sanity-checking worker health."""
    return "pong"


# ---------------------------------------------------------------------
# Comprehensive worker health check task
# ---------------------------------------------------------------------
@app.task(bind=True)
def health_check(self):
    """Run a set of lightweight diagnostics against the worker."""
    # Basic functionality test
    basic_test = "pong"
    
    # Timestamp check (confirms the worker is processing requests)
    timestamp = time.time()
    
    # Optional broker connectivity test
    broker_ok = True
    broker_error = None
    try:
        # Try sending a minimal heartbeat message to the broker
        self.app.control.inspect().ping(timeout=2)
    except Exception as e:
        broker_ok = False
        broker_error = str(e)
    
    return {
        "status": "healthy",
        "worker_id": self.request.hostname,
        "timestamp": timestamp,
        "broker_connected": broker_ok,
        "broker_error": broker_error if not broker_ok else None,
        "response": basic_test
    }


# ---------------------------------------------------------------------
# Queue statistics task (feeds dashboards)
# ---------------------------------------------------------------------
@app.task(bind=True)
def get_queue_stats(self):
    """Return queue statistics for dashboard consumption."""
    try:
        inspector = self.app.control.inspect()
        stats = inspector.stats()
        active = inspector.active()
        scheduled = inspector.scheduled()
        reserved = inspector.reserved()
        
        return {
            "workers": list(stats.keys()) if stats else [],
            "active_tasks": active,
            "scheduled_tasks": scheduled,
            "reserved_tasks": reserved,
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e), "timestamp": time.time()}


# ---------------------------------------------------------------------
# Periodic task to refresh Prometheus metrics without HTTP requests
# ---------------------------------------------------------------------
@app.task(bind=True)
def update_celery_metrics_task(self):
    """Periodic Prometheus metrics refresh scheduled via Celery beat."""
    try:
        # Import metrics helper
        from core.metrics_celery import update_metrics  # type: ignore

        # Collect light data similar to the endpoint but without HTTP overhead
        payload: dict = {
            "timestamp": time.time(),
            "latency_ms": 0,  # not applicable for an internal task
            "status": "degraded",
            "worker": {"available": False, "error": None, "stats": None},
        }
        
        # Attempt ping
        ping_ok = False
        try:
            pong_res = ping.delay()  # type: ignore[attr-defined]
            pong_val = pong_res.get(timeout=2)
            ping_ok = pong_val == "pong"
        except Exception as e:
            payload["worker"]["error"] = str(e)[:200]

        # Attempt stats only if ping succeeds
        if ping_ok:
            payload["worker"]["available"] = True
            try:
                stats_res = get_queue_stats.delay()  # type: ignore
                stats = stats_res.get(timeout=3)
                if isinstance(stats, dict) and "error" not in stats:
                    payload["worker"]["stats"] = stats
                    payload["status"] = "ok"
            except Exception:
                pass  # ignore stats errors, keep available=True flag

        # Update metrics
        update_metrics(payload)
        return {"status": "updated", "worker_available": ping_ok}
    
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}
