"""Tests for setup_app.runtime_settings (root-level module, not services/)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings


class RuntimeSettingsGetAttrTests(TestCase):
    def setUp(self):
        # Clear lru_cache before each test
        from setup_app.runtime_settings import _get_cached_config
        _get_cached_config.cache_clear()

    def tearDown(self):
        from setup_app.runtime_settings import _get_cached_config
        _get_cached_config.cache_clear()

    @override_settings(ZABBIX_API_URL="http://django.setting")
    def test_returns_django_setting_when_set(self):
        from setup_app.runtime_settings import runtime_settings
        result = runtime_settings.ZABBIX_API_URL
        self.assertEqual(result, "http://django.setting")

    def test_falls_back_to_runtime_config(self):
        from setup_app.runtime_settings import runtime_settings, _get_cached_config
        _get_cached_config.cache_clear()
        mock_config = {"SOME_RUNTIME_KEY": "runtime-value"}
        with patch("setup_app.runtime_settings.get_runtime_config", return_value=mock_config):
            _get_cached_config.cache_clear()
            with patch("setup_app.runtime_settings._get_cached_config", return_value=mock_config):
                result = runtime_settings.SOME_RUNTIME_KEY
        self.assertEqual(result, "runtime-value")

    def test_reload_config_clears_cache(self):
        from setup_app.runtime_settings import runtime_settings, _get_cached_config
        _get_cached_config.cache_clear()
        # Call once to populate cache
        with patch("setup_app.runtime_settings.get_runtime_config", return_value={}):
            _get_cached_config.cache_clear()
        # reload_config should not raise
        runtime_settings.reload_config()


class RuntimeSettingsHelperFunctionsTests(TestCase):
    def setUp(self):
        from setup_app.runtime_settings import _get_cached_config
        _get_cached_config.cache_clear()

    def tearDown(self):
        from setup_app.runtime_settings import _get_cached_config
        _get_cached_config.cache_clear()

    def test_get_zabbix_url_returns_string(self):
        from setup_app.runtime_settings import get_zabbix_url
        with patch("setup_app.runtime_settings.get_config_value", return_value="http://zabbix.test"):
            result = get_zabbix_url()
        self.assertEqual(result, "http://zabbix.test")

    def test_get_zabbix_url_default_empty(self):
        from setup_app.runtime_settings import get_zabbix_url
        with patch("setup_app.runtime_settings.get_config_value", return_value=""):
            result = get_zabbix_url()
        self.assertEqual(result, "")

    def test_get_zabbix_api_key(self):
        from setup_app.runtime_settings import get_zabbix_api_key
        with patch("setup_app.runtime_settings.get_config_value", return_value="mytoken"):
            result = get_zabbix_api_key()
        self.assertEqual(result, "mytoken")

    def test_get_zabbix_user(self):
        from setup_app.runtime_settings import get_zabbix_user
        with patch("setup_app.runtime_settings.get_config_value", return_value="Admin"):
            result = get_zabbix_user()
        self.assertEqual(result, "Admin")

    def test_get_zabbix_password(self):
        from setup_app.runtime_settings import get_zabbix_password
        with patch("setup_app.runtime_settings.get_config_value", return_value="secret"):
            result = get_zabbix_password()
        self.assertEqual(result, "secret")

    def test_get_google_maps_api_key(self):
        from setup_app.runtime_settings import get_google_maps_api_key
        with patch("setup_app.runtime_settings.get_config_value", return_value="AIzaXXXX"):
            result = get_google_maps_api_key()
        self.assertEqual(result, "AIzaXXXX")
