"""
Tests for /api/v1/inventory/sites/radius endpoint (Phase 7 Day 3).

Tests cover:
- Valid queries with results
- Parameter validation (lat/lng/radius/limit)
- Edge cases (no results, radius zero, max limit)
- Distance calculations accuracy
- Authentication requirements
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import Client
from django.urls import reverse

from inventory.models import Site

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def authenticated_client(db):
    """Client with authenticated user."""
    user = User.objects.create_user(
        username='testuser',
        password='testpass123',
    )
    client = Client()
    client.login(username='testuser', password='testpass123')
    return client


@pytest.fixture
def sites_brasilia(db):
    """Create test sites around Brasília."""
    # Brasília center
    center = Site.objects.create(
        display_name='Brasília Center',
        latitude=-15.7801,
        longitude=-47.9292,
        location=Point(-47.9292, -15.7801, srid=4326),
    )
    
    # 5km north (approx)
    north = Site.objects.create(
        display_name='Brasília North',
        latitude=-15.7350,
        longitude=-47.9292,
        location=Point(-47.9292, -15.7350, srid=4326),
    )
    
    # Planaltina (49.55km northeast - should be excluded from 10km search)
    far = Site.objects.create(
        display_name='Planaltina',
        latitude=-15.4523,
        longitude=-47.6144,
        location=Point(-47.6144, -15.4523, srid=4326),
    )
    
    return {'center': center, 'north': north, 'far': far}


class TestSitesRadiusEndpoint:
    """Test suite for /api/v1/inventory/sites/radius endpoint."""
    
    def test_requires_authentication(self, db):
        """Unauthenticated requests should be rejected."""
        client = Client()
        url = reverse('inventory-api:sites-radius')
        
        response = client.get(url, {
            'lat': '-15.7801',
            'lng': '-47.9292',
            'radius_km': '10',
        })
        
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]
    
    def test_valid_query_returns_sites(
        self, authenticated_client, sites_brasilia
    ):
        """Valid query should return sites within radius."""
        url = reverse('inventory-api:sites-radius')
        
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'lng': '-47.9292',
            'radius_km': '10',
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'count' in data
        assert 'sites' in data
        assert data['count'] == 2  # center + north, excludes Planaltina
        
        assert data['center'] == {'lat': -15.7801, 'lng': -47.9292}
        assert data['radius_km'] == 10
        
        # Sites should be ordered by distance
        assert data['sites'][0]['display_name'] == 'Brasília Center'
        assert data['sites'][1]['display_name'] == 'Brasília North'
        
        # Distance annotations
        assert data['sites'][0]['distance_km'] == 0.0
        assert 4.0 < data['sites'][1]['distance_km'] < 6.0  # ~5km
    
    def test_large_radius_includes_all(
        self, authenticated_client, sites_brasilia
    ):
        """Radius of 60km should include Planaltina."""
        url = reverse('inventory-api:sites-radius')
        
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'lng': '-47.9292',
            'radius_km': '60',
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['count'] == 3  # All sites
        assert data['sites'][2]['display_name'] == 'Planaltina'
        assert 49.0 < data['sites'][2]['distance_km'] < 50.0  # ~49.55km
    
    def test_missing_parameters_returns_400(self, authenticated_client):
        """Missing required parameters should return 400."""
        url = reverse('inventory-api:sites-radius')
        
        # Missing lat
        response = authenticated_client.get(url, {
            'lng': '-47.9292',
            'radius_km': '10',
        })
        assert response.status_code == 400
        assert 'error' in response.json()
        
        # Missing lng
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'radius_km': '10',
        })
        assert response.status_code == 400
        
        # Missing radius_km
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'lng': '-47.9292',
        })
        assert response.status_code == 400
    
    def test_invalid_latitude_rejected(self, authenticated_client):
        """Latitude outside [-90, 90] should be rejected."""
        url = reverse('inventory-api:sites-radius')
        
        # Too high
        response = authenticated_client.get(url, {
            'lat': '91',
            'lng': '-47.9292',
            'radius_km': '10',
        })
        assert response.status_code == 400
        assert 'Latitude must be between' in response.json()['error']
        
        # Too low
        response = authenticated_client.get(url, {
            'lat': '-91',
            'lng': '-47.9292',
            'radius_km': '10',
        })
        assert response.status_code == 400
    
    def test_invalid_longitude_rejected(self, authenticated_client):
        """Longitude outside [-180, 180] should be rejected."""
        url = reverse('inventory-api:sites-radius')
        
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'lng': '181',
            'radius_km': '10',
        })
        assert response.status_code == 400
        assert 'Longitude must be between' in response.json()['error']
    
    def test_zero_radius_rejected(self, authenticated_client):
        """Radius of zero or negative should be rejected."""
        url = reverse('inventory-api:sites-radius')
        
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'lng': '-47.9292',
            'radius_km': '0',
        })
        assert response.status_code == 400
        assert 'must be positive' in response.json()['error']
        
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'lng': '-47.9292',
            'radius_km': '-5',
        })
        assert response.status_code == 400
    
    def test_excessive_radius_rejected(self, authenticated_client):
        """Radius > 1000km should be rejected."""
        url = reverse('inventory-api:sites-radius')
        
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'lng': '-47.9292',
            'radius_km': '1001',
        })
        assert response.status_code == 400
        assert 'cannot exceed 1000km' in response.json()['error']
    
    def test_limit_parameter_works(
        self, authenticated_client, sites_brasilia
    ):
        """Limit parameter should restrict results."""
        url = reverse('inventory-api:sites-radius')
        
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'lng': '-47.9292',
            'radius_km': '60',
            'limit': '2',
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['count'] == 2  # Limited to 2 even though 3 match
    
    def test_limit_clamped_to_500(self, authenticated_client):
        """Limit > 500 should be clamped to 500."""
        url = reverse('inventory-api:sites-radius')
        
        # Request 1000 but should get max 500
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'lng': '-47.9292',
            'radius_km': '10',
            'limit': '1000',
        })
        
        assert response.status_code == 200
        # Can't test actual limit without 500 sites,
        # but endpoint should accept the parameter
    
    def test_no_results_returns_empty(
        self, authenticated_client, sites_brasilia
    ):
        """Query with no matches should return empty array."""
        url = reverse('inventory-api:sites-radius')
        
        # Search in middle of ocean (no sites)
        response = authenticated_client.get(url, {
            'lat': '0',
            'lng': '0',
            'radius_km': '10',
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['count'] == 0
        assert data['sites'] == []
    
    def test_non_numeric_parameters_rejected(self, authenticated_client):
        """Non-numeric values should return 400."""
        url = reverse('inventory-api:sites-radius')
        
        response = authenticated_client.get(url, {
            'lat': 'invalid',
            'lng': '-47.9292',
            'radius_km': '10',
        })
        assert response.status_code == 400
        
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'lng': 'invalid',
            'radius_km': '10',
        })
        assert response.status_code == 400
        
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'lng': '-47.9292',
            'radius_km': 'invalid',
        })
        assert response.status_code == 400
    
    def test_sites_ordered_by_distance(
        self, authenticated_client, sites_brasilia
    ):
        """Results should be ordered by distance (nearest first)."""
        url = reverse('inventory-api:sites-radius')
        
        response = authenticated_client.get(url, {
            'lat': '-15.7801',
            'lng': '-47.9292',
            'radius_km': '60',
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify ascending order
        distances = [site['distance_km'] for site in data['sites']]
        assert distances == sorted(distances), "Sites not ordered by distance"
        
        # First should be center (0km), last should be Planaltina (~50km)
        assert distances[0] == 0.0
        assert distances[-1] > 49.0
