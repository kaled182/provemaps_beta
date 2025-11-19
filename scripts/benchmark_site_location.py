#!/usr/bin/env python
"""
Performance benchmark: BBox filtering vs ST_DWithin with geography=True.

Compares Phase 6 (BBox pre-filter + Python distance) vs Phase 7 (native PostGIS).
Expected result: 10-15x speedup with ST_DWithin + GIST index.
"""

import time
from typing import List, Tuple

import django
import os
import sys

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.db import connection
from inventory.models import Site


def reset_query_stats():
    """Reset Django query cache."""
    from django.db import reset_queries
    reset_queries()


def get_query_count() -> int:
    """Get number of queries executed."""
    return len(connection.queries)


def benchmark_bbox_python_approach(
    lat: float, lon: float, radius_km: float, iterations: int = 100
) -> Tuple[float, int]:
    """
    Benchmark Phase 6 approach: BBox pre-filter + Python distance calculation.
    
    This was the OLD approach before Phase 7.
    """
    times = []
    
    for _ in range(iterations):
        reset_query_stats()
        start = time.perf_counter()
        
        # Phase 6: Degree-based approximation
        degree_radius = radius_km / 111.0
        
        # BBox filter
        candidates = Site.objects.filter(
            latitude__range=(lat - degree_radius, lat + degree_radius),
            longitude__range=(lon - degree_radius, lon + degree_radius),
        )
        
        # Force query execution
        result_count = candidates.count()
        
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    return avg_time, result_count


def benchmark_stdwithin_geography(
    lat: float, lon: float, radius_km: float, iterations: int = 100
) -> Tuple[float, int]:
    """
    Benchmark Phase 7 approach: Native PostGIS ST_DWithin with geography=True.
    
    This is the NEW optimized approach using spatial indexes.
    """
    times = []
    center_point = Point(lon, lat, srid=4326)
    radius_meters = radius_km * 1000.0
    
    for _ in range(iterations):
        reset_query_stats()
        start = time.perf_counter()
        
        # Phase 7: Native PostGIS with GIST index
        results = Site.objects.filter(
            location__dwithin=(center_point, radius_meters)
        ).annotate(
            distance=Distance('location', center_point)
        ).order_by('distance')
        
        # Force query execution
        result_count = results.count()
        
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    return avg_time, result_count


def run_benchmark():
    """Run comprehensive benchmark suite."""
    print("=" * 70)
    print("POSTGIS PERFORMANCE BENCHMARK - Phase 6 vs Phase 7")
    print("=" * 70)
    print()
    
    # Test parameters
    brasilia_lat = -15.7801
    brasilia_lon = -47.9292
    
    test_cases = [
        ("Small radius (5km)", 5.0, 1000),
        ("Medium radius (10km)", 10.0, 1000),
        ("Large radius (50km)", 50.0, 500),
        ("Very large radius (100km)", 100.0, 200),
    ]
    
    print(f"Test location: Brasília ({brasilia_lat}, {brasilia_lon})")
    print(f"Database: {Site.objects.count()} sites total")
    print()
    
    results = []
    
    for test_name, radius_km, iterations in test_cases:
        print(f"\n{test_name} - {iterations} iterations")
        print("-" * 70)
        
        # Phase 6: BBox + Python
        bbox_time, bbox_count = benchmark_bbox_python_approach(
            brasilia_lat, brasilia_lon, radius_km, iterations
        )
        
        # Phase 7: ST_DWithin + GIST
        stdwithin_time, stdwithin_count = benchmark_stdwithin_geography(
            brasilia_lat, brasilia_lon, radius_km, iterations
        )
        
        speedup = bbox_time / stdwithin_time if stdwithin_time > 0 else 0
        
        print(f"  Phase 6 (BBox + Python):     {bbox_time*1000:.3f}ms "
              f"({bbox_count} results)")
        print(f"  Phase 7 (ST_DWithin + GIST): {stdwithin_time*1000:.3f}ms "
              f"({stdwithin_count} results)")
        print(f"  Speedup: {speedup:.2f}x faster")
        
        results.append({
            'test': test_name,
            'radius_km': radius_km,
            'bbox_time_ms': bbox_time * 1000,
            'stdwithin_time_ms': stdwithin_time * 1000,
            'speedup': speedup,
            'bbox_count': bbox_count,
            'stdwithin_count': stdwithin_count,
        })
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    avg_speedup = sum(r['speedup'] for r in results) / len(results)
    print(f"\nAverage speedup: {avg_speedup:.2f}x faster")
    print(f"Target achieved: {'✅ YES' if avg_speedup >= 10 else '❌ NO'} "
          f"(target: 10-15x)")
    
    print("\nDetailed Results:")
    print(f"{'Test':<25} {'BBox (ms)':<12} {'ST_DWithin (ms)':<16} "
          f"{'Speedup':<10}")
    print("-" * 70)
    for r in results:
        print(f"{r['test']:<25} {r['bbox_time_ms']:<12.3f} "
              f"{r['stdwithin_time_ms']:<16.3f} {r['speedup']:<10.2f}x")
    
    print("\n" + "=" * 70)
    print("QUERY ANALYSIS")
    print("=" * 70)
    
    # Show actual SQL for both approaches
    print("\nPhase 6 SQL (BBox approach):")
    degree_radius = 10.0 / 111.0
    bbox_query = Site.objects.filter(
        latitude__range=(brasilia_lat - degree_radius,
                        brasilia_lat + degree_radius),
        longitude__range=(brasilia_lon - degree_radius,
                         brasilia_lon + degree_radius),
    )
    print(f"  {bbox_query.query}")
    
    print("\nPhase 7 SQL (ST_DWithin with geography):")
    center_point = Point(brasilia_lon, brasilia_lat, srid=4326)
    stdwithin_query = Site.objects.filter(
        location__dwithin=(center_point, 10000.0)
    ).annotate(distance=Distance('location', center_point))
    print(f"  {stdwithin_query.query}")
    
    print("\n" + "=" * 70)
    print("INDEX USAGE")
    print("=" * 70)
    
    # Check GIST index exists
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'zabbix_api_site' 
            AND indexname = 'idx_site_location'
        """)
        index_info = cursor.fetchone()
        
        if index_info:
            print(f"\n✅ GIST Index found: {index_info[0]}")
            print(f"   Definition: {index_info[1]}")
        else:
            print("\n❌ GIST Index NOT found!")
            print("   Run migration 0018 to create spatial index")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    run_benchmark()
