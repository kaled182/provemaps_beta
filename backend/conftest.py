"""
Pytest configuration for the mapsprovefiber project.
Includes shared fixtures and Django test configuration.
"""

import importlib
import os
import tempfile
import pytest
from collections.abc import Iterator
from typing import Any
from django.conf import settings
from django.test import override_settings
from django.core.cache import cache


def pytest_configure() -> None:
    """Project-specific pytest configuration."""
    # Ensure tests run under the explicit testing flag
    settings.TESTING = True

    # Additional test configuration
    if not getattr(settings, "TEST_CONFIGURED", False):
        settings.TEST_CONFIGURED = True

    # Emit debug info only outside CI
    if not os.getenv("CI"):
        app_name = getattr(settings, "APP_NAME", "mapsprovefiber")
        settings_module = os.getenv("DJANGO_SETTINGS_MODULE")
        print(f"[pytest] configured for {app_name}")
        print(f"[pytest] settings module: {settings_module}")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register custom command-line options for pytest."""
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="Run tests marked as slow",
    )
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Modify test collection based on custom command-line options."""
    # Skip slow tests unless --slow is provided
    if not config.getoption("--slow"):
        skip_slow = pytest.mark.skip(reason="Slow test - add --slow flag")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    # Skip integration tests unless --integration is provided
    if not config.getoption("--integration"):
        skip_integration = pytest.mark.skip(
            reason="Integration test - use --integration to include it"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db: None) -> Iterator[None]:
    """Enable database access automatically for every test."""
    yield


@pytest.fixture
def use_transactional_db(transactional_db: None) -> Iterator[None]:
    """Provide transactional database access when a test requires it."""
    yield


@pytest.fixture(autouse=True)
def clear_cache() -> Iterator[None]:
    """Clear cache before and after each test to guarantee isolation.
    Redis connection failures are ignored so tests can run without Redis.
    """
    try:
        cache.clear()
    except Exception:
        pass  # Ignore cache failures (useful when Redis is offline)
    
    try:
        yield
    finally:
        try:
            cache.clear()
        except Exception:
            pass  # Ignore cache failures during teardown


# =============================================================================
# AUTHENTICATION AND USER FIXTURES
# =============================================================================

@pytest.fixture
def test_user(db: None) -> Any:
    """Create a basic test user."""
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
def admin_user(db: None) -> Any:
    """Create an administrative test user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin",
        email="admin@mapsprovefiber.com",
        password="adminpass123",
    )


@pytest.fixture
def authenticated_client(client: Any, test_user: Any) -> Any:
    """Return a Django test client authenticated with the test user."""
    client.force_login(test_user)
    return client


# =============================================================================
# API (DRF) FIXTURES
# =============================================================================

@pytest.fixture
def api_client() -> Any:
    """Return a Django REST Framework API client for tests."""
    try:
        drf_test = importlib.import_module(
            "rest_framework.test"
        )  # type: ignore[import-not-found]
        api_client_cls = getattr(  # type: ignore[attr-defined]
            drf_test,
            "APIClient",
        )
    except Exception:
        pytest.skip("djangorestframework is not installed")
    return api_client_cls()


@pytest.fixture
def authenticated_api_client(api_client: Any, test_user: Any) -> Any:
    """Return an authenticated DRF API client."""
    api_client.force_authenticate(user=test_user)
    return api_client


# =============================================================================
# EXTERNAL SERVICE MOCK FIXTURES
# =============================================================================

@pytest.fixture
def zabbix_mock(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Mock Zabbix API calls during tests."""
    def mock_zabbix_call(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"result": "mocked_response", "jsonrpc": "2.0", "id": 1}

    # Tolerate missing module in environments without the dependency
    monkeypatch.setattr(
        "integrations.zabbix.client.resilient_client.call",
        mock_zabbix_call,
        raising=False,
    )
    return mock_zabbix_call


@pytest.fixture
def zabbix_authenticated_mock(
    monkeypatch: pytest.MonkeyPatch,
    zabbix_mock: Any,
) -> Any:
    """Mock Zabbix calls including simulated authentication."""
    def mock_auth_call(*args: Any, **kwargs: Any) -> dict[str, Any]:
        method = kwargs.get("method") or (args[0] if args else "")
        if method == "user.login":
            return {"result": "fake_auth_token_12345", "id": 1}
        return zabbix_mock(*args, **kwargs)

    monkeypatch.setattr(
        "integrations.zabbix.client.resilient_client.call",
        mock_auth_call,
        raising=False,
    )
    return mock_auth_call


@pytest.fixture
def maps_api_mock() -> Iterator[Any]:
    """Mock geocoding and mapping service calls."""
    from unittest.mock import patch

    with patch("maps_view.services.GeocodingService.geocode") as mock_geocode:
        mock_geocode.return_value = {
            "lat": -1.4557,
            "lng": -48.4902,
            "address": "Belem, PA, Brazil",
            "formatted_address": "Belem, State of Para, Brazil",
        }
        yield mock_geocode


@pytest.fixture
def redis_mock(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Mock Redis-like cache operations with an in-memory store."""
    store: dict[str, Any] = {}

    def mock_get(key: str, default: Any | None = None) -> Any | None:
        return store.get(key, default)

    def mock_set(key: str, value: Any, timeout: int | None = None) -> bool:
        store[key] = value
        return True

    def mock_delete(key: str) -> bool:
        return store.pop(key, None) is not None

    def mock_clear() -> None:
        store.clear()

    # Monkeypatch the resolved cache object directly
    monkeypatch.setattr(cache, "get", mock_get, raising=False)
    monkeypatch.setattr(cache, "set", mock_set, raising=False)
    monkeypatch.setattr(cache, "delete", mock_delete, raising=False)
    monkeypatch.setattr(cache, "clear", mock_clear, raising=False)
    return store


# =============================================================================
# CONFIGURATION FIXTURES
# =============================================================================

@pytest.fixture
def debug_settings() -> Iterator[None]:
    """Fixture for tests that require DEBUG=True."""
    with override_settings(DEBUG=True):
        yield


@pytest.fixture
def production_settings() -> Iterator[None]:
    """Fixture for tests that emulate production settings."""
    with override_settings(
        DEBUG=False,
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
    ):
        yield


@pytest.fixture
def temp_media_root() -> Iterator[str]:
    """Fixture for tests that need a temporary media directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with override_settings(MEDIA_ROOT=temp_dir):
            yield temp_dir


# =============================================================================
# PERFORMANCE TEST FIXTURES
# =============================================================================

@pytest.fixture
def benchmark(request: pytest.FixtureRequest) -> Any:
    """Fixture for benchmark-style tests (requires pytest-benchmark)."""
    try:
        return request.getfixturevalue("benchmark")
    except pytest.FixtureLookupError:
        pytest.skip("pytest-benchmark is not installed")


@pytest.fixture(autouse=True)
def setup_test_environment() -> Iterator[None]:
    """Automatic setup and teardown for every test."""
    original_debug = settings.DEBUG
    try:
        yield
    finally:
        settings.DEBUG = original_debug


# =============================================================================
# CELERY FIXTURES
# =============================================================================

@pytest.fixture
def celery_app() -> Any:
    """Fixture for tests that exercise Celery tasks."""
    try:
        from core.celery_app import app as celery_app_instance
    except Exception:
        pytest.skip("Celery is not configured (missing core.celery_app)")
    # Run Celery tasks synchronously during tests
    celery_app_instance.conf.update(  # type: ignore[attr-defined]
        task_always_eager=True,
        task_eager_propagates=True,
    )
    return celery_app_instance
