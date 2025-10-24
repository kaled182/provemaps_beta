"""
Configuração do pytest para o projeto mapsprovefiber.
Inclui fixtures comuns e configurações para testes Django.
"""

import os
import tempfile
import pytest
from django.conf import settings
from django.test import override_settings
from django.core.cache import cache


def pytest_configure():
    """Configurações específicas para pytest."""
    # Garante que estamos em ambiente de teste
    settings.TESTING = True

    # Configurações adicionais para testes
    if not getattr(settings, "TEST_CONFIGURED", False):
        settings.TEST_CONFIGURED = True

    # Debug info apenas se não for CI
    if not os.getenv("CI"):
        print(f"🧪 pytest configured for {getattr(settings, 'APP_NAME', 'mapsprovefiber')}")
        print(f"📁 Settings module: {os.getenv('DJANGO_SETTINGS_MODULE')}")


def pytest_addoption(parser):
    """Adiciona opções customizadas ao pytest."""
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="Executar testes marcados como lentos",
    )
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Executar testes de integração",
    )


def pytest_collection_modifyitems(config, items):
    """Modifica a coleção de testes baseado em opções."""
    # Filtro para testes lentos
    if not config.getoption("--slow"):
        skip_slow = pytest.mark.skip(reason="Teste lento - use --slow para executar")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    # Filtro para testes de integração
    if not config.getoption("--integration"):
        skip_integration = pytest.mark.skip(
            reason="Teste de integração - use --integration para executar"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


# =============================================================================
# FIXTURES DE BANCO DE DADOS
# =============================================================================

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Habilita acesso ao banco de dados em todos os testes automaticamente."""
    yield


@pytest.fixture
def use_transactional_db(transactional_db):
    """Habilita transações reais quando necessário."""
    yield


@pytest.fixture(autouse=True)
def clear_cache():
    """Limpa o cache antes e depois de cada teste para garantir isolamento."""
    cache.clear()
    try:
        yield
    finally:
        cache.clear()


# =============================================================================
# FIXTURES DE AUTENTICAÇÃO E USUÁRIOS
# =============================================================================

@pytest.fixture
def test_user(db):
    """Cria um usuário de teste básico."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        email="test@mapsprovefiber.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def admin_user(db):
    """Cria um usuário administrador para testes."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin",
        email="admin@mapsprovefiber.com",
        password="adminpass123",
    )


@pytest.fixture
def authenticated_client(client, test_user):
    """Client Django autenticado para testes de views."""
    client.force_login(test_user)
    return client


# =============================================================================
# FIXTURES PARA TESTES DE API (DRF)
# =============================================================================

@pytest.fixture
def api_client():
    """Client para testes de API REST (DRF)."""
    try:
        from rest_framework.test import APIClient
    except Exception:
        pytest.skip("djangorestframework não está instalado")
    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, test_user):
    """API Client autenticado."""
    api_client.force_authenticate(user=test_user)
    return api_client


# =============================================================================
# FIXTURES DE SERVIÇOS EXTERNOS (MOCKS)
# =============================================================================

@pytest.fixture
def zabbix_mock(monkeypatch):
    """Mock para chamadas da API do Zabbix durante os testes."""
    def mock_zabbix_call(*args, **kwargs):
        return {"result": "mocked_response", "jsonrpc": "2.0", "id": 1}

    # tolera ausência do módulo em ambientes que não tenham a lib
    monkeypatch.setattr("zabbix_api.client.ZabbixClient._call", mock_zabbix_call, raising=False)
    return mock_zabbix_call


@pytest.fixture
def zabbix_authenticated_mock(monkeypatch, zabbix_mock):
    """Mock para Zabbix com autenticação simulada."""
    def mock_auth_call(*args, **kwargs):
        method = kwargs.get("method") or (args[0] if args else "")
        if method == "user.login":
            return {"result": "fake_auth_token_12345", "id": 1}
        return zabbix_mock(*args, **kwargs)

    monkeypatch.setattr("zabbix_api.client.ZabbixClient._call", mock_auth_call, raising=False)
    return mock_auth_call


@pytest.fixture
def maps_api_mock():
    """Mock para APIs de mapas/geolocalização."""
    from unittest.mock import patch

    with patch("maps_view.services.GeocodingService.geocode") as mock_geocode:
        mock_geocode.return_value = {
            "lat": -1.4557,
            "lng": -48.4902,
            "address": "Belém, PA, Brasil",
            "formatted_address": "Belém, State of Pará, Brazil",
        }
        yield mock_geocode


@pytest.fixture
def redis_mock(monkeypatch):
    """Mock para operações de cache como se fosse Redis (em memória)."""
    store = {}

    def mock_get(key, default=None):
        return store.get(key, default)

    def mock_set(key, value, timeout=None):
        store[key] = value
        return True

    def mock_delete(key):
        return store.pop(key, None) is not None

    def mock_clear():
        store.clear()

    # Monkeypatch diretamente o cache resolvido
    monkeypatch.setattr(cache, "get", mock_get, raising=False)
    monkeypatch.setattr(cache, "set", mock_set, raising=False)
    monkeypatch.setattr(cache, "delete", mock_delete, raising=False)
    monkeypatch.setattr(cache, "clear", mock_clear, raising=False)
    return store


# =============================================================================
# FIXTURES DE CONFIGURAÇÃO
# =============================================================================

@pytest.fixture
def debug_settings():
    """Fixture para testes que precisam de DEBUG=True."""
    with override_settings(DEBUG=True):
        yield


@pytest.fixture
def production_settings():
    """Fixture para testes que simulam ambiente de produção."""
    with override_settings(
        DEBUG=False,
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
    ):
        yield


@pytest.fixture
def temp_media_root():
    """Fixture para testes com upload de arquivos."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with override_settings(MEDIA_ROOT=temp_dir):
            yield temp_dir


# =============================================================================
# FIXTURES PARA TESTES DE PERFORMANCE
# =============================================================================

@pytest.fixture
def benchmark(request):
    """Fixture para testes de benchmark (requer pytest-benchmark)."""
    try:
        return request.getfixturevalue("benchmark")
    except pytest.FixtureLookupError:
        pytest.skip("pytest-benchmark não está instalado")


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup/teardown automático para todos os testes."""
    original_debug = settings.DEBUG
    try:
        yield
    finally:
        settings.DEBUG = original_debug


# =============================================================================
# FIXTURES PARA CELERY
# =============================================================================

@pytest.fixture
def celery_app():
    """Fixture para testes com Celery."""
    try:
        from core.celery_app import app as celery_app_instance
    except Exception:
        pytest.skip("Celery não está configurado (core.celery_app ausente)")
    # Modo síncrono em testes
    celery_app_instance.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
    return celery_app_instance
