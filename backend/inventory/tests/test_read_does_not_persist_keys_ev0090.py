"""EV-0090 — abrir um ecrã (leitura) nunca grava chaves ópticas na base.

`persist_keys` passa a False por omissão; os três caminhos de leitura de
`usecases/devices_ports.py` não gravam; só a descoberta de equipamentos pede True.
"""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import patch

import pytest

from inventory.domain import optical
from inventory.models import Device, Port, Site
from inventory.tests.test_optical_key_discovery_ev0086 import OPTICAL_ZABBIX, _fake_optical_zabbix
from inventory.usecases import devices_ports

DISCOVERABLE = "269025536.1"  # a descoberta, se corresse, gravaria onu.rx[...] nesta porta
PRESET_RX = "hwEntityOpticalLaneRxPower[67469902]"


@pytest.fixture
def host_device(db):
    site = Site.objects.create(display_name="POP", latitude=-15.0, longitude=-47.0)
    return Device.objects.create(name="OLT", site=site, zabbix_hostid="101")


@pytest.fixture
def ports(host_device):
    keyless = Port.objects.create(device=host_device, name=DISCOVERABLE)
    keyed = Port.objects.create(
        device=host_device, name="XGigabitEthernet0/0/9", rx_power_item_key=PRESET_RX
    )
    return keyless, keyed


def _keys() -> dict[str, tuple[str, str]]:
    return {p.name: (p.rx_power_item_key, p.tx_power_item_key) for p in Port.objects.all()}


def _no_status(*_a: Any, **_k: Any) -> dict:
    return {}


def test_persist_keys_defaults_to_false():
    for func in (optical.fetch_port_optical_snapshot, optical.fetch_ports_optical_snapshots):
        assert inspect.signature(func).parameters["persist_keys"].default is False


@pytest.mark.django_db
def test_default_call_does_not_write_keys(ports):
    before = _keys()
    with patch(OPTICAL_ZABBIX, side_effect=_fake_optical_zabbix([])):
        optical.fetch_ports_optical_snapshots(list(ports), include_status_meta=False)
        optical.fetch_port_optical_snapshot(ports[0], include_status_meta=False)
    assert _keys() == before
    for port in ports:
        port.refresh_from_db()
    assert (ports[0].rx_power_item_key, ports[0].tx_power_item_key) == ("", "")


@pytest.mark.django_db
def test_explicit_persist_keys_still_writes(ports):
    with patch(OPTICAL_ZABBIX, side_effect=_fake_optical_zabbix([])):
        optical.fetch_ports_optical_snapshots(
            list(ports), persist_keys=True, include_status_meta=False
        )
    ports[0].refresh_from_db()
    assert ports[0].rx_power_item_key == "onu.rx[GPON00A87658,9,1,1]"


@pytest.mark.django_db
def test_live_status_get_does_not_write_keys(host_device, ports):
    before = _keys()
    with (
        patch(OPTICAL_ZABBIX, side_effect=_fake_optical_zabbix([])),
        patch.object(devices_ports, "_preload_optical_discovery_cache", return_value={}),
        patch.object(devices_ports, "_fetch_interface_status_bulk", side_effect=_no_status),
    ):
        devices_ports.get_device_ports_with_live_status(host_device.pk)
    assert _keys() == before


@pytest.mark.django_db
def test_ports_with_optical_get_does_not_write_keys(host_device, ports):
    before = _keys()
    with (
        patch(OPTICAL_ZABBIX, side_effect=_fake_optical_zabbix([])),
        patch.object(devices_ports, "_preload_optical_discovery_cache", return_value={}),
    ):
        devices_ports.get_device_ports_with_optical(host_device.pk)
    assert _keys() == before


@pytest.mark.django_db
def test_port_optical_status_get_does_not_write_keys(ports):
    before = _keys()
    with (
        patch(OPTICAL_ZABBIX, side_effect=_fake_optical_zabbix([])),
        patch(
            "inventory.services.fiber_status.zabbix_request",
            side_effect=_fake_optical_zabbix([]),
        ),
    ):
        devices_ports.device_port_optical_status(ports[0].pk)
        devices_ports.device_port_optical_status(ports[1].pk)
    assert _keys() == before


@pytest.mark.django_db
def test_usecases_ask_for_persist_keys_false(host_device, ports):
    seen: list[bool] = []
    real = optical.fetch_ports_optical_snapshots

    def spy(*args: Any, **kwargs: Any):
        seen.append(kwargs.get("persist_keys", "omitido"))
        return real(*args, **kwargs)

    with (
        patch(OPTICAL_ZABBIX, side_effect=_fake_optical_zabbix([])),
        patch.object(devices_ports, "fetch_ports_optical_snapshots", side_effect=spy),
        patch.object(devices_ports, "_preload_optical_discovery_cache", return_value={}),
        patch.object(devices_ports, "_fetch_interface_status_bulk", side_effect=_no_status),
    ):
        devices_ports.get_device_ports_with_live_status(host_device.pk)
        devices_ports.get_device_ports_with_optical(host_device.pk)
    assert seen == [False, False]


@pytest.mark.django_db
def test_read_screens_do_not_preload_discovery_ev0094(host_device, ports):
    """EV-0094: sem descoberta na leitura, a pré-carga (um item.get do host inteiro) não corre."""
    with (
        patch(OPTICAL_ZABBIX, side_effect=_fake_optical_zabbix([])),
        patch.object(devices_ports, "_preload_optical_discovery_cache") as preload,
        patch.object(devices_ports, "_fetch_interface_status_bulk", side_effect=_no_status),
    ):
        devices_ports.get_device_ports_with_live_status(host_device.pk)
        devices_ports.get_device_ports_with_optical(host_device.pk)
    preload.assert_not_called()
