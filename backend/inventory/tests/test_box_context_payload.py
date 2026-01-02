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


def _extract_strand(segments, direction, strand_id):
    for segment in segments:
        if segment.get("direction") != direction:
            continue
        for tube_payload in segment["tubes"]:
            for strand_payload in tube_payload["strands"]:
                if strand_payload["id"] == strand_id:
                    return strand_payload
    return None


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

    incoming_strand = _extract_strand(segments, "IN", strand.pk)
    outgoing_strand = _extract_strand(segments, "OUT", strand.pk)

    assert incoming_strand is not None, "Expected incoming strand payload not found"
    assert outgoing_strand is not None, "Expected outgoing strand payload not found"

    assert incoming_strand["is_primary_render"] is True
    assert outgoing_strand["is_primary_render"] is False

    assert incoming_strand["fusion_count"] == 2
    assert incoming_strand["has_multiple_fusions"] is True
    assert incoming_strand["is_fused_here"] is True
    assert incoming_strand["fused_elsewhere"] is True
    assert incoming_strand["fused_on_other_segment"] is False
    assert incoming_strand["blocked_segment_direction"] is None
    assert incoming_strand["primary_fusion"]["id"] == fusion_local.id
    assert incoming_strand["primary_peer_fiber_id"] == peer_strand_a.id

    assert outgoing_strand["is_fused_here"] is False
    assert outgoing_strand["fused_elsewhere"] is True
    assert outgoing_strand["fused_on_other_segment"] is True
    assert outgoing_strand["blocked_segment_direction"] == "IN"

    fusion_ids = {fusion["id"] for fusion in incoming_strand["fusions"]}
    assert fusion_remote.id in fusion_ids
    assert any(not fusion["is_local"] for fusion in incoming_strand["fusions"])


@pytest.mark.django_db
def test_box_context_local_fusion_only_affects_incoming_segment(
    authenticated_api_client,
):
    site_a = Site.objects.create(display_name="POP A", city="Brasília")
    site_b = Site.objects.create(display_name="POP B", city="Anápolis")

    cable = FiberCable.objects.create(
        name="CABO-PASSANTE",
        site_a=site_a,
        site_b=site_b,
        length_km=5,
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

    peer_cable = FiberCable.objects.create(name="CABO-PEER", site_a=site_b)
    peer_tube = BufferTube.objects.create(
        cable=peer_cable,
        number=1,
        color="Vermelho",
        color_hex="#FF0000",
    )
    peer_strand = FiberStrand.objects.create(
        tube=peer_tube,
        number=2,
        absolute_number=2,
        color="Amarelo",
        color_hex="#FFFF00",
        status=FiberStrand.STATUS_DARK,
    )

    current_box = FiberInfrastructure.objects.create(
        cable=cable,
        type="splice_box",
        name="CEO-CENTRAL",
        location=Point(-47.92, -15.78, srid=4326),
        distance_from_origin=1000,
    )
    FiberInfrastructure.objects.create(
        cable=cable,
        type="splice_box",
        name="CEO-PRÓXIMA",
        location=Point(-47.90, -15.77, srid=4326),
        distance_from_origin=2500,
    )

    FiberFusion.objects.create(
        infrastructure=current_box,
        tray=1,
        slot=1,
        fiber_a=strand,
        fiber_b=peer_strand,
    )

    response = authenticated_api_client.get(
        f"/api/v1/inventory/splice-boxes/{current_box.pk}/context/"
    )

    assert response.status_code == 200
    segments = response.json()

    incoming_strand = _extract_strand(segments, "IN", strand.pk)
    outgoing_strand = _extract_strand(segments, "OUT", strand.pk)

    assert incoming_strand is not None
    assert outgoing_strand is not None

    assert incoming_strand["is_primary_render"] is True
    assert outgoing_strand["is_primary_render"] is False

    assert incoming_strand["is_fused_here"] is True
    assert incoming_strand["fused_elsewhere"] is False
    assert incoming_strand["fused_on_other_segment"] is False
    assert incoming_strand["blocked_segment_direction"] is None

    assert outgoing_strand["is_fused_here"] is False
    assert outgoing_strand["fused_elsewhere"] is False
    assert outgoing_strand["fused_on_other_segment"] is True
    assert outgoing_strand["blocked_segment_direction"] == "IN"


@pytest.mark.django_db
def test_box_context_remote_fusion_only_marks_as_fused_elsewhere(
    authenticated_api_client,
):
    site_a = Site.objects.create(display_name="POP A", city="Brasília")
    site_b = Site.objects.create(display_name="POP B", city="Anápolis")

    cable = FiberCable.objects.create(
        name="CABO-REMOTO",
        site_a=site_a,
        site_b=site_b,
        length_km=5,
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

    peer_cable = FiberCable.objects.create(name="CABO-REMOTO-PEER", site_a=site_b)
    peer_tube = BufferTube.objects.create(
        cable=peer_cable,
        number=1,
        color="Vermelho",
        color_hex="#FF0000",
    )
    peer_strand = FiberStrand.objects.create(
        tube=peer_tube,
        number=2,
        absolute_number=2,
        color="Amarelo",
        color_hex="#FFFF00",
        status=FiberStrand.STATUS_DARK,
    )

    current_box = FiberInfrastructure.objects.create(
        cable=cable,
        type="splice_box",
        name="CEO-LOCAL",
        location=Point(-47.92, -15.78, srid=4326),
        distance_from_origin=1000,
    )
    remote_box = FiberInfrastructure.objects.create(
        cable=cable,
        type="splice_box",
        name="CEO-REMOTA",
        location=Point(-47.90, -15.77, srid=4326),
        distance_from_origin=2500,
    )

    FiberFusion.objects.create(
        infrastructure=remote_box,
        tray=1,
        slot=1,
        fiber_a=strand,
        fiber_b=peer_strand,
    )

    response = authenticated_api_client.get(
        f"/api/v1/inventory/splice-boxes/{current_box.pk}/context/"
    )

    assert response.status_code == 200
    segments = response.json()

    incoming_strand = _extract_strand(segments, "IN", strand.pk)
    outgoing_strand = _extract_strand(segments, "OUT", strand.pk)

    assert incoming_strand is not None
    assert outgoing_strand is not None

    assert incoming_strand["is_primary_render"] is True
    assert outgoing_strand["is_primary_render"] is False

    assert incoming_strand["is_fused_here"] is False
    assert outgoing_strand["is_fused_here"] is False

    assert incoming_strand["fused_elsewhere"] is True
    assert outgoing_strand["fused_elsewhere"] is True
    assert incoming_strand["fused_on_other_segment"] is False
    assert outgoing_strand["fused_on_other_segment"] is False
    assert incoming_strand["blocked_segment_direction"] is None
    assert outgoing_strand["blocked_segment_direction"] is None
