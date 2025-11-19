#!/usr/bin/env python
"""Smoke test for Phase 7 spatial radius cache."""
from inventory.cache.radius_search import get_radius_search_with_cache

print('=== Phase 1 (10%) Cache Smoke Test ===\n')

# Test coordinates: Brasília center
lat, lng, radius = -15.7942, -47.8825, 10.0

print(f'Query: lat={lat}, lng={lng}, radius={radius}km\n')

# First request (cache MISS expected)
print('--- Request 1 (cache MISS) ---')
result1 = get_radius_search_with_cache(lat, lng, radius)
print(f'Sites found: {len(result1["sites"])}')
print(f'Cached: {result1["cached"]}')
print(f'Fresh: {result1.get("fresh", "N/A")}')
print(f'Stale: {result1.get("stale", False)}')

# Second request (cache HIT expected)
print('\n--- Request 2 (cache HIT - fresh) ---')
result2 = get_radius_search_with_cache(lat, lng, radius)
print(f'Sites found: {len(result2["sites"])}')
print(f'Cached: {result2["cached"]}')
print(f'Fresh: {result2.get("fresh", "N/A")}')
print(f'Stale: {result2.get("stale", False)}')

if result2["cached"] and result2.get("fresh"):
    print('\n✅ Cache working correctly!')
else:
    print('\n❌ Cache not working as expected')
