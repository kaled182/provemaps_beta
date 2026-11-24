"""EV-0095 — coleta: upsert, transições observadas, motivo pelo valuemap, Zabbix fora."""

from datetime import timedelta

import pytest
from django.utils import timezone

from gpon import usecases
from gpon.models import OnuState

from .conftest import VSOL_HOST, ZTE_HOST, item, vsol_onu, zte_onu

pytestmark = pytest.mark.django_db


def test_only_olts_by_name_vendor_and_hostid(olts):
    found = [(d.name, vendor) for d, vendor in usecases.olt_devices()]
    assert found == [("VSOL - OLT EPON PLANURA", "vsol"), ("ZTE - OLT BRV C300", "zte")]


def test_one_item_get_per_olt_with_minimal_output_and_families(olts, fake_zabbix):
    usecases.collect_onu_states()
    item_gets = [p for m, p in fake_zabbix.calls if m == "item.get"]
    assert len(item_gets) == 2
    by_host = {p["hostids"][0]: p for p in item_gets}
    zte = by_host[ZTE_HOST]
    assert "name" not in zte["output"] and "valuemapid" in zte["output"]
    assert zte["search"]["key_"][:4] == ["onu.status", "onu.offreason", "onu.rx", "onu.dist"]
    assert "onu.last_offline" not in zte["search"]["key_"]  # relógio da OLT errado
    assert zte["startSearch"] is True and zte["searchByAny"] is True
    assert "name" in by_host[VSOL_HOST]["output"]


def test_first_collection_creates_states_with_first_seen(olts, fake_zabbix):
    now = timezone.now()
    fake_zabbix.items[ZTE_HOST] = zte_onu("SHLN3C3C2609", 13, 2, rx="-25.086", dist="1854")
    fake_zabbix.items[VSOL_HOST] = vsol_onu(1, 11, "a8:bf:3c:26:30:7a", rx="-19.75")
    result = usecases.collect_onu_states(now=now)
    assert result["zabbix_ok"] is True and result["zabbix_error"] is None
    assert result["onus_seen"] == 2 and result["transitions"] == 0
    zte = OnuState.objects.get(device=olts.zte)
    assert zte.onu_key == "SHLN3C3C2609"
    assert (zte.vendor, zte.technology, zte.pon_id, zte.onu_index) == ("zte", "gpon", "9/13", 2)
    assert zte.rx_olt_dbm == -25.086 and zte.distance_m == 1854
    assert zte.status_since == now and zte.first_seen == now and zte.last_seen == now
    assert zte.status_since_is_first_seen is True
    vsol = OnuState.objects.get(device=olts.vsol)
    assert vsol.onu_key == "1:11|a8:bf:3c:26:30:7a"
    assert (vsol.technology, vsol.rx_onu_dbm, vsol.mac) == ("epon", -19.75, "a8:bf:3c:26:30:7a")


def test_status_since_only_changes_on_transition(olts, fake_zabbix):
    t0 = timezone.now()
    t1, t2 = t0 + timedelta(minutes=2), t0 + timedelta(minutes=4)
    fake_zabbix.items[ZTE_HOST] = zte_onu("SHLN3C3C2609", 13, 2, rx="-20.0")
    usecases.collect_onu_states(now=t0)

    fake_zabbix.items[ZTE_HOST] = zte_onu("SHLN3C3C2609", 13, 2, rx="-21.0")  # só o RX muda
    usecases.collect_onu_states(now=t1)
    state = OnuState.objects.get()
    assert state.status_since == t0 and state.status_since_is_first_seen is True
    assert state.rx_olt_dbm == -21.0 and state.last_seen == t1

    fake_zabbix.items[ZTE_HOST] = zte_onu(
        "SHLN3C3C2609", 13, 2, status="offline", reason="2", rx="-80"
    )
    result = usecases.collect_onu_states(now=t2)
    state.refresh_from_db()
    assert result["transitions"] == 1
    assert state.status == "offline" and state.reason == "los" and state.reason_label == "LOS"
    assert state.status_since == t2 and state.status_since_is_first_seen is False
    assert state.first_seen == t0
    assert state.rx_olt_dbm is None  # -80 é sentinela


def test_reason_change_while_offline_is_a_transition(olts, fake_zabbix):
    t0 = timezone.now()
    fake_zabbix.items[ZTE_HOST] = zte_onu("A1", 1, 1, status="offline", reason="9", rx="-80")
    usecases.collect_onu_states(now=t0)
    assert OnuState.objects.get().reason == "dying_gasp"
    fake_zabbix.items[ZTE_HOST] = zte_onu("A1", 1, 1, status="offline", reason="2", rx="-80")
    usecases.collect_onu_states(now=t0 + timedelta(minutes=2))
    state = OnuState.objects.get()
    assert state.reason == "los" and state.status_since == t0 + timedelta(minutes=2)


def test_online_onu_has_no_reason_even_with_last_offreason(olts, fake_zabbix):
    fake_zabbix.items[ZTE_HOST] = zte_onu("A1", 1, 1, status="online", reason="2")
    usecases.collect_onu_states()
    state = OnuState.objects.get()
    assert state.reason == "" and state.raw_reason == "2"


def test_reason_classification_and_one_valuemap_call_per_olt(olts, fake_zabbix):
    fake_zabbix.items[ZTE_HOST] = (
        zte_onu("A1", 1, 1, status="offline", reason="2", rx="-80")
        + zte_onu("A2", 1, 2, status="offline", reason="9", rx="-80")
        + zte_onu("A3", 1, 3, status="offline", reason="1", rx="-80")
    )
    usecases.collect_onu_states()
    reasons = dict(OnuState.objects.values_list("onu_key", "reason"))
    assert reasons == {"A1": "los", "A2": "dying_gasp", "A3": "other"}
    assert fake_zabbix.count("valuemap.get") == 1
    usecases.collect_onu_states()
    assert fake_zabbix.count("valuemap.get") == 1  # em cache 1 h


def test_without_readable_valuemap_reason_is_null(olts, fake_zabbix):
    fake_zabbix.valuemaps = {}
    fake_zabbix.items[ZTE_HOST] = zte_onu("A1", 1, 1, status="offline", reason="2", rx="-80")
    usecases.collect_onu_states()
    state = OnuState.objects.get()
    assert state.reason == "" and state.reason_label == "" and state.raw_reason == "2"


def test_onu_missing_from_zabbix_keeps_old_last_seen(olts, fake_zabbix):
    t0 = timezone.now()
    fake_zabbix.items[ZTE_HOST] = zte_onu("A1", 1, 1) + zte_onu("A2", 1, 2)
    usecases.collect_onu_states(now=t0)
    fake_zabbix.items[ZTE_HOST] = zte_onu("A1", 1, 1)
    usecases.collect_onu_states(now=t0 + timedelta(minutes=2))
    seen = dict(OnuState.objects.values_list("onu_key", "last_seen"))
    assert seen == {"A1": t0 + timedelta(minutes=2), "A2": t0}


def test_zabbix_down_for_every_olt(olts, fake_zabbix):
    fake_zabbix.down_hosts = {ZTE_HOST, VSOL_HOST}
    result = usecases.collect_onu_states()
    assert result["zabbix_ok"] is False
    assert "2 de 2 OLT sem resposta" in result["zabbix_error"]
    assert OnuState.objects.count() == 0


def test_partial_failure_keeps_zabbix_ok_and_reports_olt(olts, fake_zabbix):
    fake_zabbix.down_hosts = {VSOL_HOST}
    fake_zabbix.items[ZTE_HOST] = [*zte_onu("A1", 1, 1), item("icmpping", "1", value_type="3")]
    result = usecases.collect_onu_states()
    assert result["zabbix_ok"] is True
    assert "VSOL - OLT EPON PLANURA" in result["zabbix_error"]
    overview = usecases.gpon_overview()
    by_id = {o["device_id"]: o for o in overview["olts"]}
    assert by_id[olts.vsol.pk]["collection_ok"] is False
    assert by_id[olts.zte.pk]["collection_ok"] is True


def test_exception_from_gateway_does_not_raise(olts, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("gpon.usecases.zabbix_request", boom)
    result = usecases.collect_onu_states()
    assert result["zabbix_ok"] is False
    assert "connection refused" in result["zabbix_error"]
