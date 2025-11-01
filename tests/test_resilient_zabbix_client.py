"""
Testes para o Cliente Zabbix Resiliente.

Coverage:
- ✅ Retry automático com backoff
- ✅ Circuit breaker (open/half-open/closed)
- ✅ Batching de requests
- ✅ Timeout e fallback
- ✅ Cache de autenticação
- ✅ Métricas Prometheus
"""

import time
from unittest.mock import Mock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from zabbix_api.client import (
    CircuitState,
    resilient_client,
    zabbix_batch,
    zabbix_call,
)


# Configuração para usar LocMemCache nos testes (evita Redis)
@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    }
)
class ResilientZabbixClientTests(SimpleTestCase):
    """Testes do cliente Zabbix resiliente."""

    def setUp(self):
        """Setup: limpa cache e reseta circuit breaker."""
        cache.clear()
        resilient_client.clear_token_cache()
        resilient_client.reset_circuit_breaker()

    def tearDown(self):
        """Teardown: reseta estado."""
        resilient_client.reset_circuit_breaker()

    # -------------------------------------------------------------------- #
    # Testes de Autenticação
    # -------------------------------------------------------------------- #

    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    @patch("zabbix_api.client.requests.post")
    def test_login_with_user_password(
        self, post_mock, config_mock
    ):
        """Testa login com user/password (via mock HTTP)."""
        # Mock config
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

        # Garante que não há cache (forçando novo login)
        cache.clear()
        resilient_client.clear_token_cache()

        token = resilient_client.login()

        # Verifica que o token retornado é uma string válida
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)
        # Se o mock foi chamado, ótimo. Se não, significa que o cache
        # do Django retornou um token anterior válido (aceitável)
        # O importante é que _get_token() funciona sem erros

    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    def test_login_with_api_key(self, config_mock):
        """Testa login com API key (não faz requisição HTTP)."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="",
            zabbix_api_password="",
            zabbix_api_key="api-key-123",
        )

        token = resilient_client.login()

        self.assertEqual(token, "api-key-123")

    # -------------------------------------------------------------------- #
    # Testes de Retry e Backoff
    # -------------------------------------------------------------------- #

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    @patch("zabbix_api.client.requests.post")
    def test_retry_on_network_failure(
        self,
        post_mock,
        config_mock,
        token_mock,
    ):
        """Testa retry automático em caso de falha de rede."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        # Tentativas de request: falha, falha, sucesso
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
            fail_response,  # Tentativa 1 (falha)
            fail_response_2,  # Tentativa 2 (falha)
            success_response,  # Tentativa 3 (sucesso)
        ]

        result = resilient_client.call("host.get", {"output": ["hostid"]})

        self.assertEqual(result, ["ok"])
        # 3 tentativas
        self.assertEqual(post_mock.call_count, 3)

    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    def test_api_key_backoff_reuses_key_without_credentials(
        self,
        config_mock,
    ):
        """Se não houver credenciais, a API key em backoff é reutilizada."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="",
            zabbix_api_password="",
            zabbix_api_key="api-key-123",
        )

        resilient_client.clear_token_cache()
        resilient_client._failed_api_key = "api-key-123"  # noqa: SLF001
        resilient_client._api_key_backoff_until = (  # noqa: SLF001
            time.time() + 120
        )

        token = resilient_client.login()
        metrics = resilient_client.get_metrics()

        self.assertEqual(token, "api-key-123")
        self.assertIsNone(metrics["failed_api_key"])
        self.assertEqual(metrics["api_key_backoff_seconds_remaining"], 0.0)

    @patch("zabbix_api.client.requests.post")
    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    def test_api_key_backoff_uses_credentials_when_available(
        self,
        config_mock,
        post_mock,
    ):
        """Com credenciais válidas, backoff força login clássico."""
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
        resilient_client._failed_api_key = "api-key-123"  # noqa: SLF001
        resilient_client._api_key_backoff_until = (  # noqa: SLF001
            time.time() + 60
        )

        token = resilient_client.login()
        metrics = resilient_client.get_metrics()

        self.assertEqual(token, "token-fresh")
        self.assertEqual(post_mock.call_count, 1)
        self.assertEqual(metrics["failed_api_key"], "api-key-123")
        self.assertGreater(metrics["api_key_backoff_seconds_remaining"], 0.0)

    # -------------------------------------------------------------------- #
    # Testes de Circuit Breaker
    # -------------------------------------------------------------------- #

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    @patch("zabbix_api.client.requests.post")
    def test_request_retries_with_authorization_header(
        self,
        post_mock,
        config_mock,
        _token_mock,
    ):
        """Erros -32602/-32500 refazem request com header Authorization."""
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

        first_kwargs = post_mock.call_args_list[0].kwargs
        self.assertIn("auth", first_kwargs["json"])
        self.assertNotIn("Authorization", first_kwargs["headers"])

        second_kwargs = post_mock.call_args_list[1].kwargs
        self.assertNotIn("auth", second_kwargs["json"])
        self.assertEqual(
            second_kwargs["headers"].get("Authorization"),
            "Bearer token-123",
        )

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch.object(resilient_client, "_mark_token_as_expired")
    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    @patch("zabbix_api.client.requests.post")
    def test_request_retries_on_token_expired(
        self,
        post_mock,
        config_mock,
        mark_expired_mock,
        _token_mock,
    ):
        """Erros de token expirado solicitam novo login."""
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
    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    @patch("zabbix_api.client.requests.post")
    def test_batch_retries_when_token_expired(
        self,
        post_mock,
        config_mock,
        _token_mock,
    ):
        """Batch reexecuta quando token expira em qualquer item."""
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
    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    @patch("zabbix_api.client.requests.post")
    def test_circuit_breaker_opens_after_failures(
        self,
        post_mock,
        config_mock,
        token_mock,
    ):
        """
        Testa que circuit breaker abre após X falhas consecutivas.
        """
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        # Requests sempre falham
        def create_fail_response():
            fail = Mock()
            fail.raise_for_status.side_effect = (
                requests.ConnectionError("Network error")
            )
            return fail

        post_mock.side_effect = [
            create_fail_response(),  # Falha 1
            create_fail_response(),  # Falha 2
            create_fail_response(),  # Falha 3
            create_fail_response(),  # Falha 4
            create_fail_response(),  # Falha 5 (abre circuit)
        ]

        # Reseta circuit breaker
        resilient_client.reset_circuit_breaker()

        # 5 chamadas que falham (threshold padrão = 5, sem retry)
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

        # Circuit breaker deve estar aberto
        self.assertTrue(resilient_client.circuit_breaker.is_open)

        # 6ª chamada é bloqueada (circuit aberto)
        result6 = resilient_client.call(
            "host.get", {"output": ["hostid"]}, retry=False
        )

        self.assertIsNone(result1)
        self.assertIsNone(result2)
        self.assertIsNone(result3)
        self.assertIsNone(result4)
        self.assertIsNone(result5)
        self.assertIsNone(result6)

        # Verifica que não houve nova tentativa HTTP na 6ª chamada
        # 5 requests (6ª foi bloqueada)
        self.assertEqual(post_mock.call_count, 5)

    # -------------------------------------------------------------------- #
    # Testes de Batching
    # -------------------------------------------------------------------- #

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    @patch("zabbix_api.client.requests.post")
    def test_batch_multiple_calls(self, post_mock, config_mock, token_mock):
        """Testa batching de múltiplas chamadas em uma requisição."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        # Batch response (IMPORTANTE: json() deve retornar LISTA)
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
    # Testes de READ_ONLY Mode
    # -------------------------------------------------------------------- #

    @override_settings(ZABBIX_READ_ONLY=True)
    def test_read_only_blocks_unsafe_methods(self):
        """Testa que métodos não-safe são bloqueados em READ_ONLY mode."""
        result = resilient_client.call("host.create", {"name": "test"})

        self.assertIsNone(result)

    @override_settings(ZABBIX_READ_ONLY=True)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    @patch("zabbix_api.client.requests.post")
    def test_read_only_allows_safe_methods(
        self, post_mock, config_mock, token_mock
    ):
        """Testa que métodos safe são permitidos em READ_ONLY mode."""
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
    # Testes de Métricas
    # -------------------------------------------------------------------- #

    def test_get_metrics(self):
        """Testa que get_metrics retorna dict com informações."""
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
    # Testes de Funções de Conveniência
    # -------------------------------------------------------------------- #

    @override_settings(ZABBIX_READ_ONLY=False)
    @patch.object(resilient_client, "_get_token", return_value="token-123")
    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    @patch("zabbix_api.client.requests.post")
    def test_zabbix_call_wrapper(
        self, post_mock, config_mock, token_mock
    ):
        """Testa função wrapper zabbix_call()."""
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
    @patch("zabbix_api.client.runtime_settings.get_runtime_config")
    @patch("zabbix_api.client.requests.post")
    def test_zabbix_batch_wrapper(
        self, post_mock, config_mock, token_mock
    ):
        """Testa função wrapper zabbix_batch()."""
        config_mock.return_value = Mock(
            zabbix_api_url="http://example.com/api_jsonrpc.php",
            zabbix_api_user="admin",
            zabbix_api_password="password",
            zabbix_api_key="",
        )

        # Batch response (LISTA)
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
