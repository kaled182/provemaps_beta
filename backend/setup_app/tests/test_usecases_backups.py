"""Usecases de backups (EV-0017a): ficheiros, retenção, listagem, nuvem."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from setup_app.usecases import backups as uc


class _TmpBackupDir(SimpleTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self._patch = patch.object(uc, "BACKUP_DIR", self.dir)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def _touch(self, name: str, age_days: float = 0, size: int = 3) -> Path:
        path = self.dir / name
        path.write_bytes(b"x" * size)
        if age_days:
            mtime = time.time() - age_days * 86400
            os.utime(path, (mtime, mtime))
        return path


class ListBackupsTests(_TmpBackupDir):
    def test_lists_only_zips_newest_first_with_cloud_marker_and_settings(self):
        self._touch("manual_backup_old.zip", age_days=2)
        self._touch("auto_backup_new.zip")
        self._touch("notes.txt")
        (self.dir / ".auto_backup_new.zip.uploaded").touch()

        with patch.object(
            uc.env_manager,
            "read_values",
            return_value={"BACKUP_RETENTION_DAYS": "30", "BACKUP_RETENTION_COUNT": ""},
        ):
            result = uc.list_backups()

        names = [b["filename"] for b in result["backups"]]
        self.assertEqual(names, ["auto_backup_new.zip", "manual_backup_old.zip"])
        newest = result["backups"][0]
        self.assertEqual(newest["type"], "auto")
        self.assertTrue(newest["cloud_uploaded"])
        self.assertEqual(
            newest["download_url"], "/setup_app/api/backups/download/auto_backup_new.zip/"
        )
        self.assertFalse(result["backups"][1]["cloud_uploaded"])
        self.assertEqual(result["settings"], {"retention_days": "30", "retention_count": ""})


class RetentionTests(_TmpBackupDir):
    def test_days_and_count_remove_the_right_files(self):
        self._touch("a_old.zip", age_days=10)
        self._touch("b_mid.zip", age_days=3)
        self._touch("c_new.zip")
        self._touch("keep.txt", age_days=30)

        with patch.object(
            uc.env_manager,
            "read_values",
            return_value={"BACKUP_RETENTION_DAYS": "7", "BACKUP_RETENTION_COUNT": "1"},
        ):
            uc.apply_backup_retention()

        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["c_new.zip", "keep.txt"])

    def test_noop_without_settings_or_with_garbage(self):
        self._touch("a.zip", age_days=100)
        with patch.object(
            uc.env_manager,
            "read_values",
            return_value={"BACKUP_RETENTION_DAYS": "abc", "BACKUP_RETENTION_COUNT": ""},
        ):
            uc.apply_backup_retention()
        self.assertTrue((self.dir / "a.zip").exists())


class UploadAndDeleteTests(_TmpBackupDir):
    def test_store_uploaded_backup_rejects_bad_names_and_formats(self):
        upload = MagicMock()
        upload.name = "dump.sql"  # `name` é argumento especial do MagicMock; atribui-se depois
        with self.assertRaises(uc.InvalidBackupFile):
            uc.store_uploaded_backup(upload)

    def test_store_uploaded_backup_writes_and_avoids_overwrite(self):
        self._touch("site.zip")
        upload = MagicMock()
        upload.name = "site.zip"
        upload.chunks.return_value = [b"ab", b"cd"]
        with patch.object(uc.env_manager, "read_values", return_value={}):
            name = uc.store_uploaded_backup(upload)
        self.assertTrue(name.startswith("upload_") and name.endswith("_site.zip"))
        self.assertEqual((self.dir / name).read_bytes(), b"abcd")

    def test_delete_and_download_path(self):
        self._touch("x.zip")
        self.assertEqual(uc.backup_download_path("x.zip"), self.dir / "x.zip")
        uc.delete_backup("x.zip")
        self.assertFalse((self.dir / "x.zip").exists())
        with self.assertRaises(uc.BackupNotFound):
            uc.delete_backup("x.zip")
        with self.assertRaises(ValueError):
            uc.delete_backup("../x.zip")


class CreateAndRestoreTests(_TmpBackupDir):
    def test_create_requires_pg_dump_and_password(self):
        with patch.object(uc.shutil, "which", return_value=None):
            with self.assertRaises(uc.BackupToolMissing):
                uc.create_backup()
        with (
            patch.object(uc.shutil, "which", return_value="/usr/bin/pg_dump"),
            patch.object(
                uc.env_manager, "read_values", return_value={"BACKUP_ZIP_PASSWORD": "short"}
            ),
        ):
            with self.assertRaises(ValueError):
                uc.create_backup()

    def test_create_runs_make_backup_uploads_and_applies_retention(self):
        with (
            patch.object(uc.shutil, "which", return_value="/usr/bin/pg_dump"),
            patch.object(
                uc.env_manager, "read_values", return_value={"BACKUP_ZIP_PASSWORD": "senha-forte-1"}
            ),
            patch.object(uc, "call_command", return_value="novo.zip") as cmd,
            patch.object(uc, "upload_backup_if_enabled", return_value={"success": False}) as gd,
            patch.object(uc, "upload_backup_via_ftp", return_value={"success": True}) as ftp,
            patch.object(uc, "apply_backup_retention") as ret,
        ):
            result = uc.create_backup()
        cmd.assert_called_once_with("make_backup")
        gd.assert_called_once_with("novo.zip")
        ftp.assert_called_once_with("novo.zip")
        ret.assert_called_once()
        self.assertEqual(result["filename"], "novo.zip")
        self.assertEqual(result["ftp_upload"], {"success": True})

    def test_restore_errors(self):
        with self.assertRaises(uc.BackupNotFound):
            uc.restore_backup("nao-existe.zip")
        self._touch("db.zip")
        with patch.object(uc.shutil, "which", return_value=None):
            with self.assertRaises(uc.BackupToolMissing):
                uc.restore_backup("db.zip")

    def test_restore_plain_dump_calls_restore_db(self):
        self._touch("db.dump")
        with (
            patch.object(uc.shutil, "which", return_value="/usr/bin/psql"),
            patch.object(uc, "call_command") as cmd,
        ):
            uc.restore_backup("db.dump")
        cmd.assert_called_once_with("restore_db", "db.dump")


class CloudTests(_TmpBackupDir):
    def test_upload_existing_backup_marks_when_any_provider_succeeds(self):
        self._touch("x.zip")
        with (
            patch.object(
                uc, "upload_backup_if_enabled", return_value={"success": False, "message": "off"}
            ),
            patch.object(uc, "upload_backup_via_ftp", return_value={"success": True}),
        ):
            result = uc.upload_existing_backup("x.zip")
        self.assertTrue(result["marked"])
        self.assertTrue((self.dir / ".x.zip.uploaded").exists())

    def test_upload_backup_if_enabled_respects_env_and_explicit_flags(self):
        self._touch("x.zip")
        with patch.object(uc, "get_gdrive_settings", return_value={"enabled": False}):
            self.assertFalse(uc.upload_backup_if_enabled("x.zip")["success"])
        with patch.object(uc, "upload_backup_to_gdrive", return_value={"success": True}) as up:
            result = uc.upload_backup_if_enabled("x.zip", enabled=True, folder_id="f1")
        self.assertTrue(result["success"])
        self.assertEqual(up.call_args.kwargs["folder_id"], "f1")
        self.assertFalse(uc.upload_backup_if_enabled("missing.zip", enabled=True)["success"])

    def test_gdrive_test_fills_from_env_when_request_is_incomplete(self):
        with (
            patch.object(
                uc.env_manager,
                "read_values",
                return_value={"GDRIVE_AUTH_MODE": "oauth", "GDRIVE_OAUTH_REFRESH_TOKEN": "rt"},
            ),
            patch.object(uc, "test_gdrive_connection", return_value={"success": True}) as test,
        ):
            uc.gdrive_test({})
        self.assertEqual(test.call_args.kwargs["auth_mode"], "oauth")
        self.assertEqual(test.call_args.kwargs["oauth_refresh_token"], "rt")

    def test_gdrive_oauth_start_requires_credentials_and_sdk(self):
        with patch.object(uc.env_manager, "read_values", return_value={}):
            with self.assertRaises(ValueError):
                uc.gdrive_oauth_start({}, "http://x/cb")
        with patch.object(uc, "_oauth_flow_class", side_effect=uc.BackupToolMissing("sdk")):
            with self.assertRaises(uc.BackupToolMissing):
                uc.gdrive_oauth_start(
                    {"gdrive_oauth_client_id": "id", "gdrive_oauth_client_secret": "s"},
                    "http://x/cb",
                )

    def test_update_backup_settings_writes_env_and_applies_retention(self):
        with (
            patch.object(uc.env_manager, "write_values") as write,
            patch.object(uc, "apply_backup_retention") as ret,
        ):
            payload = uc.update_backup_settings(
                {
                    "retention_days": 7,
                    "auto_backup": True,
                    "frequency": "daily",
                    "cloud_upload": False,
                }
            )
        self.assertEqual(
            payload,
            {
                "BACKUP_RETENTION_DAYS": "7",
                "BACKUP_RETENTION_COUNT": "",
                "BACKUP_AUTO_ENABLED": "true",
                "BACKUP_FREQUENCY": "daily",
                "BACKUP_CLOUD_UPLOAD": "false",
            },
        )
        write.assert_called_once_with(payload)
        ret.assert_called_once()
