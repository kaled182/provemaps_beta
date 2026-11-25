"""EV-0058 — métricas em lote: origem do número (Zabbix x manual), última coleta e
«Zabbix fora» distinto de «sem dados»; idem no estado Zabbix dos equipamentos."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from inventory.models import Device, Site

ZABBIX = "integrations.zabbix.zabbix_service.zabbix_request"


@pytest.fixture
def client(db):
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    return c


@pytest.fixture
def devices(db):
    site = Site.objects.create(display_name="POP", latitude=-15.0, longitude=-47.0)
    measured = Device.objects.create(
        name="OLT-1",
        site=site,
        zabbix_hostid="101",
        uptime_item_key="system.uptime",
        cpu_usage_item_key="cpu.util",
    )
    manual = Device.objects.create(
        name="SW-2",
        site=site,
        zabbix_hostid="102",
        uptime_item_key="system.uptime",
        cpu_usage_manual_percent=35,
    )
    return measured, manual


def _get(client, devices):
    ids = ",".join(str(d.id) for d in devices)
    return client.get(f"/api/v1/devices/metrics-batch/?ids={ids}")


@pytest.mark.django_db
def test_measured_vs_manual_and_last_collected(client, devices):
    measured, manual = devices
    items = [
        {"hostid": "101", "key_": "system.uptime", "lastvalue": "90061", "lastclock": "1795450000"},
        {"hostid": "101", "key_": "cpu.util", "lastvalue": "12.5%", "lastclock": "1795450060"},
        {"hostid": "102", "key_": "system.uptime", "lastvalue": "60", "lastclock": "1795449000"},
    ]
    with patch(ZABBIX, return_value=items):
        body = _get(client, devices).json()

    assert body["zabbix_error"] is False
    m = body["results"][str(measured.id)]
    assert m["cpu"] == 12.5
    assert m["cpu_source"] == "zabbix"
    assert m["uptime_human"] == "1d 1h 1m"
    # o lastclock mais recente das métricas do equipamento
    assert m["last_collected"] == datetime.fromtimestamp(1795450060, tz=UTC).isoformat()
    s = body["results"][str(manual.id)]
    assert s["cpu"] == 35.0
    assert s["cpu_source"] == "manual"  # configurado, não medido
    assert s["memory_source"] is None


@pytest.mark.django_db
def test_zabbix_down_is_flagged_not_silent(client, devices):
    with patch(ZABBIX, side_effect=RuntimeError("timeout")):
        body = _get(client, devices).json()
    assert body["zabbix_error"] is True
    assert all(r["uptime_seconds"] is None for r in body["results"].values())

    with patch(ZABBIX, return_value=None):  # circuit breaker aberto
        assert _get(client, devices).json()["zabbix_error"] is True

    with patch(ZABBIX, return_value=[]):  # respondeu, só não há itens
        assert _get(client, devices).json()["zabbix_error"] is False


@pytest.mark.django_db
def test_zabbix_status_flags_failure(client, devices):
    ids = ",".join(str(d.id) for d in devices)
    url = f"/api/v1/inventory/devices/zabbix-status/?device_ids={ids}"
    with patch(ZABBIX, side_effect=RuntimeError("timeout")):
        body = client.get(url).json()
    assert body["zabbix_error"] is True
    assert set(body["statuses"].values()) == {"unknown"}

    with patch(ZABBIX, return_value=None):
        assert client.get(url).json()["zabbix_error"] is True

    hosts = [
        {"hostid": "101", "status": "0", "available": "1", "interfaces": []},
        {"hostid": "102", "status": "0", "available": "2", "interfaces": []},
    ]
    with patch(ZABBIX, return_value=hosts):
        body = client.get(url).json()
    assert "zabbix_error" not in body
    assert body["statuses"] == {str(devices[0].id): "online", str(devices[1].id): "offline"}
