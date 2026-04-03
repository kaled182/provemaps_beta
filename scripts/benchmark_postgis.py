#!/usr/bin/env python
"""
Performance benchmark for PostGIS spatial queries (Phase 10).

Compares performance of:
1. BBox filtering (path__bboverlaps) - O(log n) with GiST index
2. Full table scan (all segments) - O(n)

Target: BBox query <100ms for 10k+ segments with 10x+ speedup.

Usage:
    cd backend
    python scripts/benchmark_postgis.py
"""
from __future__ import annotations

import os
import sys
import time
from typing import List

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')

import django
django.setup()

from django.conf import settings
from django.contrib.gis.geos import LineString, Polygon

from inventory.models import FiberCable, Port, Site
from inventory.models_routes import Route, RouteSegment


def print_header(title: str) -> None:
    """Print section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def check_postgis_enabled() -> bool:
    """Verify PostGIS is configured."""
    db_engine = getattr(settings, 'DB_ENGINE', 'mysql')
    if db_engine != 'postgis':
        print("ERROR: DB_ENGINE != postgis")
        print(f"   Current: {db_engine}")
        print("\nConfigure PostGIS first:")
        print("  export DB_ENGINE=postgis")
        print("  docker-compose -f docker/docker-compose.postgis.yml up -d")
        return False
    
    print("OK: PostGIS backend detected")
    return True


def create_test_data(count: int = 1000) -> None:
    """
    Create test route segments with spatial data.
    
    Generates segments in a grid covering Brazil:
    - Lat: -35.0 to -5.0 (30 degrees)
    - Lng: -75.0 to -35.0 (40 degrees)
    """
    print_header(f"Creating {count} Test Segments")
    
    # Check if test data already exists
    existing_count = RouteSegment.objects.count()
    if existing_count >= count:
        print(f"OK: Test data already exists: {existing_count} segments")
        print("   (delete RouteSegment records to regenerate)")
        return
    
    # Create test site and route
    site, _ = Site.objects.get_or_create(
        display_name='Benchmark Test Site',
        defaults={
            'latitude': -15.7801,
            'longitude': -47.9292,
        },
    )
    
    device, _ = site.devices.get_or_create(
        name='BENCH-DEVICE-01',
        defaults={'zabbix_hostid': '999999'},
    )
    
    port_a, _ = Port.objects.get_or_create(
        device=device,
        name='eth0',
        defaults={'zabbix_item_key': 'net.if.in[eth0]'},
    )
    port_b, _ = Port.objects.get_or_create(
        device=device,
        name='eth1',
        defaults={'zabbix_item_key': 'net.if.in[eth1]'},
    )
    
    route, _ = Route.objects.get_or_create(
        name='Benchmark Route',
        defaults={
            'origin_port': port_a,
            'destination_port': port_b,
        },
    )
    
    # Generate segments in grid pattern
    print(f"Generating {count} segments...")
    
    segments: List[RouteSegment] = []
    lat_step = 30.0 / count
    lng_step = 40.0 / count
    
    for i in range(count):
        lat_base = -35.0 + (i * lat_step)
        lng_base = -75.0 + (i * lng_step)
        
        # Create short segment (~1km)
        segment = RouteSegment(
            route=route,
            order=i + 1,
            path=LineString(
                [
                    (lng_base, lat_base),
                    (lng_base + 0.01, lat_base + 0.01),
                ],
                srid=4326,
            ),
            length_km=1.0 + (i % 10) * 0.1,
        )
        segments.append(segment)
        
        # Bulk insert every 1000 segments
        if len(segments) >= 1000 or i == count - 1:
            RouteSegment.objects.bulk_create(segments)
            print(f"  Created {i + 1}/{count} segments...")
            segments = []
    
    print(f"OK: Created {count} test segments")


def benchmark_bbox_query(iterations: int = 5) -> float:
    """
    Benchmark BBox spatial query.
    
    Query Brasilia region: (-48.0, -16.0, -47.5, -15.5)
    
    Returns:
        Average query time in milliseconds
    """
    bbox = Polygon.from_bbox((-48.0, -16.0, -47.5, -15.5))
    bbox.srid = 4326
    
    times: List[float] = []
    result_count = 0
    
    for i in range(iterations):
        start = time.time()
        results = list(RouteSegment.objects.filter(path__bboverlaps=bbox))
        duration = (time.time() - start) * 1000
        times.append(duration)
        result_count = len(results)
    
    avg_time = sum(times) / len(times)
    
    print("\nBBox Query Performance:")
    print(f"   Results:  {result_count} segments")
    print(f"   Avg time: {avg_time:.2f}ms ({iterations} runs)")
    print(f"   Min/Max:  {min(times):.2f}ms / {max(times):.2f}ms")
    
    return avg_time


def benchmark_full_scan(iterations: int = 5) -> float:
    """
    Benchmark full table scan (no spatial filtering).
    
    Returns:
        Average query time in milliseconds
    """
    times: List[float] = []
    result_count = 0
    
    for i in range(iterations):
        start = time.time()
        results = list(RouteSegment.objects.all())
        duration = (time.time() - start) * 1000
        times.append(duration)
        result_count = len(results)
    
    avg_time = sum(times) / len(times)
    
    print("\nFull Scan Performance:")
    print(f"   Results:  {result_count} segments")
    print(f"   Avg time: {avg_time:.2f}ms ({iterations} runs)")
    print(f"   Min/Max:  {min(times):.2f}ms / {max(times):.2f}ms")
    
    return avg_time


def verify_spatial_index() -> None:
    """Check if GiST index exists and is being used."""
    from django.db import connection
    
    print_header("Spatial Index Verification")
    
    with connection.cursor() as cursor:
        # Check if index exists
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'inventory_routesegment'
            AND indexdef LIKE '%USING gist%'
        """)
        
        indexes = cursor.fetchall()
        
        if indexes:
            print("OK: GiST index found:")
            for idx_name, idx_def in indexes:
                print(f"   {idx_name}")
        else:
            print("WARN: No GiST index found!")
            print("   Run: python manage.py migrate inventory 0012")
        
        # Check query plan
        cursor.execute("""
            EXPLAIN
            SELECT * FROM inventory_routesegment
            WHERE path && ST_MakeEnvelope(-48, -16, -47.5, -15.5, 4326)
        """)
        
        plan = cursor.fetchall()

        print("\nQuery Plan:")
        for line in plan:
            print(f"   {line[0]}")
            if 'Index Scan' in line[0]:
                print("   OK: index is being used")


def main() -> None:
    """Run performance benchmark."""
    print_header("PostGIS Performance Benchmark")
    
    if not check_postgis_enabled():
        sys.exit(1)
    
    # Create test data
    create_test_data(count=1000)
    
    # Verify index
    verify_spatial_index()
    
    # Run benchmarks
    print_header("Performance Tests")
    
    bbox_time = benchmark_bbox_query(iterations=5)
    full_scan_time = benchmark_full_scan(iterations=5)
    
    # Calculate speedup
    speedup = full_scan_time / bbox_time if bbox_time > 0 else 0
    
    print_header("Results Summary")
    print(f"BBox Query:   {bbox_time:.2f}ms")
    print(f"Full Scan:    {full_scan_time:.2f}ms")
    print(f"Speedup:      {speedup:.1f}x faster")
    
    # Check targets
    print("\nPerformance Targets:")
    
    bbox_pass = bbox_time < 100
    speedup_pass = speedup >= 10
    
    print(
        f"   BBox <100ms:   {'PASS' if bbox_pass else 'FAIL'}"
    )
    print(
        f"   Speedup >10x:  {'PASS' if speedup_pass else 'SLOW'}"
    )
    
    if bbox_pass and speedup_pass:
        print("\nAll targets met.")
        sys.exit(0)
    else:
        print(
            "\nSome targets not met (may need more data or index tuning)"
        )
        sys.exit(0)  # Non-fatal - just informational


if __name__ == '__main__':
    main()
