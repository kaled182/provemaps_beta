"""
Tests for spatial API endpoints (Phase 10).

Tests BBox filtering for RouteSegment and FiberCable models.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import Client

try:
    from django.contrib.gis.geos import LineString
except (ImportError, ImproperlyConfigured):  # pragma: no cover - CI lacking GDAL
    LineString = None

if LineString is None:  # pragma: no cover - allows skipping on CI without GDAL
    pytest.skip(
        "GDAL/GEOS libraries unavailable; skipping spatial API tests.",
        allow_module_level=True,
    )

assert LineString is not None  # For type checkers: we bail earlier when missing

from inventory.models import FiberCable, Port, Site
from inventory.models_routes import Route, RouteSegment

User = get_user_model()

pytestmark = pytest.mark.django_db

@pytest.fixture
def authenticated_client(db):
    """Create authenticated test client."""
    User.objects.create_user(
        username='testuser',
        password='testpass123',
        is_staff=True,
    )
    client = Client()
    client.login(username='testuser', password='testpass123')
    return client


@pytest.fixture
def brasilia_site(db):
    """Create test site in Brasília."""
    return Site.objects.create(
        display_name='Brasília DF',
        latitude=-15.7801,
        longitude=-47.9292,
    )


@pytest.fixture
def test_route(db, brasilia_site):
    """Create test route with ports."""
    device = brasilia_site.devices.create(
        name='BSB-OLT-01',
        zabbix_hostid='12345',
    )
    
    port_a = Port.objects.create(
        device=device,
        name='eth1',
        zabbix_item_key='net.if.in[eth1]',
    )
    port_b = Port.objects.create(
        device=device,
        name='eth2',
        zabbix_item_key='net.if.in[eth2]',
    )
    
    route = Route.objects.create(
        name='BSB-Route-Test',
        origin_port=port_a,
        destination_port=port_b,
    )
    
    return route


@pytest.fixture
def test_segments_with_spatial(db, test_route):
    """Create RouteSegments with spatial data (PostGIS LineString)."""
    # Segment 1: Inside Brasília bbox (-48.0, -16.0, -47.5, -15.5)
    seg1 = RouteSegment.objects.create(
        route=test_route,
        order=1,
        path=LineString(
            [(-47.9292, -15.7801), (-47.9200, -15.7750)],
            srid=4326,
        ),
        length_km=1.2,
    )
    
    # Segment 2: Outside Brasília bbox (in São Paulo)
    seg2 = RouteSegment.objects.create(
        route=test_route,
        order=2,
        path=LineString(
            [(-46.6333, -23.5505), (-46.6200, -23.5400)],
            srid=4326,
        ),
        length_km=1.5,
    )
    
    # Segment 3: No spatial data (path=None, legacy compatibility test)
    seg3 = RouteSegment.objects.create(
        route=test_route,
        order=3,
        path=None,
        length_km=0.8,
    )
    
    return seg1, seg2, seg3

class TestSpatialAPIPostGIS:
    """Tests for spatial API with PostGIS backend."""

    @pytest.fixture(autouse=True)
    def use_postgis_engine(self, settings):
        settings.DB_ENGINE = "postgis"
    
    def test_route_segments_bbox_filter(
        self,
        authenticated_client,
        test_segments_with_spatial,
    ):
        """Test BBox filtering returns only intersecting segments."""
        seg1, seg2, seg3 = test_segments_with_spatial
        
        # Query Brasília bbox (should return seg1 only)
        response = authenticated_client.get(
            '/api/v1/inventory/segments/',
            {'bbox': '-48.0,-16.0,-47.5,-15.5'},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['count'] == 1
        assert data['bbox'] == '-48.0,-16.0,-47.5,-15.5'
        assert len(data['segments']) == 1
        assert data['segments'][0]['id'] == seg1.id
        assert data['segments'][0]['length_km'] == 1.2
        
        # Verify GeoJSON format
        geojson = data['segments'][0]['path_geojson']
        assert geojson['type'] == 'LineString'
        assert len(geojson['coordinates']) == 2
        assert geojson['coordinates'][0] == [-47.9292, -15.7801]
    
    def test_route_segments_bbox_multiple_results(
        self,
        authenticated_client,
        test_route,
    ):
        """Test BBox returning multiple segments."""
        # Create 3 segments in Brasília area
        for i in range(3):
            RouteSegment.objects.create(
                route=test_route,
                order=i + 1,
                path=LineString(
                    [
                        (-47.95 + i * 0.01, -15.78),
                        (-47.94 + i * 0.01, -15.77),
                    ],
                    srid=4326,
                ),
                length_km=1.0 + i * 0.1,
            )
        
        response = authenticated_client.get(
            '/api/v1/inventory/segments/',
            {'bbox': '-48.0,-16.0,-47.5,-15.5'},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 3
    
    def test_route_segments_bbox_no_results(
        self,
        authenticated_client,
        test_segments_with_spatial,
    ):
        """Test BBox with no intersecting segments."""
        # Query Rio de Janeiro area (no segments there)
        response = authenticated_client.get(
            '/api/v1/inventory/segments/',
            {'bbox': '-43.5,-23.0,-43.0,-22.5'},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 0
        assert data['segments'] == []
    
    def test_route_segments_bbox_missing_parameter(
        self,
        authenticated_client,
    ):
        """Test API returns 400 when bbox param is missing."""
        response = authenticated_client.get('/api/v1/inventory/segments/')
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'bbox' in data['error']
    
    def test_route_segments_bbox_invalid_format(
        self,
        authenticated_client,
    ):
        """Test API returns 400 for invalid bbox format."""
        invalid_bboxes = [
            'invalid',
            '1,2,3',  # Too few values
            '1,2,3,4,5',  # Too many values
            'a,b,c,d',  # Non-numeric
            '-200,-100,200,100',  # Out of range
            '-47,-16,-48,-15.5',  # Inverted (min > max)
        ]
        
        for bbox in invalid_bboxes:
            response = authenticated_client.get(
                '/api/v1/inventory/segments/',
                {'bbox': bbox},
            )
            assert response.status_code == 400, f"Failed for bbox: {bbox}"
    
    def test_fiber_cables_bbox_filter(
        self,
        authenticated_client,
        test_route,
    ):
        """Test FiberCable BBox filtering."""
        # Create cable with spatial data
        cable = FiberCable.objects.create(
            name='Fiber-BSB-01',
            origin_port=test_route.origin_port,
            destination_port=test_route.destination_port,
            path=LineString(
                [(-47.9292, -15.7801), (-47.9200, -15.7750)],
                srid=4326,
            ),
            length_km=1.2,
        )
        
        response = authenticated_client.get(
            '/api/v1/inventory/fibers/bbox/',
            {'bbox': '-48.0,-16.0,-47.5,-15.5'},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['count'] == 1
        assert data['cables'][0]['id'] == cable.id
        assert data['cables'][0]['name'] == 'Fiber-BSB-01'
        assert 'path_geojson' in data['cables'][0]

class TestSpatialAPIMySQL:
    """Test spatial API gracefully degrades on MySQL backend."""

    @pytest.fixture(autouse=True)
    def use_mysql_engine(self, settings):
        settings.DB_ENGINE = "mysql"
    
    def test_route_segments_bbox_not_implemented(
        self,
        authenticated_client,
    ):
        """Test API returns 501 when PostGIS is not available."""
        response = authenticated_client.get(
            '/api/v1/inventory/segments/',
            {'bbox': '-48.0,-16.0,-47.5,-15.5'},
        )
        
        assert response.status_code == 501
        data = response.json()
        assert 'error' in data
        assert 'postgis' in data['error'].lower()
    
    def test_fiber_cables_bbox_not_implemented(
        self,
        authenticated_client,
    ):
        """Test FiberCable bbox returns 501 on MySQL."""
        response = authenticated_client.get(
            '/api/v1/inventory/fibers/bbox/',
            {'bbox': '-48.0,-16.0,-47.5,-15.5'},
        )
        
        assert response.status_code == 501


class TestSpatialAPIAuthentication:
    """Test spatial API requires authentication."""
    
    def test_unauthenticated_request(self, db):
        """Test API requires login."""
        client = Client()
        
        response = client.get(
            '/api/v1/inventory/segments/',
            {'bbox': '-48.0,-16.0,-47.5,-15.5'},
        )
        
        # Should redirect to login (302) or return 401/403
        assert response.status_code in [302, 401, 403]
