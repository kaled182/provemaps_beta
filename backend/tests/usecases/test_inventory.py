from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from django.test import TestCase

from inventory.models import Device, Port, Site
from inventory.usecases import devices as device_uc


class GetDevicePortsTests(TestCase):
    def setUp(self) -> None:
        self.site = Site.objects.create(display_name="Test Site")
        self.device = Device.objects.create(name="Test Device", site=self.site)
        self.port1 = Port.objects.create(name="Port 1", device=self.device)
        self.port2 = Port.objects.create(
            name="Port 2",
            device=self.device,
            notes="some notes",
        )

    def test_get_ports_for_existing_device(self) -> None:
        result = device_uc.get_device_ports(self.device.pk)

        self.assertIn("ports", result)
        self.assertEqual(len(result["ports"]), 2)

        port_data = next(
            payload
            for payload in result["ports"]
            if payload["id"] == self.port2.pk
        )
        self.assertEqual(port_data["name"], "Port 2")
        self.assertEqual(port_data["device"], "Test Device")
        self.assertEqual(port_data["notes"], "some notes")

    def test_raises_not_found_for_nonexistent_device(self) -> None:
        with self.assertRaises(device_uc.InventoryNotFound):
            device_uc.get_device_ports(999)


class AddDeviceFromZabbixTests(TestCase):
    @patch("inventory.usecases.devices.ZABBIX_REQUEST")
    def test_add_new_device_happy_path(
        self, mock_zabbix_request: MagicMock
    ) -> None:
        zabbix_hostid = "10101"
        mock_host_response: List[Dict[str, Any]] = [
            {
                "hostid": zabbix_hostid,
                "name": "Zabbix Host Name",
                "host": "zabbix.host.name",
                "inventory": {
                    "location": "IDC-Confresa",
                    "location_lat": "-23.5505",
                    "location_lon": "-46.6333",
                    "site_address": "Sao Paulo",
                },
            }
        ]
        mock_items_response: List[Dict[str, Any]] = [
            {
                "itemid": "20202",
                "key_": "ifOperStatus[eth0]",
                "name": "Interface eth0 status",
                "interfaceid": "30303",
            },
            {
                "itemid": "20203",
                "key_": "net.if.in[eth0]",
                "name": "Incoming traffic on eth0",
            },
        ]

        def zabbix_side_effect(
            method: str,
            params: Dict[str, Any],
        ) -> List[Dict[str, Any]]:
            if (
                method == "host.get"
                and params.get("selectInventory") == "extend"
            ):
                return mock_host_response
            if method == "item.get":
                return mock_items_response
            return []

        mock_zabbix_request.side_effect = zabbix_side_effect

        payload = {"hostid": zabbix_hostid}

        result = device_uc.add_device_from_zabbix(payload)

        self.assertEqual(Site.objects.count(), 1)
        site = Site.objects.first()
        assert site is not None
        self.assertEqual(site.display_name, "IDC-Confresa")
        self.assertEqual(site.latitude, Decimal("-23.5505"))
        self.assertTrue(site.slug)

        self.assertEqual(Device.objects.count(), 1)
        device = Device.objects.first()
        assert device is not None
        self.assertEqual(device.name, "zabbix.host.name")
        self.assertEqual(device.site, site)
        self.assertEqual(device.zabbix_hostid, zabbix_hostid)

        self.assertEqual(Port.objects.count(), 1)
        port = Port.objects.first()
        assert port is not None
        self.assertEqual(port.name, "eth0")
        self.assertEqual(port.device, device)
        self.assertEqual(port.zabbix_item_key, "ifOperStatus[eth0]")

        self.assertEqual(result["created"]["sites"], 1)
        self.assertEqual(result["created"]["devices"], 1)
        self.assertEqual(result["created"]["ports"], 1)

    @patch("inventory.usecases.devices.ZABBIX_REQUEST")
    def test_add_device_updates_existing_device(
        self, mock_zabbix_request: MagicMock
    ) -> None:
        existing_site = Site.objects.create(display_name="Legacy Confresa")
        existing_device = Device.objects.create(
            site=existing_site,
            name="legacy-device",
            zabbix_hostid="10101",
        )

        mock_host_response: List[Dict[str, Any]] = [
            {
                "hostid": "10101",
                "name": "Zabbix Host Name",
                "host": "zabbix.host.name",
                "inventory": {
                    "location": "IDC-Confresa",
                    "location_lat": "10.0000",
                    "location_lon": "-50.0000",
                },
            }
        ]
        mock_items_response: List[Dict[str, Any]] = [
            {
                "itemid": "20202",
                "key_": "ifOperStatus[eth0]",
                "name": "Interface eth0 status",
                "interfaceid": "30303",
            }
        ]

        def zabbix_side_effect(
            method: str,
            params: Dict[str, Any],
        ) -> List[Dict[str, Any]]:
            if (
                method == "host.get"
                and params.get("selectInventory") == "extend"
            ):
                return mock_host_response
            if method == "item.get":
                return mock_items_response
            return []

        mock_zabbix_request.side_effect = zabbix_side_effect

        result = device_uc.add_device_from_zabbix({"hostid": "10101"})

        self.assertEqual(Site.objects.count(), 1)
        site = Site.objects.first()
        assert site is not None
        self.assertEqual(site.display_name, "IDC-Confresa")

        self.assertEqual(Device.objects.count(), 1)
        device = Device.objects.first()
        assert device is not None
        self.assertEqual(device.pk, existing_device.pk)
        self.assertEqual(device.site, site)
        self.assertEqual(device.zabbix_hostid, "10101")

        self.assertEqual(result["created"]["sites"], 0)
        self.assertEqual(result["created"]["devices"], 0)
        self.assertEqual(result["created"]["ports"], 1)
