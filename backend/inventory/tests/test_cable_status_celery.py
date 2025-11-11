"""
Tests for cable status Celery background processing.
"""

import pytest
from unittest.mock import Mock, patch
from django.core.cache import cache


@pytest.mark.django_db
def test_refresh_cables_oper_status_task():
    """Test that the Celery task processes cables and populates cache."""
    from inventory.tasks import refresh_cables_oper_status
    from inventory.models import FiberCable, Port, Device, Site
    
    # Create test data
    site = Site.objects.create(name="Test Site", city="Test City")
    device1 = Device.objects.create(name="Device1", site=site)
    device2 = Device.objects.create(name="Device2", site=site)
    port1 = Port.objects.create(name="Port1", device=device1)
    port2 = Port.objects.create(name="Port2", device=device2)
    
    cable = FiberCable.objects.create(
        name="Test Cable",
        origin_port=port1,
        destination_port=port2,
    )
    
    # Mock the Zabbix-calling function
    mock_status = {
        "cable_id": cable.id,
        "status": "up",
        "origin_status": "up",
        "destination_status": "up",
        "origin_optical": {"rx_dbm": -5.2, "tx_dbm": -3.1},
        "destination_optical": {"rx_dbm": -6.1, "tx_dbm": -2.9},
    }
    
    with patch('inventory.usecases.fibers.update_cable_oper_status', return_value=mock_status):
        with patch('maps_view.realtime.publisher.broadcast_cable_status_update'):
            # Run the task
            result = refresh_cables_oper_status()
    
    # Verify result
    assert result["success"] is True
    assert result["processed"] == 1
    assert result["errors"] == 0
    
    # Verify cache was populated
    cache_key = f"cable:oper_status:{cable.id}"
    cached_data = cache.get(cache_key)
    
    assert cached_data is not None
    assert cached_data["cable_id"] == cable.id
    assert cached_data["status"] == "up"


@pytest.mark.django_db
def test_api_fibers_oper_status_reads_from_cache(client):
    """Test that the API endpoint reads from cache instead of calling Zabbix."""
    from django.contrib.auth import get_user_model
    from inventory.models import FiberCable, Port, Device, Site
    
    User = get_user_model()
    user = User.objects.create_user(username='testuser', password='testpass')
    client.login(username='testuser', password='testpass')
    
    # Create test data
    site = Site.objects.create(name="Test Site", city="Test City")
    device1 = Device.objects.create(name="Device1", site=site)
    device2 = Device.objects.create(name="Device2", site=site)
    port1 = Port.objects.create(name="Port1", device=device1)
    port2 = Port.objects.create(name="Port2", device=device2)
    
    cable = FiberCable.objects.create(
        name="Test Cable",
        origin_port=port1,
        destination_port=port2,
    )
    
    # Pre-populate cache (simulating Celery task)
    cache_key = f"cable:oper_status:{cable.id}"
    cached_status = {
        "cable_id": cable.id,
        "status": "up",
        "origin_optical": {"rx_dbm": -5.2},
    }
    cache.set(cache_key, cached_status, timeout=180)
    
    # Call API
    response = client.get(f'/api/v1/inventory/fibers/oper-status/?ids={cable.id}')
    
    assert response.status_code == 200
    data = response.json()
    
    # Should read from cache, not call Zabbix
    assert len(data["results"]) == 1
    assert data["results"][0]["cable_id"] == cable.id
    assert data["results"][0]["status"] == "up"
    assert "cache_misses" not in data or cable.id not in data.get("cache_misses", [])


@pytest.mark.django_db
def test_api_fibers_oper_status_fallback_on_cache_miss(client):
    """Test that the API falls back to direct query on cache miss."""
    from django.contrib.auth import get_user_model
    from inventory.models import FiberCable, Port, Device, Site
    
    User = get_user_model()
    user = User.objects.create_user(username='testuser', password='testpass')
    client.login(username='testuser', password='testpass')
    
    # Create test data
    site = Site.objects.create(name="Test Site", city="Test City")
    device1 = Device.objects.create(name="Device1", site=site)
    device2 = Device.objects.create(name="Device2", site=site)
    port1 = Port.objects.create(name="Port1", device=device1)
    port2 = Port.objects.create(name="Port2", device=device2)
    
    cable = FiberCable.objects.create(
        name="Test Cable",
        origin_port=port1,
        destination_port=port2,
    )
    
    # Ensure cache is empty (cache miss scenario)
    cache_key = f"cable:oper_status:{cable.id}"
    cache.delete(cache_key)
    
    # Mock the fallback query
    mock_status = {
        "cable_id": cable.id,
        "status": "degraded",
    }
    
    with patch('inventory.usecases.fibers.update_cable_oper_status', return_value=mock_status):
        response = client.get(f'/api/v1/inventory/fibers/oper-status/?ids={cable.id}')
    
    assert response.status_code == 200
    data = response.json()
    
    # Should report cache miss
    assert cable.id in data.get("cache_misses", [])
    
    # Should still return data (from fallback)
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "degraded"
