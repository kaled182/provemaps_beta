"""EV-0095 — resumo para o ecrã: formato e ordem do contrato, PON, queda coletiva, API."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from gpon import usecases
from gpon.models import OnuState

from .conftest import VSOL_HOST, ZTE_HOST, item, vsol_onu, zte_onu

pytestmark = pytest.mark.django_db

URL = "/api/v1/monitoring/gpon/"

TOP_KEYS = [
    "collected_at",
    "zabbix_ok",
    "zabbix_error",
    "thresholds",
    "capacity",
    "totals",
    "olts",
    "onus",
]
TOTALS_KEYS = [
    "olts",
    "olts_online",
    "olts_offline",
    "pons",
    "onus_provisioned",
    "onus_online",
    "onus_offline",
    "onus_unknown",
    "signal_warning",
    "signal_critical",
    "los",
    "dying_gasp",
    "pons_collective_drop",
]
OLT_KEYS = [
    "device_id",
    "name",
    "vendor",
    "technology",
    "model",
    "ip",
    "site_name",
    "status",
    "collection_ok",
    "cpu_pct",
    "temperature_c",
    "onus_total",
    "onus_online",
    "pons",
]
PON_KEYS = [
    "pon_id",
    "label",
    "status",
    "capacity",
    "onus_provisioned",
    "onus_online",
    "occupancy_pct",
    "rx_avg_dbm",
    "los",
    "dying_gasp",
    "signal_warning",
    "signal_critical",
    "collective_drop",
    "severity",
]
ONU_KEYS = [
    "id",
    "device_id",
    "olt_name",
    "pon_id",
    "onu_index",
    "serial",
    "mac",
    "description",
    "status",
    "reason",
    "reason_label",
    "rx_onu_dbm",
    "rx_olt_dbm",
    "signal",
    "distance_m",
    "status_since",
    "status_since_is_first_seen",
    "last_seen",
    "cliente_nome",
    "login_radius",
    "caixa_cto",
    "severity_rank",
    "has_history",
]


def _state(
    device,
    key,
    *,
    pon="9/1",
    index=1,
    status="online",
    reason="",
    since=None,
    first=False,
    rx_olt=None,
    rx_onu=None,
    last_seen=None,
    vendor="zte",
    technology="gpon",
):
    now = timezone.now()
    return OnuState.objects.create(
        device=device,
        onu_key=key,
        vendor=vendor,
        technology=technology,
        pon_id=pon,
        onu_index=index,
        serial=key,
        status=status,
        reason=reason,
        reason_label={"los": "LOS", "dying_gasp": "PowerOff", "other": "Desconhecido"}.get(
            reason, ""
        ),
        rx_olt_dbm=rx_olt,
        rx_onu_dbm=rx_onu,
        rx_item_key=f"onu.rx[{key},9,1,{index}]",
        status_since=since or now,
        status_since_is_first_seen=first,
        first_seen=now - timedelta(days=2),
        last_seen=last_seen or now,
    )


def test_keys_and_order_follow_the_contract(olts, fake_zabbix, config):
    fake_zabbix.items[ZTE_HOST] = [
        *zte_onu("ZYXE8CAEECCE", 14, 1, status="offline", reason="2", rx="-80", dist="0"),
        item("icmpping", "1", value_type="3"),
        item("ifOperStatus[285280526]", "1", value_type="1"),
        item("cardcpu[1.1.0]", "12", value_type="3"),
        item("sysDescr", "C300 Version V2.1.0 Software", value_type="1"),
    ]
    fake_zabbix.items[VSOL_HOST] = [
        *vsol_onu(1, 11, "a8:bf:3c:26:30:7a"),
        item("icmpping", "0", value_type="3"),
    ]
    usecases.collect_onu_states()
    data = usecases.gpon_overview()
    assert list(data) == TOP_KEYS
    assert list(data["totals"]) == TOTALS_KEYS
    assert list(data["thresholds"]) == ["warning", "critical"]
    assert list(data["capacity"]) == ["gpon", "epon"]
    assert all(list(o) == OLT_KEYS for o in data["olts"])
    assert all(list(p) == PON_KEYS for o in data["olts"] for p in o["pons"])
    assert all(list(o) == ONU_KEYS for o in data["onus"])
    assert data["zabbix_ok"] is True and data["collected_at"].endswith("Z")

    zte = next(o for o in data["olts"] if o["vendor"] == "zte")
    assert (zte["status"], zte["model"], zte["cpu_pct"], zte["ip"]) == (
        "online",
        "C300",
        12.0,
        "10.254.0.2",
    )
    assert zte["site_name"] == "SITE - BARREIRA VELHA" and zte["technology"] == "gpon"
    assert zte["pons"][0]["status"] == "up" and zte["pons"][0]["label"] == "PON 9/14"
    vsol = next(o for o in data["olts"] if o["vendor"] == "vsol")
    assert vsol["status"] == "offline" and vsol["technology"] == "epon"
    assert vsol["pons"][0]["status"] == "unknown" and vsol["pons"][0]["capacity"] == 64

    onu = data["onus"][0]  # a LOS vem primeiro
    assert (onu["status"], onu["reason"], onu["reason_label"], onu["severity_rank"]) == (
        "offline",
        "los",
        "LOS",
        0,
    )
    assert onu["rx_olt_dbm"] is None and onu["distance_m"] is None and onu["signal"] is None
    assert onu["mac"] is None and onu["description"] is None and onu["cliente_nome"] is None
    assert onu["status_since_is_first_seen"] is True and onu["has_history"] is True


def test_no_collection_yet_is_honest(olts, config):
    data = usecases.gpon_overview()
    assert data["collected_at"] is None and data["zabbix_ok"] is None
    assert data["totals"]["olts"] == 2 and data["totals"]["onus_provisioned"] == 0
    assert all(o["status"] == "unknown" and o["collection_ok"] is False for o in data["olts"])


def test_collection_ok_false_when_ping_ok_but_nothing_known(olts, fake_zabbix, config):
    # Nova Barreira: responde ao ping, ONUs todas com lastclock 0.
    fake_zabbix.items[VSOL_HOST] = [
        *vsol_onu(1, 1, "00:19:46:43:9f:40", status="0", rx="0"),
        item("icmpping", "1", value_type="3"),
    ]
    for entry in fake_zabbix.items[VSOL_HOST][:2]:
        entry["lastclock"] = "0"
    usecases.collect_onu_states()
    vsol = next(o for o in usecases.gpon_overview()["olts"] if o["vendor"] == "vsol")
    assert vsol["status"] == "online" and vsol["collection_ok"] is False
    assert vsol["onus_total"] == 1 and vsol["onus_online"] == 0


def test_collective_drop_three_los_in_nine_minutes(olts, config):
    t0 = timezone.now() - timedelta(minutes=30)
    for n, minutes in enumerate([0, 4, 9], start=1):
        _state(
            olts.zte,
            f"L{n}",
            index=n,
            status="offline",
            reason="los",
            since=t0 + timedelta(minutes=minutes),
        )
    data = usecases.gpon_overview(olt_id=olts.zte.pk)
    [pon] = data["olts"][0]["pons"]
    assert pon["collective_drop"] is True and pon["severity"] == "critical" and pon["los"] == 3
    assert data["totals"]["pons_collective_drop"] == 1


def test_no_collective_drop_when_spread_over_twenty_minutes(olts, config):
    t0 = timezone.now() - timedelta(hours=1)
    for n, minutes in enumerate([0, 10.5, 20], start=1):
        _state(
            olts.zte,
            f"L{n}",
            index=n,
            status="offline",
            reason="los",
            since=t0 + timedelta(minutes=minutes),
        )
    [pon] = usecases.gpon_overview(olt_id=olts.zte.pk)["olts"][0]["pons"]
    assert pon["collective_drop"] is False
    assert pon["severity"] == "critical"  # los ≥ 3 continua crítico


def test_first_seen_times_never_make_a_collective_drop(olts, config):
    t0 = timezone.now()
    for n in range(1, 4):
        _state(olts.zte, f"L{n}", index=n, status="offline", reason="los", since=t0, first=True)
    [pon] = usecases.gpon_overview(olt_id=olts.zte.pk)["olts"][0]["pons"]
    assert pon["collective_drop"] is False


def test_pon_signal_occupancy_and_capacity_from_config(olts, config):
    config.gpon_pon_capacity = 4
    _state(olts.zte, "A", index=1, rx_olt=-20.0)
    _state(olts.zte, "B", index=2, rx_olt=-25.0)  # warning
    _state(olts.zte, "C", index=3, rx_olt=-28.0)  # critical
    _state(olts.zte, "D", index=4, status="offline", reason="dying_gasp")
    data = usecases.gpon_overview(olt_id=olts.zte.pk)
    [pon] = data["olts"][0]["pons"]
    assert pon["capacity"] == 4 and pon["occupancy_pct"] == 100.0
    assert (pon["onus_provisioned"], pon["onus_online"]) == (4, 3)
    assert pon["rx_avg_dbm"] == round((-20.0 - 25.0 - 28.0) / 3, 1)
    assert (pon["signal_warning"], pon["signal_critical"], pon["dying_gasp"]) == (1, 1, 1)
    assert pon["severity"] == "warning"
    assert data["capacity"] == {"gpon": 4, "epon": 64}
    assert [o["severity_rank"] for o in data["onus"]] == [1, 2, 3, 6]
    totals = data["totals"]
    assert (totals["signal_warning"], totals["signal_critical"], totals["dying_gasp"]) == (1, 1, 1)


def test_thresholds_come_from_config(olts, config):
    config.optical_rx_warning_threshold = -20.0
    _state(olts.zte, "A", rx_olt=-21.0)
    data = usecases.gpon_overview()
    assert data["thresholds"] == {"warning": -20.0, "critical": -27.0}
    assert data["onus"][0]["signal"] == "warning"


def test_vsol_signal_prefers_rx_onu(olts, config):
    _state(
        olts.vsol, "1:1|aa", rx_onu=-28.0, rx_olt=None, vendor="vsol", technology="epon", pon="0/1"
    )
    assert usecases.gpon_overview()["onus"][0]["signal"] == "critical"


def test_onus_order_by_rank_then_olt_pon_index(olts, config):
    _state(olts.zte, "Z-9-10", pon="9/10", index=1)
    _state(olts.zte, "Z-9-2-b", pon="9/2", index=2)
    _state(olts.zte, "Z-9-2-a", pon="9/2", index=1)
    _state(olts.vsol, "V", pon="0/1", index=1, vendor="vsol", technology="epon")
    _state(olts.zte, "Z-unknown", pon="9/1", index=5, status="unknown")
    keys = [o["serial"] for o in usecases.gpon_overview()["onus"]]
    assert keys == ["Z-unknown", "V", "Z-9-2-a", "Z-9-2-b", "Z-9-10"]


def test_stale_onu_shows_unknown(olts, config):
    now = timezone.now()
    _state(
        olts.zte,
        "OLD",
        status="offline",
        reason="los",
        last_seen=now - timedelta(days=1, minutes=1),
    )
    onu = usecases.gpon_overview(now=now)["onus"][0]
    assert onu["status"] == "unknown" and onu["reason"] is None and onu["severity_rank"] == 5


def test_overview_query_count_is_constant(olts, config):
    for n in range(1, 30):
        _state(olts.zte, f"A{n}", index=n, pon=f"9/{n % 4 + 1}")
    with CaptureQueriesContext(connection) as ctx:
        usecases.gpon_overview()
    assert len(ctx.captured_queries) <= 3


def test_overview_makes_no_zabbix_call(olts, fake_zabbix, config):
    _state(olts.zte, "A")
    usecases.gpon_overview()
    assert fake_zabbix.calls == []


# --- API ------------------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="noc", password="x")


def test_api_requires_login(client, olts):
    assert client.get(URL).status_code in (401, 403)


def test_api_returns_overview(client, user, olts, config):
    _state(olts.zte, "A")
    client.force_login(user)
    response = client.get(URL)
    assert response.status_code == 200
    assert list(response.json()) == TOP_KEYS


def test_api_filters_by_olt(client, user, olts, config):
    client.force_login(user)
    data = client.get(URL, {"olt": olts.vsol.pk}).json()
    assert [o["device_id"] for o in data["olts"]] == [olts.vsol.pk]


def test_api_invalid_olt_param_is_400_and_unknown_is_404(client, user, olts, config):
    client.force_login(user)
    assert client.get(URL, {"olt": "abc"}).status_code == 400
    assert client.get(URL, {"olt": "0"}).status_code == 400
    assert client.get(URL, {"olt": "999999"}).status_code == 404


def test_vsol_gpon_olt_shows_gpon_and_gpon_capacity(olts, fake_zabbix, config):
    """EV-0097: uma VSOL com ONUs de serial GPON (Furacão/Granada) é GPON no ecrã e a PON
    usa a capacidade GPON, não a EPON."""
    fake_zabbix.items[VSOL_HOST] = [
        *vsol_onu(1, 1, "DACM91889c5c"),
        *vsol_onu(1, 2, "SHLN3c4653fa"),
        item("icmpping", "1", value_type="3"),
    ]
    usecases.collect_onu_states()
    data = usecases.gpon_overview(olt_id=olts.vsol.pk)
    [olt] = data["olts"]
    assert olt["technology"] == "gpon"
    assert olt["pons"][0]["capacity"] == 128


def test_vsol_epon_olt_keeps_epon(olts, fake_zabbix, config):
    fake_zabbix.items[VSOL_HOST] = [*vsol_onu(1, 1, "00:19:46:49:4b:7d")]
    usecases.collect_onu_states()
    [olt] = usecases.gpon_overview(olt_id=olts.vsol.pk)["olts"]
    assert (olt["technology"], olt["pons"][0]["capacity"]) == ("epon", 64)


def test_repair_migration_rekeys_existing_vsol_rows(olts, fake_zabbix, config):
    """EV-0099: linhas gravadas antes da reparação (MAC malformado na chave) são reescritas
    pela migração 0002 e a coleta seguinte encontra-as — sem linha duplicada."""
    import importlib

    from django.apps import apps

    now = timezone.now() - timedelta(hours=1)
    old = OnuState.objects.create(
        device=olts.vsol,
        onu_key="1:12|a8:bf:3c:35a:32",
        vendor="vsol",
        technology="epon",
        pon_id="0/1",
        onu_index=12,
        mac="a8:bf:3c:35a:32",
        status="online",
        status_since=now,
        status_since_is_first_seen=False,
        first_seen=now,
        last_seen=now,
    )
    migration = importlib.import_module("gpon.migrations.0002_repair_vsol_mac_keys")
    migration._repair(apps, None)
    old.refresh_from_db()
    assert (old.onu_key, old.mac) == ("1:12|a8:bf:3c:35:0a:32", "a8:bf:3c:35:0a:32")

    fake_zabbix.items[VSOL_HOST] = [*vsol_onu(1, 12, "a8:bf:3c:35a:32")]
    usecases.collect_onu_states()
    assert OnuState.objects.filter(device=olts.vsol).count() == 1
    old.refresh_from_db()
    assert old.status_since == now  # continuou online: a história não se perdeu
