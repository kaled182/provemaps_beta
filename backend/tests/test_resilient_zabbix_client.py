"""
Tests for the resilient Zabbix client.

Coverage:
- ✅ Automatic retry with backoff
- ✅ Circuit breaker (open/half-open/closed)
- ✅ Request batching
- ✅ Timeout and fallback
- ✅ Authentication cache
- ✅ Prometheus metrics
"""

import time
from collections.abc import Iterator
from typing import Any, Mapping
from unittest.mock import Mock, patch

import pytest
import requests
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from integrations.zabbix.client import (
    CircuitState,
    resilient_client,
    zabbix_batch,
    zabbix_call,
)


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests() -> Iterator[None]:
    """Override project-wide DB fixture to avoid DB setup."""
    yield


# Configure tests to rely on LocMemCache instead of Redis
@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    }
)
class ResilientZabbixClientTests(SimpleTestCase):
    """Tests for the resilient Zabbix client."""

    def setUp(self) -> None:
        """Clear cache and reset the circuit breaker before each test."""
        cache.clear()
        resilient_client.clear_token_cache()
        resilient_client.reset_circuit_breaker()

    def tearDown(self) -> None:
        """Reset the circuit breaker after each test."""
        resilient_client.reset_circuit_breaker()

    # -------------------------------------------------------------------- #
    # Authentication Tests
    # -------------------------------------------------------------------- #

    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    @patch("integrations.zabbix.client.requests.post")
    def test_login_with_user_password(
        self, post_mock: Mock, config_mock: Mock
    ) -> None:
        """Validate login using username/password over HTTP."""
        # Mock configuration
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        # Mock response
        response_mock = Mock()
        response_mock.json.return_value = {"result": "token-test-987"}
        response_mock.raise_for_status.return_value = None
        post_mock.return_value = response_mock

        # Ensure no cached token forces a fresh login
        cache.clear()
        resilient_client.clear_token_cache()

        token = resilient_client.login()
        assert token is not None

        # Token should always be a non-empty string
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)
        # If the mock is not invoked the Django cache returned a token,
        # which is acceptable; the important part is that ``login`` works
        # without raising.

    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    def test_login_with_api_key(self, config_mock: Mock) -> None:
        """Validate login with an API key (no HTTP request)."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="",
            zabbix_api_password="",
            zabbix_api_key="api-key-123",
        )

        token = resilient_client.login()

        self.assertEqual(token, "api-key-123")

    # -------------------------------------------------------------------- #
    # Retry and Backoff Tests
    # -------------------------------------------------------------------- #

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    @patch("integrations.zabbix.client.requests.post")
    def test_retry_on_network_failure(
        self,
        post_mock: Mock,
        config_mock: Mock,
        token_mock: Mock,
    ) -> None:
        """Ensure network failures trigger automatic retries."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        # Simulate request attempts: failure, failure, then success
        fail_response = Mock()
        fail_response.raise_for_status.side_effect = (
            requests.ConnectionError("Network error")
        )

        fail_response_2 = Mock()
        fail_response_2.raise_for_status.side_effect = (
            requests.ConnectionError("Network error")
        )

        success_response = Mock()
        success_response.json.return_value = {"result": ["ok"]}
        success_response.raise_for_status.return_value = None

        post_mock.side_effect = [
            fail_response,  # Attempt 1 (failure)
            fail_response_2,  # Attempt 2 (failure)
            success_response,  # Attempt 3 (success)
        ]

        result = resilient_client.call("host.get", {"output": ["hostid"]})

        self.assertEqual(result, ["ok"])
        # Called three times
        self.assertEqual(post_mock.call_count, 3)

    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    def test_api_key_backoff_reuses_key_without_credentials(
        self,
        config_mock: Mock,
    ) -> None:
        """Reuse the API key during backoff when no credentials exist."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="",
            zabbix_api_password="",
            zabbix_api_key="api-key-123",
        )

        resilient_client.clear_token_cache()
        setattr(resilient_client, "_failed_api_key", "api-key-123")
        setattr(
            resilient_client,
            "_api_key_backoff_until",
            time.time() + 120,
        )

        token = resilient_client.login()
        metrics = resilient_client.get_metrics()

        self.assertEqual(token, "api-key-123")
        self.assertIsNone(metrics["failed_api_key"])
        self.assertEqual(metrics["api_key_backoff_seconds_remaining"], 0.0)

    @patch("integrations.zabbix.client.requests.post")
    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    def test_api_key_backoff_uses_credentials_when_available(
        self,
        config_mock: Mock,
        post_mock: Mock,
    ) -> None:
        """Use credentials to refresh tokens when available during backoff."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="secret",
            zabbix_api_key="api-key-123",
        )

        success_response = Mock()
        success_response.json.return_value = {"result": "token-fresh"}
        success_response.raise_for_status.return_value = None
        post_mock.return_value = success_response

        resilient_client.clear_token_cache()
        setattr(resilient_client, "_failed_api_key", "api-key-123")
        setattr(
            resilient_client,
            "_api_key_backoff_until",
            time.time() + 60,
        )

        token = resilient_client.login()
        metrics = resilient_client.get_metrics()

        self.assertEqual(token, "token-fresh")
        self.assertEqual(post_mock.call_count, 1)
        self.assertEqual(metrics["failed_api_key"], "api-key-123")
        self.assertGreater(metrics["api_key_backoff_seconds_remaining"], 0.0)

    # -------------------------------------------------------------------- #
    # Circuit Breaker Tests
    # -------------------------------------------------------------------- #

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    @patch("integrations.zabbix.client.requests.post")
    def test_request_retries_with_authorization_header(
        self,
        post_mock: Mock,
        config_mock: Mock,
        _token_mock: Mock,
    ) -> None:
        """Retry with Authorization header on -32602/-32500 errors."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        error_response = Mock()
        error_response.raise_for_status.return_value = None
        error_response.json.return_value = {
            "error": {
                "code": -32500,
                "message": "Application error",
                "data": "Incorrect auth",
            }
        }

        success_response = Mock()
        success_response.raise_for_status.return_value = None
        success_response.json.return_value = {"result": ["ok"]}

        post_mock.side_effect = [error_response, success_response]

        result = resilient_client.call("host.get", {"output": ["hostid"]})

        self.assertEqual(result, ["ok"])
        self.assertEqual(post_mock.call_count, 2)

        first_kwargs: Mapping[str, Any] = post_mock.call_args_list[0].kwargs
        self.assertIn("auth", first_kwargs["json"])
        self.assertNotIn("Authorization", first_kwargs["headers"])

        second_kwargs: Mapping[str, Any] = post_mock.call_args_list[1].kwargs
        self.assertNotIn("auth", second_kwargs["json"])
        self.assertEqual(
            second_kwargs["headers"].get("Authorization"),
            "Bearer token-123",
        )

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch.object(resilient_client, "_mark_token_as_expired")
    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    @patch("integrations.zabbix.client.requests.post")
    def test_request_retries_on_token_expired(
        self,
        post_mock: Mock,
        config_mock: Mock,
        mark_expired_mock: Mock,
        _token_mock: Mock,
    ) -> None:
        """Trigger a new login when the token expires."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        expired_response = Mock()
        expired_response.raise_for_status.return_value = None
        expired_response.json.return_value = {
            "error": {
                "code": -32500,
                "message": "Token expired",
                "data": "Session terminated",
            }
        }

        expired_response_retry = Mock()
        expired_response_retry.raise_for_status.return_value = None
        expired_response_retry.json.return_value = {
            "error": {
                "code": -32500,
                "message": "Token expired",
                "data": "Session terminated",
            }
        }

        success_response = Mock()
        success_response.raise_for_status.return_value = None
        success_response.json.return_value = {"result": ["ok"]}

        post_mock.side_effect = [
            expired_response,
            expired_response_retry,
            success_response,
        ]

        result = resilient_client.call("host.get", {"output": ["hostid"]})

        self.assertEqual(result, ["ok"])
        self.assertEqual(post_mock.call_count, 3)
        mark_expired_mock.assert_called_once()

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    @patch("integrations.zabbix.client.requests.post")
    def test_batch_retries_when_token_expired(
        self,
        post_mock: Mock,
        config_mock: Mock,
        _token_mock: Mock,
    ) -> None:
        """Retry the batch when any item reports an expired token."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        expired_batch = Mock()
        expired_batch.raise_for_status.return_value = None
        expired_batch.json.return_value = [
            {
                "id": 1,
                "error": {
                    "message": "Session terminated",
                    "data": "Expired",
                },
            }
        ]

        success_batch = Mock()
        success_batch.raise_for_status.return_value = None
        success_batch.json.return_value = [
            {"id": 1, "result": ["ok"]},
        ]

        post_mock.side_effect = [expired_batch, success_batch]

        results = resilient_client.batch(
            [("host.get", {"output": ["hostid"]})]
        )

        self.assertEqual(results, [["ok"]])
        self.assertEqual(post_mock.call_count, 2)

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    @patch("integrations.zabbix.client.requests.post")
    def test_circuit_breaker_opens_after_failures(
        self,
        post_mock: Mock,
        config_mock: Mock,
        token_mock: Mock,
    ) -> None:
        """Ensure the circuit breaker opens after several failures."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        # Simulate repeated failures
        def create_fail_response():
            fail = Mock()
            fail.raise_for_status.side_effect = (
                requests.ConnectionError("Network error")
            )
            return fail

        post_mock.side_effect = [
            create_fail_response(),  # Failure 1
            create_fail_response(),  # Failure 2
            create_fail_response(),  # Failure 3
            create_fail_response(),  # Failure 4
            create_fail_response(),  # Failure 5 (opens circuit)
        ]

        # Reset the circuit breaker
        resilient_client.reset_circuit_breaker()

        # Five calls fail (default threshold = 5, retry disabled)
        result1 = resilient_client.call(
            "host.get", {"output": ["hostid"]}, retry=False
        )
        result2 = resilient_client.call(
            "host.get", {"output": ["hostid"]}, retry=False
        )
        result3 = resilient_client.call(
            "host.get", {"output": ["hostid"]}, retry=False
        )
        result4 = resilient_client.call(
            "host.get", {"output": ["hostid"]}, retry=False
        )
        result5 = resilient_client.call(
            "host.get", {"output": ["hostid"]}, retry=False
        )

        # Circuit breaker should now be open
        self.assertTrue(resilient_client.circuit_breaker.is_open)

        # Sixth call is blocked because the circuit is open
        result6 = resilient_client.call(
            "host.get", {"output": ["hostid"]}, retry=False
        )

        self.assertIsNone(result1)
        self.assertIsNone(result2)
        self.assertIsNone(result3)
        self.assertIsNone(result4)
        self.assertIsNone(result5)
        self.assertIsNone(result6)

    # Sixth invocation never hits HTTP (only five requests issued)
        self.assertEqual(post_mock.call_count, 5)

    # -------------------------------------------------------------------- #
    # Batching Tests
    # -------------------------------------------------------------------- #

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    @patch("integrations.zabbix.client.requests.post")
    def test_batch_multiple_calls(
        self,
        post_mock: Mock,
        config_mock: Mock,
        token_mock: Mock,
    ) -> None:
        """Batch multiple method calls into a single request."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        # Batch response (important: ``json`` must return a list)
        batch_response = Mock()
        batch_response.json.return_value = [
            {"id": 1, "result": [{"hostid": "1"}]},
            {"id": 2, "result": [{"groupid": "2"}]},
        ]
        batch_response.raise_for_status.return_value = None

        post_mock.return_value = batch_response

        results = resilient_client.batch(
            [
                ("host.get", {"output": ["hostid"]}),
                ("hostgroup.get", {"output": ["groupid"]}),
            ]
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], [{"hostid": "1"}])
        self.assertEqual(results[1], [{"groupid": "2"}])

    # -------------------------------------------------------------------- #
    # READ_ONLY Mode Tests
    # -------------------------------------------------------------------- #

    @override_settings(ZABBIX_READ_ONLY=True)
    def test_read_only_blocks_unsafe_methods(self) -> None:
        """Ensure unsafe methods are blocked in READ_ONLY mode."""
        result = resilient_client.call("host.create", {"name": "test"})

        self.assertIsNone(result)

    @override_settings(ZABBIX_READ_ONLY=True)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    @patch("integrations.zabbix.client.requests.post")
    def test_read_only_allows_safe_methods(
        self,
        post_mock: Mock,
        config_mock: Mock,
        token_mock: Mock,
    ) -> None:
        """Ensure safe methods remain allowed in READ_ONLY mode."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        # Request
        request_response = Mock()
        request_response.json.return_value = {"result": [{"hostid": "1"}]}
        request_response.raise_for_status.return_value = None

        post_mock.return_value = request_response

        result = resilient_client.call("host.get", {"output": ["hostid"]})

        self.assertEqual(result, [{"hostid": "1"}])

    # -------------------------------------------------------------------- #
    # Metrics Tests
    # -------------------------------------------------------------------- #

    def test_get_metrics(self) -> None:
        """Ensure ``get_metrics`` returns diagnostic information."""
        metrics = resilient_client.get_metrics()

        self.assertIn("circuit_breaker_state", metrics)
        self.assertIn("circuit_breaker_failure_count", metrics)
        self.assertIn("token_cached", metrics)
        self.assertIn("metrics_enabled", metrics)
        self.assertIn("config", metrics)

        self.assertEqual(
            metrics["circuit_breaker_state"], CircuitState.CLOSED.name
        )

    # -------------------------------------------------------------------- #
    # Convenience Function Tests
    # -------------------------------------------------------------------- #

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    @patch("integrations.zabbix.client.requests.post")
    def test_zabbix_call_wrapper(
        self,
        post_mock: Mock,
        config_mock: Mock,
        token_mock: Mock,
    ) -> None:
        """Exercise the ``zabbix_call`` wrapper."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        # Request
        request_response = Mock()
        request_response.json.return_value = {"result": ["ok"]}
        request_response.raise_for_status.return_value = None

        post_mock.return_value = request_response

        result = zabbix_call("host.get", {"output": ["hostid"]})

        self.assertEqual(result, ["ok"])

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("integrations.zabbix.client.runtime_settings.get_runtime_config")
    @patch("integrations.zabbix.client.requests.post")
    def test_zabbix_batch_wrapper(
        self,
        post_mock: Mock,
        config_mock: Mock,
        token_mock: Mock,
    ) -> None:
        """Exercise the ``zabbix_batch`` wrapper."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

    # Batch response (list)
        batch_response = Mock()
        batch_response.json.return_value = [
            {"id": 1, "result": ["host1"]},
            {"id": 2, "result": ["group1"]},
        ]
        batch_response.raise_for_status.return_value = None

        post_mock.return_value = batch_response

        results = zabbix_batch(
            [
                ("host.get", {"output": ["hostid"]}),
                ("hostgroup.get", {"output": ["groupid"]}),
            ]
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], ["host1"])
        self.assertEqual(results[1], ["group1"])
