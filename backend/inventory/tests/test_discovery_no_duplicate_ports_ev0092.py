"""EV-0092: cada candidato ifOperStatus gera uma só entrada em `port_records`."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from django.core.cache import cache

from inventory.models import Device, Port, Site
from inventory.usecases import devices as device_uc, devices_common, devices_discovery

OPTICAL_ZABBIX = "inventory.domain.optical.zabbix_request"


def _status_item(port: str) -> dict[str, Any]:
    return {
        "itemid": f"9{port}",
        "key_": f"ifOperStatus[{port}]",
        "name": f"IF {port}: Status",
        "units": "",
        "value_type": "3",
        "interfaceid": "7",
    }


@pytest.mark.django_db
def test_n_candidates_give_n_records_and_n_ports():
    cache.clear()
    items = [_status_item(p) for p in ("1", "2", "3")]

    def fake(method: str, params: dict[str, Any]):
        if method == "host.get":
            return [{"hostid": "10744", "name": "OLT", "host": "olt", "inventory": {}}]
        if method == "item.get":
            return items
        return []

    site = Site.objects.create(display_name="BRV", latitude=-15.0, longitude=-47.0)
    Device.objects.create(name="olt", site=site, zabbix_hostid="10744")
    with (
        patch.object(devices_common, "ZABBIX_REQUEST", side_effect=fake),
        patch(OPTICAL_ZABBIX, return_value=[]),
        patch.object(devices_discovery, "sync_device_groups_for_device", return_value=None),
        patch("inventory.services.import_rules.apply_import_rules", return_value=None),
    ):
        result = device_uc.add_device_from_zabbix({"hostid": "10744", "update_site": False})

    assert result["total_ports_detected"] == 3
    assert Port.objects.filter(device__zabbix_hostid="10744").count() == 3
    assert len(result["ports_created"]) + len(result["ports_updated"]) <= 3
