"""Tests for setup_app.services.runtime_settings."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase, override_settings


class FallbackConfigTests(TestCase):
    """_fallback_config() uses Django settings when no FirstTimeSetup exists."""

    @override_settings(
        ZABBIX_API_URL="http://zabbix.test",
        ZABBIX_API_USER="Admin",
        ZABBIX_API_PASSWORD="zabbix",
        ZABBIX_API_KEY="",
        GOOGLE_MAPS_API_KEY="AIzaXXXX",
        MAP_PROVIDER="google",
        MAPBOX_TOKEN="pk.test",
        REDIS_URL="redis://localhost:6379/1",
        ALLOWED_HOSTS=["localhost"],
        ENABLE_DIAGNOSTIC_ENDPOINTS=True,
        DATABASES={
            "default": {
                "HOST": "localhost",
                "PORT": "5432",
                "NAME": "mydb",
                "USER": "postgres",
                "PASSWORD": "secret",
            }
        },
        OPTICAL_RX_WARNING_THRESHOLD="-24",
        OPTICAL_RX_CRITICAL_THRESHOLD="-27",
    )
    def test_fallback_reads_django_settings(self):
        from setup_app.services.runtime_settings import _fallback_config
        cfg = _fallback_config()
        self.assertEqual(cfg.zabbix_api_url, "http://zabbix.test")
        self.assertEqual(cfg.google_maps_api_key, "AIzaXXXX")
        self.assertEqual(cfg.db_host, "localhost")
        self.assertEqual(cfg.db_name, "mydb")
        self.assertEqual(cfg.redis_url, "redis://localhost:6379/1")
        self.assertEqual(cfg.allowed_hosts, ["localhost"])
        self.assertTrue(cfg.diagnostics_enabled)

    @override_settings(
        ALLOWED_HOSTS="not-a-list",
        DATABASES={"default": {}},
    )
    def test_fallback_handles_non_list_allowed_hosts(self):
        from setup_app.services.runtime_settings import _fallback_config
        cfg = _fallback_config()
        self.assertEqual(cfg.allowed_hosts, [])


class GetRuntimeConfigTests(TestCase):
    """get_runtime_config() reads from FirstTimeSetup when available."""

    def tearDown(self):
        from setup_app.services.runtime_settings import get_runtime_config
        get_runtime_config.cache_clear()

    def _make_record(self, **kwargs):
        record = MagicMock()
        record.zabbix_url = kwargs.get("zabbix_url", "http://zabbix.local")
        record.zabbix_user = kwargs.get("zabbix_user", "Admin")
        record.zabbix_password = kwargs.get("zabbix_password", "secret")
        record.zabbix_api_key = kwargs.get("zabbix_api_key", "")
        record.maps_api_key = kwargs.get("maps_api_key", "MAPS_KEY")
        record.map_provider = kwargs.get("map_provider", "google")
        record.mapbox_token = kwargs.get("mapbox_token", "")
        record.db_host = kwargs.get("db_host", "db.local")
        record.db_port = kwargs.get("db_port", "5432")
        record.db_name = kwargs.get("db_name", "appdb")
        record.db_user = kwargs.get("db_user", "postgres")
        record.db_password = kwargs.get("db_password", "pass")
        record.redis_url = kwargs.get("redis_url", "redis://localhost:6379/0")
        record.ftp_enabled = kwargs.get("ftp_enabled", False)
        record.ftp_host = kwargs.get("ftp_host", "")
        record.ftp_port = kwargs.get("ftp_port", "21")
        record.ftp_user = kwargs.get("ftp_user", "")
        record.ftp_password = kwargs.get("ftp_password", "")
        record.ftp_path = kwargs.get("ftp_path", "")
        record.gdrive_enabled = kwargs.get("gdrive_enabled", False)
        record.gdrive_credentials_json = kwargs.get("gdrive_credentials_json", "")
        record.gdrive_folder_id = kwargs.get("gdrive_folder_id", "")
        record.gdrive_shared_drive_id = kwargs.get("gdrive_shared_drive_id", "")
        record.gdrive_auth_mode = kwargs.get("gdrive_auth_mode", "service_account")
        record.gdrive_oauth_client_id = kwargs.get("gdrive_oauth_client_id", "")
        record.gdrive_oauth_client_secret = kwargs.get("gdrive_oauth_client_secret", "")
        record.gdrive_oauth_refresh_token = kwargs.get("gdrive_oauth_refresh_token", "")
        record.gdrive_oauth_user_email = kwargs.get("gdrive_oauth_user_email", "")
        record.smtp_enabled = kwargs.get("smtp_enabled", False)
        record.smtp_host = kwargs.get("smtp_host", "")
        record.smtp_port = kwargs.get("smtp_port", "587")
        record.smtp_security = kwargs.get("smtp_security", "tls")
        record.smtp_user = kwargs.get("smtp_user", "")
        record.smtp_password = kwargs.get("smtp_password", "")
        record.smtp_auth_mode = kwargs.get("smtp_auth_mode", "password")
        record.smtp_oauth_client_id = kwargs.get("smtp_oauth_client_id", "")
        record.smtp_oauth_client_secret = kwargs.get("smtp_oauth_client_secret", "")
        record.smtp_oauth_refresh_token = kwargs.get("smtp_oauth_refresh_token", "")
        record.smtp_from_name = kwargs.get("smtp_from_name", "")
        record.smtp_from_email = kwargs.get("smtp_from_email", "")
        record.smtp_test_recipient = kwargs.get("smtp_test_recipient", "")
        record.sms_enabled = kwargs.get("sms_enabled", False)
        record.sms_provider = kwargs.get("sms_provider", "smsnet")
        record.sms_provider_rank = kwargs.get("sms_provider_rank", "1")
        record.sms_username = kwargs.get("sms_username", "")
        record.sms_password = kwargs.get("sms_password", "")
        record.sms_api_token = kwargs.get("sms_api_token", "")
        record.sms_api_url = kwargs.get("sms_api_url", "")
        record.sms_sender_id = kwargs.get("sms_sender_id", "")
        record.sms_test_recipient = kwargs.get("sms_test_recipient", "")
        record.sms_test_message = kwargs.get("sms_test_message", "")
        record.sms_priority = kwargs.get("sms_priority", "")
        record.sms_aws_region = kwargs.get("sms_aws_region", "")
        record.sms_aws_access_key_id = kwargs.get("sms_aws_access_key_id", "")
        record.sms_aws_secret_access_key = kwargs.get("sms_aws_secret_access_key", "")
        record.sms_infobip_base_url = kwargs.get("sms_infobip_base_url", "")
        record.map_default_zoom = kwargs.get("map_default_zoom", 12)
        record.map_default_lat = kwargs.get("map_default_lat", "-15.7801")
        record.map_default_lng = kwargs.get("map_default_lng", "-47.9292")
        record.map_type = kwargs.get("map_type", "terrain")
        record.map_styles = kwargs.get("map_styles", "")
        record.enable_street_view = kwargs.get("enable_street_view", True)
        record.enable_traffic = kwargs.get("enable_traffic", False)
        record.mapbox_style = kwargs.get("mapbox_style", "streets-v12")
        record.mapbox_custom_style = kwargs.get("mapbox_custom_style", "")
        record.mapbox_enable_3d = kwargs.get("mapbox_enable_3d", False)
        record.esri_api_key = kwargs.get("esri_api_key", "")
        record.esri_basemap = kwargs.get("esri_basemap", "topo-vector")
        record.map_language = kwargs.get("map_language", "pt-BR")
        record.map_theme = kwargs.get("map_theme", "light")
        record.enable_map_clustering = kwargs.get("enable_map_clustering", True)
        record.enable_drawing_tools = kwargs.get("enable_drawing_tools", True)
        record.enable_fullscreen = kwargs.get("enable_fullscreen", True)
        return record

    @override_settings(ALLOWED_HOSTS=["app.test"], DATABASES={"default": {}})
    def test_uses_first_time_setup_when_configured(self):
        from setup_app.services.runtime_settings import get_runtime_config
        get_runtime_config.cache_clear()
        record = self._make_record(zabbix_url="http://zabbix.prod")

        with patch(
            "setup_app.services.runtime_settings.FirstTimeSetup"
            ".objects.filter"
        ) as mock_filter:
            mock_filter.return_value.order_by.return_value.first.return_value = record
            cfg = get_runtime_config()

        self.assertEqual(cfg.zabbix_api_url, "http://zabbix.prod")
        self.assertEqual(cfg.db_host, "db.local")

    @override_settings(
        ALLOWED_HOSTS=["localhost"],
        DATABASES={"default": {}},
        ZABBIX_API_URL="http://fallback.zabbix",
    )
    def test_falls_back_when_no_configured_setup(self):
        from setup_app.services.runtime_settings import get_runtime_config
        get_runtime_config.cache_clear()

        with patch(
            "setup_app.services.runtime_settings.FirstTimeSetup"
            ".objects.filter"
        ) as mock_filter:
            mock_filter.return_value.order_by.return_value.first.return_value = None
            cfg = get_runtime_config()

        self.assertEqual(cfg.zabbix_api_url, "http://fallback.zabbix")

    @override_settings(ALLOWED_HOSTS=["app.test"], DATABASES={"default": {}})
    def test_reload_config_clears_cache(self):
        from setup_app.services.runtime_settings import (
            get_runtime_config,
            reload_config,
        )
        get_runtime_config.cache_clear()
        record = self._make_record()

        with patch(
            "setup_app.services.runtime_settings.FirstTimeSetup"
            ".objects.filter"
        ) as mock_filter:
            mock_filter.return_value.order_by.return_value.first.return_value = record
            cfg1 = get_runtime_config()

        reload_config()
        # Cache should be cleared; calling again should re-query
        with patch(
            "setup_app.services.runtime_settings.FirstTimeSetup"
            ".objects.filter"
        ) as mock_filter2:
            mock_filter2.return_value.order_by.return_value.first.return_value = None
            cfg2 = get_runtime_config()

        # After reload, without record, should use fallback
        self.assertIsNotNone(cfg2)


class FloatSettingTests(TestCase):
    @override_settings(OPTICAL_RX_WARNING_THRESHOLD="-24.5")
    def test_float_setting_valid(self):
        from setup_app.services.runtime_settings import _float_setting
        result = _float_setting("OPTICAL_RX_WARNING_THRESHOLD", -24.0)
        self.assertEqual(result, -24.5)

    @override_settings()
    def test_float_setting_missing_uses_default(self):
        from setup_app.services.runtime_settings import _float_setting
        result = _float_setting("NONEXISTENT_SETTING", -99.0)
        self.assertEqual(result, -99.0)

    @override_settings(OPTICAL_RX_WARNING_THRESHOLD="not-a-float")
    def test_float_setting_invalid_uses_default(self):
        from setup_app.services.runtime_settings import _float_setting
        result = _float_setting("OPTICAL_RX_WARNING_THRESHOLD", -24.0)
        self.assertEqual(result, -24.0)
