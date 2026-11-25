"""EV-0086 — a descoberta só propõe/grava uma chave óptica quando o item É uma potência óptica.

Regra única (`inventory.domain.optical.match_optical_keys_for_ports`): unidade dBm (ou família
conhecida sem unidade), exclusão de tráfego/energia/estado/limiares, correspondência EXATA do
nome da porta ao nome da interface ou ao índice do item, um só candidato por sentido. Casos
reais do EV-0081: `net.if.in[ifHCInOctets…]` e `olt[power0|1]` gravados como RX/TX, a mesma
chave em portas «1»/«9», RX da VSOL usado também como TX.
"""

from __future__ import annotations

import itertools
import logging
from typing import Any
from unittest.mock import patch

import pytest
from django.core.cache import cache

from inventory.domain import optical
from inventory.models import Device, Port, Site
from inventory.services.fiber_status import fetch_interface_status_advanced
from inventory.usecases import devices as device_uc, devices_common, devices_discovery
from inventory.usecases.devices_common import _identify_item_role
from inventory.usecases.devices_ports import _preload_optical_discovery_cache

OPTICAL_ZABBIX = "inventory.domain.optical.zabbix_request"
STATUS_ZABBIX = "inventory.services.fiber_status.zabbix_request"
CLOCK = "1795450000"
_ITEMIDS = itertools.count(1000)


def _item(key: str, name: str = "", units: str = "dBm", **extra: Any) -> dict[str, Any]:
    item = {
        "itemid": extra.pop("itemid", str(next(_ITEMIDS))),
        "key_": key,
        "name": name,
        "units": units,
        "value_type": "0",
        "state": "0",
        "lastvalue": "-20.5",
        "lastclock": CLOCK,
        "interfaceid": "38",
    }
    item.update(extra)
    return item


def _huawei(direction: str, index: int, iface: str, **extra: Any) -> dict[str, Any]:
    label = "Recebida (RX)" if direction == "rx" else "Transmitida (TX)"
    family = "Rx" if direction == "rx" else "Tx"
    return _item(
        f"hwEntityOpticalLane{family}Power[{index}]",
        f"Potência {label} na interface {iface}",
        **extra,
    )


def _onu_rx(serial: str, slot: int, pon: int, onu: int, **extra: Any) -> dict[str, Any]:
    return _item(
        f"onu.rx[{serial},{slot},{pon},{onu}]",
        f"ONU {serial}: Potencia RX na OLT (upstream)",
        interfaceid="0",
        **extra,
    )


def _vsol(pon: int, onu: int, units: str = "dbm", iface: str | None = None) -> dict[str, Any]:
    iface = iface or f"GPON0/{pon}:{onu}"
    return _item(
        f"SinalRXS0P{pon}[{iface} - {onu}]",
        f"Sinal RX da ONU 0/{pon}/{onu} - SHLN3c350aca - {iface}",
        units=units,
    )


def _match(port_names: list[str], items: list[dict[str, Any]]) -> dict[str, dict]:
    return optical.match_optical_keys_for_ports(port_names, items, hostid="101")


# --- regra única: o que é potência óptica --------------------------------------------------


def test_traffic_item_with_in_in_name_is_not_chosen():
    port = "ifHCInOctets.269025536"
    items = [
        _item(
            f"net.if.in[{port}]",
            f"Interface {port}: Bits received (input)",
            units="bps",
            lastvalue="729352",
        ),
        # mesmo com a unidade mal configurada como dBm, tráfego nunca é potência
        _item(f"net.if.in[{port}]", f"{port}: input power", units="dBm"),
    ]
    assert _match([port], items)[port] == {"rx": None, "tx": None}
    assert optical.classify_optical_item(items[0])[0] is None


def test_olt_power_supply_is_not_chosen():
    items = [
        _item("olt[power0]", "OLT Power #0", units="W", value_type="3", lastvalue="322"),
        _item("olt[power1]", "OLT Power #1", units="", value_type="3", lastvalue="0"),
        _item("olt[power0]", "OLT Power #0 rx", units="dBm"),
    ]
    assert _match(["power0", "power1"], items) == {
        "power0": {"rx": None, "tx": None},
        "power1": {"rx": None, "tx": None},
    }


def test_two_dbm_candidates_for_the_same_port_choose_none(caplog):
    items = [
        _onu_rx("SHLN3C3C2609", 9, 13, 2),
        _onu_rx("SHLN3C4D936E", 9, 13, 2),
    ]
    port = f"{(0x10 << 24) | (9 << 16) | (13 << 8)}.2"  # 269028608.2
    with caplog.at_level(logging.INFO, logger="inventory.domain.optical"):
        result = _match([port], items)
    assert result[port] == {"rx": None, "tx": None}
    assert "2 candidatos RX" in caplog.text


def test_onu_rx_is_rx_without_invented_tx():
    items = [_onu_rx("GPON00A87658", 9, 1, 1), _onu_rx("GPON00A8CF38", 9, 1, 2)]
    # porta-ONU nomeada pelo ifIndex antigo da PON (0x10SSPP00) e porta de cartão «9»/«1»
    result = _match(["269025536.1", "269025536.2", "9", "1"], items)
    assert result["269025536.1"] == {"rx": "onu.rx[GPON00A87658,9,1,1]", "tx": None}
    assert result["269025536.2"] == {"rx": "onu.rx[GPON00A8CF38,9,1,2]", "tx": None}
    assert result["9"] == {"rx": None, "tx": None}
    assert result["1"] == {"rx": None, "tx": None}
    assert _identify_item_role("onu.rx[gpon00a87658,9,1,1]", "onu x: potencia rx") == ("optical_rx")
    assert _identify_item_role("olt[power0]", "olt power #0") is None


def test_huawei_rx_tx_dbm_are_chosen_by_exact_interface_name():
    items = [
        _huawei("rx", 67469902, "XGigabitEthernet0/0/9"),
        _huawei("tx", 67469902, "XGigabitEthernet0/0/9"),
        _huawei("rx", 67472206, "XGigabitEthernet0/0/45"),
        _huawei("tx", 67472206, "XGigabitEthernet0/0/45"),
        # limiares do transceptor também vêm em dBm e não são a potência medida
        _item("hwEntityOpticalRxLowThreshold[67469902]", "Rx Low Threshold XGigabitEthernet0/0/9"),
    ]
    result = _match(["XGigabitEthernet0/0/9", "XGigabitEthernet0/0/4"], items)
    assert result["XGigabitEthernet0/0/9"] == {
        "rx": "hwEntityOpticalLaneRxPower[67469902]",
        "tx": "hwEntityOpticalLaneTxPower[67469902]",
    }
    # «XGigabitEthernet0/0/4» é substring de «…0/0/45»: antes levava as chaves da 0/0/45
    assert result["XGigabitEthernet0/0/4"] == {"rx": None, "tx": None}


def test_vsol_sinal_rx_only_as_rx_and_macro_duplicate_ignored():
    items = [
        _vsol(1, 1),
        _vsol(1, 4, units=""),  # template sem unidade: aceite pela família
        _vsol(1, 4, iface="{#USERNAME}"),  # cópia LLD por expandir (outra ONU)
    ]
    result = _match(["GPON0/1:1", "GPON0/1:4", "GPON0/1:6", "GPON0/1"], items)
    assert result["GPON0/1:1"] == {"rx": "SinalRXS0P1[GPON0/1:1 - 1]", "tx": None}
    assert result["GPON0/1:4"] == {"rx": "SinalRXS0P1[GPON0/1:4 - 4]", "tx": None}
    assert result["GPON0/1:6"] == {"rx": None, "tx": None}
    assert result["GPON0/1"] == {"rx": None, "tx": None}  # PON ≠ ONU


def test_unsupported_or_impossible_current_reading_is_not_proposed():
    """Huawei sem DDM (portas 334/514): RX unsupported, TX = 32,2471 «dBm»."""
    items = [
        _huawei("rx", 67469646, "XGigabitEthernet0/0/5", state="1", lastvalue="0"),
        _huawei("tx", 67469646, "XGigabitEthernet0/0/5", lastvalue="32.2471"),
        # sentinela de ONU offline não desqualifica o item
        _onu_rx("ZTEGC8F88195", 9, 7, 1, lastvalue="-80"),
    ]
    result = _match(["XGigabitEthernet0/0/5", f"{(0x10 << 24) | (9 << 16) | (7 << 8)}.1"], items)
    assert result["XGigabitEthernet0/0/5"] == {"rx": None, "tx": None}
    assert result["269027072.1"]["rx"] == "onu.rx[ZTEGC8F88195,9,7,1]"


def test_generic_dbm_item_needs_unit_and_direction():
    items = [
        _item("custom.rx[eth1]", "eth1: optical RX", units="dBm"),
        _item("custom.tx[eth1]", "eth1: optical TX", units="DBM"),
        _item("custom.rx[eth2]", "eth2: RX power", units=""),  # sem unidade, fora das famílias
        _item("custom.power[eth3]", "eth3: power", units="dBm"),  # sentido indefinido
    ]
    result = _match(["eth1", "eth2", "eth3"], items)
    assert result["eth1"] == {"rx": "custom.rx[eth1]", "tx": "custom.tx[eth1]"}
    assert result["eth2"] == {"rx": None, "tx": None}
    assert result["eth3"] == {"rx": None, "tx": None}


# --- os caminhos que gravam chaves --------------------------------------------------------


@pytest.fixture
def host_device(db):
    site = Site.objects.create(display_name="POP", latitude=-15.0, longitude=-47.0)
    return Device.objects.create(name="OLT", site=site, zabbix_hostid="101")


HOST_ITEMS = [
    _onu_rx("GPON00A87658", 9, 1, 1),
    _item("olt[power0]", "OLT Power #0", units="W", value_type="3", lastvalue="322"),
    _item(
        "net.if.in[ifHCInOctets.285280520]",
        "Bits received",
        units="bps",
        value_type="3",
        lastvalue="729352",
    ),
    _huawei("rx", 67469902, "XGigabitEthernet0/0/9"),
    _huawei("tx", 67469902, "XGigabitEthernet0/0/9"),
    _vsol(1, 1, units=""),
]


def _fake_optical_zabbix(calls: list[tuple[str, dict]]):
    def fake(method: str, params: dict[str, Any] | None = None, *a: Any, **k: Any):
        params = params or {}
        calls.append((method, params))
        if method != "item.get":
            return []
        wanted = (params.get("filter") or {}).get("key_")
        if wanted:
            wanted = set(wanted if isinstance(wanted, list) else [wanted])
            return [i for i in HOST_ITEMS if i["key_"] in wanted]
        return list(HOST_ITEMS)

    return fake


@pytest.mark.django_db
def test_persist_keys_writes_only_real_optical_keys(host_device):
    names = [
        "269025536.1",
        "9",
        "1",
        "power0",
        "ifHCInOctets.285280520",
        "XGigabitEthernet0/0/9",
        "GPON0/1:1",
    ]
    ports = [Port.objects.create(device=host_device, name=n) for n in names]
    calls: list[tuple[str, dict]] = []
    with patch(OPTICAL_ZABBIX, side_effect=_fake_optical_zabbix(calls)):
        optical.fetch_ports_optical_snapshots(ports, persist_keys=True, include_status_meta=False)

    keys = {p.name: (p.rx_power_item_key, p.tx_power_item_key) for p in Port.objects.all()}
    assert keys == {
        "269025536.1": ("onu.rx[GPON00A87658,9,1,1]", ""),
        "9": ("", ""),
        "1": ("", ""),
        "power0": ("", ""),
        "ifHCInOctets.285280520": ("", ""),
        "XGigabitEthernet0/0/9": (
            "hwEntityOpticalLaneRxPower[67469902]",
            "hwEntityOpticalLaneTxPower[67469902]",
        ),
        "GPON0/1:1": ("SinalRXS0P1[GPON0/1:1 - 1]", ""),
    }
    discovery_calls = [p for m, p in calls if m == "item.get" and "key_" not in p.get("filter", {})]
    assert len(discovery_calls) == 1  # um item.get por host, nunca por porta
    assert all("search" not in p for _, p in calls)  # sem LIKE


@pytest.mark.django_db
def test_preload_cache_uses_the_same_rule(host_device):
    cache.clear()
    ports = [
        Port.objects.create(device=host_device, name=n)
        for n in ("9", "269025536.1", "XGigabitEthernet0/0/9", "power0")
    ]
    with patch.object(devices_common, "ZABBIX_REQUEST", return_value=list(HOST_ITEMS)) as zbx:
        result = _preload_optical_discovery_cache("101", ports)
    assert zbx.call_count == 1
    assert "search" not in zbx.call_args.args[1]
    assert result[("101", "9")] == {"rx": None, "tx": None}
    assert result[("101", "power0")] == {"rx": None, "tx": None}
    assert result[("101", "269025536.1")] == {"rx": "onu.rx[GPON00A87658,9,1,1]", "tx": None}
    assert result[("101", "XGigabitEthernet0/0/9")]["tx"] == (
        "hwEntityOpticalLaneTxPower[67469902]"
    )


@pytest.mark.django_db
def test_add_device_from_zabbix_assigns_onu_rx_only_to_its_port():
    cache.clear()
    items = [
        _item("ifOperStatus[1]", "IF 1: Status", units="", interfaceid="7"),
        _item("ifOperStatus[9]", "IF 9: Status", units="", interfaceid="7"),
        _item("ifOperStatus[269025536.1]", "ONU 9/1/1: Status", units="", interfaceid="7"),
        _onu_rx("GPON00A87658", 9, 1, 1),
        _item("olt[power1]", "OLT Power #1", units="W", value_type="3"),
    ]

    def fake(method: str, params: dict[str, Any]):
        if method == "host.get":
            return [{"hostid": "10744", "name": "ZTE - OLT", "host": "zte-olt", "inventory": {}}]
        if method == "item.get":
            return items
        return []

    site = Site.objects.create(display_name="BRV", latitude=-15.0, longitude=-47.0)
    Device.objects.create(name="zte-olt", site=site, zabbix_hostid="10744")
    with (
        patch.object(devices_common, "ZABBIX_REQUEST", side_effect=fake),
        patch(OPTICAL_ZABBIX, return_value=[]),
        patch.object(devices_discovery, "sync_device_groups_for_device", return_value=None),
        patch("inventory.services.import_rules.apply_import_rules", return_value=None),
    ):
        device_uc.add_device_from_zabbix({"hostid": "10744", "update_site": False})

    keys = {p.name: (p.rx_power_item_key, p.tx_power_item_key) for p in Port.objects.all()}
    assert keys == {
        "1": ("", ""),
        "9": ("", ""),
        "269025536.1": ("onu.rx[GPON00A87658,9,1,1]", ""),
    }


@pytest.mark.django_db
def test_fiber_status_interface_discovery_requires_exact_port_and_dbm():
    interface_items = [
        _item("ifInErrors.rx[eth0]", "eth0 rx errors", units=""),  # antes: `rx_key_generic`
        _item("rx.counter[eth0]", "eth0 rx packets", units="pps"),
        _huawei("rx", 67469902, "XGigabitEthernet0/0/9", lastvalue="-12.3"),
        _huawei("rx", 67472206, "XGigabitEthernet0/0/45", lastvalue="-30.1"),
    ]

    def fake(method: str, params: dict[str, Any] | None = None, *a: Any, **k: Any):
        if method == "item.get" and params and "interfaceids" in params:
            return interface_items
        return []

    with patch(STATUS_ZABBIX, side_effect=fake):
        no_name = fetch_interface_status_advanced("101", interfaceid="38")
        other = fetch_interface_status_advanced("101", interfaceid="38", port_name="eth0")
        exact = fetch_interface_status_advanced(
            "101", interfaceid="38", port_name="XGigabitEthernet0/0/9"
        )

    assert no_name == (
        "unknown",
        {"method": "no_items_found", "interfaceid": "38", "auto_discovery_attempt": True},
    )
    assert other[0] == "unknown"
    assert "rx_key_generic" not in other[1] and "rx_key" not in other[1]
    assert exact[1]["rx_key"] == "hwEntityOpticalLaneRxPower[67469902]"
    assert exact[1]["rx"] == -12.3
    assert "tx_key" not in exact[1]
