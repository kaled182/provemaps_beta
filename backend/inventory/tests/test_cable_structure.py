"""EV-0133 — estrutura física do cabo: perfil pelo grupo, tubos/fibras ABNT, cabo sem grupo
pede o perfil, criação já com estrutura, e a ocupação (iluminadas ou fusionadas / total)."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from inventory.models import (
    BufferTube,
    CableGroup,
    Device,
    FiberCable,
    FiberFusion,
    FiberInfrastructure,
    FiberProfile,
    FiberStrand,
    Port,
    Site,
)
from inventory.usecases.cable_structure import ensure_cable_structure

pytestmark = pytest.mark.django_db


@pytest.fixture
def profiles():
    """Os perfis vêm da migração de dados do inventário (1, 2, 6, 12, 36, 48, 72, 144 FO)."""
    return {
        n: FiberProfile.objects.filter(total_fibers=n).order_by("id").first()
        for n in (2, 6, 12, 36)
    }


@pytest.fixture
def client():
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    return c


def test_profile_from_the_group_and_abnt_colors(profiles):
    group = CableGroup.objects.create(name="FURUKAWA AS120 36-FO", fiber_count=36)
    cable = FiberCable.objects.create(name="MANDI - VLP", cable_group=group)
    assert ensure_cable_structure(cable) == {"created": True, "needs_profile": False}
    cable.refresh_from_db()
    assert cable.profile == profiles[36]
    tubes = list(
        BufferTube.objects.filter(cable=cable).order_by("number").values_list("color", flat=True)
    )
    assert tubes == ["Verde", "Amarelo", "Branco"]
    strands = FiberStrand.objects.filter(tube__cable=cable).order_by("absolute_number")
    assert strands.count() == 36
    assert [s.color for s in strands[:4]] == ["Verde", "Amarelo", "Branco", "Azul"]
    assert strands[12].number == 1 and strands[12].absolute_number == 13  # 1.ª fibra do 2.º tubo
    assert ensure_cable_structure(cable)["created"] is False  # idempotente


def test_structure_endpoint_generates_and_cable_without_group_asks_for_profile(profiles, client):
    group = CableGroup.objects.create(name="FURUKAWA AS120 12-FO", fiber_count=12)
    with_group = FiberCable.objects.create(name="A", cable_group=group)
    body = client.get(f"/api/v1/fiber-cables/{with_group.pk}/structure/").json()
    assert (
        body["needs_profile"] is False
        and len(body["tubes"]) == 1
        and len(body["tubes"][0]["strands"]) == 12
    )

    orphan = FiberCable.objects.create(name="JBS-CFS")
    body = client.get(f"/api/v1/fiber-cables/{orphan.pk}/structure/").json()
    assert body["needs_profile"] is True and body["tubes"] == []
    assert [p["total_fibers"] for p in body["available_profiles"]] == sorted(
        FiberProfile.objects.values_list("total_fibers", flat=True)
    )
    url = f"/api/v1/fiber-cables/{orphan.pk}/structure/profile/"
    assert (
        client.post(url, {"profile_id": profiles[12].pk}, content_type="application/json").json()[
            "created"
        ]
        is True
    )
    assert FiberStrand.objects.filter(tube__cable=orphan).count() == 12
    again = client.post(url, {"profile_id": profiles[36].pk}, content_type="application/json")
    assert again.status_code == 400  # já tem estrutura


def test_occupancy_counts_lit_or_fused_strands(profiles, client):
    group = CableGroup.objects.create(name="12-FO", fiber_count=12)
    site = Site.objects.create(display_name="SITE - VILA MANDI", latitude=-9.0, longitude=-50.0)
    sw = Device.objects.create(name="SW", site=site)
    port = Port.objects.create(device=sw, name="XGE0/0/3")
    cable = FiberCable.objects.create(name="C1", cable_group=group)
    other = FiberCable.objects.create(name="C2", cable_group=group)
    ensure_cable_structure(cable)
    ensure_cable_structure(other)
    s = list(FiberStrand.objects.filter(tube__cable=cable).order_by("absolute_number"))
    s[0].connected_device_port = port  # iluminada (ligada a uma porta)
    s[0].save()
    s[1].status = "lit"
    s[1].save()
    ceo = FiberInfrastructure.objects.create(
        cable=cable, type="splice_box", name="CEO-04", location="POINT(-50 -9)"
    )
    FiberFusion.objects.create(
        infrastructure=ceo,
        tray=1,
        slot=1,
        fiber_a=s[2],
        fiber_b=FiberStrand.objects.filter(tube__cable=other).first(),
    )
    occ = client.get(f"/api/v1/fiber-cables/{cable.pk}/").json()["occupancy"]
    assert (occ["registered"], occ["used"]) == (12, 3)


def test_new_cable_is_born_with_its_structure(profiles):
    """Pelo caminho real de criação (inventário → create_manual_fiber)."""
    from inventory.usecases.fibers import create_manual_fiber

    group = CableGroup.objects.create(name="12-FO", fiber_count=12)
    site = Site.objects.create(display_name="S", latitude=-9.0, longitude=-50.0)
    a = Device.objects.create(name="A", site=site)
    b = Device.objects.create(name="B", site=site)
    pa = Port.objects.create(device=a, name="p1")
    pb = Port.objects.create(device=b, name="p2")
    create_manual_fiber(
        {
            "name": "NOVO",
            "origin_device_id": a.pk,
            "origin_port_id": pa.pk,
            "dest_device_id": b.pk,
            "dest_port_id": pb.pk,
            "path": [{"lat": -9.0, "lng": -50.0}, {"lat": -9.01, "lng": -50.0}],
            "cable_group_id": group.pk,
        }
    )
    assert FiberStrand.objects.filter(tube__cable__name="NOVO").count() == 12
