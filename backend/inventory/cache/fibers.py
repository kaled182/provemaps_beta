from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)

FIBER_LIST_CACHE_KEY = "fibers:list"
FIBER_LIST_CACHE_TIMEOUT = 120  # 2 minutes (fresh data)
FIBER_LIST_SWR_TIMEOUT = 240  # 4 minutes (stale-while-revalidate)


def invalidate_fiber_cache() -> None:
    """Clear cached fiber listings used in dashboards and APIs."""
    try:
        cache.delete(FIBER_LIST_CACHE_KEY)
    except Exception as exc:  # pragma: no cover - cache may be unavailable
        logger.debug(
            "Cache offline (Redis indisponivel); unable to invalidate fiber "
            "cache: %s",
            exc.__class__.__name__,
        )


def get_cached_fiber_list(
    fetch_fn: Callable[[], list[dict[str, Any]]]
) -> tuple[list[dict[str, Any]], bool]:
    """
    Get fiber list with stale-while-revalidate (SWR) caching.
    
    Returns:
        tuple: (data, is_fresh) where is_fresh indicates if data is current
    """
    try:
        cached_entry = cache.get(FIBER_LIST_CACHE_KEY)
    except Exception as exc:  # pragma: no cover - cache may be unavailable
        logger.debug(
            "Cache offline (Redis unavailable); fetching fresh data: %s",
            exc.__class__.__name__,
        )
        return fetch_fn(), True

    now = time.time()
    
    if cached_entry is None:
        # Cache miss - fetch fresh data
        logger.debug("[Fiber Cache] MISS - fetching fresh data")
        data = fetch_fn()
        try:
            cache.set(
                FIBER_LIST_CACHE_KEY,
                {"data": data, "timestamp": now},
                FIBER_LIST_SWR_TIMEOUT,
            )
        except Exception as exc:  # pragma: no cover
            logger.debug("Failed to cache fiber list: %s", exc)
        return data, True
    
    # Cache hit - check freshness
    cached_timestamp = cached_entry.get("timestamp", 0)
    age = now - cached_timestamp
    
    if age < FIBER_LIST_CACHE_TIMEOUT:
        # Data is fresh
        logger.debug(
            "[Fiber Cache] HIT - serving fresh data (age: %.1fs)",
            age,
        )
        return cached_entry["data"], True
    
    # Data is stale but acceptable - serve immediately
    logger.debug(
        "[Fiber Cache] HIT - serving stale data (age: %.1fs) - "
        "background refresh needed",
        age,
    )
    return cached_entry["data"], False


__all__ = [
    "FIBER_LIST_CACHE_KEY",
    "FIBER_LIST_CACHE_TIMEOUT",
    "FIBER_LIST_SWR_TIMEOUT",
    "invalidate_fiber_cache",
    "get_cached_fiber_list",
]
