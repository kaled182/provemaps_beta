"""
Tests for Fusion API - Atomic 1:1 Logic.

Tests the corrected fusion logic that ensures:
1. Fusion is atomic (Strand A <-> Strand B only)
2. No side effects on other fibers
3. Physical slot occupation is independent of fiber color/number
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from inventory.models import (
    Site,
    FiberCable,
    BufferTube,
    FiberStrand,
    FiberInfrastructure,
)

User = get_user_model()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(username="testuser", password="testpass")


@pytest.fixture
def api_client(user):
    """Create authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def site(db):
    """Create test site."""
    return Site.objects.create(
        display_name="Site Test",
        city="Brasília",
    )


@pytest.fixture
def ceo(db, cable_a):
    """Create CEO (splice box)."""
    from django.contrib.gis.geos import Point
    
    cable, _ = cable_a
    return FiberInfrastructure.objects.create(
        name="CEO-Test-001",
        type="splice_box",
        cable=cable,
        # lon, lat order for Point (WGS84)
        location=Point(-47.9292, -15.7801, srid=4326),
        installed_trays=4,  # 4 trays for testing
    )


@pytest.fixture
def cable_a(db, site):
    """Create Cable A with 12 fibers."""
    cable = FiberCable.objects.create(
        label="Cabo-Entrada",
        fiber_count=12,
        origin_site=site,
    )
    
    tube = BufferTube.objects.create(
        cable=cable,
        number=1,
        color="Azul",
        color_hex="#0000FF",
        strand_count=12,
    )
    
    # Create 12 fibers with standard colors
    colors = [
        ("Verde", "#00FF00"),
        ("Amarelo", "#FFFF00"),
        ("Branco", "#FFFFFF"),
        ("Azul", "#0000FF"),
        ("Vermelho", "#FF0000"),
        ("Violeta", "#8B00FF"),
        ("Marrom", "#8B4513"),
        ("Rosa", "#FFC0CB"),
        ("Preto", "#000000"),
        ("Cinza", "#808080"),
        ("Laranja", "#FFA500"),
        ("Aqua", "#00FFFF"),
    ]
    
    strands = []
    for i, (color, hex_code) in enumerate(colors, start=1):
        strand = FiberStrand.objects.create(
            tube=tube,
            number=i,
            absolute_number=i,
            color=color,
            color_hex=hex_code,
            status="dark",
        )
        strands.append(strand)
    
    return cable, strands


@pytest.fixture
def cable_b(db, site):
    """Create Cable B with 12 fibers."""
    cable = FiberCable.objects.create(
        label="Cabo-Saida",
        fiber_count=12,
        origin_site=site,
    )
    
    tube = BufferTube.objects.create(
        cable=cable,
        number=1,
        color="Azul",
        color_hex="#0000FF",
        strand_count=12,
    )
    
    colors = [
        ("Verde", "#00FF00"),
        ("Amarelo", "#FFFF00"),
        ("Branco", "#FFFFFF"),
        ("Azul", "#0000FF"),
        ("Vermelho", "#FF0000"),
        ("Violeta", "#8B00FF"),
        ("Marrom", "#8B4513"),
        ("Rosa", "#FFC0CB"),
        ("Preto", "#000000"),
        ("Cinza", "#808080"),
        ("Laranja", "#FFA500"),
        ("Aqua", "#00FFFF"),
    ]
    
    strands = []
    for i, (color, hex_code) in enumerate(colors, start=1):
        strand = FiberStrand.objects.create(
            tube=tube,
            number=i,
            absolute_number=i,
            color=color,
            color_hex=hex_code,
            status="dark",
        )
        strands.append(strand)
    
    return cable, strands


@pytest.mark.django_db
class TestAtomicFusionLogic:
    """Test atomic 1:1 fusion logic."""
    
    def test_different_colors_same_slot_allowed(
        self, api_client, ceo, cable_a, cable_b
    ):
        """
        CRITICAL TEST: Fusing different fiber numbers should NOT block others.
        
        Scenario:
        - Slot 1: Cable A FO-12 (Aqua) <-> Cable B FO-4 (Azul)
        - Slot 2: Cable A FO-1 (Verde) <-> Cable B FO-1 (Verde) should succeed
        
        The old logic would incorrectly block this.
        """
        _, strands_a = cable_a
        _, strands_b = cable_b
        
        # Fusion 1: FO-12 (Aqua) from A with FO-4 (Azul) from B at Slot 1
        response1 = api_client.post('/api/v1/inventory/fusions/', {
            "infrastructure_id": ceo.id,
            "tray": 1,
            "slot": 1,
            "fiber_a": strands_a[11].id,  # Aqua (12th fiber)
            "fiber_b": strands_b[3].id,    # Azul (4th fiber)
        })
        
        assert response1.status_code == 201
        assert response1.data["status"] == "success"
        
        # Fusion 2: FO-1 (Verde) from A with FO-1 (Verde) from B at Slot 2
        # This should SUCCEED because Slot 2 is free
        response2 = api_client.post('/api/v1/inventory/fusions/', {
            "infrastructure_id": ceo.id,
            "tray": 1,
            "slot": 2,
            "fiber_a": strands_a[0].id,   # Verde (1st fiber)
            "fiber_b": strands_b[0].id,   # Verde (1st fiber)
        })
        
        assert response2.status_code == 201
        assert response2.data["status"] == "success"
        
        # Verify both fusions exist independently
        strands_a[11].refresh_from_db()
        strands_a[0].refresh_from_db()
        
        assert strands_a[11].fused_to.id == strands_b[3].id
        assert strands_a[0].fused_to.id == strands_b[0].id
        
        # Verify different slots
        assert strands_a[11].fusion_slot == 1
        assert strands_a[0].fusion_slot == 2
    
    def test_same_slot_blocked(self, api_client, ceo, cable_a, cable_b):
        """Physical slot must be exclusive."""
        _, strands_a = cable_a
        _, strands_b = cable_b
        
        # First fusion at Slot 1
        api_client.post('/api/v1/inventory/fusions/', {
            "infrastructure_id": ceo.id,
            "tray": 1,
            "slot": 1,
            "fiber_a": strands_a[0].id,
            "fiber_b": strands_b[0].id,
        })
        
        # Try to use same slot (should fail)
        response = api_client.post('/api/v1/inventory/fusions/', {
            "infrastructure_id": ceo.id,
            "tray": 1,
            "slot": 1,  # Same slot!
            "fiber_a": strands_a[1].id,
            "fiber_b": strands_b[1].id,
        })
        
        assert response.status_code == 409  # Conflict
        assert "ocupado" in response.data["error"].lower()
    
    def test_already_fused_strand_blocked(
        self, api_client, ceo, cable_a, cable_b
    ):
        """Cannot fuse a strand that's already fused."""
        _, strands_a = cable_a
        _, strands_b = cable_b
        
        # First fusion
        api_client.post('/api/v1/inventory/fusions/', {
            "infrastructure_id": ceo.id,
            "tray": 1,
            "slot": 1,
            "fiber_a": strands_a[0].id,
            "fiber_b": strands_b[0].id,
        })
        
        # Try to fuse strand_a[0] again (should fail)
        response = api_client.post('/api/v1/inventory/fusions/', {
            "infrastructure_id": ceo.id,
            "tray": 1,
            "slot": 2,
            "fiber_a": strands_a[0].id,  # Already fused!
            "fiber_b": strands_b[1].id,
        })
        
        assert response.status_code == 409
        assert "já está fundida" in response.data["error"]
    
    def test_disconnect_frees_both_strands(
        self, api_client, ceo, cable_a, cable_b
    ):
        """Disconnecting should free both strands symmetrically."""
        _, strands_a = cable_a
        _, strands_b = cable_b
        
        # Create fusion
        api_client.post('/api/v1/inventory/fusions/', {
            "infrastructure_id": ceo.id,
            "tray": 1,
            "slot": 1,
            "fiber_a": strands_a[0].id,
            "fiber_b": strands_b[0].id,
        })
        
        # Disconnect
        response = api_client.post('/api/v1/inventory/fusion/disconnect/', {
            "infrastructure_id": ceo.id,
            "tray": 1,
            "slot": 1,
        })
        
        assert response.status_code == 200
        assert "liberadas" in response.data["message"]
        
        # Verify both strands are freed
        strands_a[0].refresh_from_db()
        strands_b[0].refresh_from_db()
        
        assert strands_a[0].fused_to is None
        assert strands_b[0].fused_to is None
        assert strands_a[0].fusion_slot is None
        assert strands_b[0].fusion_slot is None
        assert strands_a[0].status == "dark"
    
    def test_get_matrix_shows_correct_fibers(
        self, api_client, ceo, cable_a, cable_b
    ):
        """Matrix view should show actual fibers, not assume by slot number."""
        _, strands_a = cable_a
        _, strands_b = cable_b
        
        # Fusion: Aqua (12) <-> Azul (4) at Slot 1
        api_client.post('/api/v1/inventory/fusions/', {
            "infrastructure_id": ceo.id,
            "tray": 1,
            "slot": 1,
            "fiber_a": strands_a[11].id,
            "fiber_b": strands_b[3].id,
        })
        
        # Get matrix
        response = api_client.get(f'/api/v1/inventory/fusion/matrix/{ceo.id}/')
        
        assert response.status_code == 200
        matrix = response.data["matrix"]
        
        # Check Slot 1 has correct fibers
        assert "1-1" in matrix
        fusion = matrix["1-1"]
        
        assert "Aqua" in fusion["fiber_a"]["name"]
        assert "Azul" in fusion["fiber_b"]["name"]
        assert "12" in fusion["fiber_a"]["name"]  # FO number
        assert "4" in fusion["fiber_b"]["name"]
