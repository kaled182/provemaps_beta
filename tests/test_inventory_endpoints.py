import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.models import Device, FiberCable, Port, Site


class PortTrafficHistoryAPITests(TestCase):
    def setUp(self):
        self.site = Site.objects.create(name="Goiania-POP", city="Goiania")
        self.device = Device.objects.create(
            site=self.site,
            name="SW-GYN-01",
            vendor="Cisco",
            model="C9500",
            zabbix_hostid="10101",
        )
        self.port = Port.objects.create(
            device=self.device,
            name="Gi1/0/1",
        )

    def test_returns_400_when_port_missing_traffic_items(self):
        url = reverse("zabbix_api:api_port_traffic_history", args=[self.port.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("traffic items", response.json()["error"])

    @patch("zabbix_api.usecases.inventory.ZABBIX_REQUEST")
    def test_returns_history_payload(self, request_mock):
        self.port.zabbix_item_id_traffic_in = "111"
        self.port.zabbix_item_id_traffic_out = "222"
        self.port.save(
            update_fields=[
                "zabbix_item_id_traffic_in",
                "zabbix_item_id_traffic_out",
            ]
        )

        def fake_zabbix_request(method, params=None, **kwargs):
            if method == "item.get":
                itemid = params.get("itemids")
                if itemid == "111":
                    return [{"value_type": "3", "units": "bps"}]
                if itemid == "222":
                    return [{"value_type": "0", "units": "pps"}]
                return []
            if method == "history.get":
                itemid = params.get("itemids")
                if itemid == "111":
                    return [{"clock": "1690000000", "value": "10"}]
                if itemid == "222":
                    return [{"clock": "1690000000", "value": "5"}]
            return []

        request_mock.side_effect = fake_zabbix_request

        url = reverse("zabbix_api:api_port_traffic_history", args=[self.port.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["in"]["unit"], "bps")
        self.assertEqual(payload["out"]["unit"], "pps")
        self.assertEqual(len(payload["in"]["history"]), 1)
        self.assertEqual(payload["in"]["history"][0]["value"], 10.0)
        self.assertEqual(payload["out"]["history"][0]["value"], 5.0)


class ManualFiberCreationTests(TestCase):
    def setUp(self):
        site = Site.objects.create(name="HQ", city="Goiania")
        self.device = Device.objects.create(
            site=site,
            name="CORE-01",
            vendor="Cisco",
            model="C9500",
            zabbix_hostid="2001",
        )
        self.origin_port = Port.objects.create(device=self.device, name="Gi1/0/1")
        self.dest_port = Port.objects.create(device=self.device, name="Gi1/0/2")
        user = get_user_model().objects.create_user("staff", password="pass", is_staff=True)
        self.client.force_login(user)

    @patch("zabbix_api.inventory.staff_guard", return_value=None)
    def test_create_manual_fiber_for_same_device(self, guard_mock):
        url = reverse("zabbix_api:api_create_manual_fiber")
        payload = {
            "name": "Manual Backbone",
            "origin_device_id": str(self.device.id),
            "origin_port_id": str(self.origin_port.id),
            "dest_device_id": str(self.device.id),
            "dest_port_id": str(self.dest_port.id),
            "path": [
                {"lat": -16.6, "lng": -49.2},
                {"lat": -16.7, "lng": -49.3},
                {"lat": -16.8, "lng": -49.4},
            ],
        }

        response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("fiber_id", data)

        fiber = FiberCable.objects.get(id=data["fiber_id"])
        self.assertEqual(fiber.origin_port, self.origin_port)
        self.assertEqual(fiber.destination_port, self.dest_port)
        self.assertEqual(len(fiber.path_coordinates), 3)
        self.assertGreater(float(data["length_km"]), 0.0)

    @patch("zabbix_api.inventory.staff_guard", return_value=None)
    def test_create_manual_fiber_single_port(self, guard_mock):
        url = reverse("zabbix_api:api_create_manual_fiber")
        payload = {
            "name": "Local Loop",
            "origin_device_id": str(self.device.id),
            "origin_port_id": str(self.origin_port.id),
            "dest_device_id": "",
            "dest_port_id": "",
            "single_port": True,
            "path": [
                {"lat": -16.6, "lng": -49.2},
                {"lat": -16.61, "lng": -49.25},
            ],
        }

        response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        fiber = FiberCable.objects.get(id=data["fiber_id"])
        self.assertEqual(fiber.origin_port, self.origin_port)
        self.assertEqual(fiber.destination_port, self.origin_port)
        self.assertTrue(data["single_port"])
