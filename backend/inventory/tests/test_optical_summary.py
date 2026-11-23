"""EV-0057 / EV-0049 — agregado de níveis ópticos de todos os cabos, lido do banco."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from inventory.models import Device, FiberCable, Port, Site
from inventory.usecases.fibers import list_cables_optical_summary

URL = "/api/v1/fiber-cables/optical-summary/"
THRESHOLDS = {"warning": -24.0, "critical": -27.0}


@pytest.fixture(autouse=True)
def _fixed_thresholds():
    # Limiares da configuração fixos: o teste não depende do FirstTimeSetup.
    with patch("inventory.usecases.fibers._resolve_port_thresholds", return_value=THRESHOLDS):
        yield


def _port(device, name, rx, tx, checked_ago=timedelta(seconds=30)):
    return Port.objects.create(
        device=device,
        name=name,
        rx_power_item_key="rx",
        tx_power_item_key="tx",
        last_rx_power=rx,
        last_tx_power=tx,
        last_optical_check=None if checked_ago is None else timezone.now() - checked_ago,
    )


@pytest.fixture
def network(db):
    site = Site.objects.create(display_name="POP A", latitude=-15.78, longitude=-47.93)
    a = Device.objects.create(name="OLT-A", site=site, zabbix_hostid="1")
    b = Device.objects.create(name="SW-B", site=site, zabbix_hostid="2")
    ok = FiberCable.objects.create(
        name="C-ok",
        origin_port=_port(a, "a1", -18.0, 2.0),
        destination_port=_port(b, "b1", -19.5, 1.5),
    )
    los = FiberCable.objects.create(
        name="C-los",
        origin_port=_port(a, "a2", -40.0, 2.0),
        destination_port=_port(b, "b2", -20.0, 2.0),
    )
    old = FiberCable.objects.create(
        name="C-velho",
        origin_port=_port(a, "a3", -45.0, 2.0, checked_ago=timedelta(hours=2)),
        destination_port=_port(b, "b3", -45.0, 2.0, checked_ago=timedelta(hours=2)),
    )
    no_ports = FiberCable.objects.create(name="C-sem-portas")
    return {"ok": ok, "los": los, "old": old, "no_ports": no_ports}


@pytest.mark.django_db
def test_summary_classifies_each_cable_and_counts_totals(network):
    data = list_cables_optical_summary()
    by_name = {c["name"]: c for c in data["cables"]}

    assert by_name["C-ok"]["health"] == "healthy"
    assert by_name["C-los"]["health"] == "critical"
    assert by_name["C-los"]["origin"]["status"] == "critical"
    # Só leituras velhas: não se afirma saúde nenhuma, mesmo com -45 dBm guardado
    assert by_name["C-velho"]["health"] == "unknown"
    assert by_name["C-velho"]["origin"]["stale"] is True
    assert by_name["C-sem-portas"]["health"] == "unknown"
    assert by_name["C-sem-portas"]["origin"]["rx"] is None
    assert data["totals"] == {"total": 4, "healthy": 1, "attention": 0, "critical": 1, "unknown": 2}


@pytest.mark.django_db
def test_loss_per_direction_and_worst_ignores_stale(network):
    data = list_cables_optical_summary()
    ok = next(c for c in data["cables"] if c["name"] == "C-ok")
    assert ok["loss_ab_db"] == 21.5  # TX origem 2.0 - RX destino -19.5
    assert ok["loss_ba_db"] == 19.5  # TX destino 1.5 - RX origem -18.0
    # -45 dBm do cabo velho não conta; o pior fresco é o -40 da origem do C-los
    assert data["worst"] == {
        "cable_id": network["los"].id,
        "cable_name": "C-los",
        "side": "origin",
        "rx": -40.0,
    }


@pytest.mark.django_db
def test_without_readings_loss_and_worst_are_null(db):
    FiberCable.objects.create(name="sozinho")
    data = list_cables_optical_summary()
    assert data["worst"] is None
    assert data["last_check"] is None
    assert data["cables"][0]["loss_ab_db"] is None


@pytest.mark.django_db
def test_endpoint_requires_login_and_returns_summary(network):
    assert Client().get(URL).status_code in (401, 403, 302)
    client = Client()
    client.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    response = client.get(URL)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"cables", "totals", "worst", "last_check"}
    assert body["totals"]["total"] == 4
