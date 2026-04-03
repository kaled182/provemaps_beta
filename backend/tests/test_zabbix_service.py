from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import requests
import subprocess

from django.test import SimpleTestCase, override_settings

from integrations.zabbix import zabbix_service


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests() -> Iterator[None]:
    """Override project-wide DB fixture to keep tests DB-free."""
    yield


class ZabbixServiceTests(SimpleTestCase):
    def tearDown(self) -> None:
        zabbix_service.clear_token_cache()

    @override_settings(ZABBIX_READ_ONLY=True)
    @patch("integrations.zabbix.client.requests.post")
    def test_zabbix_request_blocks_write_operations(
        self,
        post_mock: Mock,
    ) -> None:
        result = zabbix_service.zabbix_request("host.create", {"name": "test"})
        self.assertIsNone(result)
        post_mock.assert_not_called()

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch(
        "integrations.zabbix.client.resilient_client._get_token",
        return_value="token-123",
    )
    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    @patch("integrations.zabbix.client.requests.post")
    def test_zabbix_request_retries_without_auth_header(
        self,
        post_mock: Mock,
        current_config_mock: Mock,
        token_mock: Mock,
    ) -> None:
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

        # First call omits Authorization header; the second uses a Bearer token
        first_call_kwargs = post_mock.call_args_list[0].kwargs
        second_call_kwargs = post_mock.call_args_list[1].kwargs

        self.assertNotIn("Authorization", first_call_kwargs["headers"])
        self.assertEqual(
            second_call_kwargs["headers"].get("Authorization"),
            "Bearer token-123",
        )
        self.assertEqual(token_mock.call_count, 2)

    @patch("integrations.zabbix.zabbix_service.requests.get")
    def test_get_geolocation_handles_request_exception(
        self,
        get_mock: Mock,
    ) -> None:
        get_mock.side_effect = requests.RequestException("boom")

        data = zabbix_service.get_geolocation_from_ip("8.8.8.8")

        self.assertIsNone(data)
        get_mock.assert_called_once()

    @patch("integrations.zabbix.zabbix_service.requests.get")
    def test_get_geolocation_returns_payload_when_successful(
        self,
        get_mock: Mock,
    ) -> None:
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

        assert payload is not None
        self.assertEqual(payload["city"], "Goiânia")
        response.raise_for_status.assert_called_once()
        response.json.assert_called_once()

    @patch("integrations.zabbix.zabbix_service.subprocess.run")
    @patch(
        "integrations.zabbix.zabbix_service.platform.system",
        return_value="Linux",
    )
    def test_check_host_connectivity_handles_timeout(
        self,
        _system_mock: Mock,
        run_mock: Mock,
    ) -> None:
        run_mock.side_effect = subprocess.TimeoutExpired(
            cmd=["ping"],
            timeout=5,
        )

        ok = zabbix_service.check_host_connectivity("10.0.0.1")

        self.assertFalse(ok)
        run_mock.assert_called_once()

    @patch("integrations.zabbix.zabbix_service.subprocess.run")
    @patch(
        "integrations.zabbix.zabbix_service.platform.system",
        return_value="Linux",
    )
    def test_check_host_connectivity_returns_true_for_success(
        self,
        _system_mock: Mock,
        run_mock: Mock,
    ) -> None:
        run_mock.return_value = SimpleNamespace(returncode=0)

        ok = zabbix_service.check_host_connectivity("10.0.0.1")

        self.assertTrue(ok)
        run_mock.assert_called_once()
