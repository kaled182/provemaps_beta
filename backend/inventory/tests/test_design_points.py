"""EV-0139 — CTOs (sobre um cabo, projetada e com km, ou solta) e postes; escrita só staff."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString
from django.test import Client

from inventory.models import FiberCable
from inventory.usecases import design_points as uc
from inventory.usecases.devices_common import InventoryValidationError

pytestmark = pytest.mark.django_db


@pytest.fixture
def cable():
    return FiberCable.objects.create(
        name="DROP", path=LineString([(-50.0, 0.0), (-50.0, 0.09)], srid=4326)
    )


def test_cto_on_cable_is_projected_and_standalone_keeps_the_click(cable):
    on = uc.create_cto(lat=0.045, lng=-49.99, name="CTO-01", capacity=16, cable_id=cable.pk)
    assert on["point"][0] == pytest.approx(-50.0, abs=1e-6) and on["km"] == pytest.approx(
        4.976, abs=0.05
    )
    assert (on["cable_name"], on["capacity"]) == ("DROP", 16)
    solo = uc.create_cto(lat=0.01, lng=-49.9, name="CTO-02")
    assert solo["point"] == [-49.9, 0.01] and solo["cable_id"] is None and solo["km"] is None
    moved = uc.move_cto(on["id"], lat=0.07, lng=-49.98)
    assert moved["point"][0] == pytest.approx(-50.0, abs=1e-6)
    assert [c["name"] for c in uc.list_ctos()] == ["CTO-01", "CTO-02"]
    uc.delete_cto(solo["id"])
    assert len(uc.list_ctos()) == 1


def test_cto_and_pole_validation():
    with pytest.raises(InventoryValidationError, match="portas"):
        uc.create_cto(lat=0, lng=0, name="X", capacity=7)
    with pytest.raises(InventoryValidationError, match="nome"):
        uc.create_cto(lat=0, lng=0, name=" ")
    with pytest.raises(InventoryValidationError, match="altura"):
        uc.create_pole(lat=0, lng=0, name="P1", height_m=80)


def test_poles_crud():
    p = uc.create_pole(lat=-10.5, lng=-50.1, name="P-0123", owner="Energisa", height_m=11)
    assert p == {
        "id": p["id"],
        "name": "P-0123",
        "point": [-50.1, -10.5],
        "owner": "Energisa",
        "height_m": 11,
    }
    assert uc.move_pole(p["id"], lat=-10.6, lng=-50.2)["point"] == [-50.2, -10.6]
    uc.delete_pole(p["id"])
    assert uc.list_poles() == []


def test_endpoints_read_for_all_write_for_staff(cable):
    noc, eng = Client(), Client()
    noc.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    eng.force_login(
        get_user_model().objects.create_user(username="eng", password="x", is_staff=True)
    )
    body = {"lat": 0.02, "lng": -50.0, "name": "CTO-09", "capacity": 8, "cable_id": cable.pk}
    assert (
        noc.post("/api/v1/inventory/ctos/", body, content_type="application/json").status_code
        == 403
    )
    r = eng.post("/api/v1/inventory/ctos/", body, content_type="application/json")
    assert r.status_code == 201
    assert noc.get("/api/v1/inventory/ctos/").json()[0]["name"] == "CTO-09"
    r = eng.post(
        "/api/v1/inventory/poles/",
        {"lat": 0.01, "lng": -50.0, "name": "P-1"},
        content_type="application/json",
    )
    assert r.status_code == 201
    assert (
        eng.patch(
            f"/api/v1/inventory/poles/{r.json()['id']}/",
            {"lat": 0.02, "lng": -50.0},
            content_type="application/json",
        ).status_code
        == 200
    )
    assert eng.delete(f"/api/v1/inventory/poles/{r.json()['id']}/").status_code == 204
    assert (
        eng.post(
            "/api/v1/inventory/poles/",
            {"lat": 0.01, "lng": -50.0, "name": " "},
            content_type="application/json",
        ).status_code
        == 400
    )
