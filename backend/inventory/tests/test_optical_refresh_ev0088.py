"""EV-0088 — o refresh manual de níveis ópticos aplica a mesma regra da coleta automática
(`apply_optical_snapshot`): ponta sem leitura válida passa a null quando a outra é gravada,
e sem nenhuma leitura válida nada muda nem `last_optical_check` avança."""

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from inventory.domain.optical_apply import apply_optical_snapshot
from inventory.models import Device, FiberCable, Port, Site

FETCH = "inventory.domain.optical.fetch_ports_optical_snapshots"


def _port():
    return SimpleNamespace(
        last_rx_power=Decimal("-21.50"),
        last_tx_power=Decimal("1.20"),
        last_optical_check=None,
    )


def test_helper_rx_only_clears_tx_and_advances_check():
    port, now = _port(), timezone.now()
    fields = apply_optical_snapshot(port, {"rx_dbm": Decimal("-18.4")}, now)
    assert port.last_rx_power == Decimal("-18.4")
    assert port.last_tx_power is None
    assert port.last_optical_check == now
    assert set(fields) == {"last_rx_power", "last_tx_power", "last_optical_check"}


def test_helper_no_valid_reading_changes_nothing():
    port = _port()
    assert apply_optical_snapshot(port, {"rx_problem": "x", "tx_dbm": None}, timezone.now()) == []
    assert port.last_rx_power == Decimal("-21.50")
    assert port.last_tx_power == Decimal("1.20")
    assert port.last_optical_check is None


def test_helper_already_null_side_is_not_listed():
    port = _port()
    port.last_tx_power = None
    fields = apply_optical_snapshot(port, {"rx_dbm": Decimal("-10")}, timezone.now())
    assert set(fields) == {"last_rx_power", "last_optical_check"}


@pytest.fixture
def cable(db):
    site = Site.objects.create(display_name="POP", latitude=-15.0, longitude=-47.0)
    dev = Device.objects.create(name="SW", site=site, zabbix_hostid="101")
    old = timezone.now() - timedelta(hours=3)
    kwargs = {
        "device": dev,
        "rx_power_item_key": "rx[1]",
        "tx_power_item_key": "tx[1]",
        "last_rx_power": Decimal("-21.50"),
        "last_tx_power": Decimal("1.20"),
        "last_optical_check": old,
    }
    a = Port.objects.create(name="P1", **kwargs)
    b = Port.objects.create(name="P2", **kwargs)
    return FiberCable.objects.create(name="C", site_a=site, origin_port=a, destination_port=b)


@pytest.fixture
def client(db):
    user = get_user_model().objects.create_user(username="u", password="x")
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_refresh_rx_valid_tx_missing_clears_tx_and_advances_check(client, cable):
    before = cable.origin_port.last_optical_check
    snaps = {
        cable.origin_port_id: {"rx_dbm": Decimal("-18.4"), "tx_dbm": None},
        cable.destination_port_id: {"rx_dbm": None, "tx_dbm": None},
    }
    with patch(FETCH, return_value=snaps):
        resp = client.post(f"/api/v1/inventory/fibers/{cable.id}/refresh-optical/")
    assert resp.status_code == 200
    a = Port.objects.get(pk=cable.origin_port_id)
    assert a.last_rx_power == Decimal("-18.40")
    assert a.last_tx_power is None
    assert a.last_optical_check > before
    b = Port.objects.get(pk=cable.destination_port_id)  # sem leitura válida: intacta
    assert b.last_rx_power == Decimal("-21.50")
    assert b.last_tx_power == Decimal("1.20")
    assert b.last_optical_check == before


@pytest.mark.django_db
def test_refresh_without_any_valid_reading_changes_nothing(client, cable):
    before = cable.origin_port.last_optical_check
    snaps = {
        cable.origin_port_id: {"rx_problem": "fora de faixa"},
        cable.destination_port_id: {},
    }
    with patch(FETCH, return_value=snaps):
        resp = client.post(f"/api/v1/inventory/fibers/{cable.id}/refresh-optical/")
    assert resp.status_code == 200
    for pk in (cable.origin_port_id, cable.destination_port_id):
        p = Port.objects.get(pk=pk)
        assert p.last_rx_power == Decimal("-21.50")
        assert p.last_tx_power == Decimal("1.20")
        assert p.last_optical_check == before
