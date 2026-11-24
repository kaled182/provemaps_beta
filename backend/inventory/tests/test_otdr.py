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


# ── EV-0130: ajuste fino, referências no traçado, ajuste de um ponto fixado ───
def test_offset_moves_the_point_along_the_trace_and_stays_between_the_ends(cable):
    base = locate_otdr(cable.pk, direction="ab", distance_m=2500, slack_pct=0)
    moved = locate_otdr(cable.pk, direction="ab", distance_m=2500, slack_pct=0, offset_m=500)
    assert (moved["base_map_distance_m"], moved["map_distance_m"], moved["offset_m"]) == (
        2500,
        3000,
        500,
    )
    assert moved["point"][1] > base["point"][1]  # mais para B
    clamped = locate_otdr(cable.pk, direction="ab", distance_m=2500, slack_pct=0, offset_m=-9000)
    assert clamped["map_distance_m"] == 0 and clamped["offset_m"] == -2500


def test_references_before_and_after_the_point(cable):
    from django.contrib.gis.geos import Point

    from inventory.models import FiberInfrastructure

    # ~1 km e ~4 km a partir de A (0,009° ≈ 1 km de latitude)
    FiberInfrastructure.objects.create(
        cable=cable, type="splice_box", name="CEO-01", location=Point(-50.0, 0.009, srid=4326)
    )
    FiberInfrastructure.objects.create(
        cable=cable, type="slack", name="", location=Point(-50.0001, 0.036, srid=4326)
    )
    r = locate_otdr(cable.pk, direction="ab", distance_m=2500, slack_pct=0)["references"]
    assert r["registered"] == 2
    assert (r["before"]["name"], r["before"]["type_label"]) == ("CEO-01", "Caixa de Emenda (CEO)")
    assert r["before"]["distance_m"] == pytest.approx(1500, abs=15)
    assert r["after"]["type"] == "slack" and r["after"]["distance_m"] == pytest.approx(1500, abs=15)
    # medido de B, a ordem inverte-se
    rb = locate_otdr(cable.pk, direction="ba", distance_m=2500, slack_pct=0)["references"]
    assert rb["before"] is None and rb["after"]["type"] == "slack"


def test_no_references_registered(cable):
    r = locate_otdr(cable.pk, direction="ab", distance_m=2500, slack_pct=0)["references"]
    assert r == {"registered": 0, "before": None, "after": None}


def test_adjusting_a_pinned_alert_recomputes_for_everyone_and_logs_it(cable):
    c = Client()
    c.force_login(
        get_user_model().objects.create_user(username="ana", password="x", first_name="Ana")
    )
    url = "/api/v1/inventory/otdr-alerts/"
    alert = c.post(
        url,
        {"cable_id": cable.pk, "direction": "ab", "distance_m": 2500},
        content_type="application/json",
    ).json()
    adjusted = c.patch(f"{url}{alert['id']}/", {"offset_m": 200}, content_type="application/json")
    assert adjusted.status_code == 200
    body = adjusted.json()
    assert body["result"]["map_distance_m"] == 2700
    assert [e["action"] for e in body["log"]] == ["pinned", "adjusted"]
    assert body["log"][1]["delta_m"] == 200 and body["log"][1]["by"] == "Ana"
    other = Client()
    other.force_login(get_user_model().objects.create_user(username="rui", password="x"))
    assert other.get(url).json()[0]["result"]["map_distance_m"] == 2700  # todos veem
    other.post(f"{url}{alert['id']}/clear/")
    assert (
        c.patch(
            f"{url}{alert['id']}/", {"offset_m": 0}, content_type="application/json"
        ).status_code
        == 404
    )


# ── EV-0131: medição cruzada (A + B) ─────────────────────────────────────────
def test_cross_measurement_uses_the_real_slack_and_the_proportion(cable):
    total = total_m()
    # fibra com 3 % a mais que o traçado; rompimento a 30 % de A
    fiber = total * 1.03
    a, b = fiber * 0.3, fiber * 0.7
    r = locate_otdr(cable.pk, direction="ba", distance_m=a, slack_pct=0, distance_b_m=b)
    assert r["mode"] == "cross" and r["direction"] == "ab"  # o sentido é sempre a partir de A
    assert r["cross"]["slack_real_pct"] == pytest.approx(3.0, abs=0.01)
    assert r["cross"]["proportion"] == pytest.approx(0.3, abs=1e-4)
    assert r["map_distance_m"] == pytest.approx(total * 0.3, abs=0.2)
    assert r["warnings"] == []


def test_cross_warns_when_the_readings_are_shorter_than_the_trace(cable):
    r = locate_otdr(cable.pk, direction="ab", distance_m=3000, slack_pct=0, distance_b_m=5000)
    assert r["cross"]["slack_real_pct"] < 0
    assert "menor que o traçado" in r["warnings"][0]
    assert r["map_distance_m"] == pytest.approx(total_m() * 3 / 8, abs=0.2)


def test_pinning_a_cross_measurement_keeps_b_and_the_offset_on_adjust(cable):
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="ana", password="x"))
    url = "/api/v1/inventory/otdr-alerts/"
    body = {
        "cable_id": cable.pk,
        "direction": "ab",
        "distance_m": 3000,
        "distance_b_m": 7300,
        "offset_m": 50,
    }
    alert = c.post(url, body, content_type="application/json").json()
    assert alert["result"]["mode"] == "cross" and alert["result"]["offset_m"] == 50
    moved = c.patch(
        f"{url}{alert['id']}/", {"offset_m": 150}, content_type="application/json"
    ).json()
    assert moved["result"]["mode"] == "cross"
    assert moved["result"]["map_distance_m"] == pytest.approx(
        alert["result"]["base_map_distance_m"] + 150, abs=0.2
    )


# ── EV-0132: estado do atendimento e histórico do cabo ────────────────────────
def test_status_flow_logs_and_done_removes_the_pin_and_history_keeps_it(cable):
    c = Client()
    c.force_login(
        get_user_model().objects.create_user(username="ana", password="x", first_name="Ana")
    )
    url = "/api/v1/inventory/otdr-alerts/"
    alert = c.post(
        url,
        {"cable_id": cable.pk, "direction": "ab", "distance_m": 2500},
        content_type="application/json",
    ).json()
    assert (alert["status"], alert["status_label"]) == ("registered", "Registado")
    st = f"{url}{alert['id']}/status/"
    assert (
        c.post(st, {"status": "en_route"}, content_type="application/json").json()["status_label"]
        == "Em deslocamento"
    )
    assert (
        c.post(st, {"status": "splicing"}, content_type="application/json").json()["status"]
        == "splicing"
    )
    assert len(c.get(url).json()) == 1  # ainda no mapa
    done = c.post(st, {"status": "done"}, content_type="application/json").json()
    assert done["status"] == "done" and done["cleared_at"] and done["cleared_by"] == "Ana"
    assert c.get(url).json() == []  # saiu do mapa
    history = c.get(f"/api/v1/inventory/cables/{cable.pk}/otdr-alerts/").json()
    assert [h["id"] for h in history] == [alert["id"]]
    assert [e.get("status") or e["action"] for e in history[0]["log"]] == [
        "pinned",
        "en_route",
        "splicing",
        "done",
    ]
    assert (
        c.post(st, {"status": "en_route"}, content_type="application/json").status_code == 404
    )  # concluído
    assert c.post(st, {"status": "xx"}, content_type="application/json").status_code == 400
    assert c.get("/api/v1/inventory/cables/999999/otdr-alerts/").status_code == 404


def test_clear_marks_the_alert_done(cable):
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="ana", password="x"))
    url = "/api/v1/inventory/otdr-alerts/"
    alert = c.post(
        url,
        {"cable_id": cable.pk, "direction": "ab", "distance_m": 2500},
        content_type="application/json",
    ).json()
    c.post(f"{url}{alert['id']}/clear/")
    assert c.get(f"/api/v1/inventory/cables/{cable.pk}/otdr-alerts/").json()[0]["status"] == "done"
