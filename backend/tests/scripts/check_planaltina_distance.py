#!/usr/bin/env python
"""Debug script to check actual distance between Brasilia and Planaltina."""

import django
import os
import sys

# Setup Django
sys.path.insert(0, '/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from django.contrib.gis.geos import Point
from django.db import connection

# Coordinates from test fixture
brasilia_center = Point(-47.9292, -15.7801, srid=4326)
planaltina = Point(-47.6144, -15.4523, srid=4326)

print("=" * 60)
print("DISTANCE CALCULATION - Brasília Center to Planaltina")
print("=" * 60)
print(f"Brasília Center: {brasilia_center}")
print(f"Planaltina: {planaltina}")
print()

# Method 1: ST_Distance with geography cast
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT ST_Distance(
            ST_GeogFromWKB(ST_AsEWKB(%s::geometry)),
            ST_GeogFromWKB(ST_AsEWKB(%s::geometry))
        )
    """, [brasilia_center.ewkb, planaltina.ewkb])
    distance_meters = cursor.fetchone()[0]
    distance_km = distance_meters / 1000.0
    
    print(f"Method 1 (ST_Distance with geography):")
    print(f"  Distance: {distance_meters:.2f} meters")
    print(f"  Distance: {distance_km:.2f} km")
    print()

# Method 2: Using Point.distance() (geodetic)
geodetic_distance_degrees = brasilia_center.distance(planaltina)
print(f"Method 2 (Point.distance - degrees):")
print(f"  Distance: {geodetic_distance_degrees:.6f} degrees")
print(f"  Distance: {geodetic_distance_degrees * 111:.2f} km (approx)")
print()

# Method 3: Check what ST_DWithin would return
with connection.cursor() as cursor:
    for radius_km in [5, 10, 20, 30, 40, 50]:
        radius_meters = radius_km * 1000.0
        cursor.execute("""
            SELECT ST_DWithin(
                ST_GeogFromWKB(ST_AsEWKB(%s::geometry)),
                ST_GeogFromWKB(ST_AsEWKB(%s::geometry)),
                %s
            )
        """, [brasilia_center.ewkb, planaltina.ewkb, radius_meters])
        result = cursor.fetchone()[0]
        print(f"ST_DWithin({radius_km}km / {radius_meters}m): {result}")

print("=" * 60)
