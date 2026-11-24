"""EV-0111 — portas em uso e pior RX por dispositivo (cards do modal de Site)."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from inventory.models import Device, FiberCable, Port, Site
from inventory.usecases.device_summaries import ports_summaries

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _thresholds(monkeypatch):
    cfg = SimpleNamespace(optical_rx_warning_threshold=-24.0, optical_rx_critical_threshold=-27.0)
    monkeypatch.setattr(
        "inventory.usecases.fibers.runtime_settings.get_runtime_config", lambda: cfg
    )


@pytest.fixture
def switch():
    site = Site.objects.create(display_name="SITE - CONFRESA", latitude=-10.6, longitude=-51.5)
    return Device.objects.create(name="SW HUAWEI CONFRESA", site=site)


def test_in_use_worst_fresh_rx_and_stale_readings(switch):
    now = timezone.now()
    Port.objects.create(
        device=switch,
        name="XGE0/0/1",
        last_rx_power=-12.5,
        last_tx_power=-2,
        last_optical_check=now,
    )
    Port.objects.create(
        device=switch,
        name="XGE0/0/2",
        last_rx_power=-25.1,
        last_tx_power=-2,
        last_optical_check=now,
    )
    # leitura velha: em uso, mas não entra no pior RX
    Port.objects.create(
        device=switch,
        name="XGE0/0/3",
        last_rx_power=-30,
        last_optical_check=now - timedelta(hours=1),
    )
    # só cabo ligado: em uso, sem leitura
    linked = Port.objects.create(device=switch, name="XGE0/0/4")
    other = Device.objects.create(name="OUTRO", site=switch.site)
    FiberCable.objects.create(
        name="CABO 1",
        origin_port=linked,
        destination_port=Port.objects.create(device=other, name="P1"),
    )
    Port.objects.create(device=switch, name="GE0/0/9")  # livre

    data = ports_summaries([switch.pk], now=now)

    assert data["thresholds"] == {"warning": -24.0, "critical": -27.0}
    assert data["devices"][str(switch.pk)] == {
        "ports_total": 5,
        "ports_in_use": 4,
        "worst_rx_dbm": -25.1,
        "worst_rx_level": "warning",
        "stale_readings": 1,
    }


def test_device_without_ports_is_absent(switch):
    assert ports_summaries([switch.pk])["devices"] == {}


def test_endpoint_requires_login_and_validates(switch):
    url = "/api/v1/inventory/devices/ports-summary/"
    assert Client().get(url, {"device_ids": str(switch.pk)}).status_code in (401, 403, 302)
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    assert c.get(url, {"device_ids": str(switch.pk)}).json() == {
        "devices": {},
        "thresholds": {"warning": -24.0, "critical": -27.0},
    }
    assert c.get(url, {"device_ids": "x"}).status_code == 400
    assert c.get(url, {"device_ids": ",".join(str(i) for i in range(1, 202))}).status_code == 400
