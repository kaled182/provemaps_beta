"""Prometheus metrics for Celery status.

This module defines gauges updated by the `/celery/status` endpoint.
It is safe to import even if Prometheus client isn't available (fails silently).
Controlled by environment variable `CELERY_METRICS_ENABLED` (default: true).
"""
from __future__ import annotations
import os
from typing import Dict, Any

METRICS_ENABLED = os.getenv("CELERY_METRICS_ENABLED", "true").lower() == "true"

try:  # pragma: no cover - defensive import
    from prometheus_client import Gauge  # type: ignore
except Exception:  # pragma: no cover
    METRICS_ENABLED = False
    Gauge = None  # type: ignore

if METRICS_ENABLED:
    CELERY_WORKER_AVAILABLE = Gauge(
        "celery_worker_available", "Celery worker availability (1=up,0=down)"
    )
    CELERY_STATUS_LATENCY_MS = Gauge(
        "celery_status_latency_ms", "Latency (ms) of /celery/status endpoint"
    )
    CELERY_ACTIVE_TASKS = Gauge(
        "celery_active_tasks", "Total number of active tasks across workers"
    )
    CELERY_SCHEDULED_TASKS = Gauge(
        "celery_scheduled_tasks", "Total number of scheduled/ETA tasks across workers"
    )
    CELERY_RESERVED_TASKS = Gauge(
        "celery_reserved_tasks", "Total number of reserved tasks across workers"
    )
    CELERY_WORKER_COUNT = Gauge(
        "celery_worker_count", "Number of responding Celery workers"
    )
else:
    CELERY_WORKER_AVAILABLE = None  # type: ignore
    CELERY_STATUS_LATENCY_MS = None  # type: ignore
    CELERY_ACTIVE_TASKS = None  # type: ignore
    CELERY_SCHEDULED_TASKS = None  # type: ignore
    CELERY_RESERVED_TASKS = None  # type: ignore
    CELERY_WORKER_COUNT = None  # type: ignore


def _sum_task_dict(d: Dict[str, list] | None) -> int:
    if not d:
        return 0
    return sum(len(v) for v in d.values())


def update_metrics(payload: Dict[str, Any]) -> None:
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
    stats = payload.get("worker", {}).get("stats") or {}
    available = 1 if payload.get("worker", {}).get("available") else 0
    latency = payload.get("latency_ms") or 0

    try:
        CELERY_WORKER_AVAILABLE.set(available)  # type: ignore[attr-defined]
        CELERY_STATUS_LATENCY_MS.set(latency)  # type: ignore[attr-defined]
        CELERY_WORKER_COUNT.set(len(stats.get("workers", []) or []))  # type: ignore[attr-defined]
        CELERY_ACTIVE_TASKS.set(_sum_task_dict(stats.get("active_tasks")))  # type: ignore[attr-defined]
        CELERY_SCHEDULED_TASKS.set(_sum_task_dict(stats.get("scheduled_tasks")))  # type: ignore[attr-defined]
        CELERY_RESERVED_TASKS.set(_sum_task_dict(stats.get("reserved_tasks")))  # type: ignore[attr-defined]
    except Exception:
        # Silencia qualquer falha para não quebrar o endpoint
        return
