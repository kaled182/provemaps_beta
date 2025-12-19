import pytest
from django.contrib.gis.geos import Point

from inventory.models import (
    BufferTube,
    FiberCable,
    FiberFusion,
    FiberInfrastructure,
    FiberStrand,
    Site,
)


@pytest.mark.django_db
def test_box_context_returns_enhanced_fusion_payload(
    authenticated_api_client,
):
    site_a = Site.objects.create(display_name="POP A", city="Brasília")
    site_b = Site.objects.create(display_name="POP B", city="Anápolis")

    cable = FiberCable.objects.create(
        name="CABO-BACKBONE",
        site_a=site_a,
        site_b=site_b,
        length_km=10,
    )
    tube = BufferTube.objects.create(
        cable=cable,
        number=1,
        color="Azul",
        color_hex="#0000FF",
    )
    strand = FiberStrand.objects.create(
        tube=tube,
        number=1,
        absolute_number=1,
        color="Verde",
        color_hex="#00FF00",
        status=FiberStrand.STATUS_DARK,
    )

    peer_cable_a = FiberCable.objects.create(name="CABO-PEER-A", site_a=site_b)
    peer_tube_a = BufferTube.objects.create(
        cable=peer_cable_a,
        number=1,
        color="Vermelho",
        color_hex="#FF0000",
    )
    peer_strand_a = FiberStrand.objects.create(
        tube=peer_tube_a,
        number=3,
        absolute_number=3,
        color="Amarelo",
        color_hex="#FFFF00",
        status=FiberStrand.STATUS_DARK,
    )

    peer_cable_b = FiberCable.objects.create(name="CABO-PEER-B", site_a=site_b)
    peer_tube_b = BufferTube.objects.create(
        cable=peer_cable_b,
        number=1,
        color="Branco",
        color_hex="#FFFFFF",
    )
    peer_strand_b = FiberStrand.objects.create(
        tube=peer_tube_b,
        number=4,
        absolute_number=4,
        color="Roxo",
        color_hex="#800080",
        status=FiberStrand.STATUS_DARK,
    )

    box_current = FiberInfrastructure.objects.create(
        cable=cable,
        type="splice_box",
        name="CEO-ATUAL",
        location=Point(-47.92, -15.78, srid=4326),
        distance_from_origin=1500,
    )
    box_next = FiberInfrastructure.objects.create(
        cable=cable,
        type="splice_box",
        name="CEO-PROXIMO",
        location=Point(-47.90, -15.77, srid=4326),
        distance_from_origin=3500,
    )

    fusion_local = FiberFusion.objects.create(
        infrastructure=box_current,
        tray=1,
        slot=1,
        fiber_a=strand,
        fiber_b=peer_strand_a,
    )
    fusion_remote = FiberFusion.objects.create(
        infrastructure=box_next,
        tray=1,
        slot=2,
        fiber_a=strand,
        fiber_b=peer_strand_b,
    )

    response = authenticated_api_client.get(
        f"/api/v1/inventory/splice-boxes/{box_current.pk}/context/"
    )

    assert response.status_code == 200
    segments = response.json()
    assert segments, "Box context must return at least one segment"

    target_strand = None
    for segment in segments:
        for tube_payload in segment["tubes"]:
            for strand_payload in tube_payload["strands"]:
                if strand_payload["id"] == strand.pk:
                    target_strand = strand_payload
                    break
            if target_strand:
                break
        if target_strand:
            break

    assert target_strand is not None, "Expected strand payload not found"
    assert target_strand["fusion_count"] == 2
    assert target_strand["has_multiple_fusions"] is True
    assert target_strand["is_fused_here"] is True
    assert target_strand["fused_elsewhere"] is True
    assert target_strand["primary_fusion"]["id"] == fusion_local.id
    assert target_strand["primary_peer_fiber_id"] == peer_strand_a.id

    fusion_ids = {fusion["id"] for fusion in target_strand["fusions"]}
    assert fusion_remote.id in fusion_ids
    assert any(not fusion["is_local"] for fusion in target_strand["fusions"])
