"""EV-0060 — topologia: POPs pelos equipamentos das portas; ocupação só com fibras."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from inventory.models import BufferTube, CableGroup, Device, FiberCable, FiberStrand, Port, Site
from inventory.usecases.topology import build_topology


@pytest.fixture(autouse=True)
def _health():
    with patch(
        "inventory.usecases.topology.list_cables_optical_summary",
        return_value={"cables": []},
    ):
        yield


def _site(name, lat=-16.0, lng=-49.0):
    return Site.objects.create(display_name=name, latitude=lat, longitude=lng)


def _port(site, name):
    device = Device.objects.create(name=f"dev-{name}", site=site, zabbix_hostid=name)
    return Port.objects.create(device=device, name=name)


@pytest.mark.django_db
def test_edges_use_device_sites_and_unplaced_has_reasons():
    a, b = _site("POP A", -16.0, -49.0), _site("POP B", -16.5, -49.5)
    group = CableGroup.objects.create(name="Backbone 36", fiber_count=36)
    FiberCable.objects.create(
        name="A-B", origin_port=_port(a, "a1"), destination_port=_port(b, "b1"), cable_group=group
    )
    FiberCable.objects.create(
        name="A-A", origin_port=_port(a, "a2"), destination_port=_port(a, "a3")
    )
    FiberCable.objects.create(name="solto")

    topo = build_topology()
    assert [n["name"] for n in topo["nodes"]] == ["POP A", "POP B"]
    edge = topo["edges"][0]
    assert (edge["name"], edge["source"], edge["target"]) == ("A-B", a.id, b.id)
    assert edge["fiber_count"] == 36
    assert edge["occupancy"] is None  # sem fibras cadastradas: nunca 0 inventado
    reasons = {u["name"]: u["reason"] for u in topo["unplaced"]}
    assert reasons["A-A"].startswith("as duas pontas no mesmo site")
    assert reasons["solto"] == "sem site numa das pontas"
    assert topo["strands_registered"] == 0


@pytest.mark.django_db
def test_occupancy_counts_registered_strands():
    a, b = _site("POP A"), _site("POP B", -17.0, -50.0)
    cable = FiberCable.objects.create(
        name="A-B", origin_port=_port(a, "a1"), destination_port=_port(b, "b1")
    )
    tube = BufferTube.objects.create(cable=cable, number=1, color="azul", color_hex="#0000ff")
    for i, status in enumerate(["lit", "lit", "reserved", "dark", "broken"], start=1):
        FiberStrand.objects.create(
            tube=tube, number=i, absolute_number=i, color="c", color_hex="#000000", status=status
        )
    edge = build_topology()["edges"][0]
    assert edge["occupancy"] == {"registered": 5, "used": 3, "free": 1, "broken": 1}


@pytest.mark.django_db
def test_endpoint_requires_login():
    url = "/api/v1/fiber-cables/topology/"
    assert Client().get(url).status_code in (401, 403, 302)
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    assert set(c.get(url).json()) == {"nodes", "edges", "unplaced", "strands_registered"}
