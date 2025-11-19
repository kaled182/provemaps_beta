#!/usr/bin/env python
"""Debug script to check test data in test database."""

import django
import os
import sys

# Setup Django
sys.path.insert(0, '/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.test')
django.setup()

from django.contrib.gis.geos import Point
from inventory.models import Site
from django.test import TestCase

# Use TestCase to create test DB
class DebugTest(TestCase):
    def test_check_sites(self):
        """Check sites created in test."""
        # Create test sites
        center = Site.objects.create(
            display_name='Brasilia Center',
            latitude=-15.7801,
            longitude=-47.9292,
            location=Point(-47.9292, -15.7801, srid=4326),
        )

        nearby = Site.objects.create(
            display_name='Brasilia North',
            latitude=-15.7350,
            longitude=-47.9292,
            location=Point(-47.9292, -15.7350, srid=4326),
        )

        far = Site.objects.create(
            display_name='Planaltina',
            latitude=-15.4523,
            longitude=-47.6144,
            location=Point(-47.6144, -15.4523, srid=4326),
        )

        print("\n" + "=" * 60)
        print("SITES CREATED:")
        for site in Site.objects.all():
            print(f"  {site.display_name}:")
            print(f"    lat/lng: {site.latitude}, {site.longitude}")
            print(f"    location: {site.location}")
            print()

        # Test ST_DWithin with 10km radius
        from django.db import connection
        center_point = Point(-47.9292, -15.7801, srid=4326)
        radius_10km = 10000.0  # meters

        print("=" * 60)
        print("ST_DWithin TEST (10km radius):")
        print("="  * 60)
        
        with connection.cursor() as cursor:
            for site in [center, nearby, far]:
                cursor.execute("""
                    SELECT ST_DWithin(
                        location::geography,
                        ST_GeogFromWKB(ST_AsEWKB(%s::geometry)),
                        %s
                    ) as within,
                    ST_Distance(
                        location::geography,
                        ST_GeogFromWKB(ST_AsEWKB(%s::geometry))
                    ) as distance
                    FROM zabbix_api_site
                    WHERE id = %s
                """, [center_point.ewkb, radius_10km, center_point.ewkb, site.id])
                row = cursor.fetchone()
                within = row[0]
                distance_m = row[1]
                distance_km = distance_m / 1000.0
                print(f"{site.display_name}:")
                print(f"  ST_DWithin(10km): {within}")
                print(f"  ST_Distance: {distance_km:.2f} km ({distance_m:.2f} m)")

        print("=" * 60)

# Run the test
import pytest
pytest.main([__file__, '-v', '-s'])
