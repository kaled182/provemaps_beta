"""
Stale-While-Revalidate cache helpers for the dashboard.

Strategy:
1. Serve cached (possibly stale) data immediately for fast responses.
2. Trigger a background refresh via Celery when data is stale.
3. Let the frontend display a "stale data" banner with a timestamp.

Features:
- Fresh TTL defaults to 30 seconds.
- Stale TTL defaults to 60 seconds (data remains servable while refresh runs).
- Background refresh powered by Celery tasks.
- Synchronous fallback when the cache does not have any snapshot yet.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional

from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# SWR configuration tuned for near real-time monitoring
SWR_FRESH_TTL = getattr(settings, "SWR_FRESH_TTL", 30)  # 30 segundos (fresh)
SWR_STALE_TTL = getattr(settings, "SWR_STALE_TTL", 60)  # 1 min (stale)
SWR_ENABLED = getattr(settings, "SWR_ENABLED", True)


class SWRCache:
    """
    Cache helper that follows the Stale-While-Revalidate pattern.

    Example:
        cache_swr = SWRCache(key="dashboard:hosts")
        data = cache_swr.get_or_fetch(
            fetch_fn=lambda: get_hosts_status_data(),
            async_task=refresh_dashboard_cache_task.delay
        )
    """

    def __init__(
        self,
        key: str,
        fresh_ttl: int = SWR_FRESH_TTL,
        stale_ttl: int = SWR_STALE_TTL,
    ):
        """
        Args:
            key: Unique cache key identifier.
            fresh_ttl: Number of seconds data is considered fresh.
            stale_ttl: Number of seconds stale data can still be served.
        """
        self.key = key
        self.fresh_ttl = fresh_ttl
        self.stale_ttl = stale_ttl
        self.timestamp_key = f"{key}:timestamp"
        self.monotonic_key = f"{key}:monotonic"

    def get_cached_data(self) -> Optional[Dict[str, Any]]:
        """
        Return cached data (fresh or stale) if available.

        Returns:
            Dict with ``data``, ``timestamp``, ``is_stale`` or ``None`` if
            the cache is empty.
        """
        try:
            data = cache.get(self.key)
            timestamp = cache.get(self.timestamp_key)
            monotonic_mark = cache.get(self.monotonic_key)

            if data is None:
                return None

            if monotonic_mark is not None:
                # Use monotonic time so clock drift does not flip freshness.
                age = time.monotonic() - monotonic_mark
            else:
                age = time.time() - (timestamp or 0)
                if timestamp is not None:
                    # Backfill monotonic marker for legacy cache entries.
                    try:
                        cache.set(
                            self.monotonic_key,
                            time.monotonic(),
                            self.stale_ttl,
                        )
                    except Exception:
                        logger.exception(
                            "Failed to backfill SWR monotonic marker for key=%s",
                            self.key,
                        )

            if age < 0:
                # Clamp negative ages that arise from backwards clock jumps.
                age = 0

            is_stale = age >= self.fresh_ttl

            return {
                "data": data,
                "timestamp": timestamp,
                "age_seconds": int(age),
                "is_stale": is_stale,
            }
        except Exception:
            logger.exception("Failed to read SWR cache for key=%s", self.key)
            return None

    def set_cached_data(self, data: Any) -> None:
        """
        Store data in the cache together with a timestamp.

        Args:
            data: Payload to store.
        """
        try:
            now = time.time()
            cache.set(self.key, data, self.stale_ttl)
            cache.set(self.timestamp_key, now, self.stale_ttl)
            cache.set(self.monotonic_key, time.monotonic(), self.stale_ttl)
            logger.debug(
                "SWR cache updated: key=%s, ttl=%d", self.key, self.stale_ttl
            )
        except Exception:
            logger.exception("Failed to write SWR cache for key=%s", self.key)

    def get_or_fetch(
        self,
        fetch_fn: Callable[[], Any],
        async_task: Optional[Callable[[], Any]] = None,
    ) -> Dict[str, Any]:
        """
        Implement the SWR pattern for the configured cache key.

        Workflow:
        1. Fresh cache -> return immediately.
        2. Stale cache -> return stale data and trigger a background refresh.
        3. Empty cache -> perform a synchronous fetch.

        Args:
            fetch_fn: Synchronous callable that retrieves fresh data.
            async_task: Optional Celery task trigger for async refresh.

        Returns:
            Dict with ``data``, ``timestamp``, ``is_stale`` and ``cache_hit``.
        """
        if not SWR_ENABLED:
            # SWR disabled: fetch directly
            data = fetch_fn()
            return {
                "data": data,
                "timestamp": time.time(),
                "is_stale": False,
                "cache_hit": False,
            }

        cached = self.get_cached_data()

        if cached is None:
            # Empty cache: synchronous fetch
            logger.info(
                "SWR cache miss (empty): key=%s, fetching sync",
                self.key,
            )
            data = fetch_fn()
            self.set_cached_data(data)
            return {
                "data": data,
                "timestamp": time.time(),
                "is_stale": False,
                "cache_hit": False,
            }

        if not cached["is_stale"]:
            # Fresh cache: serve immediately
            logger.debug(
                "SWR cache hit (fresh): key=%s, age=%ds",
                self.key,
                cached["age_seconds"],
            )
            return {**cached, "cache_hit": True}

        # Stale cache: serve now and trigger refresh
        logger.info(
            "SWR cache hit (stale): key=%s, age=%ds, "
            "triggering background refresh",
            self.key,
            cached["age_seconds"],
        )

        if async_task:
            try:
                async_task()
                logger.debug(
                    "Background refresh task dispatched for key=%s",
                    self.key,
                )
            except Exception:
                logger.exception(
                    "Failed to dispatch background refresh for key=%s",
                    self.key,
                )

        return {**cached, "cache_hit": True}

    def invalidate(self) -> None:
        """Remove cached data for this key."""
        try:
            cache.delete(self.key)
            cache.delete(self.timestamp_key)
            cache.delete(self.monotonic_key)
            logger.info("SWR cache invalidated: key=%s", self.key)
        except Exception:
            logger.exception(
                "Failed to invalidate SWR cache for key=%s",
                self.key,
            )


# Global instance reused by the dashboard view
dashboard_cache = SWRCache(key="dashboard:hosts_status")


def get_dashboard_cached(
    fetch_fn: Callable[[], Dict[str, Any]],
    async_task: Optional[Callable[[], Any]] = None,
) -> Dict[str, Any]:
    """Helper around :class:`SWRCache` for the dashboard payload."""
    return dashboard_cache.get_or_fetch(fetch_fn, async_task)


def invalidate_dashboard_cache() -> None:
    """Invalidate the dashboard cache (useful after inventory updates)."""
    dashboard_cache.invalidate()


__all__ = [
    "SWRCache",
    "dashboard_cache",
    "get_dashboard_cached",
    "invalidate_dashboard_cache",
    "SWR_FRESH_TTL",
    "SWR_STALE_TTL",
    "SWR_ENABLED",
]
