from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
import subprocess

from django.test import SimpleTestCase, override_settings

from zabbix_api.services import zabbix_service


class ZabbixServiceTests(SimpleTestCase):
    def tearDown(self):
        zabbix_service.clear_token_cache()

    @override_settings(ZABBIX_READ_ONLY=True)
    @patch("zabbix_api.client.requests.post")
    def test_zabbix_request_blocks_write_operations(self, post_mock):
        result = zabbix_service.zabbix_request("host.create", {"name": "test"})
        self.assertIsNone(result)
        post_mock.assert_not_called()

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch(
        "zabbix_api.client.resilient_client._get_token",
        return_value="token-123",
    )
    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    @patch("zabbix_api.client.requests.post")
    def test_zabbix_request_retries_without_auth_header(
        self,
        post_mock,
        current_config_mock,
        token_mock,
    ):
        current_config_mock.return_value = SimpleNamespace(
            zabbix_api_url="http://example/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="secret",
            zabbix_api_key="",
        )

        first_response = Mock()
        first_response.raise_for_status.return_value = None
        first_response.json.return_value = {"error": {"code": -32602}}

        second_response = Mock()
        second_response.raise_for_status.return_value = None
        second_response.json.return_value = {"result": ["ok"]}

        post_mock.side_effect = [first_response, second_response]

        data = zabbix_service.zabbix_request("host.get", {"output": ["host"]})

        self.assertEqual(data, ["ok"])
        self.assertEqual(post_mock.call_count, 2)

        # first call sem Authorization; segunda chamada usa header Bearer
        first_call_kwargs = post_mock.call_args_list[0].kwargs
        second_call_kwargs = post_mock.call_args_list[1].kwargs

        self.assertNotIn("Authorization", first_call_kwargs["headers"])
        self.assertEqual(
            second_call_kwargs["headers"].get("Authorization"),
            "Bearer token-123",
        )
        self.assertEqual(token_mock.call_count, 2)

    @patch("zabbix_api.services.zabbix_service.requests.get")
    def test_get_geolocation_handles_request_exception(self, get_mock):
        get_mock.side_effect = requests.RequestException("boom")

        data = zabbix_service.get_geolocation_from_ip("8.8.8.8")

        self.assertIsNone(data)
        get_mock.assert_called_once()

    @patch("zabbix_api.services.zabbix_service.requests.get")
    def test_get_geolocation_returns_payload_when_successful(self, get_mock):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "status": "success",
            "country": "Brazil",
            "regionName": "GO",
            "city": "Goiânia",
            "lat": -16.6869,
            "lon": -49.2648,
            "isp": "Example ISP",
            "timezone": "America/Sao_Paulo",
        }
        get_mock.return_value = response

        payload = zabbix_service.get_geolocation_from_ip("8.8.4.4")

        self.assertEqual(payload["city"], "Goiânia")
        response.raise_for_status.assert_called_once()
        response.json.assert_called_once()

    @patch("zabbix_api.services.zabbix_service.subprocess.run")
    @patch(
        "zabbix_api.services.zabbix_service.platform.system",
        return_value="Linux",
    )
    def test_check_host_connectivity_handles_timeout(
        self,
        system_mock,
        run_mock,
    ):
        run_mock.side_effect = subprocess.TimeoutExpired(
            cmd=["ping"],
            timeout=5,
        )

        ok = zabbix_service.check_host_connectivity("10.0.0.1")

        self.assertFalse(ok)
        run_mock.assert_called_once()

    @patch("zabbix_api.services.zabbix_service.subprocess.run")
    @patch(
        "zabbix_api.services.zabbix_service.platform.system",
        return_value="Linux",
    )
    def test_check_host_connectivity_returns_true_for_success(
        self,
        system_mock,
        run_mock,
    ):
        run_mock.return_value = SimpleNamespace(returncode=0)

        ok = zabbix_service.check_host_connectivity("10.0.0.1")

        self.assertTrue(ok)
        run_mock.assert_called_once()
