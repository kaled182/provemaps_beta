"""EV-0143 — rastreamento destacado em árvore: fonte (OLT) encontrada a montante, ramos dos
splitters em cascata com km/dBm acumulados, ramo em foco e geometria de cada troço."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from inventory.tests.test_ceo_fusions import _fiber, net  # noqa: F401  (fixture)
from inventory.usecases import ceo_fusions as uc
from inventory.usecases.design_points import create_cto
from inventory.usecases.trace_tree import trace_tree

pytestmark = pytest.mark.django_db


@pytest.fixture
def cascade(net):  # noqa: F811
    """OLT → tronco F1 → 1x8 na CEO-04 (porta 1 → derivado F1) → 1x4 numa CTO no derivado."""
    f1, d1 = _fiber(net.trunk, 1), _fiber(net.derived, 1)
    s8 = uc.create_splitter(net.ceo, ratio="1x8")["id"]
    uc.update_splitter(net.ceo, s8, input={"strand_id": f1.pk, "side": "a"})
    uc.update_splitter_port(net.ceo, s8, 1, status="ocupada", output={"strand_id": d1.pk})
    cto = create_cto(lat=0.045, lng=-49.96, name="CTO-01", capacity=4, cable_id=net.derived.pk)
    s4 = uc.create_splitter(cto["id"], ratio="1x4")["id"]
    uc.update_splitter(cto["id"], s4, input={"strand_id": d1.pk, "side": "a"})
    net.f1, net.d1, net.s8, net.s4, net.cto = f1, d1, s8, s4, cto["id"]
    return net


def _sp(box, sid):
    return next(s for s in uc.ceo_fusions(box)["splitters"] if s["id"] == sid)


def test_tree_from_the_olt_branches_at_each_splitter(cascade):
    t = trace_tree(cascade.f1.pk, start="a")
    assert t["source"] == {"found": True, "label": "OLT Mandi → gpon 1/1/1"}
    root = t["tree"]
    assert root["steps"][0]["type"] == "port" and root["end"]["reason"] == "splitter"
    assert root["splitter"]["ratio"] == "1x8" and root["splitter"]["ceo_name"] == "CEO-04"
    assert root["splitter"]["lat"] == pytest.approx(0.045)
    assert len(root["branches"]) == 8
    first, others = root["branches"][0], root["branches"][1:]
    assert first["status"] == "ocupada" and all(b["node"] is None for b in others)
    # o dBm de cada porta é o mesmo que o painel de splitters mostra (EV-0142)
    assert first["dbm"] == _sp(cascade.ceo, cascade.s8)["ports"][0]["dbm"]
    child = first["node"]
    assert child["end"]["reason"] == "splitter" and child["splitter"]["ratio"] == "1x4"
    assert child["splitter"]["kind"] == "cto"
    assert child["km"] > root["km"] and child["dbm"] < first["dbm"]
    assert child["branches"][0]["dbm"] == _sp(cascade.cto, cascade.s4)["ports"][0]["dbm"]
    # cada troço de cabo traz a parte do traçado percorrida, em [lng, lat]
    cable = next(s for s in root["steps"] if s["type"] == "cable")
    assert cable["path"][0] == pytest.approx([-50.0, 0.0])
    assert cable["path"][-1][1] == pytest.approx(0.045, abs=1e-4)
    assert "from_km" not in cable


def test_tree_from_a_downstream_fiber_finds_the_olt_and_marks_the_focus(cascade):
    t = trace_tree(cascade.d1.pk, start="a")  # o derivado F1 não tem porta na ponta A
    assert t["source"]["found"] and t["tx"]["port_name"] == "gpon 1/1/1"
    root = t["tree"]
    assert root["focus"] and root["branches"][0]["node"]["focus"]
    assert not any(s.get("strand_id") == cascade.d1.pk for s in root["steps"])


def test_without_source_there_is_no_power(net):  # noqa: F811
    t = trace_tree(_fiber(net.trunk, 5).pk, start="a")
    assert t["source"]["found"] is False and t["tx"] is None
    assert t["tree"]["dbm"] is None and t["tree"]["focus"]


def test_endpoint_reads_for_any_logged_user(cascade):
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc3", password="x"))
    r = c.get(f"/api/v1/inventory/strands/{cascade.f1.pk}/trace/tree/", {"from": "a"})
    assert r.status_code == 200 and r.json()["tree"]["splitter"]["ratio"] == "1x8"
    assert c.get(f"/api/v1/inventory/strands/{cascade.f1.pk}/trace/tree/?from=x").status_code == 400
