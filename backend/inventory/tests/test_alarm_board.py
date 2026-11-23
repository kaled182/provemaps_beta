"""EV-0059 — quadro de alarmes derivado de FiberEvent: `unknown` não abre nem fecha."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from inventory.models import FiberCable, FiberEvent
from inventory.usecases.alarms import _incidents_for, build_alarm_board

NOW = timezone.now()


def _t(hours_ago):
    return NOW - timedelta(hours=hours_ago)


def _ev(cable, hours_ago, status):
    return FiberEvent.objects.create(fiber=cable, timestamp=_t(hours_ago), new_status=status)


@pytest.fixture(autouse=True)
def _no_optical():
    with patch(
        "inventory.usecases.alarms.list_cables_optical_summary", return_value={"cables": []}
    ):
        yield


def test_unknown_neither_opens_nor_closes():
    closed, current = _incidents_for(
        [(_t(10), "down"), (_t(9), "unknown"), (_t(8), "down"), (_t(7), "unknown")], None
    )
    assert closed == []
    assert current["opened_at"] == _t(10)
    assert current["severity"] == "critical"


def test_severity_escalates_and_up_closes():
    closed, current = _incidents_for([(_t(10), "degraded"), (_t(9), "down"), (_t(8), "up")], None)
    assert current is None
    assert closed[0]["severity"] == "critical"
    assert closed[0]["closed_at"] - closed[0]["opened_at"] == timedelta(hours=2)


@pytest.mark.django_db
def test_board_active_resolved_and_mttr():
    flapping = FiberCable.objects.create(name="Flap")
    for h, s in [(5, "up"), (4, "down"), (3.9, "unknown"), (3.8, "down"), (3.7, "unknown")]:
        _ev(flapping, h, s)
    recovered = FiberCable.objects.create(name="Volta")
    _ev(recovered, 10, "degraded")
    _ev(recovered, 9, "unknown")
    _ev(recovered, 6, "up")  # incidente de 4 h, fechado nas últimas 24 h
    FiberCable.objects.create(name="Quieto")

    board = build_alarm_board(now=NOW)
    assert [a["cable_name"] for a in board["active"]] == ["Flap"]
    assert board["active"][0]["severity"] == "critical"
    assert board["active"][0]["duration_seconds"] == 4 * 3600
    assert board["resolved_24h"] == 1
    assert board["mttr_seconds"] == 4 * 3600
    assert board["mttr_sample"] == 1


@pytest.mark.django_db
def test_incident_older_than_window_keeps_real_opening():
    old = FiberCable.objects.create(name="Antigo")
    _ev(old, 24 * 50, "up")
    _ev(old, 24 * 45, "degraded")
    _ev(old, 24 * 44, "down")
    _ev(old, 24 * 31, "unknown")
    _ev(old, 24 * 30.5, "down")  # último conhecido antes da janela de 30 d
    board = build_alarm_board(now=NOW, window_days=30)
    a = board["active"][0]
    assert a["opened_at"] == _t(24 * 45).isoformat()  # abriu no 1.º em baixo após o último up
    assert a["severity"] == "critical"
    assert board["mttr_sample"] == 0
    assert board["mttr_seconds"] is None


@pytest.mark.django_db
def test_endpoint_auth_and_window_param():
    url = "/api/v1/fiber-cables/alarm-board/"
    assert Client().get(url).status_code in (401, 403, 302)
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    assert c.get(url).json()["window_days"] == 30
    assert c.get(url + "?dias=500").json()["window_days"] == 90
    assert c.get(url + "?dias=x").status_code == 400
