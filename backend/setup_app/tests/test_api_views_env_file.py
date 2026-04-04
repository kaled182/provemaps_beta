"""Tests for get_env_file and related helpers in setup_app.api_views."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase


class GetEnvFileTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _make_request(self):
        request = self.factory.get("/api/env-file/")
        request.user = MagicMock(is_authenticated=True, is_staff=True)
        return request

    def test_returns_empty_content_when_file_missing(self):
        from setup_app.api_views import get_env_file
        request = self._make_request()
        with patch("setup_app.api_views.env_manager") as mock_em:
            mock_em.ENV_PATH = MagicMock()
            mock_em.ENV_PATH.exists.return_value = False
            response = get_env_file(request)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["content"], "")

    def test_returns_file_content(self):
        from setup_app.api_views import get_env_file
        request = self._make_request()
        with patch("setup_app.api_views.env_manager") as mock_em:
            mock_em.ENV_PATH = MagicMock()
            mock_em.ENV_PATH.exists.return_value = True
            mock_em.ENV_PATH.read_text.return_value = "KEY=value\n"
            response = get_env_file(request)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["content"], "KEY=value\n")

    def test_returns_400_when_file_too_large(self):
        from setup_app.api_views import get_env_file
        request = self._make_request()
        with patch("setup_app.api_views.env_manager") as mock_em:
            mock_em.ENV_PATH = MagicMock()
            mock_em.ENV_PATH.exists.return_value = True
            mock_em.ENV_PATH.read_text.return_value = "x" * 600_000
            response = get_env_file(request)
        self.assertEqual(response.status_code, 400)

    def test_returns_500_on_exception(self):
        from setup_app.api_views import get_env_file
        request = self._make_request()
        with patch("setup_app.api_views.env_manager") as mock_em:
            mock_em.ENV_PATH = MagicMock()
            mock_em.ENV_PATH.exists.side_effect = OSError("permission denied")
            response = get_env_file(request)
        self.assertEqual(response.status_code, 500)


class EnsureBackupDirTests(TestCase):
    def test_creates_backup_dir(self):
        from setup_app.api_views import _ensure_backup_dir
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            _ensure_backup_dir()
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


class EnsureFtpDirTests(TestCase):
    def test_returns_immediately_for_empty_path(self):
        from setup_app.api_views import _ensure_ftp_dir
        ftp = MagicMock()
        _ensure_ftp_dir(ftp, "")
        ftp.cwd.assert_not_called()

    def test_returns_immediately_for_whitespace_path(self):
        from setup_app.api_views import _ensure_ftp_dir
        ftp = MagicMock()
        _ensure_ftp_dir(ftp, "   ")
        ftp.cwd.assert_not_called()

    def test_navigates_relative_path(self):
        from setup_app.api_views import _ensure_ftp_dir
        ftp = MagicMock()
        _ensure_ftp_dir(ftp, "backups/daily")
        # Should try to cwd into "backups" then "daily"
        self.assertGreaterEqual(ftp.cwd.call_count, 2)

    def test_navigates_absolute_path(self):
        from setup_app.api_views import _ensure_ftp_dir
        ftp = MagicMock()
        _ensure_ftp_dir(ftp, "/backups/daily")
        # First cwd should be to "/"
        calls = [c[0][0] for c in ftp.cwd.call_args_list]
        self.assertIn("/", calls)

    def test_creates_directory_when_cwd_fails(self):
        from setup_app.api_views import _ensure_ftp_dir
        ftp = MagicMock()
        ftp.cwd.side_effect = [Exception("not found"), None]
        _ensure_ftp_dir(ftp, "newdir")
        ftp.mkd.assert_called_once_with("newdir")


class UploadBackupViaFtpTests(TestCase):
    def test_returns_failure_for_empty_filename(self):
        from setup_app.api_views import _upload_backup_via_ftp
        result = _upload_backup_via_ftp("")
        self.assertFalse(result["success"])

    def test_returns_failure_when_ftp_disabled(self):
        from setup_app.api_views import _upload_backup_via_ftp
        with patch("setup_app.api_views._get_ftp_settings", return_value={"enabled": False}):
            result = _upload_backup_via_ftp("backup.zip")
        self.assertFalse(result["success"])
        self.assertIn("desabilitado", result["message"].lower())
