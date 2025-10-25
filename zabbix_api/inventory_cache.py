from __future__ import annotations

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)
FIBER_LIST_CACHE_KEY = "fibers:list"


def invalidate_fiber_cache() -> None:
    """Clear cached fiber listings used in dashboards and APIs."""
    try:
        cache.delete(FIBER_LIST_CACHE_KEY)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis indispon?vel), n?o foi poss?vel invalidar cache: %s",
            exc.__class__.__name__,
        )


__all__ = ["FIBER_LIST_CACHE_KEY", "invalidate_fiber_cache"]
