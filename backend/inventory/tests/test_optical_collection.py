"""EV-0063 — coleta óptica: um item.get por equipamento, sem fallback chave a chave
nem procura sem hostid, valores fora da gama de dBm não gravados, uma coleta de
cada vez."""

from unittest.mock import patch

import pytest
from django.core.cache import cache

from inventory.domain import optical
from inventory.models import Device, Port, Site
from inventory.tasks import OPTICAL_LOCK_KEY, update_all_port_optical_levels

ZABBIX = "inventory.domain.optical.zabbix_request"
# EV-0082: o item.get pede `state`/`lastclock`; sem eles a leitura é descartada.
OK = {"state": "0", "lastclock": "1795450000"}


def test_plausible_dbm_range():
    assert optical.is_plausible_dbm(-18.5)
    assert optical.is_plausible_dbm(2.0)
    assert not optical.is_plausible_dbm(-80)
    assert not optical.is_plausible_dbm(380)
    assert not optical.is_plausible_dbm(2246566704.0)
    assert not optical.is_plausible_dbm(None)


def test_missing_key_is_not_fetched_again_nor_without_hostid():
    calls = []

    def fake(method, params=None, *a, **k):
        calls.append((method, params))
        return [{"itemid": "1", "key_": "rx.ok", "lastvalue": "-20.5", "value_type": "0", **OK}]

    with patch(ZABBIX, side_effect=fake):
        cache_map = optical._bulk_fetch_item_values("101", ["rx.ok", "rx.nao-existe"])

    assert len(calls) == 1  # só o item.get do host
    assert calls[0][1]["hostids"] == ["101"]
    assert cache_map[optical._value_cache_key("101", "rx.ok")][0] == -20.5
    assert cache_map[optical._value_cache_key("101", "rx.nao-existe")] == (None, None, None)


def test_single_item_lookup_never_searches_other_hosts():
    calls = []

    def fake(method, params=None, *a, **k):
        calls.append(params)
        return []

    with patch(ZABBIX, side_effect=fake):
        assert optical._fetch_item_value("101", "rx.key") == (None, None, None)
    assert len(calls) == 1
    assert calls[0]["hostids"] == ["101"]


@pytest.fixture
def ports(db):
    site = Site.objects.create(display_name="POP", latitude=-15.0, longitude=-47.0)
    dev = Device.objects.create(name="OLT", site=site, zabbix_hostid="101")
    good = Port.objects.create(
        device=dev, name="xe-1", rx_power_item_key="rx.good", tx_power_item_key="tx.good"
    )
    octets = Port.objects.create(
        device=dev,
        name="ifHC",
        rx_power_item_key="net.if.in[ifHCInOctets.1]",
        tx_power_item_key="tx.nao-existe",
    )
    return good, octets


@pytest.mark.django_db
def test_task_one_call_per_host_and_rejects_non_dbm(ports):
    good, octets = ports
    cache.delete(OPTICAL_LOCK_KEY)
    calls = []

    def fake(method, params=None, *a, **k):
        calls.append(method)
        return [
            {"itemid": "1", "key_": "rx.good", "lastvalue": "-19.25", "value_type": "0", **OK},
            {"itemid": "2", "key_": "tx.good", "lastvalue": "2.1", "value_type": "0", **OK},
            {
                "itemid": "3",
                "key_": "net.if.in[ifHCInOctets.1]",
                "lastvalue": "2246566704",
                "value_type": "3",
                **OK,
            },
        ]

    with patch(ZABBIX, side_effect=fake):
        result = update_all_port_optical_levels()

    assert calls == ["item.get"]  # um host → uma chamada (antes: ~5 por porta)
    assert result["updated"] == 1
    assert result["errors"] == 1
    good.refresh_from_db()
    octets.refresh_from_db()
    assert float(good.last_rx_power) == -19.25
    assert octets.last_rx_power is None  # contador de octetos não é dBm
    assert cache.get(OPTICAL_LOCK_KEY) is None  # lock libertado


@pytest.mark.django_db
def test_task_skips_while_previous_run_holds_lock(ports):
    cache.set(OPTICAL_LOCK_KEY, "a correr", 60)
    try:
        with patch(ZABBIX) as zabbix:
            result = update_all_port_optical_levels()
        assert result["skipped"] == "lock"
        zabbix.assert_not_called()
    finally:
        cache.delete(OPTICAL_LOCK_KEY)
