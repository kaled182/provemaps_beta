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
from inventory.serializers import FiberStrandSerializer


@pytest.mark.django_db
def test_fiberstrand_serializer_includes_multi_fusion_metadata():
    site = Site.objects.create(display_name="Site A", city="Brasília")
    peer_site = Site.objects.create(display_name="Site B", city="Goiânia")

    main_cable = FiberCable.objects.create(name="CABO-PRINCIPAL", site_a=site)
    main_tube = BufferTube.objects.create(
        cable=main_cable,
        number=1,
        color="Azul",
        color_hex="#0000FF",
    )
    main_strand = FiberStrand.objects.create(
        tube=main_tube,
        number=1,
        absolute_number=1,
        color="Verde",
        color_hex="#00FF00",
        status=FiberStrand.STATUS_DARK,
    )

    peer_cable_one = FiberCable.objects.create(name="CABO-PEER-1", site_a=peer_site)
    peer_tube_one = BufferTube.objects.create(
        cable=peer_cable_one,
        number=1,
        color="Vermelho",
        color_hex="#FF0000",
    )
    peer_strand_one = FiberStrand.objects.create(
        tube=peer_tube_one,
        number=5,
        absolute_number=5,
        color="Laranja",
        color_hex="#FFA500",
        status=FiberStrand.STATUS_DARK,
    )

    peer_cable_two = FiberCable.objects.create(name="CABO-PEER-2", site_a=peer_site)
    peer_tube_two = BufferTube.objects.create(
        cable=peer_cable_two,
        number=1,
        color="Amarelo",
        color_hex="#FFFF00",
    )
    peer_strand_two = FiberStrand.objects.create(
        tube=peer_tube_two,
        number=7,
        absolute_number=7,
        color="Branco",
        color_hex="#FFFFFF",
        status=FiberStrand.STATUS_DARK,
    )

    box_one = FiberInfrastructure.objects.create(
        cable=main_cable,
        type="splice_box",
        name="CEO-01",
        location=Point(-47.88, -15.78, srid=4326),
        distance_from_origin=1000,
    )
    box_two = FiberInfrastructure.objects.create(
        cable=main_cable,
        type="splice_box",
        name="CEO-02",
        location=Point(-47.87, -15.77, srid=4326),
        distance_from_origin=2000,
    )

    fusion_one = FiberFusion.objects.create(
        infrastructure=box_one,
        tray=1,
        slot=1,
        fiber_a=main_strand,
        fiber_b=peer_strand_one,
    )
    fusion_two = FiberFusion.objects.create(
        infrastructure=box_two,
        tray=1,
        slot=2,
        fiber_a=main_strand,
        fiber_b=peer_strand_two,
    )

    data = FiberStrandSerializer(main_strand).data

    assert data["fusion_count"] == 2
    assert data["has_multiple_fusions"] is True
    assert data["primary_fusion"]["id"] == fusion_one.id
    assert data["primary_peer"]["id"] == peer_strand_one.id
    assert data["fused_to"] == peer_strand_one.id
    fusion_ids = {fusion["id"] for fusion in data["fusions"]}
    assert fusion_one.id in fusion_ids
    assert fusion_two.id in fusion_ids
    assert {
        fusion["peer_color"]
        for fusion in data["fusions"]
    } == {"Laranja", "Branco"}
