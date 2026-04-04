"""Tests for pure utility functions in setup_app.api_views."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings


class StaffCheckTests(TestCase):
    def test_active_staff_returns_true(self):
        from setup_app.api_views import _staff_check
        user = MagicMock(is_active=True, is_staff=True)
        self.assertTrue(_staff_check(user))

    def test_inactive_user_returns_false(self):
        from setup_app.api_views import _staff_check
        user = MagicMock(is_active=False, is_staff=True)
        self.assertFalse(_staff_check(user))

    def test_non_staff_returns_false(self):
        from setup_app.api_views import _staff_check
        user = MagicMock(is_active=True, is_staff=False)
        self.assertFalse(_staff_check(user))


class ToBoolTests(TestCase):
    def test_true_bool_passthrough(self):
        from setup_app.api_views import _to_bool
        self.assertTrue(_to_bool(True))

    def test_false_bool_passthrough(self):
        from setup_app.api_views import _to_bool
        self.assertFalse(_to_bool(False))

    def test_string_truthy_values(self):
        from setup_app.api_views import _to_bool
        for val in ("true", "1", "yes", "on"):
            self.assertTrue(_to_bool(val), f"Expected True for {val!r}")

    def test_string_falsy_values(self):
        from setup_app.api_views import _to_bool
        for val in ("false", "0", "no", "off"):
            self.assertFalse(_to_bool(val), f"Expected False for {val!r}")

    def test_unknown_string_returns_false(self):
        from setup_app.api_views import _to_bool
        self.assertFalse(_to_bool("maybe"))

    def test_integer_truthy(self):
        from setup_app.api_views import _to_bool
        self.assertTrue(_to_bool(1))
        self.assertFalse(_to_bool(0))


class DetectBackupTypeTests(TestCase):
    def test_config_json(self):
        from setup_app.api_views import _detect_backup_type
        self.assertEqual(_detect_backup_type("backup.config.json"), "config")

    def test_manual_prefix(self):
        from setup_app.api_views import _detect_backup_type
        self.assertEqual(_detect_backup_type("manual_backup_2024.zip"), "manual")

    def test_manual_in_name(self):
        from setup_app.api_views import _detect_backup_type
        self.assertEqual(_detect_backup_type("db_manual.zip"), "manual")

    def test_auto_keyword(self):
        from setup_app.api_views import _detect_backup_type
        self.assertEqual(_detect_backup_type("auto_backup.zip"), "auto")

    def test_scheduled_keyword(self):
        from setup_app.api_views import _detect_backup_type
        self.assertEqual(_detect_backup_type("scheduled_backup.zip"), "auto")

    def test_snapshot_keyword(self):
        from setup_app.api_views import _detect_backup_type
        self.assertEqual(_detect_backup_type("snapshot_2024.zip"), "auto")

    def test_import_keyword(self):
        from setup_app.api_views import _detect_backup_type
        self.assertEqual(_detect_backup_type("import_data.zip"), "upload")

    def test_upload_keyword(self):
        from setup_app.api_views import _detect_backup_type
        self.assertEqual(_detect_backup_type("upload_2024.zip"), "upload")

    def test_unknown_returns_unknown(self):
        from setup_app.api_views import _detect_backup_type
        self.assertEqual(_detect_backup_type("randomfile.zip"), "unknown")


class SafeBackupPathTests(TestCase):
    def test_valid_filename_returns_path(self):
        from setup_app.api_views import _safe_backup_path, BACKUP_DIR
        result = _safe_backup_path("backup.zip")
        self.assertEqual(result, BACKUP_DIR / "backup.zip")

    def test_empty_filename_raises(self):
        from setup_app.api_views import _safe_backup_path
        with self.assertRaises(ValueError):
            _safe_backup_path("")

    def test_traversal_raises(self):
        from setup_app.api_views import _safe_backup_path
        with self.assertRaises(ValueError):
            _safe_backup_path("../etc/passwd")

    def test_subdirectory_raises(self):
        from setup_app.api_views import _safe_backup_path
        with self.assertRaises(ValueError):
            _safe_backup_path("subdir/file.zip")


class UserCanAccessVideoGatewayTests(TestCase):
    def test_superuser_always_has_access(self):
        from setup_app.api_views import _user_can_access_video_gateway
        user = MagicMock(is_superuser=True)
        gateway = MagicMock()
        gateway.departments.exists.return_value = True
        self.assertTrue(_user_can_access_video_gateway(user, gateway))

    def test_gateway_without_departments_is_public(self):
        from setup_app.api_views import _user_can_access_video_gateway
        user = MagicMock(is_superuser=False)
        gateway = MagicMock()
        gateway.departments.exists.return_value = False
        self.assertTrue(_user_can_access_video_gateway(user, gateway))

    def test_user_without_profile_returns_false(self):
        from setup_app.api_views import _user_can_access_video_gateway
        user = MagicMock(is_superuser=False, spec=["is_superuser"])
        user.profile = None
        gateway = MagicMock()
        gateway.departments.exists.return_value = True
        # getattr(user, "profile", None) will return None when profile attr missing
        type(user).profile = property(lambda self: None)
        result = _user_can_access_video_gateway(user, gateway)
        self.assertFalse(result)


class FileInfoTests(TestCase):
    def test_none_field_returns_empty(self):
        from setup_app.api_views import _file_info
        result = _file_info(None, None)
        self.assertEqual(result, {"name": "", "url": ""})

    def test_field_without_name_returns_empty(self):
        from setup_app.api_views import _file_info
        field = MagicMock()
        field.name = ""
        result = _file_info(field, None)
        self.assertEqual(result, {"name": "", "url": ""})

    def test_field_with_name_returns_info(self):
        from setup_app.api_views import _file_info
        field = MagicMock()
        field.name = "logos/logo.png"
        field.url = "/media/logos/logo.png"
        result = _file_info(field, None)
        self.assertEqual(result["name"], "logos/logo.png")
        self.assertEqual(result["url"], "/media/logos/logo.png")

    def test_field_url_exception_returns_empty_url(self):
        from setup_app.api_views import _file_info
        field = MagicMock()
        field.name = "logo.png"
        type(field).url = property(lambda self: (_ for _ in ()).throw(ValueError("no url")))
        result = _file_info(field, None)
        self.assertEqual(result["name"], "logo.png")
        self.assertEqual(result["url"], "")


class SerializeMonitoringServerTests(TestCase):
    def _make_server(self, **kwargs):
        from datetime import datetime
        server = MagicMock()
        server.id = kwargs.get("id", 1)
        server.name = kwargs.get("name", "Test Server")
        server.server_type = kwargs.get("server_type", "zabbix")
        server.url = kwargs.get("url", "http://zabbix.local")
        server.is_active = kwargs.get("is_active", True)
        server.auth_token = kwargs.get("auth_token", "secret-token")
        server.extra_config = kwargs.get("extra_config", {})
        server.created_at = datetime(2024, 1, 1)
        return server

    def test_serializes_fields(self):
        from setup_app.api_views import _serialize_monitoring_server
        server = self._make_server()
        result = _serialize_monitoring_server(server)
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["name"], "Test Server")
        self.assertEqual(result["server_type"], "zabbix")
        self.assertTrue(result["is_active"])

    def test_auth_token_not_exposed(self):
        from setup_app.api_views import _serialize_monitoring_server
        server = self._make_server(auth_token="my-secret")
        result = _serialize_monitoring_server(server)
        self.assertTrue(result["has_auth_token"])
        self.assertEqual(result["auth_token"], "")

    def test_no_auth_token_has_auth_false(self):
        from setup_app.api_views import _serialize_monitoring_server
        server = self._make_server(auth_token=None)
        result = _serialize_monitoring_server(server)
        self.assertFalse(result["has_auth_token"])


class SerializeGatewayTests(TestCase):
    def _make_gateway(self, **kwargs):
        from datetime import datetime
        gw = MagicMock()
        gw.id = kwargs.get("id", 1)
        gw.name = kwargs.get("name", "GW1")
        gw.gateway_type = kwargs.get("gateway_type", "whatsapp")
        gw.provider = kwargs.get("provider", "")
        gw.priority = kwargs.get("priority", 1)
        gw.enabled = kwargs.get("enabled", True)
        gw.site_name = kwargs.get("site_name", "")
        gw.config = kwargs.get("config", {})
        gw.created_at = datetime(2024, 1, 1)
        gw.updated_at = datetime(2024, 1, 2)
        return gw

    def test_serializes_basic_fields(self):
        from setup_app.api_views import _serialize_gateway
        gw = self._make_gateway()
        result = _serialize_gateway(gw)
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["name"], "GW1")
        self.assertEqual(result["gateway_type"], "whatsapp")
        self.assertTrue(result["enabled"])

    def test_is_active_alias(self):
        from setup_app.api_views import _serialize_gateway
        gw = self._make_gateway(enabled=False)
        result = _serialize_gateway(gw)
        self.assertFalse(result["is_active"])

    def test_video_gateway_adds_playback_url(self):
        from setup_app.api_views import _serialize_gateway
        gw = self._make_gateway(gateway_type="video", config={"stream_url": "rtmp://live"})
        with patch("setup_app.api_views.video_gateway_service.build_playback_url",
                   return_value="http://hls.example.com/live/gw1/index.m3u8"):
            result = _serialize_gateway(gw)
        self.assertEqual(result["playback_url"], "http://hls.example.com/live/gw1/index.m3u8")

    def test_video_gateway_omits_playback_url_when_empty(self):
        from setup_app.api_views import _serialize_gateway
        gw = self._make_gateway(gateway_type="video")
        with patch("setup_app.api_views.video_gateway_service.build_playback_url",
                   return_value=""):
            result = _serialize_gateway(gw)
        self.assertNotIn("playback_url", result)

    def test_video_gateway_handles_exception(self):
        from setup_app.api_views import _serialize_gateway
        gw = self._make_gateway(gateway_type="video")
        with patch("setup_app.api_views.video_gateway_service.build_playback_url",
                   side_effect=Exception("error")):
            result = _serialize_gateway(gw)
        self.assertNotIn("playback_url", result)
