"""
Unit tests for setup_app management commands.
Covers: make_backup, restore_db, sync_env_from_setup
"""
from __future__ import annotations

import subprocess
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _runtime_config(**kwargs):
    cfg = MagicMock()
    cfg.db_name = kwargs.get("db_name", "testdb")
    cfg.db_user = kwargs.get("db_user", "postgres")
    cfg.db_host = kwargs.get("db_host", "localhost")
    cfg.db_port = kwargs.get("db_port", "5432")
    cfg.db_password = kwargs.get("db_password", "secret")
    return cfg


_DB_SETTINGS = {
    "default": {
        "NAME": "testdb",
        "USER": "postgres",
        "HOST": "localhost",
        "PORT": "5432",
        "PASSWORD": "secret",
    }
}

_INCOMPLETE_DB = {
    "default": {
        "NAME": "testdb",
        "USER": "postgres",
        "HOST": "",
        "PORT": "",
        "PASSWORD": "",
    }
}

_PATCH_RUNTIME = "setup_app.management.commands.make_backup.runtime_settings"
_PATCH_ENV = "setup_app.management.commands.make_backup.env_manager"
_PATCH_RUN = "setup_app.management.commands.make_backup.subprocess.run"


def _env_manager_mock(password="strongpass123"):
    m = MagicMock()
    m.read_values.return_value = {
        "BACKUP_ZIP_PASSWORD": password,
        "SECRET_KEY": "x",
    }
    m.ENV_PATH = MagicMock()
    m.ENV_PATH.exists.return_value = False
    return m


# ---------------------------------------------------------------------------
# make_backup
# ---------------------------------------------------------------------------

class MakeBackupCommandTests(TestCase):
    """Tests for the make_backup management command."""

    @patch(_PATCH_RUNTIME)
    def test_incomplete_db_config_raises(self, mock_runtime):
        mock_runtime.get_runtime_config.return_value = _runtime_config(
            db_host=""
        )
        with tempfile.TemporaryDirectory() as base:
            with override_settings(BASE_DIR=base):
                with pytest.raises(RuntimeError, match="incomplete"):
                    call_command("make_backup")

    @patch(_PATCH_ENV)
    @patch(_PATCH_RUNTIME)
    @patch(_PATCH_RUN)
    def test_pg_dump_not_found_raises(self, mock_run, mock_runtime, mock_env):
        mock_runtime.get_runtime_config.return_value = _runtime_config()
        mock_env.read_values.return_value = _env_manager_mock().read_values()
        mock_env.ENV_PATH = MagicMock()
        mock_env.ENV_PATH.exists.return_value = False
        mock_run.side_effect = FileNotFoundError("pg_dump not found")

        with tempfile.TemporaryDirectory() as base:
            with override_settings(BASE_DIR=base):
                with pytest.raises(RuntimeError, match="pg_dump"):
                    call_command("make_backup")

    @patch(_PATCH_ENV)
    @patch(_PATCH_RUNTIME)
    @patch(_PATCH_RUN)
    def test_pg_dump_subprocess_error_raises(
        self, mock_run, mock_runtime, mock_env
    ):
        mock_runtime.get_runtime_config.return_value = _runtime_config()
        mock_env.read_values.return_value = _env_manager_mock().read_values()
        mock_env.ENV_PATH = MagicMock()
        mock_env.ENV_PATH.exists.return_value = False
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "pg_dump", stderr="connection refused"
        )

        with tempfile.TemporaryDirectory() as base:
            with override_settings(BASE_DIR=base):
                with pytest.raises(RuntimeError, match="pg_dump"):
                    call_command("make_backup")

    @patch(_PATCH_ENV)
    @patch(_PATCH_RUNTIME)
    @patch(_PATCH_RUN)
    def test_short_password_raises(self, mock_run, mock_runtime, mock_env):
        mock_runtime.get_runtime_config.return_value = _runtime_config()
        mock_env.read_values.return_value = {
            "BACKUP_ZIP_PASSWORD": "short",
            "SECRET_KEY": "x",
        }
        mock_env.ENV_PATH = MagicMock()
        mock_env.ENV_PATH.exists.return_value = False
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as base:
            with override_settings(BASE_DIR=base):
                with pytest.raises(RuntimeError, match="senha"):
                    call_command("make_backup")

    @patch(_PATCH_ENV)
    @patch(_PATCH_RUNTIME)
    @patch(_PATCH_RUN)
    def test_pg_dump_called_with_correct_args(
        self, mock_run, mock_runtime, mock_env
    ):
        mock_runtime.get_runtime_config.return_value = _runtime_config(
            db_host="db.local",
            db_port="5433",
            db_user="myuser",
            db_name="mydb",
        )
        mock_env.read_values.return_value = {
            "BACKUP_ZIP_PASSWORD": "short",
            "SECRET_KEY": "x",
        }
        mock_env.ENV_PATH = MagicMock()
        mock_env.ENV_PATH.exists.return_value = False
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as base:
            with override_settings(BASE_DIR=base):
                with pytest.raises(RuntimeError):
                    call_command("make_backup")

        cmd = mock_run.call_args[0][0]
        assert "pg_dump" in cmd
        assert "db.local" in cmd
        assert "5433" in cmd
        assert "myuser" in cmd
        assert "mydb" in cmd


# ---------------------------------------------------------------------------
# restore_db
# ---------------------------------------------------------------------------

_PATCH_RESTORE_RUN = (
    "setup_app.management.commands.restore_db.subprocess.run"
)


class RestoreDbCommandTests(TestCase):
    """Tests for the restore_db management command."""

    @override_settings(DATABASES=_DB_SETTINGS, BASE_DIR="/tmp")
    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            call_command("restore_db", "nonexistent_backup.dump")

    @override_settings(DATABASES=_DB_SETTINGS)
    def test_restore_dump_format_calls_pg_restore(self):
        with tempfile.TemporaryDirectory() as base:
            backup_dir = Path(base) / "database" / "backups"
            backup_dir.mkdir(parents=True)
            (backup_dir / "backup.dump").touch()

            with override_settings(BASE_DIR=base):
                with patch(_PATCH_RESTORE_RUN) as mock_run:
                    out = StringIO()
                    call_command("restore_db", "backup.dump", stdout=out)

        cmd = mock_run.call_args[0][0]
        assert "pg_restore" in cmd
        assert "-d" in cmd

    @override_settings(DATABASES=_DB_SETTINGS)
    def test_restore_sql_format_calls_psql(self):
        with tempfile.TemporaryDirectory() as base:
            backup_dir = Path(base) / "database" / "backups"
            backup_dir.mkdir(parents=True)
            (backup_dir / "backup.sql").touch()

            with override_settings(BASE_DIR=base):
                with patch(_PATCH_RESTORE_RUN) as mock_run:
                    call_command("restore_db", "backup.sql", stdout=StringIO())

        cmd = mock_run.call_args[0][0]
        assert "psql" in cmd

    @override_settings(DATABASES=_INCOMPLETE_DB)
    def test_incomplete_db_config_raises(self):
        with tempfile.TemporaryDirectory() as base:
            backup_dir = Path(base) / "database" / "backups"
            backup_dir.mkdir(parents=True)
            (backup_dir / "backup.dump").touch()

            with override_settings(BASE_DIR=base):
                with pytest.raises(RuntimeError, match="incomplete"):
                    call_command("restore_db", "backup.dump")

    @override_settings(DATABASES=_DB_SETTINGS)
    def test_unsupported_format_raises(self):
        with tempfile.TemporaryDirectory() as base:
            backup_dir = Path(base) / "database" / "backups"
            backup_dir.mkdir(parents=True)
            (backup_dir / "backup.tar.gz").touch()

            with override_settings(BASE_DIR=base):
                with pytest.raises(RuntimeError, match="suportado"):
                    call_command("restore_db", "backup.tar.gz")

    @override_settings(DATABASES=_DB_SETTINGS)
    def test_pg_restore_not_found_raises(self):
        with tempfile.TemporaryDirectory() as base:
            backup_dir = Path(base) / "database" / "backups"
            backup_dir.mkdir(parents=True)
            (backup_dir / "backup.dump").touch()

            with override_settings(BASE_DIR=base):
                with patch(
                    _PATCH_RESTORE_RUN,
                    side_effect=FileNotFoundError("pg_restore not found"),
                ):
                    with pytest.raises(RuntimeError, match="pg_restore"):
                        call_command("restore_db", "backup.dump")

    @override_settings(DATABASES=_DB_SETTINGS)
    def test_subprocess_error_raises(self):
        with tempfile.TemporaryDirectory() as base:
            backup_dir = Path(base) / "database" / "backups"
            backup_dir.mkdir(parents=True)
            (backup_dir / "backup.dump").touch()

            with override_settings(BASE_DIR=base):
                with patch(
                    _PATCH_RESTORE_RUN,
                    side_effect=subprocess.CalledProcessError(
                        1, "pg_restore"
                    ),
                ):
                    with pytest.raises(RuntimeError, match="restore"):
                        call_command("restore_db", "backup.dump")

    @override_settings(DATABASES=_DB_SETTINGS)
    def test_restore_succeeds(self):
        with tempfile.TemporaryDirectory() as base:
            backup_dir = Path(base) / "database" / "backups"
            backup_dir.mkdir(parents=True)
            (backup_dir / "backup.dump").touch()

            with override_settings(BASE_DIR=base):
                with patch(_PATCH_RESTORE_RUN) as mock_run:
                    out = StringIO()
                    call_command("restore_db", "backup.dump", stdout=out)

        assert mock_run.called
        assert "conclu" in out.getvalue().lower()


# ---------------------------------------------------------------------------
# sync_env_from_setup
# ---------------------------------------------------------------------------

_PATCH_FTS = (
    "setup_app.management.commands.sync_env_from_setup.FirstTimeSetup"
)
_PATCH_SYNC_ENV = (
    "setup_app.management.commands.sync_env_from_setup.env_manager"
)
_PATCH_RESTART = (
    "setup_app.management.commands.sync_env_from_setup.trigger_restart"
)


class SyncEnvFromSetupCommandTests(TestCase):
    """Tests for the sync_env_from_setup management command."""

    def _make_record(self, auth_type="login", **kwargs):
        record = MagicMock()
        record.company_name = kwargs.get("company_name", "Acme")
        record.zabbix_url = kwargs.get("zabbix_url", "http://zabbix.local")
        record.maps_api_key = kwargs.get("maps_api_key", "MAPS_KEY")
        record.unique_licence = kwargs.get("unique_licence", "LIC-001")
        record.db_host = kwargs.get("db_host", "localhost")
        record.db_port = kwargs.get("db_port", "5432")
        record.db_name = kwargs.get("db_name", "appdb")
        record.db_user = kwargs.get("db_user", "postgres")
        record.db_password = kwargs.get("db_password", "secret")
        record.redis_url = kwargs.get("redis_url", "redis://localhost:6379/1")
        record.auth_type = auth_type
        record.zabbix_user = kwargs.get("zabbix_user", "Admin")
        record.zabbix_password = kwargs.get("zabbix_password", "zabbix")
        record.zabbix_api_key = kwargs.get("zabbix_api_key", "APIKEY")
        return record

    def _setup_model(self, mock_model, record):
        (
            mock_model.objects
            .filter.return_value
            .order_by.return_value
            .first.return_value
        ) = record

    @patch(_PATCH_FTS)
    def test_no_record_raises_command_error(self, mock_model):
        self._setup_model(mock_model, None)
        with pytest.raises(CommandError, match="No configured"):
            call_command("sync_env_from_setup")

    @patch(_PATCH_RESTART, return_value=False)
    @patch(_PATCH_SYNC_ENV)
    @patch(_PATCH_FTS)
    def test_login_auth_writes_user_and_password(
        self, mock_model, mock_env, mock_restart
    ):
        self._setup_model(mock_model, self._make_record(auth_type="login"))

        call_command("sync_env_from_setup", stdout=StringIO())

        payload = mock_env.write_values.call_args[0][0]
        assert payload["ZABBIX_API_USER"] == "Admin"
        assert payload["ZABBIX_API_PASSWORD"] == "zabbix"
        assert payload["ZABBIX_API_KEY"] == ""

    @patch(_PATCH_RESTART, return_value=False)
    @patch(_PATCH_SYNC_ENV)
    @patch(_PATCH_FTS)
    def test_token_auth_writes_api_key(
        self, mock_model, mock_env, mock_restart
    ):
        self._setup_model(mock_model, self._make_record(auth_type="token"))

        call_command("sync_env_from_setup", stdout=StringIO())

        payload = mock_env.write_values.call_args[0][0]
        assert payload["ZABBIX_API_KEY"] == "APIKEY"
        assert payload["ZABBIX_API_USER"] == ""
        assert payload["ZABBIX_API_PASSWORD"] == ""

    @patch(_PATCH_RESTART, return_value=False)
    @patch(_PATCH_SYNC_ENV)
    @patch(_PATCH_FTS)
    def test_db_fields_in_payload(self, mock_model, mock_env, mock_restart):
        record = self._make_record(
            db_name="mydb", db_host="db.local", db_port="5433"
        )
        self._setup_model(mock_model, record)

        call_command("sync_env_from_setup", stdout=StringIO())

        payload = mock_env.write_values.call_args[0][0]
        assert payload["DB_NAME"] == "mydb"
        assert payload["DB_HOST"] == "db.local"
        assert payload["DB_PORT"] == "5433"

    @patch(_PATCH_RESTART, return_value=True)
    @patch(_PATCH_SYNC_ENV)
    @patch(_PATCH_FTS)
    def test_restart_triggered_prints_success(
        self, mock_model, mock_env, mock_restart
    ):
        self._setup_model(mock_model, self._make_record())

        out = StringIO()
        call_command("sync_env_from_setup", stdout=out)

        assert mock_restart.called
        output = out.getvalue().lower()
        assert "restart" in output or "executed" in output

    @patch(_PATCH_RESTART, return_value=False)
    @patch(_PATCH_SYNC_ENV)
    @patch(_PATCH_FTS)
    def test_no_restart_prints_skipped(
        self, mock_model, mock_env, mock_restart
    ):
        self._setup_model(mock_model, self._make_record())

        out = StringIO()
        call_command("sync_env_from_setup", stdout=out)

        assert mock_restart.called
        assert "skipped" in out.getvalue().lower()

    @patch(_PATCH_RESTART, return_value=False)
    @patch(_PATCH_SYNC_ENV)
    @patch(_PATCH_FTS)
    def test_env_path_in_success_output(
        self, mock_model, mock_env, mock_restart
    ):
        self._setup_model(mock_model, self._make_record())
        mock_env.ENV_PATH = "/app/.env"

        out = StringIO()
        call_command("sync_env_from_setup", stdout=out)

        mock_env.write_values.assert_called_once()
        output = out.getvalue().lower()
        assert "synchronised" in output or "/app/.env" in output
