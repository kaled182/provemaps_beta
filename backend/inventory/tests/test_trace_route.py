"""
Tests for Trace Route API.

Tests the bidirectional graph traversal algorithm for optical path tracing.
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model

from django.contrib.gis.geos import Point

from inventory.models import (
    Site,
    Device,
    Port,
    FiberCable,
    BufferTube,
    FiberStrand,
    FiberFusion,
    FiberInfrastructure,
)
from inventory.api.trace_route import (
    trace_fiber_route,
    serialize_device_port,
    serialize_fiber_strand,
    serialize_fusion,
    calculate_power_budget,
)

User = get_user_model()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(username="testuser", password="testpass")


@pytest.fixture
def site_a(db):
    """Create Site A."""
    return Site.objects.create(
        display_name="Site A - Core",
        city="Brasília",
        latitude=-15.7801,
        longitude=-47.9292,
    )


@pytest.fixture
def site_b(db):
    """Create Site B."""
    return Site.objects.create(
        display_name="Site B - Distribution",
        city="Planaltina",
        latitude=-15.4533,
        longitude=-47.6142,
    )


@pytest.fixture
def switch_a(db, site_a):
    """Create Switch A at Site A."""
    return Device.objects.create(
        name="SW-Core-01",
        category="backbone",
        site=site_a,
        zabbix_hostid="10001",
    )


@pytest.fixture
def switch_b(db, site_b):
    """Create Switch B at Site B."""
    return Device.objects.create(
        name="SW-Dist-05",
        category="backbone",
        site=site_b,
        zabbix_hostid="10002",
    )


@pytest.fixture
def port_a(db, switch_a):
    """Create Port on Switch A."""
    return Port.objects.create(
        device=switch_a,
        name="GigabitEthernet1/0/1",
    )


@pytest.fixture
def port_b(db, switch_b):
    """Create Port on Switch B."""
    return Port.objects.create(
        device=switch_b,
        name="SFP2",
    )


@pytest.fixture
def cable_segment_a(db, site_a, site_b):
    """Create Cable A (Site A to CEO)."""
    cable = FiberCable.objects.create(
        name="Cabo-Backbone-01",
        site_a=site_a,
        site_b=site_b,
        length_km=Decimal("2.5"),
    )
    
    # Create buffer tube
    tube = BufferTube.objects.create(
        cable=cable,
        number=1,
        color="Azul",
        color_hex="#0000FF",
    )
    
    # Create fiber strand
    strand = FiberStrand.objects.create(
        tube=tube,
        number=5,
        absolute_number=5,
        color="Verde",
        color_hex="#00FF00",
        status="lit",
        attenuation_db=Decimal("0.875"),  # 2.5 km * 0.35 dB/km
    )
    
    return strand


@pytest.fixture
def cable_segment_b(db, site_a, site_b):
    """Create Cable B (CEO to Site B)."""
    cable = FiberCable.objects.create(
        name="Cabo-Backbone-02",
        site_a=site_a,
        site_b=site_b,
        length_km=Decimal("1.7"),
    )
    
    tube = BufferTube.objects.create(
        cable=cable,
        number=1,
        color="Azul",
        color_hex="#0000FF",
    )
    
    strand = FiberStrand.objects.create(
        tube=tube,
        number=3,
        absolute_number=3,
        color="Laranja",
        color_hex="#FFA500",
        status="lit",
        attenuation_db=Decimal("0.6"),  # Shorter segment
    )
    
    return strand


@pytest.fixture
def ceo_infrastructure(db, cable_segment_a):
    """Create CEO (Fusion infrastructure)."""
    cable = cable_segment_a.tube.cable
    return FiberInfrastructure.objects.create(
        name="CEO-Planaltina",
        type="splice_box",
        cable=cable,
        location=Point(-47.7500, -15.6000, srid=4326),
    )


@pytest.fixture
def complete_path(
    db, port_a, port_b, cable_segment_a, cable_segment_b, ceo_infrastructure
):
    """
    Create complete optical path:
    Switch A Port -> Fiber A -> CEO Fusion -> Fiber B -> Switch B Port
    """
    cable_segment_a.connected_device_port = port_a
    cable_segment_a.save()

    cable_segment_b.connected_device_port = port_b
    cable_segment_b.save()

    FiberFusion.objects.create(
        infrastructure=ceo_infrastructure,
        tray=1,
        slot=1,
        fiber_a=cable_segment_a,
        fiber_b=cable_segment_b,
    )

    return {
        "port_a": port_a,
        "port_b": port_b,
        "fiber_a": cable_segment_a,
        "fiber_b": cable_segment_b,
        "ceo": ceo_infrastructure,
    }


@pytest.mark.django_db
class TestTraceRouteAPI:
    """Test suite for Trace Route API."""
    
    def test_serialize_device_port(self, port_a):
        """Test device port serialization."""
        result = serialize_device_port(port_a, step_num=1)
        
        assert result["step_number"] == 1
        assert result["type"] == "device_port"
        assert "SW-Core-01" in result["name"]
        assert result["details"]["device_name"] == "SW-Core-01"
        assert result["details"]["port_name"] == "GigabitEthernet1/0/1"
        assert result["loss_db"] == Decimal("0.5")
        assert result["details"]["port_type"] is None
        assert result["details"]["status"] is None
    
    def test_serialize_fiber_strand(self, cable_segment_a):
        """Test fiber strand serialization."""
        result = serialize_fiber_strand(cable_segment_a, step_num=2)
        
        assert result["step_number"] == 2
        assert result["type"] == "fiber_strand"
        assert "Cabo-Backbone-01" in result["name"]
        assert result["details"]["fiber_color"] == "Verde"
        assert result["details"]["fiber_number"] == 5
        assert result["details"]["cable_name"] == "Cabo-Backbone-01"
    
    def test_serialize_fusion(
        self, cable_segment_a, cable_segment_b, ceo_infrastructure
    ):
        """Test fusion point serialization."""
        fusion = FiberFusion.objects.create(
            infrastructure=ceo_infrastructure,
            tray=1,
            slot=5,
            fiber_a=cable_segment_a,
            fiber_b=cable_segment_b,
        )

        result = serialize_fusion(
            fusion,
            cable_segment_a,
            cable_segment_b,
            step_num=3,
        )

        assert result["step_number"] == 3
        assert result["type"] == "fusion"
        assert result["loss_db"] == Decimal("0.1")
        assert result["details"]["fusion_id"] == fusion.id
        assert result["details"]["tray"] == 1
        assert result["details"]["slot"] == 5
    
    def test_calculate_power_budget_ok(self):
        """Test power budget calculation with viable link."""
        path = [
            {"type": "device_port", "loss_db": Decimal("0.5"), "details": {}},
            {
                "type": "fiber_strand",
                "loss_db": Decimal("0.875"),
                "details": {"distance_km": 2.5},
            },
            {"type": "fusion", "loss_db": Decimal("0.1"), "details": {}},
            {
                "type": "fiber_strand",
                "loss_db": Decimal("0.6"),
                "details": {"distance_km": 1.7},
            },
            {"type": "device_port", "loss_db": Decimal("0.5"), "details": {}},
        ]
        
        budget = calculate_power_budget(path)
        
        assert budget["total_distance_km"] == 4.2
        assert budget["fusion_count"] == 1
        assert budget["connector_count"] == 2
        assert budget["is_viable"] is True
        assert budget["status"] == "OK"
    
    def test_trace_fiber_route_complete_path(self, rf, user, complete_path):
        """Test complete trace route from fiber strand."""
        fiber_a = complete_path["fiber_a"]
        
        request = rf.get(
            f"/api/v1/inventory/trace-route/?strand_id={fiber_a.id}"
        )
        request.user = user
        
        response = trace_fiber_route(request)
        
        assert response.status_code == 200
        data = response.data
        
        # Verify source and destination
        assert data["source"]["device_name"] == "SW-Core-01"
        assert data["destination"]["device_name"] == "SW-Dist-05"
        
        # Verify path has all steps
        assert len(data["path"]) == 5
        # Path order: Port A -> Fiber A -> Fusion -> Fiber B -> Port B
        
        # Verify step types in order
        step_types = [step["type"] for step in data["path"]]
        assert step_types == [
            "device_port",
            "fiber_strand",
            "fusion",
            "fiber_strand",
            "device_port",
        ]
        
        # Verify power budget
        assert data["fusion_count"] == 1
        assert data["connector_count"] == 2
        assert data["power_budget"]["is_viable"] is True
    
    def test_trace_fiber_route_missing_strand_id(self, rf, user):
        """Test trace route without strand_id parameter."""
        request = rf.get("/api/v1/inventory/trace-route/")
        request.user = user
        
        response = trace_fiber_route(request)
        
        assert response.status_code == 400
        assert "strand_id" in response.data["error"]
    
    def test_trace_fiber_route_invalid_strand_id(self, rf, user):
        """Test trace route with non-existent strand."""
        request = rf.get("/api/v1/inventory/trace-route/?strand_id=999999")
        request.user = user
        
        response = trace_fiber_route(request)
        
        assert response.status_code == 404
        assert "not found" in response.data["error"]
    
    def test_trace_fiber_route_partial_path(
        self, rf, user, port_a, cable_segment_a
    ):
        """Test trace with only one endpoint connected."""
        # Connect only to Port A
        cable_segment_a.connected_device_port = port_a
        cable_segment_a.save()
        
        request = rf.get(
            f"/api/v1/inventory/trace-route/?strand_id={cable_segment_a.id}"
        )
        request.user = user
        
        response = trace_fiber_route(request)
        
        assert response.status_code == 200
        data = response.data
        
        # Should have source but no destination
        assert data["source"]["device_name"] == "SW-Core-01"
        assert data["destination"] == {}
        
        # Path should have Port A and Fiber A only
        assert len(data["path"]) == 2
