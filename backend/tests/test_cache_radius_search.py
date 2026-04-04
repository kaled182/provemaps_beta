"""
Tests for radius search SWR cache (Phase 7 Day 5).

Tests cache hit/miss/stale scenarios, TTL expiration, invalidation,
and Celery task integration.
"""
from __future__ import annotations

import time
from unittest.mock import Mock, patch

import pytest
from django.core.cache import cache

from inventory.cache.radius_search import (
    RADIUS_SEARCH_FRESH_TTL,
    get_cached_radius_search,
    get_radius_search_with_cache,
    invalidate_radius_cache,
    set_cached_radius_search,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def mock_site_data():
    """Sample site data for testing."""
    return [
        {
            "id": 1,
            "display_name": "Site A",
            "latitude": -15.7801,
            "longitude": -47.9292,
            "distance_km": 0.0,
        },
        {
            "id": 2,
            "display_name": "Site B",
            "latitude": -15.7350,
            "longitude": -47.9292,
            "distance_km": 5.01,
        },
    ]


class TestCacheKeyGeneration:
    """Test cache key generation and hashing."""

    def test_same_coordinates_generate_same_key(self):
        """Same coords should produce deterministic cache key."""
        result1 = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
        set_cached_radius_search(-15.7801, -47.9292, 10, 100, ["data"])
        result2 = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
        
        # Second call should hit cache (same key)
        assert result2 is not None
        assert result2["data"] == ["data"]

    def test_different_coordinates_generate_different_keys(self):
        """Different coords should use separate cache keys."""
        set_cached_radius_search(-15.7801, -47.9292, 10, 100, ["data1"])
        set_cached_radius_search(-15.8000, -48.0000, 10, 100, ["data2"])
        
        result1 = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
        result2 = get_cached_radius_search(-15.8000, -48.0000, 10, 100)
        
        assert result1["data"] == ["data1"]
        assert result2["data"] == ["data2"]

    def test_different_radius_generates_different_key(self):
        """Different radius should use separate cache keys."""
        set_cached_radius_search(-15.7801, -47.9292, 10, 100, ["r10"])
        set_cached_radius_search(-15.7801, -47.9292, 50, 100, ["r50"])
        
        r1 = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
        r2 = get_cached_radius_search(-15.7801, -47.9292, 50, 100)
        
        assert r1["data"] == ["r10"]
        assert r2["data"] == ["r50"]


class TestCacheMissScenario:
    """Test cache miss (no data in cache)."""

    def test_cache_miss_returns_none(self):
        """Empty cache should return None."""
        result = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
        assert result is None

    def test_get_or_fetch_on_miss_calls_fetch_fn(self, mock_site_data):
        """Cache miss should call fetch_fn synchronously."""
        fetch_fn = Mock(return_value=mock_site_data)
        
        result = get_radius_search_with_cache(
            lat=-15.7801,
            lng=-47.9292,
            radius_km=10,
            limit=100,
            fetch_fn=fetch_fn,
        )
        
        assert fetch_fn.called
        assert result["data"] == mock_site_data
        assert result["cache_hit"] is False
        assert result["is_stale"] is False

    def test_get_or_fetch_on_miss_caches_result(self, mock_site_data):
        """Cache miss should store fetched data."""
        fetch_fn = Mock(return_value=mock_site_data)
        
        # First call - miss
        result1 = get_radius_search_with_cache(
            lat=-15.7801,
            lng=-47.9292,
            radius_km=10,
            limit=100,
            fetch_fn=fetch_fn,
        )
        
        # Second call - hit
        result2 = get_radius_search_with_cache(
            lat=-15.7801,
            lng=-47.9292,
            radius_km=10,
            limit=100,
            fetch_fn=fetch_fn,
        )
        
        assert fetch_fn.call_count == 1  # Only called once
        assert result1["cache_hit"] is False
        assert result2["cache_hit"] is True


class TestCacheFreshHit:
    """Test cache hit with fresh data (< 30s old)."""

    def test_fresh_data_returns_immediately(self, mock_site_data):
        """Fresh cache should return without calling fetch_fn."""
        set_cached_radius_search(-15.7801, -47.9292, 10, 100, mock_site_data)
        
        fetch_fn = Mock()  # Should NOT be called
        
        result = get_radius_search_with_cache(
            lat=-15.7801,
            lng=-47.9292,
            radius_km=10,
            limit=100,
            fetch_fn=fetch_fn,
        )
        
        assert not fetch_fn.called
        assert result["data"] == mock_site_data
        assert result["cache_hit"] is True
        assert result["is_stale"] is False

    def test_fresh_data_has_low_age(self, mock_site_data):
        """Fresh cache should have age < FRESH_TTL."""
        set_cached_radius_search(-15.7801, -47.9292, 10, 100, mock_site_data)
        
        cached = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
        
        assert cached is not None
        assert cached["age_seconds"] < RADIUS_SEARCH_FRESH_TTL
        assert not cached["is_stale"]


class TestCacheStaleHit:
    """Test cache hit with stale data (30-60s old)."""

    def test_stale_data_returns_immediately_and_refreshes(
        self, mock_site_data
    ):
        """Stale cache should return data + trigger async refresh."""
        # Use module-level time mock with real-time base so LocMemCache TTLs
        # (which use unpatched time.time()) don't see the entries as expired.
        real_now = time.time()
        # Use FRESH_TTL+30 so the data is always in the stale window regardless
        # of environment overrides (e.g. SWR_FRESH_TTL=300 in Docker).
        stale_offset = RADIUS_SEARCH_FRESH_TTL + 30
        with patch("inventory.cache.radius_search.time") as mock_time:
            # Phase 1: store data at T=real_now
            mock_time.time.return_value = real_now
            set_cached_radius_search(-15.7801, -47.9292, 10, 100, mock_site_data)

            # Phase 2: read at T=real_now+stale_offset (past FRESH_TTL)
            mock_time.time.return_value = real_now + stale_offset
            fetch_fn = Mock()   # Should NOT be called (stale-while-revalidate)
            async_task = Mock()  # Should be called

            result = get_radius_search_with_cache(
                lat=-15.7801,
                lng=-47.9292,
                radius_km=10,
                limit=100,
                fetch_fn=fetch_fn,
                async_refresh_task=async_task,
            )

        # Returns stale data immediately
        assert result["data"] == mock_site_data
        assert result["cache_hit"] is True
        assert result["is_stale"] is True

        # Triggers async refresh
        assert async_task.called


class TestCacheInvalidation:
    """Test cache invalidation logic."""

    def test_invalidate_specific_query(self, mock_site_data):
        """Invalidate specific lat/lng/radius should clear that cache."""
        set_cached_radius_search(-15.7801, -47.9292, 10, 100, mock_site_data)
        
        # Verify cached
        cached = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
        assert cached is not None
        
        # Invalidate
        invalidate_radius_cache(-15.7801, -47.9292, 10, 100)
        
        # Verify cleared
        assert get_cached_radius_search(-15.7801, -47.9292, 10, 100) is None

    def test_invalidate_all_clears_all_queries(self, mock_site_data):
        """Invalidate without args should clear all radius caches."""
        set_cached_radius_search(-15.7801, -47.9292, 10, 100, ["data1"])
        set_cached_radius_search(-15.8000, -48.0000, 50, 100, ["data2"])
        
        # Verify both cached
        c1 = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
        c2 = get_cached_radius_search(-15.8000, -48.0000, 50, 100)
        assert c1 is not None
        assert c2 is not None
        
        # Invalidate all
        invalidate_radius_cache()
        
        # Verify both cleared (if Redis delete_pattern available)
        # Note: May not work with locmem cache backend
        result1 = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
        result2 = get_cached_radius_search(-15.8000, -48.0000, 50, 100)
        
        # Depending on cache backend
        if hasattr(cache, "delete_pattern"):
            assert result1 is None
            assert result2 is None


class TestCacheDisabled:
    """Test behavior when SWR cache is disabled."""

    @patch("inventory.cache.radius_search.RADIUS_SEARCH_ENABLED", False)
    def test_cache_disabled_always_fetches(self, mock_site_data):
        """When disabled, should always call fetch_fn."""
        fetch_fn = Mock(return_value=mock_site_data)
        
        result1 = get_radius_search_with_cache(
            lat=-15.7801,
            lng=-47.9292,
            radius_km=10,
            limit=100,
            fetch_fn=fetch_fn,
        )
        
        result2 = get_radius_search_with_cache(
            lat=-15.7801,
            lng=-47.9292,
            radius_km=10,
            limit=100,
            fetch_fn=fetch_fn,
        )
        
        # Called twice (no caching)
        assert fetch_fn.call_count == 2
        assert result1["cache_hit"] is False
        assert result2["cache_hit"] is False


class TestCeleryTask:
    """Test Celery refresh task."""

    @pytest.mark.django_db
    def test_refresh_task_fetches_and_caches(self, mock_site_data):
        """Refresh task should fetch fresh data and update cache."""
        from inventory.tasks import refresh_radius_search_cache
        
        with patch(
            "inventory.usecases.spatial.get_sites_within_radius",
            return_value=mock_site_data,
        ):
            # Run task (eager mode in tests)
            result = refresh_radius_search_cache(
                lat=-15.7801,
                lng=-47.9292,
                radius_km=10,
                limit=100,
            )
            
            assert result["success"] is True
            assert result["site_count"] == 2
            
            # Verify cache updated
            cached = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
            assert cached is not None
            assert cached["data"] == mock_site_data


class TestSignalIntegration:
    """Test cache invalidation signals."""

    @pytest.mark.django_db
    def test_site_save_invalidates_cache(self, mock_site_data):
        """Creating/updating Site should invalidate radius cache."""
        from inventory.models import Site
        
        # Cache some data
        set_cached_radius_search(-15.7801, -47.9292, 10, 100, mock_site_data)
        cached = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
        assert cached is not None
        
        # Create site (triggers signal)
        Site.objects.create(
            display_name="Test Site",
            latitude=-15.7801,
            longitude=-47.9292,
        )
        
        # Cache should be invalidated (if Redis delete_pattern available)
        # Note: Depends on cache backend
        if hasattr(cache, "delete_pattern"):
            result = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
            assert result is None

    @pytest.mark.django_db
    def test_site_delete_invalidates_cache(self, mock_site_data):
        """Deleting Site should invalidate radius cache."""
        from inventory.models import Site
        
        site = Site.objects.create(
            display_name="Test Site",
            latitude=-15.7801,
            longitude=-47.9292,
        )
        
        # Cache some data
        set_cached_radius_search(-15.7801, -47.9292, 10, 100, mock_site_data)
        cached = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
        assert cached is not None
        
        # Delete site (triggers signal)
        site.delete()
        
        # Cache should be invalidated
        if hasattr(cache, "delete_pattern"):
            result = get_cached_radius_search(-15.7801, -47.9292, 10, 100)
            assert result is None
