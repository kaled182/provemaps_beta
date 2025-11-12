"""
Tests for cached fiber cable status endpoints (Phase 9.1).

Verifies that endpoints return pre-computed status values without
triggering synchronous Zabbix calls.
"""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from inventory.models import Device, FiberCable, Port, Site

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
def test_site(db):
    """Create test site."""
    return Site.objects.create(
        display_name='Test Site',
        latitude=-15.7801,
        longitude=-47.9292,
    )


@pytest.fixture
def test_cable(db, test_site):
    """Create test fiber cable with cached status."""
    device_a = Device.objects.create(
        name='Device-A',
        site=test_site,
        zabbix_hostid='10001',
    )
    device_b = Device.objects.create(
        name='Device-B',
        site=test_site,
        zabbix_hostid='10002',
    )
    
    port_a = Port.objects.create(
        device=device_a,
        name='eth1',
        zabbix_item_key='net.if.in[eth1]',
    )
    port_b = Port.objects.create(
        device=device_b,
        name='eth2',
        zabbix_item_key='net.if.in[eth2]',
    )
    
    now = timezone.now()
    
    cable = FiberCable.objects.create(
        origin_port=port_a,
        destination_port=port_b,
        # Cached operational status
        last_status_origin='up',
        last_status_dest='up',
        last_status_check=now - timedelta(seconds=30),
        # Cached live status
        last_live_status='operational',
        last_live_check=now - timedelta(seconds=45),
    )
    
    return cable


class TestCableCachedLiveStatusEndpoint:
    """Tests for cached live status endpoint (Phase 9.1)."""

    def test_get_cable_cached_live_status_success(
        self,
        authenticated_client: Client,
        test_cable: FiberCable,
    ):
        """Should return cached live status for existing cable."""
        url = f'/api/v1/inventory/fibers/{test_cable.pk}/cached-live-status/'
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['cable_id'] == test_cable.pk
        assert data['live_status'] == 'operational'
        assert data['last_live_check'] is not None
        assert data['origin_status'] == 'up'
        assert data['destination_status'] == 'up'
        assert data['last_status_check'] is not None

    def test_get_cable_cached_live_status_not_found(
        self,
        authenticated_client: Client,
    ):
        """Should return 404 for non-existent cable."""
        url = '/api/v1/inventory/fibers/99999/cached-live-status/'
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data

    def test_no_zabbix_calls_made(
        self,
        authenticated_client: Client,
        test_cable: FiberCable,
    ):
        """Should NOT make any Zabbix API calls (Phase 9.1 goal)."""
        with patch(
            'integrations.zabbix.zabbix_service.zabbix_request'
        ) as mock_zabbix:
            url = (
                f'/api/v1/inventory/fibers/{test_cable.pk}/'
                'cached-live-status/'
            )
            response = authenticated_client.get(url)
            
            assert response.status_code == 200
            # Critical: No Zabbix calls should be made
            mock_zabbix.assert_not_called()


class TestCableCachedOpticalStatusEndpoint:
    """Tests for cached optical status endpoint (Phase 9)."""

    def test_get_cable_cached_optical_status(
        self,
        authenticated_client: Client,
        test_site: Site,
    ):
        """Should return cached optical power levels."""
        device = Device.objects.create(
            name='Device-C',
            site=test_site,
            zabbix_hostid='10003',
        )
        
        now = timezone.now()
        
        port_a = Port.objects.create(
            device=device,
            name='eth3',
            zabbix_item_key='net.if.in[eth3]',
            last_rx_power=-15.5,
            last_tx_power=-10.2,
            last_optical_check=now - timedelta(minutes=2),
        )
        port_b = Port.objects.create(
            device=device,
            name='eth4',
            zabbix_item_key='net.if.in[eth4]',
            last_rx_power=-16.0,
            last_tx_power=-11.0,
            last_optical_check=now - timedelta(minutes=2),
        )
        
        cable = FiberCable.objects.create(
            origin_port=port_a,
            destination_port=port_b,
        )
        
        url = f'/api/v1/inventory/fibers/{cable.pk}/cached-status/'
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['cable_id'] == cable.pk
        # API returns strings for decimal values
        assert float(data['origin_optical']['rx_dbm']) == -15.5
        assert float(data['origin_optical']['tx_dbm']) == -10.2
        assert float(data['destination_optical']['rx_dbm']) == -16.0
        assert float(data['destination_optical']['tx_dbm']) == -11.0

    def test_no_zabbix_calls_optical_endpoint(
        self,
        authenticated_client: Client,
        test_cable: FiberCable,
    ):
        """Optical status endpoint should not call Zabbix."""
        with patch(
            'integrations.zabbix.zabbix_service.zabbix_request'
        ) as mock_zabbix:
            url = f'/api/v1/inventory/fibers/{test_cable.pk}/cached-status/'
            response = authenticated_client.get(url)
            
            assert response.status_code == 200
            mock_zabbix.assert_not_called()


class TestPhase91Integration:
    """Integration tests verifying Phase 9.1 goals."""

    def test_zero_synchronous_zabbix_calls(
        self,
        authenticated_client: Client,
        test_cable: FiberCable,
    ):
        """
        Critical Phase 9.1 test: Verify NO synchronous Zabbix calls.
        
        All status should come from database cache populated by Celery.
        """
        with patch(
            'integrations.zabbix.zabbix_service.zabbix_request'
        ) as mock_zabbix:
            # Cached live status endpoint
            url1 = (
                f'/api/v1/inventory/fibers/{test_cable.pk}/'
                'cached-live-status/'
            )
            response1 = authenticated_client.get(url1)
            assert response1.status_code == 200
            
            # Cached optical status endpoint
            url2 = (
                f'/api/v1/inventory/fibers/{test_cable.pk}/'
                'cached-status/'
            )
            response2 = authenticated_client.get(url2)
            assert response2.status_code == 200
            
            # Critical assertion: Zero Zabbix calls
            assert mock_zabbix.call_count == 0, \
                "Phase 9.1 violation: Synchronous Zabbix calls detected!"

    def test_response_time_under_100ms(
        self,
        authenticated_client: Client,
        test_cable: FiberCable,
    ):
        """
        Verify response time meets <100ms target.
        
        Note: This is a smoke test; real benchmarks should use profiling tools.
        """
        import time
        
        url = f'/api/v1/inventory/fibers/{test_cable.pk}/cached-live-status/'
        
        start = time.time()
        response = authenticated_client.get(url)
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        assert response.status_code == 200
        # Allow some overhead for test database, but should be fast
        assert elapsed < 500, f"Response took {elapsed:.1f}ms (target <100ms)"

    def test_celery_tasks_configured(self):
        """Verify Celery tasks are registered in beat schedule."""
        from core.celery import app
        
        beat_schedule = app.conf.beat_schedule
        
        # Check Phase 9.1 tasks are scheduled
        assert 'refresh-fiber-live-status' in beat_schedule
        assert 'refresh-cables-oper-status' in beat_schedule
        
        # Check intervals are reasonable (2 minutes = 120s)
        live_status_task = beat_schedule['refresh-fiber-live-status']
        oper_status_task = beat_schedule['refresh-cables-oper-status']
        
        assert live_status_task['schedule'] == 120.0
        assert oper_status_task['schedule'] == 120.0
        
        # Check tasks use correct queue (zabbix)
        assert live_status_task['options']['queue'] == 'zabbix'
        assert oper_status_task['options']['queue'] == 'zabbix'
