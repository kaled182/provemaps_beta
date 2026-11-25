"""EV-0111 — resumo por OLT (ONUs online/total, alertas ópticos) para os cards do modal de Site."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from gpon import usecases
from gpon.models import OnuState
from inventory.models import Device

from .conftest import ZTE_HOST, zte_onu

pytestmark = pytest.mark.django_db


def test_counts_online_and_signal_alerts_only_for_olts(olts, fake_zabbix, config):
    fake_zabbix.items[ZTE_HOST] = (
        zte_onu("A1", 1, 1, rx="-20.0")
        + zte_onu("A2", 1, 2, rx="-25.5")  # atenção
        + zte_onu("A3", 1, 3, rx="-28.0")  # crítico
        + zte_onu("A4", 1, 4, status="offline", reason="2", rx="-80")
    )
    usecases.collect_onu_states()
    switch = Device.objects.get(name="ZTE Switch")
    ids = [olts.zte.pk, olts.vsol.pk, switch.pk]

    data = usecases.olt_summaries(ids)["olts"]

    assert set(data) == {str(olts.zte.pk), str(olts.vsol.pk)}  # o switch não é OLT
    zte = data[str(olts.zte.pk)]
    assert (zte["onus_total"], zte["onus_online"]) == (4, 3)
    assert (zte["signal_warning"], zte["signal_critical"]) == (1, 1)
    assert data[str(olts.vsol.pk)]["onus_total"] == 0


def test_onu_without_collection_for_a_day_is_not_counted_online(olts, fake_zabbix, config):
    fake_zabbix.items[ZTE_HOST] = zte_onu("A1", 1, 1, rx="-26.0")
    usecases.collect_onu_states()
    OnuState.objects.update(last_seen=timezone.now() - timedelta(days=2))
    zte = usecases.olt_summaries([olts.zte.pk])["olts"][str(olts.zte.pk)]
    assert (zte["onus_total"], zte["onus_online"], zte["signal_warning"]) == (1, 0, 0)


def test_endpoint_requires_login_and_validates(olts, config):
    url = "/api/v1/monitoring/gpon/olt-summary/"
    assert Client().get(url, {"device_ids": str(olts.zte.pk)}).status_code in (401, 403, 302)
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    body = c.get(url, {"device_ids": f"{olts.zte.pk},{olts.vsol.pk}"}).json()
    assert list(body["olts"][str(olts.zte.pk)]) == [
        "vendor",
        "technology",
        "onus_total",
        "onus_online",
        "signal_warning",
        "signal_critical",
    ]
    assert c.get(url, {"device_ids": "a,b"}).status_code == 400
    assert c.get(url).status_code == 400
