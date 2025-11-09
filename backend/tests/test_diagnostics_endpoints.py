
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from integrations.zabbix.guards import reload_diagnostics_flag_cache
from inventory.models import Device, FiberCable, FiberEvent, Port, Site


@override_settings(ENABLE_DIAGNOSTIC_ENDPOINTS=False)
class DiagnosticsEndpointsDisabledTests(TestCase):
    def setUp(self):
        reload_diagnostics_flag_cache()
        self.env_patch = patch(
            "integrations.zabbix.guards.env_manager.read_values",
            return_value={},
        )
        self.runtime_patch = patch(
            "integrations.zabbix.guards.runtime_settings.get_runtime_config",
            return_value=SimpleNamespace(diagnostics_enabled=False),
        )
        self.env_patch.start()
        self.runtime_patch.start()
        user = get_user_model().objects.create_user(
            "staff",
            password="pass",
            is_staff=True,
        )
        self.client.force_login(user)

    def tearDown(self):
        self.env_patch.stop()
        self.runtime_patch.stop()
        reload_diagnostics_flag_cache()

    def test_ping_requires_flag(self):
        response = self.client.get(
            reverse("inventory-api:diagnostics-ping"),
            {"ip": "127.0.0.1"},
        )
        self.assertEqual(response.status_code, 403)

    def test_telnet_requires_flag(self):
        response = self.client.get(
            reverse("inventory-api:diagnostics-telnet"),
            {"ip": "127.0.0.1", "port": "80"},
        )
        self.assertEqual(response.status_code, 403)

    def test_ping_telnet_requires_flag(self):
        response = self.client.get(
            reverse("inventory-api:diagnostics-ping-telnet"),
            {"ip": "127.0.0.1", "port": "80"},
        )
        self.assertEqual(response.status_code, 403)

    def test_cable_up_requires_flag(self):
        response = self.client.post(
            reverse("inventory-api:diagnostics-cable-up", args=[1]),
        )
        self.assertEqual(response.status_code, 403)


@override_settings(ENABLE_DIAGNOSTIC_ENDPOINTS=True)
class DiagnosticsEndpointsEnabledTests(TestCase):
    def setUp(self):
        reload_diagnostics_flag_cache()
        self.env_patch = patch(
            "integrations.zabbix.guards.env_manager.read_values",
            return_value={"ENABLE_DIAGNOSTIC_ENDPOINTS": "true"},
        )
        self.runtime_patch = patch(
            "integrations.zabbix.guards.runtime_settings.get_runtime_config",
            return_value=SimpleNamespace(diagnostics_enabled=True),
        )
        self.env_patch.start()
        self.runtime_patch.start()
        user = get_user_model().objects.create_user(
            "staff",
            password="pass",
            is_staff=True,
        )
        self.client.force_login(user)

    def tearDown(self):
        self.env_patch.stop()
        self.runtime_patch.stop()
        reload_diagnostics_flag_cache()

    @patch("inventory.api.devices.platform.system", return_value="Windows")
    @patch("inventory.api.devices.subprocess.run")
    def test_ping_success(self, run_mock: Any, _platform: Any):
        stdout = (
            "Sent = 1, Received = 1, Lost = 0 (0% loss)\n"
            "Minimum = 1ms, Maximum = 1ms, Average = 1ms"
        )
        run_mock.return_value = SimpleNamespace(returncode=0, stdout=stdout)

        response = self.client.get(
            reverse("inventory-api:diagnostics-ping"),
            {"ip": "127.0.0.1", "count": "1"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["received"], 1)

    @patch("inventory.api.devices.socket.create_connection")
    def test_telnet_success(self, conn_mock: Any):
        class DummySocket:
            def __enter__(self):
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def getpeername(self):
                return ("127.0.0.1", 80)

        conn_mock.return_value = DummySocket()
        response = self.client.get(
            reverse("inventory-api:diagnostics-telnet"),
            {"ip": "127.0.0.1", "port": "80", "timeout": "1"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["peername"], ["127.0.0.1", 80])

    def test_cable_up_sets_status_and_event(self):
        site = Site.objects.create(display_name="Core", city="Goiania")
        device = Device.objects.create(
            site=site,
            name="CORE-01",
            vendor="Cisco",
            model="C96",
        )
        origin = Port.objects.create(device=device, name="Gi1/0/1")
        dest = Port.objects.create(device=device, name="Gi1/0/2")
        fiber = FiberCable.objects.create(
            name="Fiber-01",
            origin_port=origin,
            destination_port=dest,
            status=FiberCable.STATUS_UNKNOWN,
        )

        response = self.client.post(
            reverse(
                "inventory-api:diagnostics-cable-up",
                args=[int(fiber.pk)],
            )
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "up")
        fiber.refresh_from_db()
        self.assertEqual(fiber.status, FiberCable.STATUS_UP)
        self.assertTrue(
            FiberEvent.objects.filter(
                fiber=fiber,
                new_status=FiberCable.STATUS_UP,
                detected_reason="diagnostic-up",
            ).exists()
        )
