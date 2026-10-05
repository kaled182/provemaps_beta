"""Views de backups (EV-0017a): acesso, códigos HTTP e tradução das exceções de domínio."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from setup_app.usecases import backups as uc


class BackupsApiTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="bk_staff", password="pass", email="bk@test.com", is_staff=True, is_active=True
        )
        self.client.force_login(self.staff)
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self._dir_patch = patch.object(uc, "BACKUP_DIR", self.dir)
        self._dir_patch.start()
        self._env_patch = patch.object(uc.env_manager, "read_values", return_value={})
        self._env_patch.start()
        self._audit_patch = patch("setup_app.api.backups.ConfigurationAudit")
        self.audit = self._audit_patch.start()

    def tearDown(self):
        self._audit_patch.stop()
        self._env_patch.stop()
        self._dir_patch.stop()
        self._tmp.cleanup()

    def test_requires_staff(self):
        regular = User.objects.create_user(username="bk_user", password="pass", email="u@test.com")
        self.client.force_login(regular)
        resp = self.client.get("/setup_app/api/backups/")
        self.assertIn(resp.status_code, (302, 403))

    def test_list(self):
        (self.dir / "a.zip").write_bytes(b"x")
        resp = self.client.get("/setup_app/api/backups/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertEqual([b["filename"] for b in data["backups"]], ["a.zip"])
        self.assertIn("settings", data)

    def test_upload_file_returns_201_and_audits(self):
        upload = SimpleUploadedFile("novo.zip", b"zipdata")
        resp = self.client.post("/setup_app/api/backups/", {"file": upload})
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(json.loads(resp.content)["filename"], "novo.zip")
        self.assertTrue((self.dir / "novo.zip").exists())
        self.audit.log_change.assert_called_once()
        self.assertEqual(self.audit.log_change.call_args.kwargs["action"], "import")

    def test_upload_wrong_format_returns_400(self):
        resp = self.client.post(
            "/setup_app/api/backups/", {"file": SimpleUploadedFile("d.sql", b"x")}
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Unsupported", json.loads(resp.content)["message"])

    def test_create_without_pg_dump_returns_500(self):
        with patch.object(uc.shutil, "which", return_value=None):
            resp = self.client.post("/setup_app/api/backups/")
        self.assertEqual(resp.status_code, 500)
        self.assertIn("pg_dump", json.loads(resp.content)["message"])

    def test_create_returns_202_with_upload_results(self):
        with patch.object(
            uc,
            "create_backup",
            return_value={
                "filename": "n.zip",
                "gdrive_upload": {},
                "ftp_upload": {"success": True},
            },
        ):
            resp = self.client.post("/setup_app/api/backups/")
        self.assertEqual(resp.status_code, 202)
        data = json.loads(resp.content)
        self.assertEqual(data["message"], "Backup criado")
        self.assertEqual(data["filename"], "n.zip")
        self.assertEqual(self.audit.log_change.call_args.kwargs["action"], "create")

    def test_delete_restore_download_not_found(self):
        for url in ("/setup_app/api/backups/delete/", "/setup_app/api/backups/restore/"):
            resp = self.client.post(
                url, json.dumps({"filename": "nope.zip"}), content_type="application/json"
            )
            self.assertEqual(resp.status_code, 404, url)
        resp = self.client.get("/setup_app/api/backups/download/nope.zip/")
        self.assertEqual(resp.status_code, 404)

    def test_delete_invalid_json_and_traversal(self):
        resp = self.client.post(
            "/setup_app/api/backups/delete/", "{bad", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(
            "/setup_app/api/backups/delete/",
            json.dumps({"filename": "../x.zip"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_delete_and_download_ok(self):
        (self.dir / "a.zip").write_bytes(b"conteudo")
        resp = self.client.get("/setup_app/api/backups/download/a.zip/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b"".join(resp.streaming_content), b"conteudo")

        resp = self.client.post(
            "/setup_app/api/backups/delete/",
            json.dumps({"filename": "a.zip"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse((self.dir / "a.zip").exists())
        self.assertEqual(self.audit.log_change.call_args.kwargs["action"], "delete")

    def test_upload_cloud_and_settings(self):
        (self.dir / "a.zip").write_bytes(b"x")
        with (
            patch.object(uc, "upload_backup_if_enabled", return_value={"success": True}),
            patch.object(uc, "upload_backup_via_ftp", return_value={"success": False}),
        ):
            resp = self.client.post(
                "/setup_app/api/backups/upload-cloud/",
                json.dumps({"filename": "a.zip"}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["gdrive_upload"], {"success": True})
        self.assertTrue((self.dir / ".a.zip.uploaded").exists())

        with patch.object(uc.env_manager, "write_values") as write:
            resp = self.client.post(
                "/setup_app/api/backups/settings/",
                json.dumps({"retention_days": 5, "retention_count": 2}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        write.assert_called_once_with({"BACKUP_RETENTION_DAYS": "5", "BACKUP_RETENTION_COUNT": "2"})

    def test_gdrive_test_and_oauth_start(self):
        with patch.object(
            uc, "gdrive_test", return_value={"success": False, "message": "sem credenciais"}
        ):
            resp = self.client.post(
                "/setup_app/api/test-gdrive/", "{}", content_type="application/json"
            )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.audit.log_change.call_args.kwargs["section"], "Google Drive")

        with patch.object(
            uc, "gdrive_oauth_start", return_value={"auth_url": "https://g/auth", "state": "s1"}
        ):
            resp = self.client.post(
                "/setup_app/api/gdrive/oauth/start/", "{}", content_type="application/json"
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["auth_url"], "https://g/auth")
        self.assertEqual(self.client.session["gdrive_oauth_state"], "s1")

        resp = self.client.get("/setup_app/api/gdrive/oauth/callback/?state=errado&code=c")
        self.assertEqual(resp.status_code, 400)
        with patch.object(uc, "gdrive_oauth_complete", return_value={"user_email": "a@b"}):
            resp = self.client.get("/setup_app/api/gdrive/oauth/callback/?state=s1&code=c")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Conectado", resp.content.decode())
