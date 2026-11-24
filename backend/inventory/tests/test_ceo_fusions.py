"""EV-0136 — fusões na CEO (pontas fibra/lado, validações) e rastreamento da luz fim-a-fim:
porta → cabo-tronco → fusão na CEO → derivado → porta; sangria passa direto, corte acaba na caixa,
fibra sangrada acaba no lado sem emenda; rompimento OTDR ativo para a luz."""

from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString
from django.test import Client

from inventory.models import (
    CableGroup,
    Device,
    FiberCable,
    FiberInfrastructure,
    FiberStrand,
    Port,
    Site,
)
from inventory.usecases.ceo import create_ceo, derive_cable
from inventory.usecases.ceo_fusions import ceo_fusions, create_fusion, delete_fusion, trace_light
from inventory.usecases.devices_common import InventoryValidationError
from inventory.usecases.strand_ports import connect_strand_port

pytestmark = pytest.mark.django_db


def _fiber(cable, n):
    return FiberStrand.objects.get(tube__cable=cable, absolute_number=n)


@pytest.fixture
def net():
    group = CableGroup.objects.create(name="12-FO", fiber_count=12, attenuation_db_per_km=0.35)
    mandi = Site.objects.create(display_name="SITE - VILA MANDI", latitude=0.0, longitude=-50.0)
    rica = Site.objects.create(display_name="SITE - VILA RICA", latitude=0.09, longitude=-50.0)
    nova = Site.objects.create(display_name="SITE - VILA NOVA", latitude=0.045, longitude=-49.95)
    olt = Device.objects.create(name="OLT Mandi", site=mandi)
    sw = Device.objects.create(name="SW Vila Nova", site=nova)
    pon = Port.objects.create(device=olt, name="gpon 1/1/1")
    ge = Port.objects.create(device=sw, name="ge-0/0/1")
    from inventory.usecases.cable_structure import ensure_cable_structure

    trunk = FiberCable.objects.create(
        name="MANDI - VLP",
        site_a=mandi,
        site_b=rica,
        cable_group=group,
        length_km=10,
        path=LineString([(-50.0, 0.0), (-50.0, 0.09)], srid=4326),
    )
    ensure_cable_structure(trunk)
    ceo = create_ceo(trunk.pk, lat=0.045, lng=-50.0, name="CEO-04")
    derived = FiberCable.objects.get(
        pk=derive_cable(
            ceo["id"],
            name="CEO-04 - VILA NOVA",
            path=[{"lat": 0.045, "lng": -49.95}],
            cable_group_id=group.pk,
            to_site_id=nova.pk,
        )["id"]
    )
    connect_strand_port(trunk.pk, _fiber(trunk, 1).pk, end="a", port_id=pon.pk)
    connect_strand_port(derived.pk, _fiber(derived, 1).pk, end="b", port_id=ge.pk)
    return SimpleNamespace(trunk=trunk, derived=derived, ceo=ceo["id"], pon=pon, ge=ge)


def test_ends_available_in_the_ceo(net):
    d = ceo_fusions(net.ceo)
    roles = {c["name"]: (c["role"], len(c["ends"])) for c in d["cables"]}
    assert roles == {"MANDI - VLP": ("tronco", 24), "CEO-04 - VILA NOVA": ("derivado", 12)}
    trunk_f1 = [e for e in d["cables"][0]["ends"] if e["absolute_number"] == 1]
    assert [(e["side"], e["toward"]) for e in trunk_f1] == [
        ("a", "SITE - VILA MANDI"),
        ("b", "SITE - VILA RICA"),
    ]


def test_trace_port_trunk_fusion_derived_port(net):
    f1, d1 = _fiber(net.trunk, 1), _fiber(net.derived, 1)
    create_fusion(
        net.ceo, a={"strand_id": f1.pk, "side": "a"}, b={"strand_id": d1.pk}, tray=1, slot=1
    )
    t = trace_light(f1.pk, start="a")
    kinds = [s["type"] for s in t["steps"]]
    assert kinds == ["port", "cable", "fusion", "cable", "port"]
    assert t["steps"][0]["port_name"] == "gpon 1/1/1" and t["steps"][-1]["port_name"] == "ge-0/0/1"
    assert t["steps"][1]["km"] == pytest.approx(4.976, abs=0.05)
    assert t["steps"][2]["ceo_name"] == "CEO-04" and t["end"]["reason"] == "port"
    assert t["fusions"] == 1 and t["loss_db_estimate"] is not None
    # ao contrário: da ponta B do derivado chega à porta da OLT
    back = trace_light(d1.pk, start="b")
    assert back["end"] == {"reason": "port", "label": "OLT Mandi → gpon 1/1/1"}
    # a metade do lado B da fibra sangrada acaba na CEO (o lado A foi para o derivado)
    rest = trace_light(f1.pk, start="b")
    assert rest["end"]["reason"] == "dead_end" and "CEO-04" in rest["end"]["label"]


def test_sangria_passes_through_and_corte_stops(net):
    f2 = _fiber(net.trunk, 2)
    t = trace_light(f2.pk, start="a")
    assert t["steps"][0]["passes"] == ["CEO-04"]
    assert t["end"]["reason"] == "dead_end" and "SITE - VILA RICA" in t["end"]["label"]
    infra = FiberInfrastructure.objects.get(pk=net.ceo)
    infra.metadata = {**infra.metadata, "mode": "corte"}
    infra.save()
    t = trace_light(f2.pk, start="a")
    assert t["end"]["reason"] == "dead_end" and "cortada na CEO-04" in t["end"]["label"]


def test_fusion_validations_and_delete(net):
    f1, f2, d1 = _fiber(net.trunk, 1), _fiber(net.trunk, 2), _fiber(net.derived, 1)
    with pytest.raises(InventoryValidationError, match="lado"):
        create_fusion(net.ceo, a={"strand_id": f1.pk}, b={"strand_id": d1.pk})
    with pytest.raises(InventoryValidationError, match="mesma"):
        create_fusion(
            net.ceo, a={"strand_id": f1.pk, "side": "a"}, b={"strand_id": f1.pk, "side": "a"}
        )
    other = FiberCable.objects.create(name="OUTRO", cable_group=net.trunk.cable_group)
    from inventory.usecases.cable_structure import ensure_cable_structure

    ensure_cable_structure(other)
    with pytest.raises(InventoryValidationError, match="não passa nesta CEO"):
        create_fusion(net.ceo, a={"strand_id": _fiber(other, 1).pk}, b={"strand_id": d1.pk})
    fu = create_fusion(
        net.ceo, a={"strand_id": f1.pk, "side": "a"}, b={"strand_id": d1.pk}, tray=1, slot=1
    )
    with pytest.raises(InventoryValidationError, match="já está emendada"):
        create_fusion(net.ceo, a={"strand_id": f2.pk, "side": "a"}, b={"strand_id": d1.pk})
    with pytest.raises(InventoryValidationError, match="ocupada"):
        create_fusion(
            net.ceo,
            a={"strand_id": f2.pk, "side": "a"},
            b={"strand_id": f2.pk, "side": "b"},
            tray=1,
            slot=1,
        )
    with pytest.raises(InventoryValidationError, match="bandeja"):
        create_fusion(
            net.ceo,
            a={"strand_id": f2.pk, "side": "a"},
            b={"strand_id": f2.pk, "side": "b"},
            tray=9,
        )
    assert ceo_fusions(net.ceo)["fusions"][0]["id"] == fu["id"]
    delete_fusion(net.ceo, fu["id"])
    assert ceo_fusions(net.ceo)["fusions"] == []


def test_endpoints(net):
    url = f"/api/v1/inventory/ceos/{net.ceo}/fusions/"
    assert Client().get(url).status_code in (401, 403, 302)
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    f1, d1 = _fiber(net.trunk, 1), _fiber(net.derived, 1)
    r = c.post(
        url,
        {"a": {"strand_id": f1.pk, "side": "a"}, "b": {"strand_id": d1.pk}},
        content_type="application/json",
    )
    assert r.status_code == 201
    assert (
        c.post(
            url,
            {"a": {"strand_id": f1.pk, "side": "a"}, "b": {"strand_id": d1.pk}},
            content_type="application/json",
        ).status_code
        == 400
    )
    t = c.get(f"/api/v1/inventory/strands/{f1.pk}/trace/", {"from": "a"}).json()
    assert t["end"]["reason"] == "port"
    assert c.delete(f"{url}{r.json()['id']}/").status_code == 204
