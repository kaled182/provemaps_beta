"""
Tests for spatial query usecases (PostGIS).

Validates high-performance spatial queries using PostGIS operators.
"""
import pytest
from django.contrib.gis.geos import LineString

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
        """Create test site with coordinates."""
        return Site.objects.create(
            display_name='Test Site Brasilia',
            latitude=-15.7801,
            longitude=-47.9292,
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
