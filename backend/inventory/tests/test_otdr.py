"""EV-0127 — localizador OTDR: folga, sentido A→B/B→A, traçado desenhado ao contrário,
interpolação no segmento certo, trecho de ±40 m e validações."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString
from django.test import Client

from inventory.domain import otdr as geo
from inventory.models import FiberCable, Site
from inventory.usecases.devices_common import InventoryValidationError
from inventory.usecases.otdr import locate_otdr

pytestmark = pytest.mark.django_db

# ~1 km por 0,009° de latitude: um cabo reto norte-sul de A (lat 0) a B (lat 0,09) ≈ 10 km
A = (-50.0, 0.0)
MID = (-50.0, 0.045)
B = (-50.0, 0.09)


@pytest.fixture
def cable():
    site_a = Site.objects.create(display_name="SITE - VILA MANDI", latitude=0.0, longitude=-50.0)
    site_b = Site.objects.create(display_name="SITE - VILA RICA", latitude=0.09, longitude=-50.0)
    return FiberCable.objects.create(
        name="MANDI - VLP",
        site_a=site_a,
        site_b=site_b,
        path=LineString([A, MID, B], srid=4326),
        length_km=10.0,
    )


def total_m():
    return geo.cumulative_m([A, MID, B])[-1]


def test_ab_without_slack_lands_on_the_traced_distance(cable):
    r = locate_otdr(cable.pk, direction="ab", distance_m=2500, slack_pct=0)
    assert r["map_distance_m"] == 2500
    assert r["point"][0] == pytest.approx(-50.0)
    assert r["point"][1] == pytest.approx(0.09 * 2500 / total_m(), abs=1e-6)
    assert r["origin"] == {"id": cable.site_a_id, "name": "SITE - VILA MANDI", "distance_m": 2500.0}
    assert r["target"]["name"] == "SITE - VILA RICA"
    assert r["target"]["distance_m"] == pytest.approx(total_m() - 2500, abs=0.2)
    # trecho de ±40 m: começa 40 m antes e acaba 40 m depois
    seg = r["segment"]
    assert geo.cumulative_m([tuple(p) for p in seg])[-1] == pytest.approx(80, abs=0.5)


def test_slack_shortens_the_distance_on_the_map(cable):
    r = locate_otdr(cable.pk, direction="ab", distance_m=1015, slack_pct=1.5)
    assert r["map_distance_m"] == pytest.approx(1000, abs=0.1)


def test_ba_measures_from_site_b(cable):
    r = locate_otdr(cable.pk, direction="ba", distance_m=2500, slack_pct=0)
    assert r["origin"]["name"] == "SITE - VILA RICA"
    assert r["point"][1] == pytest.approx(0.09 - 0.09 * 2500 / total_m(), abs=1e-6)


def test_path_drawn_from_b_to_a_is_turned_around(cable):
    cable.path = LineString([B, MID, A], srid=4326)
    cable.save()
    r = locate_otdr(cable.pk, direction="ab", distance_m=2500, slack_pct=0)
    assert r["point"][1] == pytest.approx(
        0.09 * 2500 / total_m(), abs=1e-6
    )  # continua a partir de A


@pytest.mark.parametrize(
    "kwargs, msg",
    [
        ({"direction": "xx", "distance_m": 10, "slack_pct": 0}, "sentido"),
        ({"direction": "ab", "distance_m": 10, "slack_pct": 25}, "folga"),
        ({"direction": "ab", "distance_m": 0, "slack_pct": 0}, "positiva"),
        ({"direction": "ab", "distance_m": 20_000, "slack_pct": 0}, "passa do fim"),
    ],
)
def test_validation(cable, kwargs, msg):
    with pytest.raises(InventoryValidationError, match=msg):
        locate_otdr(cable.pk, **kwargs)


def test_endpoint_requires_login_validates_and_404(cable):
    url = f"/api/v1/inventory/cables/{cable.pk}/otdr-locate/"
    q = {"direction": "ab", "distance_m": 2500, "slack_pct": 1.5}
    assert Client().get(url, q).status_code in (401, 403, 302)
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    body = c.get(url, q).json()
    assert body["cable_name"] == "MANDI - VLP" and len(body["point"]) == 2
    over = c.get(url, {"direction": "ab", "distance_m": 99_000})
    assert over.status_code == 400 and "passa do fim" in over.json()["detail"]
    assert c.get(url, {"direction": "zz", "distance_m": 10}).status_code == 400
    assert c.get("/api/v1/inventory/cables/999999/otdr-locate/", q).status_code == 404


# ── EV-0128: pontos fixados para toda a equipa ───────────────────────────────
def test_pin_recomputes_on_the_server_lists_and_clears(cable):
    from inventory.models import OtdrAlert

    c = Client()
    user = get_user_model().objects.create_user(username="noc", password="x", first_name="Ana")
    c.force_login(user)
    url = "/api/v1/inventory/otdr-alerts/"
    body = {
        "cable_id": cable.pk,
        "direction": "ab",
        "distance_m": 2500,
        "slack_pct": 0,
        "note": "OS 123",
    }
    # o ponto vem do servidor, mesmo que o browser mande outro
    created = c.post(url, {**body, "point": [0, 0]}, content_type="application/json")
    assert created.status_code == 201
    alert = created.json()
    assert alert["created_by"] == "Ana" and alert["note"] == "OS 123"
    assert alert["result"]["point"][1] == pytest.approx(0.09 * 2500 / total_m(), abs=1e-6)
    assert [a["id"] for a in c.get(url).json()] == [alert["id"]]
    # outro operador vê o mesmo
    other = Client()
    other.force_login(get_user_model().objects.create_user(username="noc2", password="x"))
    assert len(other.get(url).json()) == 1
    cleared = other.post(f"{url}{alert['id']}/clear/")
    assert cleared.status_code == 200 and cleared.json()["cleared_at"]
    assert c.get(url).json() == []
    row = OtdrAlert.objects.get()
    assert row.cleared_by.username == "noc2"


def test_pin_validates_like_locate_and_requires_login(cable):
    url = "/api/v1/inventory/otdr-alerts/"
    assert Client().get(url).status_code in (401, 403, 302)
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    over = c.post(
        url,
        {"cable_id": cable.pk, "direction": "ab", "distance_m": 99_000},
        content_type="application/json",
    )
    assert over.status_code == 400 and "passa do fim" in over.json()["detail"]
    assert c.post(f"{url}999999/clear/").status_code == 404
