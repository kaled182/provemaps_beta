"""EV-0091: a chave gravada pede-se ao Zabbix por igualdade exata, nunca por LIKE."""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from inventory.services.fiber_status import (
    fetch_interface_status_advanced,
    get_oper_status_from_port,
    get_oper_status_from_zabbix,
)

STATUS_ZABBIX = "inventory.services.fiber_status.zabbix_request"

KEY = "hwEntityOpticalLaneRxPower[6747220]"
LONGER_KEY = "hwEntityOpticalLaneRxPower[67472206]"


def _recorder(calls: list[tuple[str, dict]]):
    def fake(method: str, params: dict[str, Any] | None = None, *a: Any, **k: Any):
        params = params or {}
        calls.append((method, params))
        if method != "item.get":
            return []
        wanted = (params.get("filter") or {}).get("key_")
        if wanted is None:
            # Um `search` (LIKE) devolveria a chave mais longa que CONTÉM a pedida.
            return [{"itemid": "1", "key_": LONGER_KEY, "lastvalue": "-9", "lastclock": "1"}]
        return [
            i
            for i in [
                {
                    "itemid": "2",
                    "key_": KEY,
                    "lastvalue": "-12.3",
                    # item completo: o validador do EV-0082 recusa leituras sem estes campos
                    "lastclock": str(int(time.time())),
                    "state": "0",
                    "value_type": "0",
                    "units": "dBm",
                }
            ]
            if i["key_"] == wanted
        ]

    return fake


def _item_gets(calls: list[tuple[str, dict]]) -> list[dict]:
    return [p for m, p in calls if m == "item.get"]


def _assert_exact(params: dict, key: str) -> None:
    assert params["filter"] == {"key_": key}
    assert "search" not in params
    assert "searchByAny" not in params
    assert params["hostids"]


def test_fetch_interface_status_advanced_asks_exact_key():
    calls: list[tuple[str, dict]] = []
    with patch(STATUS_ZABBIX, side_effect=_recorder(calls)):
        _, info = fetch_interface_status_advanced("101", rx_key=KEY)

    gets = _item_gets(calls)
    assert gets
    for params in gets:
        _assert_exact(params, KEY)
    assert info.get("rx") == -12.3


def test_get_oper_status_from_zabbix_asks_exact_key():
    calls: list[tuple[str, dict]] = []
    device = SimpleNamespace(zabbix_hostid="101")
    with patch(STATUS_ZABBIX, side_effect=_recorder(calls)):
        get_oper_status_from_zabbix(device, "eth0")

    gets = _item_gets(calls)
    assert gets
    _assert_exact(gets[0], "ifOperStatus[eth0]")


def test_get_oper_status_from_port_asks_exact_key():
    calls: list[tuple[str, dict]] = []
    port = SimpleNamespace(
        device=SimpleNamespace(zabbix_hostid="101"),
        zabbix_item_key=KEY,
        zabbix_itemid="",
    )
    with patch(STATUS_ZABBIX, side_effect=_recorder(calls)):
        get_oper_status_from_port(port)

    gets = _item_gets(calls)
    assert gets
    _assert_exact(gets[0], KEY)
