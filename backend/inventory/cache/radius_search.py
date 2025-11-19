"""
Stale-While-Revalidate (SWR) cache for spatial radius search queries.

Phase 7 Day 5 - Cache Implementation

Pattern:
1. Check cache for query (lat, lng, radius_km) → serve immediately if found
2. If cached data is fresh (< 30s old) → return as-is
3. If cached data is stale (30-60s old) → return stale + async refresh
4. If cache miss or expired (> 60s) → fetch from DB + cache result

Benefits:
- Fast responses for repeated queries (dashboard, user navigation)
- Reduced database load for common radius values (5km, 10km, 50km)
- Graceful degradation when Redis unavailable (falls back to DB)

Cache key format:
  spatial:sites:radius:{lat}:{lng}:{radius_km}:{limit}

Example:
  spatial:sites:radius:-15.780100:-47.929200:10:100
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# SWR configuration (inherit from global settings)
RADIUS_SEARCH_FRESH_TTL = getattr(settings, "SWR_FRESH_TTL", 30)  # 30s fresh
RADIUS_SEARCH_STALE_TTL = getattr(settings, "SWR_STALE_TTL", 60)  # 60s stale
RADIUS_SEARCH_ENABLED = getattr(settings, "SWR_ENABLED", True)

# Prometheus metrics (optional)
try:
    from prometheus_client import Counter, Histogram
    
    CACHE_HIT_COUNTER = Counter(
        'radius_search_cache_hits_total',
        'Total cache hits for radius search queries',
        ['status']  # fresh, stale, miss
    )
    
    CACHE_LATENCY_HISTOGRAM = Histogram(
        'radius_search_cache_latency_seconds',
        'Latency of cache operations for radius search',
        ['operation']  # get, set, invalidate
    )
    
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.debug("Prometheus metrics not available for radius search cache")


def _generate_cache_key(
    lat: float,
    lng: float,
    radius_km: float,
    limit: int = 100
) -> str:
    """
    Generate deterministic cache key for radius search query.
    
    Uses hash of coordinates to handle floating point precision variations.
    
    Args:
        lat: Latitude (WGS84)
        lng: Longitude (WGS84)
        radius_km: Search radius in kilometers
        limit: Maximum number of results
    
    Returns:
        Cache key string
    
    Example:
        >>> _generate_cache_key(-15.7801, -47.9292, 10, 100)
        'spatial:sites:radius:abc123def456:10:100'
    """
    # Round coordinates to 6 decimals (~0.1m precision)
    lat_rounded = round(lat, 6)
    lng_rounded = round(lng, 6)
    
    # Create hash of coordinates (handles float precision issues)
    coord_str = f"{lat_rounded:.6f},{lng_rounded:.6f}"
    coord_hash = hashlib.md5(coord_str.encode()).hexdigest()[:12]
    
    # Cache key includes radius and limit
    return f"spatial:sites:radius:{coord_hash}:{int(radius_km)}:{limit}"


def _generate_timestamp_key(cache_key: str) -> str:
    """Generate timestamp key for SWR pattern."""
    return f"{cache_key}:timestamp"


def get_cached_radius_search(
    lat: float,
    lng: float,
    radius_km: float,
    limit: int = 100
) -> dict[str, Any] | None:
    """
    Retrieve cached radius search results if available.
    
    Args:
        lat: Latitude
        lng: Longitude
        radius_km: Search radius in kilometers
        limit: Max results
    
    Returns:
        Dict with 'data', 'timestamp', 'age_seconds', 'is_stale'
        or None if miss
    """
    if not RADIUS_SEARCH_ENABLED:
        return None
    
    cache_key = _generate_cache_key(lat, lng, radius_km, limit)
    timestamp_key = _generate_timestamp_key(cache_key)
    
    try:
        start_time = time.time()
        
        data = cache.get(cache_key)
        timestamp = cache.get(timestamp_key)
        
        if METRICS_AVAILABLE:
            elapsed = time.time() - start_time
            CACHE_LATENCY_HISTOGRAM.labels(operation='get').observe(elapsed)
        
        if data is None:
            if METRICS_AVAILABLE:
                CACHE_HIT_COUNTER.labels(status='miss').inc()
            logger.debug(
                "[Radius Cache] MISS - no cached data for key=%s",
                cache_key
            )
            return None
        
        now = time.time()
        age = now - (timestamp or 0)
        is_stale = age >= RADIUS_SEARCH_FRESH_TTL
        
        status = 'stale' if is_stale else 'fresh'
        if METRICS_AVAILABLE:
            CACHE_HIT_COUNTER.labels(status=status).inc()
        
        logger.debug(
            "[Radius Cache] HIT - %s data (age: %.1fs) for key=%s",
            status.upper(),
            age,
            cache_key
        )
        
        return {
            "data": data,
            "timestamp": timestamp,
            "age_seconds": int(age),
            "is_stale": is_stale,
            "cache_key": cache_key
        }
        
    except Exception as exc:
        logger.warning(
            "[Radius Cache] Error reading cache: %s (falling back to DB)",
            exc.__class__.__name__,
            exc_info=exc if settings.DEBUG else None
        )
        return None


def set_cached_radius_search(
    lat: float,
    lng: float,
    radius_km: float,
    limit: int,
    data: Any
) -> bool:
    """
    Store radius search results in cache with timestamp.
    
    Args:
        lat: Latitude
        lng: Longitude
        radius_km: Search radius in kilometers
        limit: Max results
        data: Query results (list of sites)
    
    Returns:
        True if cached successfully, False otherwise
    """
    if not RADIUS_SEARCH_ENABLED:
        return False
    
    cache_key = _generate_cache_key(lat, lng, radius_km, limit)
    timestamp_key = _generate_timestamp_key(cache_key)
    
    try:
        start_time = time.time()
        now = time.time()
        
        # Store data with stale TTL
        cache.set(cache_key, data, RADIUS_SEARCH_STALE_TTL)
        cache.set(timestamp_key, now, RADIUS_SEARCH_STALE_TTL)
        
        if METRICS_AVAILABLE:
            elapsed = time.time() - start_time
            CACHE_LATENCY_HISTOGRAM.labels(operation='set').observe(elapsed)
        
        logger.debug(
            "[Radius Cache] SET - cached %d sites for key=%s (TTL: %ds)",
            len(data) if isinstance(data, list) else 0,
            cache_key,
            RADIUS_SEARCH_STALE_TTL
        )
        
        return True
        
    except Exception as exc:
        logger.warning(
            "[Radius Cache] Error writing cache: %s",
            exc.__class__.__name__,
            exc_info=exc if settings.DEBUG else None
        )
        return False


def invalidate_radius_cache(
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float | None = None,
    limit: int | None = None
) -> int:
    """
    Invalidate cached radius search results.
    
    If specific parameters provided, invalidates only that query.
    If no parameters, invalidates all radius search caches (expensive!).
    
    Args:
        lat: Optional latitude to invalidate specific query
        lng: Optional longitude
        radius_km: Optional radius
        limit: Optional limit
    
    Returns:
        Number of keys deleted (0 if Redis unavailable)
    
    Usage:
        # Invalidate specific query
        invalidate_radius_cache(-15.7801, -47.9292, 10, 100)
        
        # Invalidate all (use sparingly)
        invalidate_radius_cache()
    """
    try:
        start_time = time.time()
        
        if lat is not None and lng is not None and radius_km is not None:
            # Invalidate specific query
            limit = limit or 100
            cache_key = _generate_cache_key(lat, lng, radius_km, limit)
            timestamp_key = _generate_timestamp_key(cache_key)
            
            cache.delete(cache_key)
            cache.delete(timestamp_key)
            
            deleted_count = 2
            logger.debug(
                "[Radius Cache] INVALIDATE - deleted specific query key=%s",
                cache_key
            )
        else:
            # Invalidate all radius search caches
            # Note: This requires cache backend with delete_pattern support (Redis)
            pattern = "spatial:sites:radius:*"
            
            try:
                # Try Redis-specific pattern deletion
                deleted_count = cache.delete_pattern(pattern)
                logger.info(
                    "[Radius Cache] INVALIDATE - deleted all queries "
                    "(pattern=%s, count=%d)",
                    pattern,
                    deleted_count
                )
            except AttributeError:
                # Fallback: delete_pattern not available
                logger.warning(
                    "[Radius Cache] INVALIDATE - delete_pattern not supported, "
                    "cannot bulk invalidate"
                )
                deleted_count = 0
        
        if METRICS_AVAILABLE:
            elapsed = time.time() - start_time
            CACHE_LATENCY_HISTOGRAM.labels(operation='invalidate').observe(elapsed)
        
        return deleted_count
        
    except Exception as exc:
        logger.warning(
            "[Radius Cache] Error invalidating cache: %s",
            exc.__class__.__name__,
            exc_info=exc if settings.DEBUG else None
        )
        return 0


def get_radius_search_with_cache(
    lat: float,
    lng: float,
    radius_km: float,
    limit: int,
    fetch_fn,
    async_refresh_task=None
) -> dict[str, Any]:
    """
    Get radius search results with SWR caching.
    
    Workflow:
    1. Check cache → if fresh, return immediately
    2. If stale → return stale data + trigger async refresh
    3. If miss → fetch from DB synchronously + cache
    
    Args:
        lat: Latitude
        lng: Longitude
        radius_km: Search radius
        limit: Max results
        fetch_fn: Callable that fetches fresh data from DB
        async_refresh_task: Optional Celery task for async refresh
    
    Returns:
        Dict with 'data', 'is_stale', 'cache_hit', 'timestamp'
    
    Example:
        from inventory.tasks import refresh_radius_search_cache
        
        result = get_radius_search_with_cache(
            lat=-15.7801,
            lng=-47.9292,
            radius_km=10,
            limit=100,
            fetch_fn=lambda: get_sites_within_radius(-15.7801, -47.9292, 10, 100),
            async_refresh_task=refresh_radius_search_cache.delay
        )
        
        sites = result['data']
        is_stale = result['is_stale']
    """
    if not RADIUS_SEARCH_ENABLED:
        # Cache disabled - fetch directly
        logger.debug("[Radius Cache] Cache disabled, fetching from DB")
        data = fetch_fn()
        return {
            "data": data,
            "timestamp": time.time(),
            "is_stale": False,
            "cache_hit": False
        }
    
    # Try cache first
    cached = get_cached_radius_search(lat, lng, radius_km, limit)
    
    if cached is None:
        # Cache MISS - fetch synchronously and cache
        logger.info(
            "[Radius Cache] MISS - fetching from DB (lat=%.6f, lng=%.6f, r=%dkm)",
            lat, lng, int(radius_km)
        )
        
        data = fetch_fn()
        set_cached_radius_search(lat, lng, radius_km, limit, data)
        
        return {
            "data": data,
            "timestamp": time.time(),
            "is_stale": False,
            "cache_hit": False
        }
    
    # Cache HIT
    if cached["is_stale"]:
        # Data is STALE - return it but trigger async refresh
        logger.info(
            "[Radius Cache] STALE HIT - serving stale data (age=%ds) and "
            "triggering refresh",
            cached["age_seconds"]
        )
        
        if async_refresh_task:
            try:
                async_refresh_task(lat, lng, radius_km, limit)
                logger.debug("[Radius Cache] Async refresh task queued")
            except Exception as exc:
                logger.warning(
                    "[Radius Cache] Failed to queue async refresh: %s",
                    exc.__class__.__name__
                )
        
        return {
            "data": cached["data"],
            "timestamp": cached["timestamp"],
            "is_stale": True,
            "cache_hit": True,
            "age_seconds": cached["age_seconds"]
        }
    
    # Data is FRESH - return immediately
    logger.debug(
        "[Radius Cache] FRESH HIT - serving fresh data (age=%ds)",
        cached["age_seconds"]
    )
    
    return {
        "data": cached["data"],
        "timestamp": cached["timestamp"],
        "is_stale": False,
        "cache_hit": True,
        "age_seconds": cached["age_seconds"]
    }


__all__ = [
    "RADIUS_SEARCH_FRESH_TTL",
    "RADIUS_SEARCH_STALE_TTL",
    "RADIUS_SEARCH_ENABLED",
    "get_cached_radius_search",
    "set_cached_radius_search",
    "invalidate_radius_cache",
    "get_radius_search_with_cache",
]
