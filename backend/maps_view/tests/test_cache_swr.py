"""Tests for maps_view.cache_swr — SWRCache and helper functions."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch, call

import pytest
from django.test import TestCase, override_settings


class SWRCacheGetCachedDataTests(TestCase):
    """Tests for SWRCache.get_cached_data()."""

    def setUp(self):
        from maps_view.cache_swr import SWRCache
        self.swr = SWRCache(key="test:key", fresh_ttl=30, stale_ttl=60)

    def test_returns_none_when_cache_empty(self):
        with patch("maps_view.cache_swr.cache") as mock_cache:
            mock_cache.get.return_value = None
            result = self.swr.get_cached_data()
        self.assertIsNone(result)

    def test_returns_fresh_data(self):
        data = {"hosts": []}
        with patch("maps_view.cache_swr.cache") as mock_cache, \
             patch("maps_view.cache_swr.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            mock_time.time.return_value = 100.0

            def cache_get(key, default=None):
                if key == "test:key":
                    return data
                if "monotonic" in key:
                    return 95.0  # 5s ago — fresh (ttl=30)
                if "timestamp" in key:
                    return 95.0
                return default

            mock_cache.get.side_effect = cache_get
            result = self.swr.get_cached_data()

        self.assertIsNotNone(result)
        self.assertFalse(result["is_stale"])
        self.assertEqual(result["data"], data)

    def test_returns_stale_data(self):
        data = {"hosts": []}
        with patch("maps_view.cache_swr.cache") as mock_cache, \
             patch("maps_view.cache_swr.time") as mock_time:
            mock_time.monotonic.return_value = 200.0
            mock_time.time.return_value = 200.0

            def cache_get(key, default=None):
                if key == "test:key":
                    return data
                if "monotonic" in key:
                    return 160.0  # 40s ago — stale (ttl=30)
                if "timestamp" in key:
                    return 160.0
                return default

            mock_cache.get.side_effect = cache_get
            result = self.swr.get_cached_data()

        self.assertIsNotNone(result)
        self.assertTrue(result["is_stale"])

    def test_returns_none_on_cache_exception(self):
        with patch("maps_view.cache_swr.cache") as mock_cache:
            mock_cache.get.side_effect = Exception("Redis down")
            result = self.swr.get_cached_data()
        self.assertIsNone(result)

    def test_clamps_negative_age(self):
        data = {"hosts": []}
        with patch("maps_view.cache_swr.cache") as mock_cache, \
             patch("maps_view.cache_swr.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            mock_time.time.return_value = 100.0

            def cache_get(key, default=None):
                if key == "test:key":
                    return data
                if "monotonic" in key:
                    return 110.0  # future — negative age
                if "timestamp" in key:
                    return 100.0
                return default

            mock_cache.get.side_effect = cache_get
            result = self.swr.get_cached_data()

        self.assertIsNotNone(result)
        self.assertEqual(result["age_seconds"], 0)

    def test_uses_wall_time_when_no_monotonic(self):
        data = {"hosts": []}
        with patch("maps_view.cache_swr.cache") as mock_cache, \
             patch("maps_view.cache_swr.time") as mock_time:
            mock_time.time.return_value = 200.0
            mock_time.monotonic.return_value = 200.0

            def cache_get(key, default=None):
                if key == "test:key":
                    return data
                if "monotonic" in key:
                    return None  # no monotonic key
                if "timestamp" in key:
                    return 160.0
                return default

            mock_cache.get.side_effect = cache_get
            mock_cache.set.return_value = True
            result = self.swr.get_cached_data()

        self.assertIsNotNone(result)


class SWRCacheSetCachedDataTests(TestCase):
    def setUp(self):
        from maps_view.cache_swr import SWRCache
        self.swr = SWRCache(key="test:key", fresh_ttl=30, stale_ttl=60)

    def test_sets_data_and_timestamps(self):
        with patch("maps_view.cache_swr.cache") as mock_cache:
            mock_cache.set.return_value = True
            self.swr.set_cached_data({"foo": "bar"})

        self.assertEqual(mock_cache.set.call_count, 3)

    def test_silently_handles_exception(self):
        with patch("maps_view.cache_swr.cache") as mock_cache:
            mock_cache.set.side_effect = Exception("Redis down")
            # Should not raise
            self.swr.set_cached_data({"foo": "bar"})


class SWRCacheInvalidateTests(TestCase):
    def setUp(self):
        from maps_view.cache_swr import SWRCache
        self.swr = SWRCache(key="test:key")

    def test_deletes_all_keys(self):
        with patch("maps_view.cache_swr.cache") as mock_cache:
            mock_cache.delete.return_value = True
            self.swr.invalidate()

        self.assertEqual(mock_cache.delete.call_count, 3)

    def test_silently_handles_exception(self):
        with patch("maps_view.cache_swr.cache") as mock_cache:
            mock_cache.delete.side_effect = Exception("Redis down")
            # Should not raise
            self.swr.invalidate()


class SWRCacheGetOrFetchTests(TestCase):
    def setUp(self):
        from maps_view.cache_swr import SWRCache
        self.swr = SWRCache(key="test:key", fresh_ttl=30, stale_ttl=60)

    def test_swr_disabled_fetches_directly(self):
        fetch_fn = MagicMock(return_value={"data": "fresh"})
        from maps_view.cache_swr import SWRCache
        swr = SWRCache(key="test:disabled")
        # Patch the module-level constant directly — override_settings won't
        # work because SWR_ENABLED is captured at import time.
        with patch("maps_view.cache_swr.SWR_ENABLED", False):
            result = swr.get_or_fetch(fetch_fn)
        fetch_fn.assert_called_once()
        self.assertFalse(result["is_stale"])

    def test_empty_cache_fetches_sync_and_stores(self):
        fetch_fn = MagicMock(return_value={"data": "synced"})
        with patch("maps_view.cache_swr.SWR_ENABLED", True), \
             patch.object(self.swr, "get_cached_data", return_value=None), \
             patch.object(self.swr, "set_cached_data") as mock_set:
            result = self.swr.get_or_fetch(fetch_fn)
        fetch_fn.assert_called_once()
        mock_set.assert_called_once()
        self.assertFalse(result["cache_hit"])

    def test_fresh_cache_returns_without_fetching(self):
        cached = {
            "data": {"cached": True},
            "timestamp": time.time(),
            "age_seconds": 5,
            "is_stale": False,
        }
        fetch_fn = MagicMock()
        with patch("maps_view.cache_swr.SWR_ENABLED", True), \
             patch.object(self.swr, "get_cached_data", return_value=cached):
            result = self.swr.get_or_fetch(fetch_fn)
        fetch_fn.assert_not_called()
        self.assertTrue(result["cache_hit"])

    def test_stale_cache_triggers_async_task(self):
        cached = {
            "data": {"stale": True},
            "timestamp": time.time() - 60,
            "age_seconds": 60,
            "is_stale": True,
        }
        async_task = MagicMock()
        fetch_fn = MagicMock()
        with patch("maps_view.cache_swr.SWR_ENABLED", True), \
             patch.object(self.swr, "get_cached_data", return_value=cached):
            result = self.swr.get_or_fetch(fetch_fn, async_task=async_task)
        async_task.assert_called_once()
        fetch_fn.assert_not_called()
        self.assertTrue(result["cache_hit"])

    def test_stale_cache_no_async_task(self):
        cached = {
            "data": {"stale": True},
            "timestamp": time.time() - 60,
            "age_seconds": 60,
            "is_stale": True,
        }
        fetch_fn = MagicMock()
        with patch("maps_view.cache_swr.SWR_ENABLED", True), \
             patch.object(self.swr, "get_cached_data", return_value=cached):
            result = self.swr.get_or_fetch(fetch_fn, async_task=None)
        fetch_fn.assert_not_called()
        self.assertTrue(result["cache_hit"])

    def test_stale_async_task_exception_does_not_propagate(self):
        cached = {
            "data": {"stale": True},
            "timestamp": time.time() - 60,
            "age_seconds": 60,
            "is_stale": True,
        }
        async_task = MagicMock(side_effect=Exception("Celery down"))
        fetch_fn = MagicMock()
        with patch("maps_view.cache_swr.SWR_ENABLED", True), \
             patch.object(self.swr, "get_cached_data", return_value=cached):
            result = self.swr.get_or_fetch(fetch_fn, async_task=async_task)
        # Still returns stale data — exception must not propagate
        self.assertTrue(result["cache_hit"])


class DashboardCacheHelpersTests(TestCase):
    def test_get_dashboard_cached_delegates(self):
        from maps_view.cache_swr import get_dashboard_cached
        fetch_fn = MagicMock(return_value={"hosts": []})
        with patch("maps_view.cache_swr.dashboard_cache") as mock_swr:
            mock_swr.get_or_fetch.return_value = {
                "data": {"hosts": []},
                "is_stale": False,
                "cache_hit": False,
                "timestamp": time.time(),
            }
            result = get_dashboard_cached(fetch_fn)
        mock_swr.get_or_fetch.assert_called_once()

    def test_invalidate_dashboard_cache_delegates(self):
        from maps_view.cache_swr import invalidate_dashboard_cache
        with patch("maps_view.cache_swr.dashboard_cache") as mock_swr:
            invalidate_dashboard_cache()
        mock_swr.invalidate.assert_called_once()
