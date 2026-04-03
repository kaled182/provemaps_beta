"""Prometheus metrics wiring for Celery status reporting."""

from __future__ import annotations

import os
from typing import Any, cast

_env_enabled = os.getenv("CELERY_METRICS_ENABLED", "true").lower() == "true"
METRICS_ENABLED = _env_enabled

try:  # pragma: no cover - defensive import
    from prometheus_client import Gauge  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    METRICS_ENABLED = False  # type: ignore[assignment]
    Gauge = None  # type: ignore[assignment]

if METRICS_ENABLED and Gauge is not None:
    CELERY_WORKER_AVAILABLE = Gauge(
        "celery_worker_available",
        "Celery worker availability (1=up,0=down)",
    )
    CELERY_STATUS_LATENCY_MS = Gauge(
        "celery_status_latency_ms",
        "Latency (ms) of /celery/status endpoint",
    )
    CELERY_ACTIVE_TASKS = Gauge(
        "celery_active_tasks",
        "Total number of active tasks across workers",
    )
    CELERY_SCHEDULED_TASKS = Gauge(
        "celery_scheduled_tasks",
        "Total number of scheduled/ETA tasks across workers",
    )
    CELERY_RESERVED_TASKS = Gauge(
        "celery_reserved_tasks",
        "Total number of reserved tasks across workers",
    )
    CELERY_WORKER_COUNT = Gauge(
        "celery_worker_count",
        "Number of responding Celery workers",
    )
else:
    CELERY_WORKER_AVAILABLE = None  # type: ignore[assignment]
    CELERY_STATUS_LATENCY_MS = None  # type: ignore[assignment]
    CELERY_ACTIVE_TASKS = None  # type: ignore[assignment]
    CELERY_SCHEDULED_TASKS = None  # type: ignore[assignment]
    CELERY_RESERVED_TASKS = None  # type: ignore[assignment]
    CELERY_WORKER_COUNT = None  # type: ignore[assignment]


def _sum_task_dict(d: dict[str, list[Any]] | None) -> int:
    if not d:
        return 0
    return sum(len(v) for v in d.values())


def update_metrics(payload: dict[str, Any]) -> None:
    """Update metrics from payload produced by celery_status view.

    Expected payload shape:
    {
        'latency_ms': float,
        'worker': {
            'available': bool,
            'stats': {
                'workers': [...],
                'active_tasks': { worker: [...] },
                'scheduled_tasks': { worker: [...] },
                'reserved_tasks': { worker: [...] },
            } | None
        }
    }
    """
    if not METRICS_ENABLED:
        return
    stats_raw = payload.get("worker", {}).get("stats")
    stats: dict[str, Any] = {}
    if isinstance(stats_raw, dict):
        stats = cast(dict[str, Any], stats_raw)
    available = 1 if payload.get("worker", {}).get("available") else 0
    latency = payload.get("latency_ms") or 0

    try:
        CELERY_WORKER_AVAILABLE.set(available)  # type: ignore[attr-defined]
        CELERY_STATUS_LATENCY_MS.set(latency)  # type: ignore[attr-defined]

        workers_value = stats.get("workers")
        workers = (
            cast(list[Any], workers_value)
            if isinstance(workers_value, list)
            else []
        )
        CELERY_WORKER_COUNT.set(len(workers))  # type: ignore[attr-defined]

        active_raw = stats.get("active_tasks")
        active_dict = (
            cast(dict[str, list[Any]], active_raw)
            if isinstance(active_raw, dict)
            else None
        )
        CELERY_ACTIVE_TASKS.set(  # type: ignore[attr-defined]
            _sum_task_dict(active_dict)
        )

        scheduled_raw = stats.get("scheduled_tasks")
        scheduled_dict = (
            cast(dict[str, list[Any]], scheduled_raw)
            if isinstance(scheduled_raw, dict)
            else None
        )
        CELERY_SCHEDULED_TASKS.set(  # type: ignore[attr-defined]
            _sum_task_dict(scheduled_dict)
        )

        reserved_raw = stats.get("reserved_tasks")
        reserved_dict = (
            cast(dict[str, list[Any]], reserved_raw)
            if isinstance(reserved_raw, dict)
            else None
        )
        CELERY_RESERVED_TASKS.set(  # type: ignore[attr-defined]
            _sum_task_dict(reserved_dict)
        )
    except Exception:
        # Swallow any failure so we never break the status endpoint
        return
