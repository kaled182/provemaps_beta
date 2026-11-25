"""EV-0095 — histórico do RX (fachada de fetch_aligned_series) e a tarefa com lock."""

from datetime import UTC, datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from gpon import tasks, usecases
from gpon.models import OnuState

from .conftest import ZTE_HOST, zte_onu

pytestmark = pytest.mark.django_db

FETCH = "gpon.usecases.zabbix_history.fetch_aligned_series"
T = 1795484400  # múltiplo de 60


def _onu(device, *, vendor="zte", rx_item_key="onu.rx[A1,9,1,1]"):
    now = timezone.now()
    return OnuState.objects.create(
        device=device,
        onu_key="A1",
        vendor=vendor,
        technology="gpon" if vendor == "zte" else "epon",
        pon_id="9/1",
        onu_index=1,
        status="online",
        rx_item_key=rx_item_key,
        status_since=now,
        first_seen=now,
        last_seen=now,
    )


def _series(samples, bucket=60):
    return {
        "rows": [],
        "bucket_seconds": bucket,
        "units": {"rx": "dBm"},
        "samples": {"rx": samples},
    }


def _iso(ts):
    return datetime.fromtimestamp(ts, tz=UTC).isoformat().replace("+00:00", "Z")


@pytest.fixture
def item_get(monkeypatch):
    calls = []

    def fake(method, params=None, *a, **k):
        calls.append((method, params))
        assert method == "item.get"  # nada de history.get novo: o histórico vem pela fachada
        return [{"itemid": "601400", "value_type": "0", "units": "dBm"}]

    monkeypatch.setattr("gpon.usecases.zabbix_request", fake)
    return calls


def test_history_uses_fetch_aligned_series_and_nulls_sentinels(olts, item_get, monkeypatch):
    onu = _onu(olts.zte)
    seen = {}

    def fake_fetch(items, time_from, time_till, *, meta=None, **kwargs):
        seen.update(items=items, span=time_till - time_from, meta=meta)
        return _series([(T, -25.1), (T + 30, -25.3), (T + 60, -80.0), (T + 120, -24.0)])

    monkeypatch.setattr(FETCH, fake_fetch)
    data = usecases.onu_history(onu.pk, 6)
    assert list(data) == ["onu_id", "unit", "label", "points", "zabbix_ok", "zabbix_error"]
    assert (data["onu_id"], data["unit"], data["label"]) == (onu.pk, "dBm", "RX na OLT")
    assert data["zabbix_ok"] is True and data["zabbix_error"] is None
    assert seen["items"] == {"rx": "601400"} and seen["span"] == 6 * 3600
    assert seen["meta"]["601400"]["value_type"] == 0  # o tipo vem do item.get (CLAUDE.md §7)
    assert item_get[0][1]["filter"] == {"key_": "onu.rx[A1,9,1,1]"}
    assert data["points"] == [
        {"x": _iso(T), "y": pytest.approx(-25.2)},
        {"x": _iso(T + 60), "y": None},  # só sentinela neste bucket: buraco, não valor
        {"x": _iso(T + 120), "y": -24.0},
    ]


def test_history_label_for_vsol_is_rx_on_onu(olts, item_get, monkeypatch):
    onu = _onu(olts.vsol, vendor="vsol", rx_item_key="SinalRXS0P1[aa - 1]")
    monkeypatch.setattr(FETCH, lambda *a, **k: _series([]))
    assert usecases.onu_history(onu.pk, 24)["label"] == "RX na ONU"


def test_history_without_rx_item_is_empty_and_ok(olts, item_get):
    onu = _onu(olts.zte, rx_item_key="")
    data = usecases.onu_history(onu.pk, 24)
    assert data["points"] == [] and data["zabbix_ok"] is True
    assert item_get == []


def test_history_zabbix_down(olts, monkeypatch):
    onu = _onu(olts.zte)
    monkeypatch.setattr("gpon.usecases.zabbix_request", lambda *a, **k: None)
    data = usecases.onu_history(onu.pk, 24)
    assert data["zabbix_ok"] is False and data["points"] == [] and data["zabbix_error"]


def test_history_fetch_exception_is_zabbix_down(olts, item_get, monkeypatch):
    onu = _onu(olts.zte)

    def boom(*a, **k):
        raise RuntimeError("timeout")

    monkeypatch.setattr(FETCH, boom)
    data = usecases.onu_history(onu.pk, 24)
    assert data["zabbix_ok"] is False and data["zabbix_error"] == "timeout"


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="noc", password="x")


def test_history_api(client, user, olts, item_get, monkeypatch):
    onu = _onu(olts.zte)
    monkeypatch.setattr(FETCH, lambda *a, **k: _series([(T, -22.0)]))
    url = f"/api/v1/monitoring/gpon/onus/{onu.pk}/history/"
    assert client.get(url).status_code in (401, 403)
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200
    assert response.json()["points"] == [{"x": _iso(T), "y": -22.0}]
    assert client.get(url, {"hours": "0"}).status_code == 400
    assert client.get(url, {"hours": "169"}).status_code == 400
    assert client.get(url, {"hours": "x"}).status_code == 400
    assert client.get(url, {"hours": "168"}).status_code == 200
    assert client.get("/api/v1/monitoring/gpon/onus/999999/history/").status_code == 404


# --- Tarefa ---------------------------------------------------------------------------------


def test_task_collects_and_releases_lock(olts, fake_zabbix):
    fake_zabbix.items[ZTE_HOST] = zte_onu("A1", 1, 1)
    result = tasks.collect_onu_states()
    assert result["success"] is True and result["onus_seen"] == 1
    assert cache.get(tasks.COLLECT_LOCK_KEY) is None
    assert OnuState.objects.count() == 1


def test_task_skips_when_locked(olts, fake_zabbix):
    cache.add(tasks.COLLECT_LOCK_KEY, "x", 60)
    assert tasks.collect_onu_states() == {"success": True, "skipped": "lock"}
    assert fake_zabbix.calls == []


def test_task_with_zabbix_down_records_last_run(olts, fake_zabbix):
    fake_zabbix.down_hosts = set(fake_zabbix.items)
    result = tasks.collect_onu_states()
    assert result["success"] is True and result["zabbix_ok"] is False
    last = cache.get(usecases.LAST_RUN_CACHE_KEY)
    assert last["zabbix_ok"] is False and "sem resposta" in last["zabbix_error"]
    assert cache.get(tasks.COLLECT_LOCK_KEY) is None


def test_task_never_raises(olts, monkeypatch):
    def boom(now=None):
        raise RuntimeError("base em baixo")

    monkeypatch.setattr("gpon.tasks.usecases.collect_onu_states", boom)
    result = tasks.collect_onu_states()
    assert result == {"success": False, "zabbix_ok": False, "zabbix_error": "base em baixo"}
    assert cache.get(usecases.LAST_RUN_CACHE_KEY)["zabbix_ok"] is False
    assert cache.get(tasks.COLLECT_LOCK_KEY) is None


def test_task_is_scheduled_every_120s_on_zabbix_queue():
    from core.celery import app

    entry = app.conf.beat_schedule["collect-onu-states"]
    assert entry["task"] == "gpon.tasks.collect_onu_states"
    assert entry["schedule"] == 120.0 and entry["options"]["queue"] == "zabbix"


def test_valuemap_get_is_read_only_safe():
    from integrations.zabbix.client import READ_ONLY_SAFE_METHODS

    assert "valuemap.get" in READ_ONLY_SAFE_METHODS
