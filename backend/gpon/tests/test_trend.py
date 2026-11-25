"""EV-0109 — tendência 24 h do RX da PON (trend.get, 1 chamada) e tráfego da porta."""

from datetime import UTC, datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from gpon import usecases
from gpon.models import OnuState

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 24, 14, 0, tzinfo=UTC)
H0 = int((NOW - timedelta(hours=2)).timestamp())
H1 = int((NOW - timedelta(hours=1)).timestamp())
IFINDEX_9_14 = 285280526


class TrendZabbix:
    def __init__(self, items, trends):
        self.items, self.trends, self.calls = items, trends, []

    def __call__(self, method, params=None, *a, **k):
        self.calls.append((method, params))
        if method == "item.get":
            keys = set(params["filter"]["key_"])
            return [i for i in self.items if i["key_"] in keys]
        if method == "trend.get":
            ids = set(params["itemids"])
            return [t for t in self.trends if t["itemid"] in ids]
        return []


def _onu(device, key, n, vendor="zte"):
    now = timezone.now()
    return OnuState.objects.create(
        device=device,
        onu_key=f"K{n}",
        vendor=vendor,
        technology="gpon",
        pon_id="9/14",
        onu_index=n,
        status="online",
        rx_item_key=key,
        status_since=now,
        first_seen=now,
        last_seen=now,
    )


def trend(itemid, clock, low, avg, high):
    return {
        "itemid": itemid,
        "clock": str(clock),
        "value_min": str(low),
        "value_avg": str(avg),
        "value_max": str(high),
    }


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_ifindex_is_the_inverse_of_the_parser():
    from gpon.domain.parsers import zte_pon_from_ifindex

    assert usecases.zte_pon_ifindex("9/14") == IFINDEX_9_14
    assert zte_pon_from_ifindex(IFINDEX_9_14) == "9/14"
    assert usecases.zte_pon_ifindex("x") is None


def test_hourly_rx_skips_hours_contaminated_by_the_offline_sentinel(olts, monkeypatch):
    _onu(olts.zte, "onu.rx[A]", 1)
    _onu(olts.zte, "onu.rx[B]", 2)
    items = [
        {
            "itemid": "1",
            "key_": "onu.rx[A]",
            "lastvalue": "-20",
            "lastclock": str(int(NOW.timestamp())),
        },
        {
            "itemid": "2",
            "key_": "onu.rx[B]",
            "lastvalue": "-26",
            "lastclock": str(int(NOW.timestamp())),
        },
        {
            "itemid": "9",
            "key_": f"net.if.in[ifHCInOctets.{IFINDEX_9_14}]",
            "lastvalue": "4765008",
            "lastclock": str(int(NOW.timestamp()) - 30),
        },
        {
            "itemid": "10",
            "key_": f"net.if.out[ifHCOutOctets.{IFINDEX_9_14}]",
            "lastvalue": "17841048",
            "lastclock": str(int(NOW.timestamp()) - 30),
        },
    ]
    trends = [
        trend("1", H0, -21, -20, -19),
        trend("2", H0, -27, -26, -25),
        trend("1", H1, -21, -20, -19),
        trend("2", H1, -80, -53, -26),  # ONU caiu a meio da hora: -80 = sentinela
        trend("9", H0, 1e6, 4e6, 9e6),
    ]
    fake = TrendZabbix(items, trends)
    monkeypatch.setattr("gpon.usecases.zabbix_request", fake)

    data = usecases.pon_trend(olts.zte.pk, "9/14", now=NOW)

    assert [m for m, _ in fake.calls] == ["item.get", "trend.get"]  # 1 trend.get para todas
    assert data["zabbix_ok"] is True
    assert data["rx"] == [
        {"t": "2026-11-24T12:00:00Z", "rx_avg_dbm": -23.0, "rx_worst_dbm": -27.0, "onus": 2},
        {"t": "2026-11-24T13:00:00Z", "rx_avg_dbm": -20.0, "rx_worst_dbm": -21.0, "onus": 1},
    ]
    tr = data["traffic"]
    assert (tr["available"], tr["in_bps"], tr["out_bps"], tr["stale"]) == (
        True,
        4765008.0,
        17841048.0,
        False,
    )
    assert tr["in"] == [{"t": "2026-11-24T12:00:00Z", "bps": 4e6}] and tr["out"] == []


def test_vsol_has_no_pon_traffic_and_result_is_cached(olts, monkeypatch):
    _onu(olts.vsol, "SinalRXS0P1[aa - 1]", 1, vendor="vsol")
    fake = TrendZabbix([], [])
    monkeypatch.setattr("gpon.usecases.zabbix_request", fake)
    data = usecases.pon_trend(olts.vsol.pk, "9/14", now=NOW)
    assert data["traffic"]["available"] is False and data["rx"] == []
    usecases.pon_trend(olts.vsol.pk, "9/14", now=NOW)
    assert len(fake.calls) == 1  # o segundo pedido vem da cache de 5 min


def test_zabbix_down_is_flagged_and_not_cached(olts, monkeypatch):
    _onu(olts.zte, "onu.rx[A]", 1)
    monkeypatch.setattr("gpon.usecases.zabbix_request", lambda *a, **k: None)
    data = usecases.pon_trend(olts.zte.pk, "9/14", now=NOW)
    assert data["zabbix_ok"] is False and data["zabbix_error"]
    assert cache.get(usecases.TREND_CACHE_KEY.format(device_id=olts.zte.pk, pon_id="9/14")) is None


def test_trend_endpoint_requires_login_and_validates(olts, monkeypatch):
    monkeypatch.setattr("gpon.usecases.zabbix_request", TrendZabbix([], []))
    url = "/api/v1/monitoring/gpon/pon-trend/"
    assert Client().get(url, {"device": olts.zte.pk, "pon": "9/14"}).status_code in (401, 403, 302)
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    body = c.get(url, {"device": olts.zte.pk, "pon": "9/14"}).json()
    assert set(body) == {
        "device_id",
        "pon_id",
        "hours",
        "rx",
        "traffic",
        "zabbix_ok",
        "zabbix_error",
    }
    assert c.get(url, {"pon": "9/14"}).status_code == 400
    assert c.get(url, {"device": 999999, "pon": "9/14"}).status_code == 404
