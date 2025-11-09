from django.core.cache import cache
from django.test import TestCase, override_settings

from inventory.cache.fibers import (
    FIBER_LIST_CACHE_KEY,
    invalidate_fiber_cache,
)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
)
class FiberCacheTests(TestCase):
    def test_invalidate_fiber_cache_clears_cached_value(self):
        """Test that invalidate_fiber_cache clears the fiber list cache."""
        cache.set(FIBER_LIST_CACHE_KEY, {"sample": 1})
        self.assertIsNotNone(cache.get(FIBER_LIST_CACHE_KEY))

        invalidate_fiber_cache()

        self.assertIsNone(cache.get(FIBER_LIST_CACHE_KEY))
