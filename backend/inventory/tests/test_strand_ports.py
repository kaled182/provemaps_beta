"""EV-0134 — fibras: estado no diagrama (rompida > iluminada > fusionada > livre) e «Conectar a
porta» nas pontas Site A / Site B, com as validações do site e da porta ocupada."""

from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from inventory.models import (
    CableGroup,
    Device,
    FiberCable,
    FiberFusion,
    FiberInfrastructure,
    FiberStrand,
    OtdrAlert,
    Port,
    Site,
)
from inventory.usecases.cable_structure import ensure_cable_structure

pytestmark = pytest.mark.django_db


@pytest.fixture
def net():
    group = CableGroup.objects.create(name="12-FO", fiber_count=12)
    mandi = Site.objects.create(display_name="SITE - VILA MANDI", latitude=-9.0, longitude=-50.0)
    vlr = Site.objects.create(display_name="SITE - VILA RICA", latitude=-9.5, longitude=-50.5)
    sw_a = Device.objects.create(name="Huawei - Switch Vila Mandi", site=mandi)
    sw_b = Device.objects.create(name="Huawei - Switch Vila Rica", site=vlr)
    pa = Port.objects.create(device=sw_a, name="XGigabitEthernet0/0/3")
    pa2 = Port.objects.create(device=sw_a, name="XGigabitEthernet0/0/4")
    pb = Port.objects.create(device=sw_b, name="XGigabitEthernet0/0/1")
    cable = FiberCable.objects.create(
        name="MANDI - VLP", cable_group=group, site_a=mandi, site_b=vlr
    )
    ensure_cable_structure(cable)
    strands = list(FiberStrand.objects.filter(tube__cable=cable).order_by("absolute_number"))
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    return SimpleNamespace(cable=cable, strands=strands, pa=pa, pa2=pa2, pb=pb, c=c, mandi=mandi)


def url(net, strand):
    return f"/api/v1/fiber-cables/{net.cable.pk}/strands/{strand.pk}/port/"


def test_connect_both_ends_and_structure_shows_ports_state_and_ends(net):
    s1 = net.strands[0]
    r = net.c.post(
        url(net, s1), {"end": "a", "port_id": net.pa.pk}, content_type="application/json"
    )
    assert r.status_code == 200 and r.json()["state"] == "lit"
    assert (
        net.c.post(
            url(net, s1), {"end": "b", "port_id": net.pb.pk}, content_type="application/json"
        ).status_code
        == 200
    )
    body = net.c.get(f"/api/v1/fiber-cables/{net.cable.pk}/structure/").json()
    f1 = body["tubes"][0]["strands"][0]
    assert f1["state"] == "lit"
    assert f1["port_a"] == {
        "id": net.pa.pk,
        "name": "XGigabitEthernet0/0/3",
        "device_name": "Huawei - Switch Vila Mandi",
    }
    assert f1["port_b"]["name"] == "XGigabitEthernet0/0/1"
    assert body["tubes"][0]["strands"][1]["state"] == "free"
    assert body["ends"]["a"]["site_name"] == "SITE - VILA MANDI"
    ports_a = body["ends"]["a"]["devices"][0]["ports"]
    assert ports_a[0]["used_by"]["absolute_number"] == 1 and ports_a[1]["used_by"] is None
    assert body["otdr_alert"] is None
    # desligar
    net.c.post(url(net, s1), {"end": "a", "port_id": None}, content_type="application/json")
    s1.refresh_from_db()
    assert s1.connected_device_port_id is None and s1.connected_device_port_b_id == net.pb.pk


def test_port_must_be_of_the_end_site_and_free(net):
    s1, s2 = net.strands[0], net.strands[1]
    wrong = net.c.post(
        url(net, s1), {"end": "a", "port_id": net.pb.pk}, content_type="application/json"
    )
    assert wrong.status_code == 400 and "site da ponta A" in wrong.json()["detail"]
    net.c.post(url(net, s1), {"end": "a", "port_id": net.pa.pk}, content_type="application/json")
    busy = net.c.post(
        url(net, s2), {"end": "a", "port_id": net.pa.pk}, content_type="application/json"
    )
    assert busy.status_code == 400 and "já está ligada à fibra 1" in busy.json()["detail"]
    assert (
        net.c.post(
            url(net, s1), {"end": "x", "port_id": net.pa2.pk}, content_type="application/json"
        ).status_code
        == 400
    )


def test_fused_and_broken_states(net):
    other = FiberCable.objects.create(name="VLP - ELAGRO", cable_group=net.cable.cable_group)
    ensure_cable_structure(other)
    ceo = FiberInfrastructure.objects.create(
        cable=net.cable, type="splice_box", name="CEO-04", location="POINT(-50.2 -9.2)"
    )
    FiberFusion.objects.create(
        infrastructure=ceo,
        tray=1,
        slot=1,
        fiber_a=net.strands[2],
        fiber_b=FiberStrand.objects.filter(tube__cable=other).first(),
    )
    body = net.c.get(f"/api/v1/fiber-cables/{net.cable.pk}/structure/").json()
    assert body["tubes"][0]["strands"][2]["state"] == "fused"
    OtdrAlert.objects.create(
        cable=net.cable,
        direction="ab",
        otdr_m=1000,
        slack_pct=0,
        result={"map_distance_m": 985, "origin": {"name": "SITE - VILA MANDI"}},
    )
    body = net.c.get(f"/api/v1/fiber-cables/{net.cable.pk}/structure/").json()
    assert {s["state"] for s in body["tubes"][0]["strands"]} == {"broken"}
    assert body["otdr_alert"]["map_distance_m"] == 985
