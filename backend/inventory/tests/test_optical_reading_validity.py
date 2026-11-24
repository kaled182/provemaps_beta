"""EV-0082 — a coleta óptica só grava leituras válidas: item coletado (`lastclock` > 0),
suportado (`state` 0), `lastvalue` não vazio, valor em -60…+15 dBm e, nas chaves de ONU
ZTE/VSOL, diferente dos valores-sentinela 0 e -80. Sem leitura válida a ponta não é
gravada e `last_optical_check` não avança."""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.utils import timezone

from inventory.domain import optical
from inventory.models import Device, Port, Site
from inventory.services.fiber_status import fetch_interface_status_advanced
from inventory.tasks import OPTICAL_LOCK_KEY, update_all_port_optical_levels

ZABBIX = "inventory.domain.optical.zabbix_request"
STATUS_ZABBIX = "inventory.services.fiber_status.zabbix_request"
CLOCK = "1795450000"


def _item(key, lastvalue, *, state="0", lastclock=CLOCK, itemid="1"):
    return {
        "itemid": itemid,
        "key_": key,
        "lastvalue": lastvalue,
        "lastclock": lastclock,
        "state": state,
        "value_type": "0",
        "units": "dBm",
    }


@pytest.fixture
def port(db):
    site = Site.objects.create(display_name="POP", latitude=-15.0, longitude=-47.0)
    dev = Device.objects.create(name="SW", site=site, zabbix_hostid="101")
    old_check = timezone.now() - timedelta(hours=3)
    return Port.objects.create(
        device=dev,
        name="XGigabitEthernet0/0/1",
        rx_power_item_key="hwEntityOpticalLaneRxPower[1]",
        tx_power_item_key="hwEntityOpticalLaneTxPower[1]",
        last_rx_power=Decimal("-21.50"),
        last_tx_power=Decimal("1.20"),
        last_optical_check=old_check,
    )


def _run(items):
    cache.delete(OPTICAL_LOCK_KEY)
    with patch(ZABBIX, return_value=items) as zabbix:
        result = update_all_port_optical_levels()
    return result, zabbix


@pytest.mark.django_db
def test_item_never_collected_is_not_written_nor_touches_check(port):
    before = port.last_optical_check
    result, zabbix = _run(
        [
            _item("hwEntityOpticalLaneRxPower[1]", "0", lastclock="0"),
            _item("hwEntityOpticalLaneTxPower[1]", "0", lastclock="0", itemid="2"),
        ]
    )

    port.refresh_from_db()
    assert port.last_rx_power == Decimal("-21.50")  # o anterior fica, com a hora antiga
    assert port.last_tx_power == Decimal("1.20")
    assert port.last_optical_check == before
    assert result["updated"] == 0
    assert result["errors"] == 1  # registado no log
    assert [c.args[0] for c in zabbix.call_args_list] == ["item.get"]  # sem history.get
    params = zabbix.call_args_list[0].args[1]
    assert {"lastclock", "state"} <= set(params["output"])


@pytest.mark.django_db
def test_unsupported_item_is_not_written_nor_touches_check(port):
    before = port.last_optical_check
    result, _ = _run(
        [
            _item("hwEntityOpticalLaneRxPower[1]", "0", state="1"),
            _item("hwEntityOpticalLaneTxPower[1]", "32.2471", state="1", itemid="2"),
        ]
    )

    port.refresh_from_db()
    assert port.last_rx_power == Decimal("-21.50")
    assert port.last_tx_power == Decimal("1.20")
    assert port.last_optical_check == before
    assert result["updated"] == 0


@pytest.mark.django_db
def test_onu_rx_sentinel_is_not_written(db):
    site = Site.objects.create(display_name="OLT", latitude=-15.0, longitude=-47.0)
    dev = Device.objects.create(name="ZTE", site=site, zabbix_hostid="10744")
    offline = Port.objects.create(device=dev, name="a", rx_power_item_key="onu.rx[GP1,9,1,1]")
    no_reading = Port.objects.create(device=dev, name="b", rx_power_item_key="onu.rx[GP2,9,1,2]")
    vsol = Port.objects.create(device=dev, name="c", rx_power_item_key="SinalRXS0P1[GPON0/1:1 - 1]")
    good = Port.objects.create(device=dev, name="d", rx_power_item_key="onu.rx[GP3,9,1,3]")

    result, _ = _run(
        [
            _item("onu.rx[GP1,9,1,1]", "-80", itemid="1"),
            _item("onu.rx[GP2,9,1,2]", "0", itemid="2"),
            _item("SinalRXS0P1[GPON0/1:1 - 1]", "0", itemid="3"),
            _item("onu.rx[GP3,9,1,3]", "-23.24", itemid="4"),
        ]
    )

    for p in (offline, no_reading, vsol):
        p.refresh_from_db()
        assert p.last_rx_power is None
        assert p.last_optical_check is None
    good.refresh_from_db()
    assert good.last_rx_power == Decimal("-23.24")
    assert result["updated"] == 1
    assert result["errors"] == 3


@pytest.mark.django_db
def test_valid_huawei_tx_zero_dbm_is_written(port):
    result, _ = _run(
        [
            _item("hwEntityOpticalLaneRxPower[1]", "-18.4"),
            _item("hwEntityOpticalLaneTxPower[1]", "0", itemid="2"),
        ]
    )

    port.refresh_from_db()
    assert port.last_tx_power == Decimal("0.00")  # 0 dBm é potência real fora das ONU
    assert port.last_rx_power == Decimal("-18.40")
    assert port.last_optical_check > timezone.now() - timedelta(minutes=1)
    assert result == {"success": True, "total": 1, "updated": 1, "errors": 0}


@pytest.mark.django_db
def test_invalid_side_is_cleared_when_other_side_refreshes_check(port):
    # Um só `last_optical_check`: o TX antigo não pode ficar sob a hora nova.
    _run(
        [
            _item("hwEntityOpticalLaneRxPower[1]", "-18.4"),
            _item("hwEntityOpticalLaneTxPower[1]", "0", lastclock="0", itemid="2"),
        ]
    )

    port.refresh_from_db()
    assert port.last_rx_power == Decimal("-18.40")
    assert port.last_tx_power is None


def test_validate_optical_reading_rules():
    ok = _item("k", "-20")
    assert optical.validate_optical_reading(ok, -20.0) == (-20.0, None)
    assert optical.validate_optical_reading(None, None) == (None, None)
    assert optical.validate_optical_reading(_item("k", "", lastclock="0"), None)[1]
    assert optical.validate_optical_reading(_item("k", ""), None)[1] == "lastvalue vazio"
    missing_fields = {"itemid": "1", "key_": "k", "lastvalue": "-20"}
    assert optical.validate_optical_reading(missing_fields, -20.0)[0] is None
    assert optical.validate_optical_reading(_item("k", "380"), 380.0)[0] is None
    assert optical.validate_optical_reading(_item("ONU.RX[x]", "0"), 0.0)[0] is None
    assert optical.validate_optical_reading(_item("tx.huawei", "0"), 0.0) == (0.0, None)


def test_fiber_status_ignores_never_collected_zero():
    def fake(method, params=None, *a, **k):
        key = params["search"]["key_"]
        return [_item(key, "0", lastclock="0")]

    with patch(STATUS_ZABBIX, side_effect=fake):
        status, meta = fetch_interface_status_advanced("101", rx_key="rx.k", tx_key="tx.k")

    assert status == "unknown"  # antes: "critical" com reason "zero_signal"
    assert meta["method"] == "optical_power_no_values"
