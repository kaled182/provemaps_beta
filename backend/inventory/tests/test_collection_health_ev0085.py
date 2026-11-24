"""EV-0085 — «Saúde da coleta»: motivo gravado pela coleta, usecase/API e aviso por e-mail."""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.utils import timezone

from inventory.models import Device, Port, Site
from inventory.tasks import (
    COLLECTION_HEALTH_NOTIFIED_KEY,
    OPTICAL_ITEM_MISSING,
    OPTICAL_LOCK_KEY,
    notify_collection_health,
    update_all_port_optical_levels,
)
from inventory.usecases.collection_health import collection_health

ZABBIX_UC = "inventory.usecases.collection_health.zabbix_request"
ZABBIX_OPTICAL = "inventory.domain.optical.zabbix_request"
URL = "/api/v1/inventory/collection-health/"
CLOCK = "1795450000"


def _item(key, lastvalue, *, state="0", itemid="1"):
    return {
        "itemid": itemid,
        "key_": key,
        "lastvalue": lastvalue,
        "lastclock": CLOCK,
        "state": state,
        "value_type": "0",
        "units": "dBm",
    }


def _hosts(*hostids):
    """host.get falso: devolve só os hostids pedidos que «existem»."""

    def fake(method, params=None, *a, **k):
        assert method == "host.get"
        return [{"hostid": h} for h in params["hostids"] if h in hostids]

    return fake


@pytest.fixture
def now():
    return timezone.now()


@pytest.fixture
def inventory_data(db, now):
    site = Site.objects.create(display_name="POP Centro", latitude=-15.0, longitude=-47.0)
    sw = Device.objects.create(name="A Switch", site=site, zabbix_hostid="101")
    olt = Device.objects.create(name="B OLT", site=site, zabbix_hostid="999")
    Device.objects.create(name="C Sem Zabbix", site=site)
    fresh = now - timedelta(minutes=5)
    ports = {
        "ok": Port.objects.create(
            device=sw,
            name="p1-ok",
            rx_power_item_key="rx.1",
            tx_power_item_key="tx.1",
            last_rx_power=Decimal("-20.10"),
            last_tx_power=Decimal("1.50"),
            last_optical_check=fresh,
        ),
        # item_problem vence never e stale
        "problem": Port.objects.create(
            device=sw,
            name="p2-problem",
            rx_power_item_key="rx.2",
            last_rx_power=Decimal("-21.00"),
            last_optical_check=now - timedelta(hours=10),
            optical_problem="RX (rx.2): item unsupported no Zabbix",
        ),
        "never": Port.objects.create(device=sw, name="p3-never", tx_power_item_key="tx.3"),
        "stale": Port.objects.create(
            device=sw,
            name="p4-stale",
            rx_power_item_key="rx.4",
            last_rx_power=Decimal("-19.00"),
            last_optical_check=now - timedelta(hours=3),
        ),
        "nokey": Port.objects.create(device=sw, name="p5-sem-chave"),
        "olt1": Port.objects.create(device=olt, name="gpon-1", rx_power_item_key="onu.rx[1]"),
        "olt2": Port.objects.create(
            device=olt,
            name="gpon-2",
            rx_power_item_key="onu.rx[2]",
            last_optical_check=now - timedelta(days=120),
        ),
    }
    return {"sw": sw, "olt": olt, "ports": ports}


# ── usecase ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_format_and_key_order(inventory_data, now):
    with patch(ZABBIX_UC, side_effect=_hosts("101")) as zabbix:
        data = collection_health(now=now)

    zabbix.assert_called_once()
    assert zabbix.call_args.args[1] == {"output": ["hostid"], "hostids": ["101", "999"]}
    assert list(data) == [
        "generated_at",
        "stale_hours",
        "zabbix_ok",
        "zabbix_error",
        "totals",
        "devices_missing_host",
        "devices_without_readings",
        "ports",
    ]
    assert list(data["totals"]) == [
        "devices",
        "devices_missing_host",
        "devices_without_readings",
        "ports_with_key",
        "ports_reading",
        "ports_problem",
    ]
    assert data["generated_at"].endswith("Z")
    assert data["stale_hours"] == 2
    assert data["zabbix_ok"] is True and data["zabbix_error"] is None
    assert data["totals"] == {
        "devices": 3,
        "devices_missing_host": 1,
        "devices_without_readings": 1,
        "ports_with_key": 6,
        "ports_reading": 1,
        "ports_problem": 5,
    }
    olt = inventory_data["olt"]
    assert data["devices_missing_host"] == [
        {
            "device_id": olt.id,
            "device_name": "B OLT",
            "site_name": "POP Centro",
            "zabbix_hostid": "999",
        }
    ]
    assert data["devices_without_readings"] == [
        {
            "device_id": olt.id,
            "device_name": "B OLT",
            "site_name": "POP Centro",
            "ports_with_key": 2,
            "ports_reading": 0,
        }
    ]
    port = data["ports"][0]
    assert list(port) == [
        "port_id",
        "port_name",
        "device_id",
        "device_name",
        "rx_key",
        "tx_key",
        "last_rx_power",
        "last_tx_power",
        "last_optical_check",
        "reason",
        "problem",
    ]


@pytest.mark.django_db
def test_reason_precedence_and_order(inventory_data, now):
    with patch(ZABBIX_UC, side_effect=_hosts("101", "999")):
        data = collection_health(now=now)

    by_name = {p["port_name"]: p for p in data["ports"]}
    # ordem: device_name, port_name
    assert [p["port_name"] for p in data["ports"]] == [
        "p2-problem",
        "p3-never",
        "p4-stale",
        "gpon-1",
        "gpon-2",
    ]
    assert by_name["p2-problem"]["reason"] == "item_problem"
    assert by_name["p2-problem"]["problem"] == "RX (rx.2): item unsupported no Zabbix"
    assert by_name["p2-problem"]["last_rx_power"] == -21.0
    assert by_name["p2-problem"]["tx_key"] is None
    assert by_name["p3-never"]["reason"] == "never"
    assert by_name["p3-never"]["last_optical_check"] is None
    assert by_name["p3-never"]["problem"] is None
    assert by_name["p4-stale"]["reason"] == "stale"
    assert by_name["gpon-2"]["reason"] == "stale"
    assert data["devices_missing_host"] == []
    assert data["totals"]["devices_missing_host"] == 0

    # Com janela de 4 h a p4 (3 h) volta a contar como leitura.
    with patch(ZABBIX_UC, side_effect=_hosts("101", "999")):
        wide = collection_health(stale_hours=4, now=now)
    assert wide["totals"]["ports_reading"] == 2
    assert "p4-stale" not in {p["port_name"] for p in wide["ports"]}


@pytest.mark.django_db
def test_zabbix_down_is_unknown_not_zero(inventory_data, now):
    with patch(ZABBIX_UC, side_effect=RuntimeError("circuit open")):
        data = collection_health(now=now)

    assert data["zabbix_ok"] is False
    assert data["zabbix_error"] == "circuit open"
    assert data["devices_missing_host"] == []
    assert data["totals"]["devices_missing_host"] is None
    # o resto vem da base e continua lá
    assert data["totals"]["ports_with_key"] == 6
    assert len(data["devices_without_readings"]) == 1


@pytest.mark.django_db
def test_no_hostids_skips_zabbix(db, now):
    site = Site.objects.create(display_name="POP", latitude=-15.0, longitude=-47.0)
    Device.objects.create(name="Sem host", site=site)
    with patch(ZABBIX_UC) as zabbix:
        data = collection_health(now=now)
    zabbix.assert_not_called()
    assert data["zabbix_ok"] is True
    assert data["totals"]["devices_missing_host"] == 0


@pytest.mark.django_db
def test_queries_do_not_grow_with_ports(inventory_data, now, django_assert_max_num_queries):
    with patch(ZABBIX_UC, side_effect=_hosts("101")):
        with django_assert_max_num_queries(2):
            collection_health(now=now)


# ── API ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="noc", password="x")


@pytest.mark.django_db
def test_api_ok(client, user, inventory_data):
    client.force_login(user)
    with patch(ZABBIX_UC, side_effect=_hosts("101")):
        resp = client.get(URL, {"stale_hours": "3"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["stale_hours"] == 3
    assert body["totals"]["devices_missing_host"] == 1


@pytest.mark.django_db
@pytest.mark.parametrize("value", ["0", "169", "abc", "2.5", "-1"])
def test_api_rejects_bad_stale_hours(client, user, value):
    client.force_login(user)
    with patch(ZABBIX_UC) as zabbix:
        resp = client.get(URL, {"stale_hours": value})
    assert resp.status_code == 400
    assert "error" in resp.json()
    zabbix.assert_not_called()


@pytest.mark.django_db
def test_api_requires_login(client):
    with patch(ZABBIX_UC) as zabbix:
        resp = client.get(URL)
    assert resp.status_code in (302, 401, 403)
    zabbix.assert_not_called()


# ── coleta grava o motivo ────────────────────────────────────────────────────


@pytest.fixture
def collected_port(db):
    site = Site.objects.create(display_name="POP", latitude=-15.0, longitude=-47.0)
    dev = Device.objects.create(name="SW", site=site, zabbix_hostid="101")
    return Port.objects.create(
        device=dev,
        name="XGigabitEthernet0/0/1",
        rx_power_item_key="hwEntityOpticalLaneRxPower[1]",
        tx_power_item_key="hwEntityOpticalLaneTxPower[1]",
    )


def _collect(items=None, side_effect=None):
    cache.delete(OPTICAL_LOCK_KEY)
    with patch(ZABBIX_OPTICAL, return_value=items, side_effect=side_effect):
        return update_all_port_optical_levels()


@pytest.mark.django_db
def test_collection_writes_and_clears_optical_problem(collected_port):
    _collect(
        [
            _item("hwEntityOpticalLaneRxPower[1]", "0", state="1"),
            _item("hwEntityOpticalLaneTxPower[1]", "1.2", itemid="2"),
        ]
    )
    collected_port.refresh_from_db()
    assert collected_port.optical_problem == (
        "RX (hwEntityOpticalLaneRxPower[1]): item unsupported no Zabbix"
    )
    assert collected_port.last_tx_power == Decimal("1.20")

    _collect(
        [
            _item("hwEntityOpticalLaneRxPower[1]", "-20.5"),
            _item("hwEntityOpticalLaneTxPower[1]", "1.2", itemid="2"),
        ]
    )
    collected_port.refresh_from_db()
    assert collected_port.optical_problem == ""
    assert collected_port.last_rx_power == Decimal("-20.50")


@pytest.mark.django_db
def test_collection_does_not_save_when_problem_unchanged(collected_port):
    bad = [
        _item("hwEntityOpticalLaneRxPower[1]", "0", state="1"),
        _item("hwEntityOpticalLaneTxPower[1]", "0", state="1", itemid="2"),
    ]
    _collect(bad)
    collected_port.refresh_from_db()
    assert collected_port.optical_problem.startswith("RX (")

    with patch.object(Port, "save", autospec=True) as save:
        _collect(bad)
    save.assert_not_called()


@pytest.mark.django_db
def test_collection_truncates_problem(collected_port):
    long_key = "k" * 200
    Port.objects.filter(pk=collected_port.pk).update(
        rx_power_item_key=long_key, tx_power_item_key=long_key + "t"
    )
    _collect(
        [
            _item(long_key, "0", state="1"),
            _item(long_key + "t", "0", state="1", itemid="2"),
        ]
    )
    collected_port.refresh_from_db()
    assert len(collected_port.optical_problem) == 255


@pytest.mark.django_db
def test_collection_records_missing_item(collected_port):
    # o host responde (há um item), mas a chave TX da porta não existe nele
    _collect([_item("hwEntityOpticalLaneRxPower[1]", "-20.5")])
    collected_port.refresh_from_db()
    assert collected_port.last_rx_power == Decimal("-20.50")
    assert collected_port.optical_problem == (
        f"TX (hwEntityOpticalLaneTxPower[1]): {OPTICAL_ITEM_MISSING}"
    )


@pytest.mark.django_db
def test_collection_zabbix_down_keeps_previous_problem(collected_port):
    Port.objects.filter(pk=collected_port.pk).update(optical_problem="anterior")
    _collect(side_effect=RuntimeError("zabbix fora"))
    collected_port.refresh_from_db()
    assert collected_port.optical_problem == "anterior"

    Port.objects.filter(pk=collected_port.pk).update(optical_problem="")
    _collect(side_effect=RuntimeError("zabbix fora"))
    collected_port.refresh_from_db()
    assert collected_port.optical_problem == ""  # Zabbix em baixo ≠ item inexistente


# ── aviso por e-mail ─────────────────────────────────────────────────────────


@pytest.fixture
def staff(db):
    return get_user_model().objects.create_user(
        username="paulo", password="x", email="noc@example.com", is_staff=True
    )


@pytest.fixture
def clean_notify(settings):
    # setup_app.usecases.config._apply_runtime_overrides escreve settings.EMAIL_BACKEND no
    # processo (smtp/console) e os testes do setup_app deixam-no assim: fixar o locmem aqui.
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    cache.delete(COLLECTION_HEALTH_NOTIFIED_KEY)
    mail.outbox = []
    yield
    cache.delete(COLLECTION_HEALTH_NOTIFIED_KEY)


@pytest.mark.django_db
def test_notify_sends_once_then_again_for_new_device(inventory_data, staff, clean_notify):
    with patch(ZABBIX_UC, side_effect=_hosts("101")):
        first = notify_collection_health()
    assert first["sent"] is True
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == "[ProVeMaps] Saúde da coleta: 1 equipamento(s) sem leitura"
    assert msg.to == ["noc@example.com"]
    assert "B OLT" in msg.body
    assert "host Zabbix 999 não existe" in msg.body
    assert "/saude-coleta" in msg.body

    # mesmo conjunto → não repete
    with patch(ZABBIX_UC, side_effect=_hosts("101")):
        second = notify_collection_health()
    assert second["sent"] is False
    assert len(mail.outbox) == 1

    # o switch perde a única leitura boa → equipamento novo no conjunto → novo aviso
    Port.objects.filter(pk=inventory_data["ports"]["ok"].pk).update(
        optical_problem="RX (rx.1): item unsupported no Zabbix"
    )
    with patch(ZABBIX_UC, side_effect=_hosts("101")):
        third = notify_collection_health()
    assert third["sent"] is True
    assert len(mail.outbox) == 2
    assert mail.outbox[1].subject == "[ProVeMaps] Saúde da coleta: 2 equipamento(s) sem leitura"
    assert "A Switch" in mail.outbox[1].body


@pytest.mark.django_db
def test_notify_device_that_leaves_and_returns_is_notified_again(
    inventory_data, staff, clean_notify
):
    olt = inventory_data["olt"]
    with patch(ZABBIX_UC, side_effect=_hosts("101")):
        notify_collection_health()
    assert len(mail.outbox) == 1

    # a OLT recupera (host existe e lê) → sai do guardado
    Port.objects.filter(device=olt).update(last_optical_check=timezone.now())
    with patch(ZABBIX_UC, side_effect=_hosts("101", "999")):
        notify_collection_health()
    assert cache.get(COLLECTION_HEALTH_NOTIFIED_KEY) == []

    # volta a falhar → avisa de novo
    Port.objects.filter(device=olt).update(last_optical_check=None)
    with patch(ZABBIX_UC, side_effect=_hosts("101", "999")):
        result = notify_collection_health()
    assert result["sent"] is True
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_notify_zabbix_down_does_not_count_missing_host(db, staff, clean_notify):
    site = Site.objects.create(display_name="POP", latitude=-15.0, longitude=-47.0)
    Device.objects.create(name="OLT", site=site, zabbix_hostid="999")  # sem portas com chave
    with patch(ZABBIX_UC, side_effect=RuntimeError("fora")):
        result = notify_collection_health()
    assert result == {"sent": False, "alarms": 0, "new": 0, "zabbix_ok": False}
    assert mail.outbox == []


@pytest.mark.django_db
def test_notify_without_recipients_does_not_raise(inventory_data, clean_notify):
    with patch(ZABBIX_UC, side_effect=_hosts("101")):
        result = notify_collection_health()
    assert result["sent"] is False
    assert result["error"] == "sem destinatários"
    assert mail.outbox == []
    assert cache.get(COLLECTION_HEALTH_NOTIFIED_KEY) is None  # avisa quando houver quem


@pytest.mark.django_db
def test_notify_smtp_failure_does_not_raise(inventory_data, staff, clean_notify):
    with (
        patch(ZABBIX_UC, side_effect=_hosts("101")),
        patch("django.core.mail.send_mail", side_effect=OSError("smtp fora")),
    ):
        result = notify_collection_health()
    assert result["sent"] is False
    assert result["error"] == "smtp fora"
    assert cache.get(COLLECTION_HEALTH_NOTIFIED_KEY) is None  # tenta na hora seguinte
