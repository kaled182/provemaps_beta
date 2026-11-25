"""EV-0142 — splitters na bandeja da CEO/CTO: entrada, portas Livre/Reservada/Ocupada/Bloqueada,
saída para uma fibra, dBm estimado (TX da fonte a montante - perdas - splitter) e splitters em
cascata (OLT → tronco → 1x8 na CEO → derivado → 1x4 na CTO)."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from inventory.models import SplitterPort
from inventory.tests.test_ceo_fusions import _fiber, net  # noqa: F401  (fixture)
from inventory.usecases import ceo_fusions as uc
from inventory.usecases.design_points import create_cto
from inventory.usecases.devices_common import InventoryValidationError

pytestmark = pytest.mark.django_db


def _sp(box, sid):
    return next(s for s in uc.ceo_fusions(box)["splitters"] if s["id"] == sid)


def test_splitter_ports_power_and_status(net):  # noqa: F811
    f1, d1 = _fiber(net.trunk, 1), _fiber(net.derived, 1)
    sid = uc.create_splitter(net.ceo, ratio="1x8", name="Primário")["id"]
    sp = _sp(net.ceo, sid)
    assert len(sp["ports"]) == 8 and sp["power"] == {"dbm": None, "reason": "sem fibra de entrada"}
    uc.update_splitter(net.ceo, sid, input={"strand_id": f1.pk, "side": "a"})
    sp = _sp(net.ceo, sid)
    # OLT (TX padrão +5) → ~4,98 km do tronco a 0,35 dB/km → entrada; porta = entrada - 10,5 (1x8)
    assert sp["power"]["source"] == "padrao" and sp["power"]["from"] == "OLT Mandi → gpon 1/1/1"
    assert sp["power"]["dbm"] == pytest.approx(5 - 4.976 * 0.35, abs=0.05)
    assert sp["ports"][0]["dbm"] == pytest.approx(sp["power"]["dbm"] - 10.5, abs=0.01)
    uc.update_splitter_port(
        net.ceo, sid, 1, status="ocupada", customer="Cliente 1", output={"strand_id": d1.pk}
    )
    uc.update_splitter_port(net.ceo, sid, 2, status="bloqueada", note="conector danificado")
    sp = _sp(net.ceo, sid)
    assert sp["counts"] == {"livre": 6, "reservada": 0, "ocupada": 1, "bloqueada": 1}
    assert sp["ports"][0]["output"]["cable_name"] == "CEO-04 - VILA NOVA"
    ends = {e["key"]: e for c in uc.ceo_fusions(net.ceo)["cables"] for e in c["ends"]}
    assert ends[f"{f1.pk}:a"]["splitter_use"] == "a entrada do splitter 1x8"
    # o rastreamento a jusante a partir da OLT para ao entrar no splitter
    t = uc.trace_light(f1.pk, start="a")
    assert t["end"]["reason"] == "splitter" and "1x8" in t["end"]["label"]


def test_validations(net):  # noqa: F811
    f1, d1 = _fiber(net.trunk, 1), _fiber(net.derived, 1)
    sid = uc.create_splitter(net.ceo, ratio="1x4")["id"]
    uc.update_splitter(net.ceo, sid, input={"strand_id": f1.pk, "side": "a"})
    with pytest.raises(InventoryValidationError, match="entrada do splitter"):
        uc.create_fusion(net.ceo, a={"strand_id": f1.pk, "side": "a"}, b={"strand_id": d1.pk})
    with pytest.raises(InventoryValidationError, match="já está em"):
        uc.update_splitter_port(net.ceo, sid, 1, output={"strand_id": f1.pk, "side": "a"})
    with pytest.raises(InventoryValidationError, match="precisa do cliente"):
        uc.update_splitter_port(net.ceo, sid, 1, status="reservada")
    with pytest.raises(InventoryValidationError, match="razão"):
        uc.create_splitter(net.ceo, ratio="1x3")
    uc.delete_splitter(net.ceo, sid)
    assert SplitterPort.objects.count() == 0


def test_cascade_power_through_two_splitters(net):  # noqa: F811
    """1x8 na CEO-04 (entrada = tronco F1 vindo da OLT, porta 1 → derivado F1) e 1x4 numa CTO a
    meio do derivado com a entrada no derivado F1 (lado rumo à CEO): a potência encadeia."""
    f1, d1 = _fiber(net.trunk, 1), _fiber(net.derived, 1)
    s8 = uc.create_splitter(net.ceo, ratio="1x8")["id"]
    uc.update_splitter(net.ceo, s8, input={"strand_id": f1.pk, "side": "a"})
    uc.update_splitter_port(net.ceo, s8, 1, output={"strand_id": d1.pk})
    cto = create_cto(lat=0.045, lng=-49.96, name="CTO-01", capacity=4, cable_id=net.derived.pk)[
        "id"
    ]
    s4 = uc.create_splitter(cto, ratio="1x4")["id"]
    uc.update_splitter(cto, s4, input={"strand_id": d1.pk, "side": "a"})
    p8 = _sp(net.ceo, s8)
    p4 = _sp(cto, s4)
    assert p4["power"]["from"] == "OLT Mandi → gpon 1/1/1"
    # a montante: derivado até à CEO + 1x8 (10,5) + tronco; a porta do 1x4 tira mais 7,1
    assert p4["power"]["dbm"] < p8["ports"][0]["dbm"]
    assert p4["power"]["dbm"] == pytest.approx(
        p8["ports"][0]["dbm"] - p4["power"]["km"] * 0.35 + p8["power"]["km"] * 0.35, abs=0.1
    )
    assert p4["ports"][0]["dbm"] == pytest.approx(p4["power"]["dbm"] - 7.1, abs=0.01)


def test_endpoints_staff_only(net):  # noqa: F811
    noc, eng = Client(), Client()
    noc.force_login(get_user_model().objects.create_user(username="noc2", password="x"))
    eng.force_login(
        get_user_model().objects.create_user(username="eng2", password="x", is_staff=True)
    )
    url = f"/api/v1/inventory/ceos/{net.ceo}/splitters/"
    assert noc.post(url, {"ratio": "1x8"}, content_type="application/json").status_code == 403
    r = eng.post(url, {"ratio": "1x8"}, content_type="application/json")
    assert r.status_code == 201
    sid = r.json()["id"]
    r = eng.patch(
        f"{url}{sid}/ports/3/",
        {"status": "reservada", "customer": "Fulano"},
        content_type="application/json",
    )
    assert r.status_code == 200 and r.json() == {"number": 3, "status": "reservada"}
    assert (
        eng.patch(
            f"{url}{sid}/ports/3/", {"status": "xx"}, content_type="application/json"
        ).status_code
        == 400
    )
    assert eng.delete(f"{url}{sid}/").status_code == 204
