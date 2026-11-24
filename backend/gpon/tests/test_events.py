"""EV-0108 — eventos de ONU: transições observadas, «unknown» não é evento nem apaga o
último estado conhecido, retenção, e a consulta por PON."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from gpon import usecases
from gpon.models import OnuEvent, OnuState

from .conftest import ZTE_HOST, zte_onu

pytestmark = pytest.mark.django_db

SERIAL = "SHLN3C3C2609"


def collect(fake_zabbix, now, status="online", reason="9", serial=SERIAL, onu=2):
    fake_zabbix.items[ZTE_HOST] = zte_onu(serial, 13, onu, status=status, reason=reason, rx="-20.0")
    return usecases.collect_onu_states(now=now)


def kinds():
    return [
        (e.previous_status, e.previous_reason, e.status, e.reason)
        for e in OnuEvent.objects.order_by("at", "pk")
    ]


def test_first_observation_is_not_an_event_and_drop_and_return_are(olts, fake_zabbix):
    t0 = timezone.now()
    collect(fake_zabbix, t0)  # primeira vez que se vê a ONU: não é transição
    assert OnuEvent.objects.count() == 0
    collect(fake_zabbix, t0 + timedelta(minutes=2), status="offline", reason="2")  # LOS
    collect(fake_zabbix, t0 + timedelta(minutes=4))  # volta
    assert kinds() == [("online", "", "offline", "los"), ("offline", "los", "online", "")]
    e = OnuEvent.objects.order_by("at").first()
    assert (e.device_id, e.pon_id, e.reason_label) == (olts.zte.pk, "9/13", "LOS")


def test_unknown_is_not_an_event_and_returning_equal_is_silent(olts, fake_zabbix):
    t0 = timezone.now()
    collect(fake_zabbix, t0)
    collect(fake_zabbix, t0 + timedelta(minutes=2), status="unknown")  # falha de coleta
    collect(fake_zabbix, t0 + timedelta(minutes=4))  # volta online: não é reconexão
    assert OnuEvent.objects.count() == 0
    state = OnuState.objects.get()
    assert (state.last_known_status, state.last_known_reason) == ("online", "")


def test_drop_hidden_behind_unknown_is_recorded_from_the_last_known_state(olts, fake_zabbix):
    t0 = timezone.now()
    collect(fake_zabbix, t0)
    collect(fake_zabbix, t0 + timedelta(minutes=2), status="unknown")
    collect(fake_zabbix, t0 + timedelta(minutes=4), status="offline", reason="9")
    assert kinds() == [("online", "", "offline", "dying_gasp")]


def test_without_known_history_only_a_drop_is_recorded(olts, fake_zabbix):
    t0 = timezone.now()
    collect(fake_zabbix, t0, status="unknown")
    collect(fake_zabbix, t0 + timedelta(minutes=2))  # unknown → online: reconexão inventada
    assert OnuEvent.objects.count() == 0
    collect(fake_zabbix, t0 + timedelta(minutes=4), serial="B2", onu=3, status="unknown")
    collect(
        fake_zabbix, t0 + timedelta(minutes=6), serial="B2", onu=3, status="offline", reason="2"
    )
    assert kinds() == [("", "", "offline", "los")]


def test_retention_purges_old_events(olts, fake_zabbix):
    t0 = timezone.now()
    collect(fake_zabbix, t0)
    collect(fake_zabbix, t0 + timedelta(minutes=2), status="offline", reason="2")
    assert OnuEvent.objects.count() == 1
    later = t0 + timedelta(days=usecases.EVENT_RETENTION_DAYS, minutes=3)
    result = collect(fake_zabbix, later, status="offline", reason="2")
    assert result["events_purged"] == 1
    assert OnuEvent.objects.count() == 0


def test_pon_events_newest_first_with_window_and_since(olts, fake_zabbix):
    t0 = timezone.now() - timedelta(hours=30)
    collect(fake_zabbix, t0)
    collect(fake_zabbix, t0 + timedelta(minutes=2), status="offline", reason="2")  # há ~30 h
    t1 = timezone.now() - timedelta(hours=1)
    collect(fake_zabbix, t1)  # volta: há 1 h
    collect(fake_zabbix, t1 + timedelta(minutes=2), status="offline", reason="9")
    data = usecases.pon_events(olts.zte.pk, "9/13", hours=24)
    assert [e["kind"] for e in data["events"]] == ["dying_gasp", "online"]
    assert data["events"][0]["previous_kind"] == "online"
    assert data["events"][0]["serial"] == SERIAL and data["events"][0]["onu_index"] == 2
    assert data["since"] is not None and data["truncated"] is False
    assert usecases.pon_events(olts.zte.pk, "9/99")["events"] == []


def test_events_endpoint_requires_login_and_validates(olts, fake_zabbix):
    url = "/api/v1/monitoring/gpon/events/"
    assert Client().get(url, {"device": olts.zte.pk, "pon": "9/13"}).status_code in (401, 403, 302)
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    assert c.get(url, {"device": olts.zte.pk, "pon": "9/13"}).status_code == 200
    assert c.get(url, {"pon": "9/13"}).status_code == 400
    assert c.get(url, {"device": 999999, "pon": "9/13"}).status_code == 404
