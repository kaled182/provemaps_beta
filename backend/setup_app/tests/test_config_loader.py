"""Tests for setup_app.services.config_loader."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from django.test import TestCase


class GetRuntimeConfigTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def tearDown(self):
        from django.core.cache import cache
        cache.clear()

    def test_returns_cached_value_when_available(self):
        from django.core.cache import cache
        from setup_app.services.config_loader import get_runtime_config, _CONFIG_CACHE_KEY
        cache.set(_CONFIG_CACHE_KEY, {"ZABBIX_API_URL": "http://cached"}, 60)
        result = get_runtime_config()
        self.assertEqual(result.get("ZABBIX_API_URL"), "http://cached")

    def test_loads_from_database_when_cache_miss(self):
        from setup_app.services.config_loader import get_runtime_config
        with patch(
            "setup_app.services.config_loader.FirstTimeSetup.objects.filter"
        ) as mock_filter:
            mock_filter.return_value.order_by.return_value.first.return_value = None
            result = get_runtime_config()
        self.assertIsInstance(result, dict)

    def test_stores_config_in_cache(self):
        from django.core.cache import cache
        from setup_app.services.config_loader import get_runtime_config, _CONFIG_CACHE_KEY
        mock_record = MagicMock()
        mock_record.zabbix_url = "http://db.zabbix"
        mock_record.auth_type = "token"
        mock_record.zabbix_api_key = "key123"
        mock_record.maps_api_key = ""
        mock_record.db_host = ""
        mock_record.db_port = ""
        mock_record.db_name = ""
        mock_record.db_user = ""
        mock_record.db_password = ""
        mock_record.redis_url = ""
        mock_record.ftp_enabled = None
        mock_record.ftp_host = ""
        mock_record.ftp_port = ""
        mock_record.ftp_user = ""
        mock_record.ftp_password = ""
        mock_record.ftp_path = ""
        mock_record.gdrive_enabled = None
        mock_record.gdrive_credentials_json = ""
        mock_record.gdrive_folder_id = ""
        mock_record.gdrive_shared_drive_id = ""
        mock_record.gdrive_auth_mode = ""
        mock_record.gdrive_oauth_client_id = ""
        mock_record.gdrive_oauth_client_secret = ""
        mock_record.gdrive_oauth_refresh_token = ""
        mock_record.gdrive_oauth_user_email = ""
        mock_record.smtp_enabled = None
        mock_record.smtp_host = ""
        mock_record.smtp_port = ""
        mock_record.smtp_security = ""
        mock_record.smtp_user = ""
        mock_record.smtp_password = ""
        mock_record.smtp_auth_mode = ""
        mock_record.smtp_oauth_client_id = ""
        mock_record.smtp_oauth_client_secret = ""
        mock_record.smtp_oauth_refresh_token = ""
        mock_record.smtp_from_name = ""
        mock_record.smtp_from_email = ""
        mock_record.smtp_test_recipient = ""
        mock_record.sms_enabled = None
        mock_record.sms_provider = ""
        mock_record.sms_provider_rank = ""
        mock_record.sms_username = ""
        mock_record.sms_password = ""
        mock_record.sms_api_token = ""
        mock_record.sms_api_url = ""
        mock_record.sms_sender_id = ""
        mock_record.sms_test_recipient = ""
        mock_record.sms_test_message = ""
        mock_record.sms_priority = ""
        mock_record.sms_aws_region = ""
        mock_record.sms_aws_access_key_id = ""
        mock_record.sms_aws_secret_access_key = ""
        mock_record.sms_infobip_base_url = ""
        mock_record.map_provider = ""
        mock_record.mapbox_token = ""
        mock_record.map_default_zoom = None
        mock_record.map_default_lat = None
        mock_record.map_default_lng = None
        mock_record.map_type = ""
        mock_record.map_styles = ""
        mock_record.enable_street_view = None
        mock_record.enable_traffic = None
        mock_record.mapbox_style = ""
        mock_record.mapbox_custom_style = ""
        mock_record.mapbox_enable_3d = None
        mock_record.esri_api_key = ""
        mock_record.esri_basemap = ""
        mock_record.map_language = ""
        mock_record.map_theme = ""
        mock_record.enable_map_clustering = None
        mock_record.enable_drawing_tools = None
        mock_record.enable_fullscreen = None

        with patch(
            "setup_app.services.config_loader.FirstTimeSetup.objects.filter"
        ) as mock_filter:
            mock_filter.return_value.order_by.return_value.first.return_value = mock_record
            result = get_runtime_config()

        cached = cache.get(_CONFIG_CACHE_KEY)
        self.assertIsNotNone(cached)
        self.assertEqual(result.get("ZABBIX_API_URL"), "http://db.zabbix")


class ClearRuntimeConfigCacheTests(TestCase):
    def test_clears_cache(self):
        from django.core.cache import cache
        from setup_app.services.config_loader import (
            clear_runtime_config_cache,
            _CONFIG_CACHE_KEY,
        )
        cache.set(_CONFIG_CACHE_KEY, {"x": "y"}, 60)
        clear_runtime_config_cache()
        self.assertIsNone(cache.get(_CONFIG_CACHE_KEY))


class GetConfigValueTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def tearDown(self):
        from django.core.cache import cache
        cache.clear()

    def test_env_takes_precedence(self):
        from setup_app.services.config_loader import get_config_value
        with patch.dict(os.environ, {"MY_KEY": "env-value"}):
            result = get_config_value("MY_KEY", "default")
        self.assertEqual(result, "env-value")

    def test_falls_back_to_runtime_config(self):
        from django.core.cache import cache
        from setup_app.services.config_loader import get_config_value, _CONFIG_CACHE_KEY
        cache.set(_CONFIG_CACHE_KEY, {"DB_HOST": "db.local"}, 60)
        # Ensure DB_HOST is not in environment (safe via patch.dict)
        with patch.dict(os.environ, {}):
            os.environ.pop("DB_HOST", None)
            result = get_config_value("DB_HOST", "localhost")
        self.assertEqual(result, "db.local")

    def test_returns_default_when_key_missing(self):
        from django.core.cache import cache
        from setup_app.services.config_loader import get_config_value, _CONFIG_CACHE_KEY
        cache.set(_CONFIG_CACHE_KEY, {}, 60)
        with patch.dict(os.environ, {}):
            os.environ.pop("NONEXISTENT_KEY_XYZ", None)
            result = get_config_value("NONEXISTENT_KEY_XYZ", "my-default")
        self.assertEqual(result, "my-default")
