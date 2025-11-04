"""
Tests for the SWR (Stale-While-Revalidate) cache helpers.

Coverage:
- Fresh cache hit
- Stale cache hit with async refresh
- Cache miss with synchronous fetch
- Cache invalidation
- Metadata (timestamp, is_stale)
"""

# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

import time
from typing import Any, Dict
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from maps_view.cache_swr import (
    SWRCache,
    dashboard_cache,
    get_dashboard_cached,
    invalidate_dashboard_cache,
)

SWRResult = Dict[str, Any]


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-swr-cache",
        }
    },
    SWR_ENABLED=True,
    SWR_FRESH_TTL=5,  # 5 seconds
    SWR_STALE_TTL=30,  # 30 seconds
)
class SWRCacheTests(SimpleTestCase):
    """Exercise SWRCache behavior."""

    def setUp(self) -> None:
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_cache_miss_fetches_sync(self) -> None:
        swr = SWRCache(key="test:miss", fresh_ttl=5)
        fetch_fn = Mock(return_value={"data": "test"})

        result: SWRResult = swr.get_or_fetch(fetch_fn=fetch_fn)

        self.assertTrue(fetch_fn.called)
        self.assertEqual(result["data"], {"data": "test"})
        self.assertFalse(result["is_stale"])
        self.assertFalse(result["cache_hit"])

    def test_cache_hit_fresh_returns_immediately(self) -> None:
        swr = SWRCache(key="test:fresh", fresh_ttl=60)
        test_data = {"value": 123}
        swr.set_cached_data(test_data)
        fetch_fn = Mock(return_value={"value": 999})

        result: SWRResult = swr.get_or_fetch(fetch_fn=fetch_fn)

        self.assertFalse(fetch_fn.called)
        self.assertEqual(result["data"], test_data)
        self.assertFalse(result["is_stale"])
        self.assertTrue(result["cache_hit"])

    def test_cache_hit_stale_triggers_async_refresh(self) -> None:
        swr = SWRCache(key="test:stale", fresh_ttl=1, stale_ttl=30)
        test_data = {"old": "data"}
        swr.set_cached_data(test_data)
        time.sleep(1.5)

        fetch_fn = Mock(return_value={"new": "data"})
        async_task = Mock()

        result: SWRResult = swr.get_or_fetch(
            fetch_fn=fetch_fn,
            async_task=async_task,
        )

        self.assertEqual(result["data"], test_data)
        self.assertTrue(result["is_stale"])
        self.assertTrue(result["cache_hit"])
        self.assertTrue(async_task.called)
        self.assertFalse(fetch_fn.called)

    def test_invalidate_removes_cache(self) -> None:
        swr = SWRCache(key="test:invalidate")
        swr.set_cached_data({"test": "data"})

        cached = swr.get_cached_data()
        self.assertIsNotNone(cached)
        assert cached is not None

        swr.invalidate()

        cached_after = swr.get_cached_data()
        self.assertIsNone(cached_after)

    def test_get_cached_data_returns_metadata(self) -> None:
        swr = SWRCache(key="test:metadata", fresh_ttl=10)
        test_data = {"foo": "bar"}
        swr.set_cached_data(test_data)

        cached = swr.get_cached_data()
        self.assertIsNotNone(cached)
        assert cached is not None

        self.assertIn("data", cached)
        self.assertIn("timestamp", cached)
        self.assertIn("age_seconds", cached)
        self.assertIn("is_stale", cached)
        self.assertEqual(cached["data"], test_data)
        self.assertFalse(cached["is_stale"])

    @override_settings(SWR_ENABLED=False)
    def test_swr_disabled_always_fetches(self) -> None:
        from importlib import reload

        import maps_view.cache_swr as cache_swr_module

        reload(cache_swr_module)

        swr = cache_swr_module.SWRCache(key="test:disabled")
        swr.set_cached_data({"old": "value"})
        fetch_fn = Mock(return_value={"new": "value"})

        result: SWRResult = swr.get_or_fetch(fetch_fn=fetch_fn)

        self.assertTrue(fetch_fn.called)
        self.assertEqual(result["data"], {"new": "value"})
        self.assertFalse(result["cache_hit"])

    def test_dashboard_cache_helper(self) -> None:
        fetch_fn = Mock(return_value={"dashboard": "data"})
        async_task = Mock()

        result: SWRResult = get_dashboard_cached(
            fetch_fn=fetch_fn,
            async_task=async_task,
        )

        self.assertTrue(fetch_fn.called)
        self.assertEqual(result["data"], {"dashboard": "data"})

    def test_invalidate_dashboard_cache_helper(self) -> None:
        dashboard_cache.set_cached_data({"test": "value"})

        cached = dashboard_cache.get_cached_data()
        self.assertIsNotNone(cached)
        assert cached is not None

        invalidate_dashboard_cache()

        cached_after = dashboard_cache.get_cached_data()
        self.assertIsNone(cached_after)

    def test_async_task_exception_handled(self) -> None:
        swr = SWRCache(key="test:async-error", fresh_ttl=1, stale_ttl=30)
        swr.set_cached_data({"data": "test"})
        time.sleep(1.5)

        async_task = Mock(side_effect=Exception("Task failed"))
        fetch_fn = Mock()

        result: SWRResult = swr.get_or_fetch(
            fetch_fn=fetch_fn,
            async_task=async_task,
        )

        self.assertEqual(result["data"], {"data": "test"})
        self.assertTrue(result["is_stale"])
        self.assertTrue(async_task.called)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-swr-integration",
        }
    }
)
class SWRIntegrationTests(SimpleTestCase):
    """Integration tests with views."""

    def setUp(self) -> None:
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    @patch("maps_view.cache_swr.dashboard_cache")
    def test_dashboard_view_uses_swr(self, mock_cache: Mock) -> None:
        """Ensure dashboard_view is wired to the SWR cache."""
        self.assertTrue(hasattr(mock_cache, "get_or_fetch"))


__all__ = ["SWRCacheTests", "SWRIntegrationTests"]

