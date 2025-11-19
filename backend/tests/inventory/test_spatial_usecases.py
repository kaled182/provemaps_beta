"""
Tests for spatial query usecases (PostGIS).

Validates high-performance spatial queries using PostGIS operators.
Phase 7: Tests for PointField-based radius queries with ST_DWithin.
"""
import pytest
from django.contrib.gis.geos import LineString, Point

from inventory.models import FiberCable, Port, Site
from inventory.models_routes import Route, RouteSegment
from inventory.usecases.spatial import (
    get_cables_in_bbox,
    get_cable_length_in_region,
    get_segments_in_bbox,
    get_segments_intersecting_path,
    get_sites_in_bbox,
    get_sites_within_radius,
)


@pytest.mark.django_db
class TestSpatialUsecases:
    """Test spatial query usecases."""

    @pytest.fixture
    def test_site(self):
        """Create test site with coordinates and location PointField."""
        return Site.objects.create(
            display_name='Test Site Brasilia',
            latitude=-15.7801,
            longitude=-47.9292,
            location=Point(-47.9292, -15.7801, srid=4326),  # Phase 7
        )

    @pytest.fixture
    def test_route_with_segments(self, test_site):
        """Create test route with spatial segments."""
        device = test_site.devices.create(
            name='TEST-DEVICE',
            zabbix_hostid='999001',
        )

        port_a = Port.objects.create(
            device=device,
            name='eth0',
            zabbix_item_key='net.if.in[eth0]',
        )

        port_b = Port.objects.create(
            device=device,
            name='eth1',
            zabbix_item_key='net.if.in[eth1]',
        )

        route = Route.objects.create(
            name='Test Route',
            origin_port=port_a,
            destination_port=port_b,
        )

        # Create segments in Brasilia region
        segment1 = RouteSegment.objects.create(
            route=route,
            order=1,
            path=LineString(
                [(-47.95, -15.80), (-47.90, -15.75)],
                srid=4326,
            ),
            length_km=5.0,
        )

        segment2 = RouteSegment.objects.create(
            route=route,
            order=2,
            path=LineString(
                [(-47.90, -15.75), (-47.85, -15.70)],
                srid=4326,
            ),
            length_km=6.0,
        )

        return route, [segment1, segment2]

    @pytest.fixture
    def test_fiber_cable(self, test_site):
        """Create test fiber cable."""
        device = test_site.devices.first()
        if not device:
            device = test_site.devices.create(
                name='TEST-DEVICE',
                zabbix_hostid='999002',
            )

        port_a = device.ports.first()
        if not port_a:
            port_a = Port.objects.create(
                device=device,
                name='eth0',
                zabbix_item_key='net.if.in[eth0]',
            )

        port_b = Port.objects.create(
            device=device,
            name='eth1',
            zabbix_item_key='net.if.in[eth1]',
        )

        return FiberCable.objects.create(
            origin_port=port_a,
            destination_port=port_b,
            path=LineString(
                [(-47.95, -15.80), (-47.90, -15.75)],
                srid=4326,
            ),
        )

    def test_get_sites_in_bbox(self, test_site):
        """Test BBox filtering for sites."""
        # BBox covering Brasilia
        sites = get_sites_in_bbox(
            lng_min=-48.0,
            lat_min=-16.0,
            lng_max=-47.5,
            lat_max=-15.5,
        )

        assert test_site in sites
        assert sites.count() >= 1

    def test_get_sites_in_bbox_outside(self, test_site):
        """Test BBox filtering excludes sites outside region."""
        # BBox far from Brasilia (Rio de Janeiro region)
        sites = get_sites_in_bbox(
            lng_min=-43.5,
            lat_min=-23.0,
            lng_max=-43.0,
            lat_max=-22.5,
        )

        assert test_site not in sites

    def test_get_segments_in_bbox(self, test_route_with_segments):
        """Test BBox filtering for route segments."""
        route, segments = test_route_with_segments

        # BBox covering Brasilia
        results = get_segments_in_bbox(
            lng_min=-48.0,
            lat_min=-16.0,
            lng_max=-47.5,
            lat_max=-15.5,
        )

        assert results.count() == 2
        assert segments[0] in results
        assert segments[1] in results

    def test_get_segments_in_bbox_partial(self, test_route_with_segments):
        """Test BBox filtering with partial overlap."""
        route, segments = test_route_with_segments

        # Smaller BBox covering only first segment
        results = get_segments_in_bbox(
            lng_min=-48.0,
            lat_min=-15.85,
            lng_max=-47.9,
            lat_max=-15.75,
        )

        # Should find at least segment1
        assert results.count() >= 1

    def test_get_cables_in_bbox(self, test_fiber_cable):
        """Test BBox filtering for fiber cables."""
        cables = get_cables_in_bbox(
            lng_min=-48.0,
            lat_min=-16.0,
            lng_max=-47.5,
            lat_max=-15.5,
        )

        assert test_fiber_cable in cables
        assert cables.count() >= 1

    def test_get_sites_within_radius(self, test_site):
        """Test radius search for sites."""
        # Search within 10km of Brasilia city center
        nearby = get_sites_within_radius(
            lat=-15.7801,
            lon=-47.9292,
            radius_km=10.0,
        )

        assert test_site in nearby

    def test_get_sites_within_radius_outside(self, test_site):
        """Test radius search excludes distant sites."""
        # Search in Rio (far from Brasilia)
        nearby = get_sites_within_radius(
            lat=-22.9068,
            lon=-43.1729,
            radius_km=10.0,
        )

        assert test_site not in nearby

    def test_get_segments_intersecting_path(self, test_route_with_segments):
        """Test path intersection query."""
        route, segments = test_route_with_segments

        # Path crossing the route segments
        crossing = get_segments_intersecting_path([
            (-47.96, -15.81),
            (-47.84, -15.69),
        ])

        # Should find segments that intersect
        assert crossing.count() >= 1

    def test_get_segments_intersecting_path_empty(
        self, test_route_with_segments
    ):
        """Test path intersection with no results."""
        route, segments = test_route_with_segments

        # Path far from segments
        crossing = get_segments_intersecting_path([
            (-43.2, -22.9),
            (-43.1, -22.8),
        ])

        assert crossing.count() == 0

    def test_get_cable_length_in_region(self, test_fiber_cable):
        """Test total cable length calculation."""
        total_km = get_cable_length_in_region(
            lng_min=-48.0,
            lat_min=-16.0,
            lng_max=-47.5,
            lat_max=-15.5,
        )

        # Should have some length (PostGIS calculates geodesic distance)
        # Returns float in kilometers
        assert total_km > 0

    def test_empty_bbox_returns_empty_queryset(self):
        """Test BBox query with no results."""
        # BBox in middle of Atlantic Ocean
        segments = get_segments_in_bbox(
            lng_min=-30.0,
            lat_min=-10.0,
            lng_max=-29.0,
            lat_max=-9.0,
        )

        assert segments.count() == 0

    def test_invalid_path_returns_empty_queryset(self):
        """Test path intersection with invalid path."""
        # Path with single point (invalid LineString)
        result = get_segments_intersecting_path([(-47.9, -15.8)])

        assert result.count() == 0


@pytest.mark.django_db
class TestSpatialUsecasesPhase7:
    """
    Phase 7: Test PointField-based spatial queries.
    
    Tests ST_DWithin radius queries with GIST index optimization.
    """

    @pytest.fixture
    def sites_with_location(self):
        """Create multiple sites with location PointField."""
        # Center: Brasilia city center
        center = Site.objects.create(
            display_name='Brasilia Center',
            latitude=-15.7801,
            longitude=-47.9292,
            location=Point(-47.9292, -15.7801, srid=4326),
        )

        # 5km away (approx)
        nearby = Site.objects.create(
            display_name='Brasilia North',
            latitude=-15.7350,
            longitude=-47.9292,
            location=Point(-47.9292, -15.7350, srid=4326),
        )

        # 100km away (Planaltina-DF, actual distance from Brasilia)
        far = Site.objects.create(
            display_name='Planaltina',
            latitude=-15.4523,
            longitude=-47.6144,
            location=Point(-47.6144, -15.4523, srid=4326),
        )

        # Site without location (backwards compatibility test)
        no_location = Site.objects.create(
            display_name='Site Without Location',
            latitude=-15.8000,
            longitude=-47.9000,
            # location=None (not set)
        )

        return {
            'center': center,
            'nearby': nearby,
            'far': far,
            'no_location': no_location,
        }

    def test_radius_query_with_pointfield(self, sites_with_location):
        """Test ST_DWithin radius query finds nearby sites."""
        # Planaltina is ~49.55km away from Brasília Center
        # (verified with ST_Distance)
        
        # Test with 60km radius - should include all sites
        results_60km = get_sites_within_radius(
            lat=-15.7801,
            lon=-47.9292,
            radius_km=60.0,
        )

        # Should find all 3 sites with location
        assert sites_with_location['center'] in results_60km
        assert sites_with_location['nearby'] in results_60km
        # Planaltina at ~49.55km
        assert sites_with_location['far'] in results_60km

        # Test with 10km radius - should only include center and nearby
        results_10km = get_sites_within_radius(
            lat=-15.7801,
            lon=-47.9292,
            radius_km=10.0,
        )
        assert sites_with_location['center'] in results_10km
        # Nearby site ~5km away
        assert sites_with_location['nearby'] in results_10km
        # Planaltina ~49.55km away (excluded)
        assert sites_with_location['far'] not in results_10km

    def test_radius_query_sorted_by_distance(self, sites_with_location):
        """Test results are sorted by distance (nearest first)."""
        results = get_sites_within_radius(
            lat=-15.7801,
            lon=-47.9292,
            radius_km=100.0,
        )

        # Should have multiple results
        assert results.count() >= 2

        # First result should be center (distance ~0)
        first = results.first()
        assert first == sites_with_location['center']

        # Check distance annotation exists
        assert hasattr(first, 'distance')
        assert first.distance.km < 1.0  # Very close to center

    def test_radius_query_with_limit(self, sites_with_location):
        """Test limit parameter restricts result count."""
        results = get_sites_within_radius(
            lat=-15.7801,
            lon=-47.9292,
            radius_km=100.0,
            limit=1,
        )

        assert results.count() == 1
        # Should return closest site (center)
        assert results.first() == sites_with_location['center']

    def test_radius_query_zero_radius(self, sites_with_location):
        """Test radius query with zero radius (exact point match)."""
        # Zero radius should only find exact matches
        results = get_sites_within_radius(
            lat=-15.7801,
            lon=-47.9292,
            radius_km=0.0,
        )

        # Should find only the center site
        assert results.count() >= 1
        assert sites_with_location['center'] in results

    def test_radius_query_large_radius(self, sites_with_location):
        """Test radius query with large radius finds all sites."""
        # Very large radius (1000km) should find all sites in Brazil
        results = get_sites_within_radius(
            lat=-15.7801,
            lon=-47.9292,
            radius_km=1000.0,
        )

        # Should find center, nearby, and far
        assert sites_with_location['center'] in results
        assert sites_with_location['nearby'] in results
        assert sites_with_location['far'] in results

    def test_bbox_query_with_pointfield(self, sites_with_location):
        """Test BBox query uses location PointField with GIST index."""
        # BBox covering Brasilia region
        results = get_sites_in_bbox(
            lng_min=-48.0,
            lat_min=-16.0,
            lng_max=-47.5,
            lat_max=-15.5,
        )

        # Should find center and nearby
        assert sites_with_location['center'] in results
        assert sites_with_location['nearby'] in results

    def test_bbox_query_excludes_outside_sites(self, sites_with_location):
        """Test BBox query excludes sites outside bounding box."""
        # Small BBox around center only
        results = get_sites_in_bbox(
            lng_min=-47.95,
            lat_min=-15.80,
            lng_max=-47.90,
            lat_max=-15.75,
        )

        # Should find center, not far sites
        assert sites_with_location['center'] in results
        assert sites_with_location['far'] not in results

    def test_distance_annotation_accuracy(self, sites_with_location):
        """Test ST_Distance annotation provides accurate distances."""
        results = get_sites_within_radius(
            lat=-15.7801,
            lon=-47.9292,
            radius_km=100.0,
        )

        for site in results:
            # All results should have distance annotation
            assert hasattr(site, 'distance')

            # Distance should be within expected radius
            assert site.distance.km <= 100.0

            # Distance should be non-negative
            assert site.distance.km >= 0.0

    def test_backwards_compatibility_bbox_fallback(
        self, sites_with_location
    ):
        """Test BBox query handles sites without location field."""
        # Site without location should still be found via lat/lng fallback
        results = get_sites_in_bbox(
            lng_min=-48.0,
            lat_min=-16.0,
            lng_max=-47.5,
            lat_max=-15.5,
        )

        # Should include site without location (via fallback)
        assert sites_with_location['no_location'] in results

    def test_performance_gist_index_usage(self, sites_with_location):
        """
        Test GIST index is used (query should be fast).
        
        Note: This is a smoke test. Real performance testing
        requires benchmark script with 1000+ sites.
        """
        # Query with location field should complete quickly
        import time
        start = time.time()

        results = get_sites_within_radius(
            lat=-15.7801,
            lon=-47.9292,
            radius_km=50.0,
        )

        # Force query execution
        _ = list(results)

        elapsed = time.time() - start

        # Should complete in under 100ms (generous limit for CI)
        assert elapsed < 0.1, f"Query took {elapsed:.3f}s (expected <0.1s)"

    def test_radius_query_empty_result(self):
        """Test radius query returns empty queryset when no sites match."""
        # Search in middle of Atlantic Ocean
        results = get_sites_within_radius(
            lat=-10.0,
            lon=-30.0,
            radius_km=10.0,
        )

        assert results.count() == 0

    def test_multiple_sites_same_location(self):
        """Test radius query handles multiple sites at same coordinates."""
        # Create multiple sites at same location
        lat, lon = -15.7801, -47.9292
        for i in range(3):
            Site.objects.create(
                display_name=f'Duplicate Site {i}',
                latitude=lat,
                longitude=lon,
                location=Point(lon, lat, srid=4326),
            )

        results = get_sites_within_radius(
            lat=lat,
            lon=lon,
            radius_km=1.0,
        )

        # Should find all 3 sites
        assert results.count() == 3

        # All should have distance ~0
        for site in results:
            assert site.distance.km < 0.1
