"""Fixtures do EV-0095: duas OLT (ZTE e VSOL) e um Zabbix falso por host."""

from types import SimpleNamespace

import pytest
from django.core.cache import cache

from inventory.models import Device, Site

ZTE_HOST = "10744"
VSOL_HOST = "10701"
CLOCK = "1795484312"

VALUEMAP_1406 = [
    {"type": "0", "value": "1", "newvalue": "Desconhecido"},
    {"type": "0", "value": "2", "newvalue": "LOS"},
    {"type": "0", "value": "3", "newvalue": "LOSi"},
    {"type": "0", "value": "9", "newvalue": "PowerOff"},
]


def item(key, lastvalue, *, value_type="0", lastclock=CLOCK, state="0", **extra):
    return {
        "key_": key,
        "value_type": value_type,
        "lastvalue": lastvalue,
        "lastclock": lastclock,
        "state": state,
        **extra,
    }


def zte_onu(serial, pon, onu, *, status="online", reason="9", rx="-20.5", dist="1500", slot=9):
    params = f"{serial},{slot},{pon},{onu}"
    return [
        item(f"onu.status[{params}]", status, value_type="1"),
        item(f"onu.offreason[{params}]", reason, value_type="3", valuemapid="1406"),
        item(f"onu.rx[{params}]", rx),
        item(f"onu.dist[{params}]", dist, value_type="3"),
    ]


def vsol_onu(pon, onu, mac, *, status="1", rx="-21.0", descr="NULL"):
    return [
        item(
            f"OnlineStateS0P{pon}[{mac} - {onu}]",
            status,
            value_type="3",
            name=f"Status da ONU 0/{pon}/{onu} - {mac} - {descr}",
        ),
        item(
            f"SinalRXS0P{pon}[{mac} - {onu}]",
            rx,
            name=f"Sinal RX da ONU 0/{pon}/{onu} - {mac} - {descr}",
        ),
    ]


class FakeZabbix:
    """``zabbix_request`` falso: itens por host, valuemaps, e falhas a pedido."""

    def __init__(self):
        self.items = {ZTE_HOST: [], VSOL_HOST: []}
        self.valuemaps = {"1406": VALUEMAP_1406}
        self.down_hosts: set[str] = set()
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, method, params=None, *args, **kwargs):
        params = params or {}
        self.calls.append((method, params))
        if method == "item.get":
            host = str(params["hostids"][0])
            if host in self.down_hosts:
                return None
            return list(self.items.get(host, []))
        if method == "valuemap.get":
            vid = params["valuemapids"][0]
            if vid not in self.valuemaps:
                return []
            return [{"valuemapid": vid, "mappings": self.valuemaps[vid]}]
        raise AssertionError(f"chamada inesperada: {method}")

    def count(self, method):
        return sum(1 for m, _ in self.calls if m == method)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def config(monkeypatch):
    cfg = SimpleNamespace(
        optical_rx_warning_threshold=-24.0,
        optical_rx_critical_threshold=-27.0,
        gpon_pon_capacity=128,
        epon_pon_capacity=64,
    )
    monkeypatch.setattr("gpon.usecases.runtime_settings.get_runtime_config", lambda: cfg)
    return cfg


@pytest.fixture
def olts(db):
    site = Site.objects.create(
        display_name="SITE - BARREIRA VELHA", latitude=-15.0, longitude=-47.0
    )
    zte = Device.objects.create(
        name="ZTE - OLT BRV C300", site=site, zabbix_hostid=ZTE_HOST, primary_ip="10.254.0.2"
    )
    vsol = Device.objects.create(name="VSOL - OLT EPON PLANURA", site=site, zabbix_hostid=VSOL_HOST)
    # Não são OLT: sem «OLT» no nome, ou sem Zabbix, ou fabricante desconhecido.
    Device.objects.create(name="ZTE Switch", site=site, zabbix_hostid="1")
    Device.objects.create(name="VSOL - OLT sem zabbix", site=site)
    Device.objects.create(name="Huawei OLT", site=site, zabbix_hostid="2")
    return SimpleNamespace(zte=zte, vsol=vsol, site=site)


@pytest.fixture
def fake_zabbix(monkeypatch):
    fake = FakeZabbix()
    monkeypatch.setattr("gpon.usecases.zabbix_request", fake)
    return fake
