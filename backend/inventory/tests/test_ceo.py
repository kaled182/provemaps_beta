"""EV-0135 — CEO no traçado (ponto projetado, km, modo, reserva, bandejas) e cabos derivados
que nascem na CEO (traçado a partir dela, destino site/porta ou outra CEO, estrutura gerada)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString
from django.test import Client

from inventory.models import CableGroup, Device, FiberCable, FiberStrand, Port, Site
from inventory.usecases.ceo import (
    create_ceo,
    create_slack,
    delete_ceo,
    delete_slack,
    derive_cable,
    list_ceos,
    list_slacks,
    move_ceo,
)
from inventory.usecases.devices_common import InventoryValidationError

pytestmark = pytest.mark.django_db


@pytest.fixture
def trunk():
    a = Site.objects.create(display_name="SITE - VILA MANDI", latitude=0.0, longitude=-50.0)
    b = Site.objects.create(display_name="SITE - VILA RICA", latitude=0.09, longitude=-50.0)
    return FiberCable.objects.create(
        name="MANDI - VLP",
        site_a=a,
        site_b=b,
        path=LineString([(-50.0, 0.0), (-50.0, 0.09)], srid=4326),
    )


def test_ceo_is_projected_on_the_trace_with_km_and_options(trunk):
    ceo = create_ceo(
        trunk.pk, lat=0.045, lng=-49.99, name="CEO-04", mode="corte", slack_m=20, trays=4
    )
    assert ceo["point"][0] == pytest.approx(-50.0, abs=1e-6)  # projetado no traçado
    assert ceo["km"] == pytest.approx(5.0, abs=0.05)
    assert (ceo["mode"], ceo["mode_label"], ceo["slack_m"], ceo["trays"]) == (
        "corte",
        "Corte / emenda total",
        20,
        4,
    )
    assert [c["name"] for c in list_ceos()] == ["CEO-04"]


@pytest.mark.parametrize(
    "kwargs, msg",
    [
        ({"name": "CEO", "mode": "xx"}, "modo"),
        ({"name": "  "}, "nome"),
        ({"name": "CEO", "trays": 0}, "bandejas"),
    ],
)
def test_ceo_validation(trunk, kwargs, msg):
    with pytest.raises(InventoryValidationError, match=msg):
        create_ceo(trunk.pk, lat=0.04, lng=-50.0, **kwargs)


def test_derived_cable_starts_at_the_ceo_and_gets_its_structure(trunk):
    group = CableGroup.objects.create(name="12-FO", fiber_count=12)
    nova = Site.objects.create(display_name="SITE - VILA NOVA", latitude=0.045, longitude=-49.95)
    sw = Device.objects.create(name="SW Vila Nova", site=nova)
    port = Port.objects.create(device=sw, name="ge-0/0/1")
    ceo = create_ceo(trunk.pk, lat=0.045, lng=-50.0, name="CEO-04")
    r = derive_cable(
        ceo["id"],
        name="CEO-04 - VILA NOVA",
        path=[{"lat": 0.045, "lng": -49.97}, {"lat": 0.045, "lng": -49.95}],
        cable_group_id=group.pk,
        to_site_id=nova.pk,
        to_port_id=port.pk,
    )
    cable = FiberCable.objects.get(pk=r["id"])
    assert (
        cable.origin_infrastructure_id == ceo["id"]
        and cable.site_b == nova
        and cable.destination_port == port
    )
    first = cable.path.coords[0]
    assert first == pytest.approx((ceo["point"][0], ceo["point"][1]))  # o traçado começa na CEO
    assert r["length_km"] == pytest.approx(5.56, abs=0.05)
    assert FiberStrand.objects.filter(tube__cable=cable).count() == 12
    assert list_ceos()[0]["derived"] == [{"id": cable.pk, "name": "CEO-04 - VILA NOVA"}]
    from inventory.usecases.strand_ports import cable_ends

    ends = cable_ends(cable)
    assert ends["a"]["ceo_name"] == "CEO-04" and ends["b"]["site_name"] == "SITE - VILA NOVA"


def test_derive_validations(trunk):
    ceo = create_ceo(trunk.pk, lat=0.045, lng=-50.0, name="CEO-04")
    other = Site.objects.create(display_name="X", latitude=1, longitude=1)
    port = Port.objects.create(device=Device.objects.create(name="D", site=other), name="p")
    nova = Site.objects.create(display_name="NOVA", latitude=0, longitude=0)
    with pytest.raises(InventoryValidationError, match="já existe"):
        derive_cable(ceo["id"], name="MANDI - VLP", path=[{"lat": 0.04, "lng": -49.9}])
    with pytest.raises(InventoryValidationError, match="não é de um equipamento desse site"):
        derive_cable(
            ceo["id"],
            name="D1",
            path=[{"lat": 0.04, "lng": -49.9}],
            to_site_id=nova.pk,
            to_port_id=port.pk,
        )
    with pytest.raises(InventoryValidationError, match="tem de ser outra"):
        derive_cable(ceo["id"], name="D2", path=[{"lat": 0.04, "lng": -49.9}], to_ceo_id=ceo["id"])


def test_endpoints_require_login(trunk):
    url = "/api/v1/inventory/ceos/"
    assert Client().get(url).status_code in (401, 403, 302)
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="eng", password="x", is_staff=True))
    created = c.post(
        url,
        {"cable_id": trunk.pk, "lat": 0.02, "lng": -50.0, "name": "CEO-01"},
        content_type="application/json",
    )
    assert created.status_code == 201 and created.json()["mode"] == "sangria"
    derived = c.post(
        f"{url}{created.json()['id']}/derive/",
        {"name": "DERIV", "path": [{"lat": 0.02, "lng": -49.99}]},
        content_type="application/json",
    )
    assert derived.status_code == 201 and derived.json()["needs_profile"] is True  # sem grupo
    assert (
        c.post(
            url,
            {"cable_id": trunk.pk, "lat": 0.02, "lng": -50.0, "name": "X", "mode": "zz"},
            content_type="application/json",
        ).status_code
        == 400
    )
    nova = Site.objects.create(display_name="NOVA", latitude=0, longitude=0)
    Port.objects.create(device=Device.objects.create(name="SW", site=nova), name="ge-1")
    sp = c.get(f"{url}site-ports/", {"site": nova.pk}).json()
    assert sp["site_name"] == "NOVA" and sp["devices"][0]["ports"][0]["name"] == "ge-1"


def test_writes_are_staff_only_reads_are_not(trunk):
    """EV-0138: a operação (não-staff) lê; só a engenharia (staff) altera a topologia física."""
    noc = Client()
    noc.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    url = "/api/v1/inventory/ceos/"
    assert noc.get(url).status_code == 200
    body = {"cable_id": trunk.pk, "lat": 0.02, "lng": -50.0, "name": "CEO-01"}
    assert noc.post(url, body, content_type="application/json").status_code == 403
    assert (
        noc.post(
            "/api/v1/inventory/slacks/", {**body, "meters": 20}, content_type="application/json"
        ).status_code
        == 403
    )


def test_move_and_delete_ceo(trunk):
    ceo = create_ceo(trunk.pk, lat=0.02, lng=-50.0, name="CEO-01")
    moved = move_ceo(ceo["id"], lat=0.07, lng=-49.98)
    assert moved["point"][0] == pytest.approx(-50.0, abs=1e-6) and moved["km"] == pytest.approx(
        7.74, abs=0.05
    )
    derived = derive_cable(ceo["id"], name="D", path=[{"lat": 0.07, "lng": -49.9}])
    with pytest.raises(InventoryValidationError, match="1 cabo"):
        delete_ceo(ceo["id"])
    FiberCable.objects.filter(pk=derived["id"]).update(origin_infrastructure=None)
    delete_ceo(ceo["id"])
    assert list_ceos() == []


def test_slack_adds_and_removes_length(trunk):
    FiberCable.objects.filter(pk=trunk.pk).update(length_km=10)
    s = create_slack(trunk.pk, lat=0.03, lng=-49.99, meters=50)
    assert s["slack_m"] == 50 and s["km"] == pytest.approx(3.32, abs=0.05)
    assert float(FiberCable.objects.get(pk=trunk.pk).length_km) == pytest.approx(10.05)
    assert [x["name"] for x in list_slacks()] == ["Reserva 50 m"]
    delete_slack(s["id"])
    assert float(FiberCable.objects.get(pk=trunk.pk).length_km) == pytest.approx(10.0)
    with pytest.raises(InventoryValidationError, match="metros"):
        create_slack(trunk.pk, lat=0.03, lng=-49.99, meters=0)
