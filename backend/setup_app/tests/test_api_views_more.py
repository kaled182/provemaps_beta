"""Tests for additional utility functions in setup_app.api_views."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase


class SerializeCompanyProfileTests(TestCase):
    def _make_profile(self, **kwargs):
        from datetime import datetime
        p = MagicMock()
        for attr in [
            "company_legal_name", "company_trade_name", "company_doc",
            "company_owner_name", "company_owner_doc", "company_owner_birth",
            "company_state_reg", "company_city_reg", "company_fistel",
            "company_created_date", "company_active", "company_reports_active",
            "address_zip", "address_street", "address_number", "address_district",
            "address_city", "address_state", "address_country", "address_extra",
            "address_reference", "address_coords", "address_complex", "address_ibge",
        ]:
            setattr(p, attr, kwargs.get(attr, ""))
        p.assets_logo = MagicMock()
        p.assets_logo.name = ""
        p.assets_cert_file = MagicMock()
        p.assets_cert_file.name = ""
        p.updated_at = datetime(2024, 6, 1)
        return p

    def test_serializes_all_expected_keys(self):
        from setup_app.api_views import _serialize_company_profile
        profile = self._make_profile(company_legal_name="Test Corp")
        result = _serialize_company_profile(profile)
        self.assertIn("company_legal_name", result)
        self.assertIn("address_city", result)
        self.assertIn("assets_logo", result)
        self.assertIn("updated_at", result)

    def test_company_name_field(self):
        from setup_app.api_views import _serialize_company_profile
        profile = self._make_profile(company_legal_name="Acme Ltd")
        result = _serialize_company_profile(profile)
        self.assertEqual(result["company_legal_name"], "Acme Ltd")

    def test_updated_at_is_isoformat(self):
        from setup_app.api_views import _serialize_company_profile
        profile = self._make_profile()
        result = _serialize_company_profile(profile)
        self.assertIn("2024-06-01", result["updated_at"])

    def test_updated_at_none_returns_empty(self):
        from setup_app.api_views import _serialize_company_profile
        profile = self._make_profile()
        profile.updated_at = None
        result = _serialize_company_profile(profile)
        self.assertEqual(result["updated_at"], "")


class GetFtpSettingsTests(TestCase):
    def test_returns_dict_with_expected_keys(self):
        from setup_app.api_views import _get_ftp_settings
        with patch("setup_app.api_views.env_manager.read_values", return_value={
            "FTP_ENABLED": "true",
            "FTP_HOST": "ftp.example.com",
            "FTP_PORT": "21",
            "FTP_USER": "ftpuser",
            "FTP_PASSWORD": "secret",
            "FTP_PATH": "/backups",
        }):
            result = _get_ftp_settings()
        self.assertTrue(result["enabled"])
        self.assertEqual(result["host"], "ftp.example.com")
        self.assertEqual(result["port"], "21")
        self.assertEqual(result["path"], "/backups")

    def test_disabled_when_env_false(self):
        from setup_app.api_views import _get_ftp_settings
        with patch("setup_app.api_views.env_manager.read_values", return_value={
            "FTP_ENABLED": "false",
            "FTP_HOST": "",
            "FTP_PORT": "",
            "FTP_USER": "",
            "FTP_PASSWORD": "",
            "FTP_PATH": "",
        }):
            result = _get_ftp_settings()
        self.assertFalse(result["enabled"])


class GetGdriveSettingsTests(TestCase):
    def test_returns_dict_with_expected_keys(self):
        from setup_app.api_views import _get_gdrive_settings
        with patch("setup_app.api_views.env_manager.read_values", return_value={
            "GDRIVE_ENABLED": "true",
            "GDRIVE_AUTH_MODE": "service_account",
            "GDRIVE_CREDENTIALS_JSON": "{}",
            "GDRIVE_FOLDER_ID": "folder123",
            "GDRIVE_SHARED_DRIVE_ID": "",
            "GDRIVE_OAUTH_CLIENT_ID": "",
            "GDRIVE_OAUTH_CLIENT_SECRET": "",
            "GDRIVE_OAUTH_REFRESH_TOKEN": "",
            "GDRIVE_OAUTH_USER_EMAIL": "",
        }):
            result = _get_gdrive_settings()
        self.assertTrue(result["enabled"])
        self.assertEqual(result["folder_id"], "folder123")
        self.assertEqual(result["auth_mode"], "service_account")


class GetBackupPasswordTests(TestCase):
    def test_raises_when_password_too_short(self):
        from setup_app.api_views import _get_backup_password
        with patch("setup_app.api_views.env_manager.read_values", return_value={
            "BACKUP_ZIP_PASSWORD": "short"
        }):
            with self.assertRaises(ValueError):
                _get_backup_password()

    def test_returns_bytes_when_password_valid(self):
        from setup_app.api_views import _get_backup_password
        with patch("setup_app.api_views.env_manager.read_values", return_value={
            "BACKUP_ZIP_PASSWORD": "longpassword123"
        }):
            result = _get_backup_password()
        self.assertIsInstance(result, bytes)
        self.assertEqual(result, b"longpassword123")


class GetWhatsappQrServiceUrlTests(TestCase):
    def test_returns_config_url_when_set(self):
        from setup_app.api_views import _get_whatsapp_qr_service_url
        gw = MagicMock()
        gw.config = {"qr_service_url": "http://qr.local:3000"}
        result = _get_whatsapp_qr_service_url(gw)
        self.assertEqual(result, "http://qr.local:3000")

    def test_falls_back_to_env_when_config_empty(self):
        from setup_app.api_views import _get_whatsapp_qr_service_url
        gw = MagicMock()
        gw.config = {}
        with patch("setup_app.api_views.env_manager.read_values", return_value={
            "WHATSAPP_QR_SERVICE_URL": "http://env.qr.local"
        }):
            result = _get_whatsapp_qr_service_url(gw)
        self.assertEqual(result, "http://env.qr.local")

    def test_returns_empty_when_nothing_configured(self):
        from setup_app.api_views import _get_whatsapp_qr_service_url
        gw = MagicMock()
        gw.config = {}
        with patch("setup_app.api_views.env_manager.read_values", return_value={
            "WHATSAPP_QR_SERVICE_URL": ""
        }):
            result = _get_whatsapp_qr_service_url(gw)
        self.assertEqual(result, "")


class StreamUpstreamResponseTests(TestCase):
    def test_yields_chunks(self):
        from setup_app.api_views import _stream_upstream_response
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"chunk1", b"", b"chunk2"]
        chunks = list(_stream_upstream_response(mock_response))
        self.assertEqual(chunks, [b"chunk1", b"chunk2"])  # empty filtered out

    def test_closes_response_after_iteration(self):
        from setup_app.api_views import _stream_upstream_response
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"data"]
        list(_stream_upstream_response(mock_response))
        mock_response.close.assert_called_once()

    def test_closes_response_on_exception(self):
        from setup_app.api_views import _stream_upstream_response
        mock_response = MagicMock()
        mock_response.iter_content.side_effect = RuntimeError("broken")
        with self.assertRaises(RuntimeError):
            list(_stream_upstream_response(mock_response))
        mock_response.close.assert_called_once()


class GetDbSettingsTests(TestCase):
    def test_raises_when_required_keys_missing(self):
        from setup_app.api_views import _get_db_settings
        with patch("setup_app.api_views.env_manager.read_values", return_value={
            "DB_HOST": "",
            "DB_PORT": "5432",
            "DB_NAME": "",
            "DB_USER": "postgres",
            "DB_PASSWORD": "secret",
        }):
            with self.assertRaises(ValueError):
                _get_db_settings()

    def test_returns_values_when_all_present(self):
        from setup_app.api_views import _get_db_settings
        with patch("setup_app.api_views.env_manager.read_values", return_value={
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_NAME": "mydb",
            "DB_USER": "postgres",
            "DB_PASSWORD": "secret",
        }):
            result = _get_db_settings()
        self.assertEqual(result["DB_HOST"], "localhost")
        self.assertEqual(result["DB_NAME"], "mydb")
