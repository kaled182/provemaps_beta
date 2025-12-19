"""
Tests for Fusion API - Atomic 1:1 Logic.

Tests the corrected fusion logic that ensures:
1. Fusion is atomic (Strand A <-> Strand B only)
2. No side effects on other fibers
3. Physical slot occupation is independent of fiber color/number
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.db.models import Q
from rest_framework.test import APIClient

from inventory.models import (
    Site,
    FiberCable,
    BufferTube,
    FiberStrand,
    FiberFusion,
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
        name="Cabo-Entrada",
        site_a=site,
    )
    
    tube = BufferTube.objects.create(
        cable=cable,
        number=1,
        color="Azul",
        color_hex="#0000FF",
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
        name="Cabo-Saida",
        site_a=site,
    )
    
    tube = BufferTube.objects.create(
        cable=cable,
        number=1,
        color="Azul",
        color_hex="#0000FF",
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
        response1 = api_client.post(
            '/api/v1/inventory/fusions/',
            {
                "infrastructure_id": ceo.id,
                "tray": 1,
                "slot": 1,
                "fiber_a": strands_a[11].id,  # Aqua (12th fiber)
                "fiber_b": strands_b[3].id,   # Azul (4th fiber)
            },
            format='json',
        )
        
        assert response1.status_code == 201
        fusion1 = FiberFusion.objects.get(
            infrastructure=ceo,
            tray=1,
            slot=1,
        )
        assert fusion1.fiber_a_id == strands_a[11].id
        assert fusion1.fiber_b_id == strands_b[3].id
        
        # Fusion 2: FO-1 (Verde) from A with FO-1 (Verde) from B at Slot 2
        # This should SUCCEED because Slot 2 is free
        response2 = api_client.post(
            '/api/v1/inventory/fusions/',
            {
                "infrastructure_id": ceo.id,
                "tray": 1,
                "slot": 2,
                "fiber_a": strands_a[0].id,  # Verde (1st fiber)
                "fiber_b": strands_b[0].id,  # Verde (1st fiber)
            },
            format='json',
        )
        
        assert response2.status_code == 201
        fusion2 = FiberFusion.objects.get(
            infrastructure=ceo,
            tray=1,
            slot=2,
        )
        assert fusion2.fiber_a_id == strands_a[0].id
        assert fusion2.fiber_b_id == strands_b[0].id

        assert (
            FiberFusion.objects.filter(infrastructure=ceo).count() == 2
        )
    
    def test_same_slot_blocked(self, api_client, ceo, cable_a, cable_b):
        """Physical slot must be exclusive."""
        _, strands_a = cable_a
        _, strands_b = cable_b
        
        # First fusion at Slot 1
        api_client.post(
            '/api/v1/inventory/fusions/',
            {
                "infrastructure_id": ceo.id,
                "tray": 1,
                "slot": 1,
                "fiber_a": strands_a[0].id,
                "fiber_b": strands_b[0].id,
            },
            format='json',
        )
        
        # Try to use same slot (should fail)
        response = api_client.post(
            '/api/v1/inventory/fusions/',
            {
                "infrastructure_id": ceo.id,
                "tray": 1,
                "slot": 1,  # Same slot!
                "fiber_a": strands_a[1].id,
                "fiber_b": strands_b[1].id,
            },
            format='json',
        )
        
        assert response.status_code == 409  # Conflict
        assert "ocupado" in response.data["detail"].lower()
        assert (
            FiberFusion.objects.filter(infrastructure=ceo, tray=1, slot=1)
            .count()
            == 1
        )
    
    def test_refuse_moves_existing_strand(
        self, api_client, ceo, cable_a, cable_b
    ):
        """Re-fusing a strand should move it to the new slot."""
        _, strands_a = cable_a
        _, strands_b = cable_b
        
        # First fusion
        api_client.post(
            '/api/v1/inventory/fusions/',
            {
                "infrastructure_id": ceo.id,
                "tray": 1,
                "slot": 1,
                "fiber_a": strands_a[0].id,
                "fiber_b": strands_b[0].id,
            },
            format='json',
        )
        
        # Fuse strand_a[0] again in a different slot (should replace)
        response = api_client.post(
            '/api/v1/inventory/fusions/',
            {
                "infrastructure_id": ceo.id,
                "tray": 1,
                "slot": 2,
                "fiber_a": strands_a[0].id,  # Already fused!
                "fiber_b": strands_b[1].id,
            },
            format='json',
        )
        
        assert response.status_code == 201
        assert not FiberFusion.objects.filter(
            infrastructure=ceo,
            tray=1,
            slot=1,
        ).exists()
        replacement = FiberFusion.objects.get(
            infrastructure=ceo,
            tray=1,
            slot=2,
        )
        assert replacement.fiber_a_id == strands_a[0].id
        assert replacement.fiber_b_id == strands_b[1].id
    
    def test_disconnect_frees_both_strands(
        self, api_client, ceo, cable_a, cable_b
    ):
        """Disconnecting should free both strands symmetrically."""
        _, strands_a = cable_a
        _, strands_b = cable_b
        
        # Create fusion
        api_client.post(
            '/api/v1/inventory/fusions/',
            {
                "infrastructure_id": ceo.id,
                "tray": 1,
                "slot": 1,
                "fiber_a": strands_a[0].id,
                "fiber_b": strands_b[0].id,
            },
            format='json',
        )
        
        assert FiberFusion.objects.filter(infrastructure=ceo).exists()

        # Disconnect
        response = api_client.delete(
            f'/api/v1/inventory/fusions/{strands_a[0].id}/'
        )

        assert response.status_code == 204
        assert not FiberFusion.objects.filter(
            Q(fiber_a=strands_a[0]) | Q(fiber_b=strands_a[0])
        ).exists()
        assert not FiberFusion.objects.filter(
            Q(fiber_a=strands_b[0]) | Q(fiber_b=strands_b[0])
        ).exists()
    
    def test_get_matrix_shows_correct_fibers(
        self, api_client, ceo, cable_a, cable_b
    ):
        """Matrix view should show actual fibers, not assume by slot number."""
        _, strands_a = cable_a
        _, strands_b = cable_b
        
        # Fusion: Aqua (12) <-> Azul (4) at Slot 1
        response = api_client.post(
            '/api/v1/inventory/fusions/',
            {
                "infrastructure_id": ceo.id,
                "tray": 1,
                "slot": 1,
                "fiber_a": strands_a[11].id,
                "fiber_b": strands_b[3].id,
            },
            format='json',
        )
        assert response.status_code == 201
        fusion = FiberFusion.objects.get(
            infrastructure=ceo,
            tray=1,
            slot=1,
        )
        
        # Get matrix
        response = api_client.get(
            f'/api/v1/inventory/splice-boxes/{ceo.id}/matrix/'
        )
        
        assert response.status_code == 200
        matrix = response.data["matrix"]
        
        # Check Slot 1 has correct fibers
        assert "1-1" in matrix
        fusion_payload = matrix["1-1"]

        assert fusion_payload["fusion_id"] == fusion.pk
        assert fusion_payload["fiber_a"]["cable"] == "Cabo-Entrada"
        assert fusion_payload["fiber_a"]["number"] == 12
        assert fusion_payload["fiber_a"]["color"] == "Aqua"
        assert fusion_payload["fiber_b"]["cable"] == "Cabo-Saida"
        assert fusion_payload["fiber_b"]["number"] == 4
        assert fusion_payload["fiber_b"]["color"] == "Azul"
