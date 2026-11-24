"""EV-0115 — Monitoramento de Switches: parser dos itens Huawei, classificação das portas,
visão geral com o inventário (cabo), KPIs, cache e Zabbix fora."""

import time
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from inventory.models import Device, FiberCable, Port, Site
from switches import usecases
from switches.domain import parsers

NOW = time.time()
FRESH = str(int(NOW) - 30)
OLD = str(int(NOW) - 3600)
TH = {"warning": -20.0, "critical": -24.0}


def it(key, value, name="", clock=FRESH):
    return {
        "key_": key,
        "name": name,
        "lastvalue": str(value),
        "lastclock": clock,
        "value_type": "3",
    }


def iface(ifname, *, oper=1, admin=1, speed=10000, inb=1e9, outb=2e8, desc="", up_ms=3_383_530_000):
    n = f"Status Operacional da Porta {ifname} - {desc}"
    return [
        it(f"ifOperStatus[{ifname}]", oper, n),
        it(f"ifAdminStatus[{ifname}]", admin, n),
        it(f"ifSpeed[{ifname}]", speed, n),
        it(f"ifHCInOctets[{ifname}]", inb, n),
        it(f"ifHCOutOctets[{ifname}]", outb, n),
        it(f"InterfaceUptime[{ifname}]", up_ms, n),
    ]


def optical(idx, ifname, rx, tx=1.28, clock=FRESH):
    return [
        it(
            f"hwEntityOpticalLaneRxPower[{idx}]",
            rx,
            f"Potência Recebida (RX) na interface {ifname}",
            clock,
        ),
        it(
            f"hwEntityOpticalLaneTxPower[{idx}]",
            tx,
            f"Potência Transmitida (TX) na interface {ifname}",
            clock,
        ),
    ]


DEVICE_ITEMS = [
    it("icmpping", 1),
    it("hwCpuDevDuty", 5),
    it("sysDescr", "S6730-H24X6C \r\nHuawei Versatile Routing Platform"),
    it("sysUpTime", 7046891),
    it("sensor.temp.value[hwEntityTemperature.67108873]", 33, "MPU Board 0: Temperature"),
    it("sensor.temp.value[hwEntityTemperature.67108874]", 41, "LPU: Temperature"),
]


# ── parser ────────────────────────────────────────────────────────────────────
def test_parse_device_and_interfaces_with_optical_by_name():
    items = (
        DEVICE_ITEMS
        + iface("XGigabitEthernet0/0/1", desc="Enlace-Veranopolis")
        + optical(67469390, "XGigabitEthernet0/0/1", -15.3912)
    )
    parsed = parsers.parse_items(items, NOW)
    assert parsed["device"] == {
        "ping": 1,
        "cpu_pct": 5.0,
        "temperature_c": 41.0,
        "model": "S6730-H24X6C",
        "uptime_s": 7046891.0,
        "last_clock": int(FRESH),
    }
    entry = parsed["interfaces"]["XGigabitEthernet0/0/1"]
    assert (entry["description"], entry["rx_dbm"], entry["tx_dbm"], entry["speed_mbps"]) == (
        "Enlace-Veranopolis",
        -15.39,
        1.28,
        10000.0,
    )


def test_stale_values_are_none_not_zero():
    items = [
        it(
            "ifOperStatus[XGigabitEthernet0/0/2]",
            1,
            "Status Operacional da Porta XGigabitEthernet0/0/2 - x",
            OLD,
        )
    ]
    entry = parsers.parse_items(items, NOW)["interfaces"]["XGigabitEthernet0/0/2"]
    assert entry["oper"] is None
    assert parsers.classify_port(entry, "XGigabitEthernet0/0/2", **TH)["state"] == "unknown"


@pytest.mark.parametrize(
    "oper, admin, desc, cable, rx, inb, state, reasons",
    [
        (1, 1, "Enlace", False, -15.0, 1e9, "normal", []),
        (1, 1, "Enlace", False, -21.4, 1e9, "warning", ["rx_warning"]),
        (1, 1, "Enlace", False, -24.5, 1e9, "critical", ["rx_critical"]),
        (1, 1, "Enlace", False, -40.0, 1e9, "down", ["los"]),  # sem luz
        (2, 1, "Enlace", False, None, None, "down", ["link_down"]),
        (2, 1, "", True, None, None, "down", ["link_down"]),  # cabo ligado = em uso
        (2, 1, "", False, None, None, "free", []),
        (1, 2, "Enlace", False, None, None, "free", []),  # desligada pelo admin
        (1, 1, "Enlace", False, -15.0, 9.1e9, "warning", ["utilization"]),  # > 80 % de 10G
    ],
)
def test_classify_port(oper, admin, desc, cable, rx, inb, state, reasons):
    entry = {
        "oper": oper,
        "admin": admin,
        "speed_mbps": 10000,
        "in_bps": inb,
        "out_bps": 1e6,
        "rx_dbm": rx,
        "description": desc,
        "uptime_ms": 1000,
    }
    out = parsers.classify_port(entry, "XGigabitEthernet0/0/1", has_cable=cable, **TH)
    assert (out["state"], out["reasons"]) == (state, reasons)


def test_speed_label_kind_and_sort():
    assert parsers.speed_label(10000, "XGigabitEthernet0/0/1") == "10G"
    assert parsers.speed_label(0, "40GE0/0/1") == "40G"  # em baixo: nominal pelo nome
    assert parsers.speed_label(1000, "GigabitEthernet0/0/1") == "1G"
    assert parsers.port_kind("MEth0/0/1") == "mgmt" and parsers.port_kind("40GE0/0/1") == "optical"
    names = ["XGigabitEthernet0/0/10", "MEth0/0/1", "40GE0/0/1", "XGigabitEthernet0/0/2"]
    assert sorted(names, key=parsers.ifname_sort_key) == [
        "40GE0/0/1",
        "XGigabitEthernet0/0/2",
        "XGigabitEthernet0/0/10",
        "MEth0/0/1",
    ]


# ── visão geral ───────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _env(monkeypatch):
    cache.clear()
    cfg = SimpleNamespace(backbone_rx_warning_threshold=-20.0, backbone_rx_critical_threshold=-24.0)
    monkeypatch.setattr("switches.usecases.runtime_settings.get_runtime_config", lambda: cfg)
    yield
    cache.clear()


@pytest.fixture
def switches(db):
    site = Site.objects.create(display_name="SITE - CONFRESA", latitude=-10.6, longitude=-51.5)
    sw = Device.objects.create(
        name="huawei - Switch Confresa", site=site, zabbix_hostid="10679", primary_ip="198.18.27.1"
    )
    off = Device.objects.create(
        name="Huawei - Switch Santa terezinha", site=site, zabbix_hostid="10663"
    )
    Device.objects.create(
        name="Cisco - Switch Barreira", site=site, zabbix_hostid="10669"
    )  # fabricante sem template suportado: fora
    Device.objects.create(name="ZTE - OLT CONFRESA C600 - 01", site=site, zabbix_hostid="10744")
    port = Port.objects.create(device=sw, name="XGigabitEthernet0/0/2")
    other = Device.objects.create(name="OUTRO", site=site)
    FiberCable.objects.create(
        name="CONFRESA - VLR",
        origin_port=port,
        destination_port=Port.objects.create(device=other, name="P1"),
    )
    return SimpleNamespace(sw=sw, off=off, port=port)


def fake(monkeypatch, by_host):
    calls = []

    def zr(method, params=None, *a, **k):
        calls.append(params["hostids"][0])
        return by_host.get(params["hostids"][0])

    monkeypatch.setattr("switches.usecases.zabbix_request", zr)
    return calls


def test_overview_joins_inventory_counts_and_kpis(switches, monkeypatch):
    sw_items = (
        DEVICE_ITEMS
        + iface("XGigabitEthernet0/0/1", desc="Enlace-Veranopolis")
        + optical(1, "XGigabitEthernet0/0/1", -15.0)
        + iface("XGigabitEthernet0/0/2", oper=2, inb=0, outb=0, desc="")  # down, mas com cabo
        + optical(2, "XGigabitEthernet0/0/2", -40)
        + iface("XGigabitEthernet0/0/3", desc="Enlace-Elagro")
        + optical(3, "XGigabitEthernet0/0/3", -21.4)
        + iface("XGigabitEthernet0/0/4", oper=2, desc="")  # livre
        + iface("MEth0/0/1", speed=1000, desc="gerencia")
    )
    off_items = [it("icmpping", 0), it("ifOperStatus[XGigabitEthernet0/0/1]", 1, "x", OLD)]
    calls = fake(monkeypatch, {"10679": sw_items, "10663": off_items})

    data = usecases.switches_overview(refresh=True)

    assert sorted(calls) == ["10663", "10679"]  # Cisco e OLT fora
    assert list(data) == [
        "collected_at",
        "zabbix_ok",
        "zabbix_error",
        "thresholds",
        "totals",
        "switches",
        "ports",
        "duration_ms",
    ]
    assert data["zabbix_ok"] is True
    conf = next(s for s in data["switches"] if s["device_id"] == switches.sw.pk)
    assert (conf["model"], conf["status"], conf["cpu_pct"], conf["temperature_c"]) == (
        "S6730-H24X6C",
        "online",
        5.0,
        41.0,
    )
    assert (
        conf["ports_total"],
        conf["ports_up"],
        conf["ports_in_use"],
        conf["ports_down"],
        conf["signal_warning"],
    ) == (4, 2, 3, 1, 1)
    off = next(s for s in data["switches"] if s["device_id"] == switches.off.pk)
    assert (off["status"], off["ports_in_use"]) == ("offline", 0)
    p2 = next(
        p
        for p in data["ports"]
        if p["device_id"] == switches.sw.pk and p["name"] == "XGigabitEthernet0/0/2"
    )
    assert (p2["state"], p2["reasons"], p2["cable_name"], p2["port_id"]) == (
        "down",
        ["los"],
        "CONFRESA - VLR",
        switches.port.pk,
    )
    t = data["totals"]
    assert (
        t["switches"],
        t["switches_online"],
        t["switches_offline"],
        t["ports_down"],
        t["signal_warning"],
    ) == (2, 1, 1, 1, 1)
    assert t["hottest"] == {
        "device_id": switches.sw.pk,
        "name": "huawei - Switch Confresa",
        "value": 41.0,
    }


def test_cache_and_zabbix_down(switches, monkeypatch):
    calls = fake(monkeypatch, {"10679": DEVICE_ITEMS, "10663": DEVICE_ITEMS})
    usecases.switches_overview()
    usecases.switches_overview()
    assert len(calls) == 2  # o segundo pedido veio da cache
    cache.clear()
    fake(monkeypatch, {})  # nenhum host responde
    data = usecases.switches_overview()
    assert data["zabbix_ok"] is False and data["zabbix_error"]
    assert all(s["status"] == "unknown" and not s["collection_ok"] for s in data["switches"])
    assert cache.get(usecases.OVERVIEW_CACHE_KEY) is None


def test_endpoint_requires_login(switches, monkeypatch):
    fake(monkeypatch, {"10679": DEVICE_ITEMS, "10663": DEVICE_ITEMS})
    url = "/api/v1/monitoring/switches/"
    assert Client().get(url).status_code in (401, 403, 302)
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    body = c.get(url, {"refresh": "true"}).json()
    assert body["totals"]["switches"] == 2 and body["thresholds"]["warning"] == -20.0


def test_thresholds_come_from_config_and_are_ordered(monkeypatch):
    cfg = SimpleNamespace(backbone_rx_warning_threshold=-26.0, backbone_rx_critical_threshold=-22.0)
    monkeypatch.setattr("switches.usecases.runtime_settings.get_runtime_config", lambda: cfg)
    assert usecases.thresholds()["warning"] == -22.0 and usecases.thresholds()["critical"] == -26.0


def test_collected_at_is_iso(switches, monkeypatch):
    fake(monkeypatch, {"10679": DEVICE_ITEMS, "10663": DEVICE_ITEMS})
    data = usecases.switches_overview(now=timezone.now())
    assert data["collected_at"].endswith("Z")


def test_switch_detail_cuts_the_overview_and_404s_for_non_switches(switches, monkeypatch):
    fake(
        monkeypatch,
        {"10679": DEVICE_ITEMS + iface("XGigabitEthernet0/0/1", desc="x"), "10663": DEVICE_ITEMS},
    )
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    body = c.get(f"/api/v1/monitoring/switches/{switches.sw.pk}/").json()
    assert list(body) == [
        "collected_at",
        "zabbix_ok",
        "zabbix_error",
        "thresholds",
        "switch",
        "ports",
    ]
    assert body["switch"]["device_id"] == switches.sw.pk
    assert {p["device_id"] for p in body["ports"]} == {switches.sw.pk}
    cisco = Device.objects.get(name__startswith="Cisco")
    assert c.get(f"/api/v1/monitoring/switches/{cisco.pk}/").status_code == 404
    assert Client().get(f"/api/v1/monitoring/switches/{switches.sw.pk}/").status_code in (
        401,
        403,
        302,
    )


# ── EV-0117: Ubiquiti (template IF-MIB genérico) ──────────────────────────────
def snmp_if(idx, name, desc, *, oper=1, speed=4294967295, inb=1e8, outb=2e7, if_type=6):
    label = f"Interface {name}({desc})"
    return [
        it(f"net.if.status[ifOperStatus.{idx}]", oper, f"{label}: Operational status"),
        it(f"net.if.speed[ifSpeed.{idx}]", speed, f"{label}: Speed"),
        it(f"net.if.in[ifInOctets.{idx}]", inb, f"{label}: Bits received"),
        it(f"net.if.out[ifOutOctets.{idx}]", outb, f"{label}: Bits sent"),
        it(f"net.if.type[ifType.{idx}]", if_type, f"{label}: Interface type"),
    ]


UBQ_DEVICE = [
    it("icmpping", 1),
    it("usoCPU", 12.7),
    it("system.descr[sysDescr.0]", "EdgeSwitch 16 XG, 1.9.2, Linux 3.6.5"),
    it("system.net.uptime[sysUpTime.0]", 1349056),
    it("sensorTemp1", 58),
    it("sensorTemp3", 63),
]


def test_parse_snmp_names_speed_and_only_ethernet():
    items = (
        UBQ_DEVICE
        + snmp_if(1, "0/1", "NOVA-BARREIRA")
        + snmp_if(6, "0/6", "RB-GERENCIA", speed=1_000_000_000)
        + snmp_if(65, "lag 1", "", if_type=161)  # LAG: fora
    )
    parsed = parsers.parse_items_snmp(items, NOW)
    assert parsed["device"] == {
        "ping": 1,
        "cpu_pct": 12.7,
        "temperature_c": 63.0,
        "model": "EdgeSwitch 16 XG",
        "uptime_s": 1349056.0,
        "last_clock": int(FRESH),
    }
    assert set(parsed["interfaces"]) == {"0/1", "0/6"}
    p1 = parsed["interfaces"]["0/1"]
    assert (p1["description"], p1["if_index"], p1["speed_mbps"], p1["speed_over_4g"]) == (
        "NOVA-BARREIRA",
        1,
        None,
        True,
    )
    assert parsers.speed_label(None, "0/1", over_4g=True) == "> 4G"  # Gauge32 saturado
    assert parsed["interfaces"]["0/6"]["speed_mbps"] == 1000.0


def test_ubiquiti_enters_the_overview_and_joins_inventory_by_index(db, monkeypatch):
    site = Site.objects.create(display_name="SITE - BARREIRA VELHA", latitude=-9.0, longitude=-50.0)
    ubq = Device.objects.create(
        name="Ubiquiti - Switch Barreira velha", site=site, zabbix_hostid="10669"
    )
    port = Port.objects.create(device=ubq, name="ifOperStatus.1")
    calls = []

    def zr(method, params=None, *a, **k):
        calls.append(params["search"]["key_"])
        return (
            UBQ_DEVICE + snmp_if(1, "0/1", "NOVA-BARREIRA") + snmp_if(5, "0/5", "CASEARA", oper=2)
        )

    monkeypatch.setattr("switches.usecases.zabbix_request", zr)
    data = usecases.switches_overview(refresh=True)
    assert "net.if." in calls[0]  # pediu as chaves do template IF-MIB
    sw = data["switches"][0]
    assert (sw["vendor"], sw["model"], sw["status"], sw["ports_down"]) == (
        "ubiquiti",
        "EdgeSwitch 16 XG",
        "online",
        1,
    )
    p1 = next(p for p in data["ports"] if p["name"] == "0/1")
    assert (p1["port_id"], p1["speed_label"], p1["utilization_pct"]) == (port.pk, "> 4G", None)


def test_slow_huawei_items_stay_fresh_for_twice_their_interval():
    """EV-0129: InterfaceUptime/ifSpeed são coletados a cada 30 min."""
    age = str(int(NOW) - 1500)  # 25 min
    n = "Interface Uptime em XGigabitEthernet0/0/1 - UPlink"
    items = [
        {
            "key_": "InterfaceUptime[XGigabitEthernet0/0/1]",
            "name": n,
            "lastvalue": "1296710000",
            "lastclock": age,
            "delay": "30m",
        },
        {
            "key_": "ifOperStatus[XGigabitEthernet0/0/1]",
            "name": n,
            "lastvalue": "1",
            "lastclock": age,
            "delay": "1m",
        },
    ]
    entry = parsers.parse_items(items, NOW)["interfaces"]["XGigabitEthernet0/0/1"]
    assert entry["uptime_ms"] == 1296710000.0  # 25 min < o dobro de 30 min
    assert entry["oper"] is None  # 25 min > 10 min para um item de 1 min
    assert parsers.max_age_seconds("30m") == 3600
    assert parsers.max_age_seconds("30s") == 600
    assert parsers.max_age_seconds("{$IF.DELAY}") == 600
    assert parsers.max_age_seconds(None) == 600
