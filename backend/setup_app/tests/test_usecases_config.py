"""Usecases de configuração (EV-0017b): .env, leitura com fallback, export/import, auditoria."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase

from setup_app.models_audit import ConfigurationAudit
from setup_app.usecases import config as uc


class EnvFileUsecaseTests(TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.env_path = Path(self._tmp.name) / "nested" / ".env"
        self._path_patch = patch.object(uc.env_manager, "ENV_PATH", self.env_path)
        self._path_patch.start()
        self._reload_patch = patch.object(uc, "_reload_runtime")
        self.reload = self._reload_patch.start()

    def tearDown(self):
        self._reload_patch.stop()
        self._path_patch.stop()
        self._tmp.cleanup()

    def test_read_missing_file_is_empty_string(self):
        self.assertEqual(uc.read_env_file(), "")

    def test_read_returns_content(self):
        self.env_path.parent.mkdir(parents=True)
        self.env_path.write_text("A=1\n", encoding="utf-8")
        self.assertEqual(uc.read_env_file(), "A=1\n")

    def test_read_too_large_raises(self):
        self.env_path.parent.mkdir(parents=True)
        self.env_path.write_text("x" * (uc.ENV_MAX_BYTES + 1), encoding="utf-8")
        with self.assertRaises(uc.EnvTooLarge):
            uc.read_env_file()

    def test_write_creates_parent_adds_newline_and_reloads(self):
        uc.write_env_file("A=1")
        self.assertEqual(self.env_path.read_text(encoding="utf-8"), "A=1\n")
        self.reload.assert_called_once()

    def test_write_empty_content_stays_empty(self):
        uc.write_env_file("")
        self.assertEqual(self.env_path.read_text(encoding="utf-8"), "")

    def test_write_rejects_non_string(self):
        with self.assertRaises(uc.ConfigError):
            uc.write_env_file({"not": "a string"})
        self.assertFalse(self.env_path.exists())
        self.reload.assert_not_called()

    def test_write_rejects_too_large(self):
        with self.assertRaises(uc.EnvTooLarge):
            uc.write_env_file("x" * (uc.ENV_MAX_BYTES + 1))
        self.assertFalse(self.env_path.exists())


def _runtime_config(**overrides) -> MagicMock:
    rc = MagicMock()
    for key in [*uc.EDITABLE_KEYS, "GDRIVE_OAUTH_REFRESH_TOKEN"]:
        setattr(rc, key.lower(), "")
    rc.allowed_hosts = ["a.test", "b.test"]
    rc.optical_rx_warning_threshold = -24.0
    rc.optical_rx_critical_threshold = -27.0
    rc.optical_thresholds_by_distance = {}
    rc.diagnostics_enabled = False
    rc.ftp_enabled = False
    rc.gdrive_enabled = False
    rc.smtp_enabled = False
    rc.sms_enabled = False
    for k, v in overrides.items():
        setattr(rc, k, v)
    return rc


class GetConfigurationUsecaseTests(TestCase):
    def _get(self, env_values: dict, record=None, **rc_overrides):
        with (
            patch.object(uc.env_manager, "read_values") as read_values,
            patch.object(uc.runtime_settings, "get_runtime_config") as get_rc,
            patch.object(uc, "_db_record", return_value=record),
        ):
            read_values.side_effect = lambda keys: {
                k: env_values[k] for k in keys if k in env_values
            }
            get_rc.return_value = _runtime_config(**rc_overrides)
            return uc.get_configuration()

    def test_all_editable_keys_present_plus_oauth_flag(self):
        data = self._get({})
        for key in uc.EDITABLE_KEYS:
            self.assertIn(key, data)
        self.assertIn("GDRIVE_OAUTH_CONNECTED", data)
        self.assertFalse(data["GDRIVE_OAUTH_CONNECTED"])

    def test_env_value_wins_over_fallback(self):
        data = self._get({"ZABBIX_API_URL": "http://env.test"}, zabbix_api_url="http://db.test")
        self.assertEqual(data["ZABBIX_API_URL"], "http://env.test")

    def test_fallback_used_when_env_empty(self):
        data = self._get({"ZABBIX_API_URL": ""}, zabbix_api_url="http://db.test")
        self.assertEqual(data["ZABBIX_API_URL"], "http://db.test")
        self.assertEqual(data["ALLOWED_HOSTS"], "a.test,b.test")
        self.assertEqual(data["MAP_PROVIDER"], "google")

    def test_bool_keys_are_real_booleans(self):
        data = self._get({"DEBUG": "True", "ENABLE_TRAFFIC": "false", "FTP_ENABLED": "yes"})
        self.assertIs(data["DEBUG"], True)
        self.assertIs(data["ENABLE_TRAFFIC"], False)
        # só "true" (qualquer caixa) conta como verdadeiro no .env
        self.assertIs(data["FTP_ENABLED"], False)
        for key in uc.BOOL_KEYS:
            self.assertIsInstance(data[key], bool, key)

    def test_db_authoritative_keys_ignore_env(self):
        # Código antigo deixou defaults no .env; o que o utilizador gravou está na base.
        record = MagicMock(
            map_provider="mapbox",
            mapbox_token="pk.db",
            map_default_zoom=9,
            map_default_lat=-16.5,
            map_default_lng=-49.25,
        )
        data = self._get(
            {"MAP_PROVIDER": "google", "MAP_DEFAULT_LAT": "-15.7801", "MAP_DEFAULT_ZOOM": "12"},
            record=record,
        )
        self.assertEqual(data["MAP_PROVIDER"], "mapbox")
        self.assertEqual(data["MAPBOX_TOKEN"], "pk.db")
        self.assertEqual(data["MAP_DEFAULT_ZOOM"], "9")
        self.assertEqual(data["MAP_DEFAULT_LAT"], "-16.5")
        self.assertEqual(data["MAP_DEFAULT_LNG"], "-49.25")

    def test_db_authoritative_keys_fall_back_without_record(self):
        data = self._get({"MAP_DEFAULT_LAT": "-1"}, record=None, map_provider="osm")
        self.assertEqual(data["MAP_PROVIDER"], "osm")
        self.assertEqual(data["MAP_DEFAULT_LAT"], "-15.7801")  # o .env não conta

    def test_optical_thresholds_come_from_runtime_config(self):
        data = self._get(
            {},
            optical_rx_warning_threshold=-22.5,
            optical_rx_critical_threshold=-26.0,
            optical_thresholds_by_distance={"10": {"warning": -19, "critical": -27}},
        )
        self.assertEqual(data["OPTICAL_RX_WARNING_THRESHOLD"], "-22.5")
        self.assertEqual(data["OPTICAL_RX_CRITICAL_THRESHOLD"], "-26.0")
        by_distance = data["OPTICAL_THRESHOLDS_BY_DISTANCE"]
        self.assertEqual(by_distance["10"], {"warning": -19.0, "critical": -27.0})
        self.assertEqual(by_distance["40"], uc.DEFAULT_DISTANCE_THRESHOLDS["40"])

    def test_oauth_connected_when_refresh_token_present(self):
        data = self._get({"GDRIVE_OAUTH_REFRESH_TOKEN": "tok"})
        self.assertTrue(data["GDRIVE_OAUTH_CONNECTED"])
        self.assertNotIn("GDRIVE_OAUTH_REFRESH_TOKEN", data)


class ExportImportUsecaseTests(TestCase):
    def test_export_redacts_sensitive_and_excludes_db_password(self):
        values = {k: f"v-{k}" for k in uc.EXPORT_KEYS}
        with patch.object(uc.env_manager, "read_values", return_value=values):
            data = uc.export_configuration("paulo")
        self.assertEqual(data["version"], "1.0")
        self.assertEqual(data["exported_by"], "paulo")
        self.assertIn("exported_at", data)
        conf = data["configuration"]
        self.assertEqual(conf["ZABBIX_API_PASSWORD"], uc.REDACTED)
        self.assertEqual(conf["SECRET_KEY"], uc.REDACTED)
        self.assertEqual(conf["ZABBIX_API_URL"], "v-ZABBIX_API_URL")
        for key in uc._EXPORT_EXCLUDED:
            self.assertNotIn(key, conf)

    def test_export_keeps_empty_sensitive_values_empty(self):
        with patch.object(uc.env_manager, "read_values", return_value={"SECRET_KEY": ""}):
            data = uc.export_configuration("x")
        self.assertEqual(data["configuration"]["SECRET_KEY"], "")

    def test_import_filters_empty_and_redacted(self):
        content = json.dumps(
            {
                "configuration": {
                    "ZABBIX_API_URL": "http://z",
                    "SECRET_KEY": uc.REDACTED,
                    "MAP_THEME": "",
                    "DEBUG": "False",
                }
            }
        )
        with patch.object(uc.env_manager, "write_values") as write_values:
            imported = uc.import_configuration(content)
        self.assertEqual(sorted(imported), ["DEBUG", "ZABBIX_API_URL"])
        write_values.assert_called_once_with({"ZABBIX_API_URL": "http://z", "DEBUG": "False"})

    def test_import_rejects_wrong_shape(self):
        with patch.object(uc.env_manager, "write_values") as write_values:
            with self.assertRaises(uc.ConfigError):
                uc.import_configuration(json.dumps({"foo": 1}))
            with self.assertRaises(uc.ConfigError):
                uc.import_configuration(json.dumps([1, 2]))
        write_values.assert_not_called()

    def test_import_invalid_json_propagates(self):
        with self.assertRaises(json.JSONDecodeError):
            uc.import_configuration("{not json")


class AuditHistoryUsecaseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aud", password="p", is_staff=True)
        for i, section in enumerate(["Backups", "Env File", "Backups"]):
            ConfigurationAudit.objects.create(
                user=self.user if i else None,
                action="update",
                section=section,
                field_name=f"f{i}",
                success=True,
            )

    def test_returns_dicts_with_expected_fields(self):
        audits = uc.get_audit_history()
        self.assertEqual(len(audits), 3)
        first = audits[0]
        for key in (
            "id",
            "user",
            "action",
            "section",
            "field_name",
            "old_value",
            "new_value",
            "success",
            "error_message",
            "timestamp",
            "ip_address",
        ):
            self.assertIn(key, first)
        self.assertIn("Anonymous", [a["user"] for a in audits])

    def test_section_filter_and_limit(self):
        self.assertEqual(len(uc.get_audit_history(section="Backups")), 2)
        self.assertEqual(len(uc.get_audit_history(limit=1)), 1)
        self.assertEqual(uc.get_audit_history(section="Nada"), [])


class UpdateConfigurationUsecaseTests(TestCase):
    env_contents: dict = {}

    def _run(self, data, *, existing_password="", backup_cmd=None, backup_raises=None):
        rc = _runtime_config(
            zabbix_api_url="http://zabbix.test",
            db_host="db",
            db_port="5432",
            db_name="app",
            db_user="app",
        )
        record = MagicMock(backup_password=existing_password) if existing_password else None
        with (
            patch.object(uc.env_manager, "read_values", return_value={}),
            patch.object(uc.env_manager, "read_env", return_value=self.env_contents),
            patch.object(uc.env_manager, "write_values") as self.write_values,
            patch.object(uc.runtime_settings, "get_runtime_config", return_value=rc),
            patch.object(uc.runtime_settings, "reload_config"),
            patch.object(uc, "FirstTimeSetup") as fts,
            patch.object(uc, "clear_runtime_config_cache"),
            patch.object(uc, "reload_diagnostics_flag_cache"),
            patch.object(uc, "trigger_restart", return_value=True) as restart,
            patch.object(uc, "_apply_runtime_overrides"),
            patch.object(uc, "_persist_configuration") as persist,
            patch.object(uc, "call_command") as call_command,
            patch.object(uc, "upload_backup_if_enabled", return_value={"success": False}),
            patch.object(uc, "upload_backup_via_ftp", return_value={"success": False}),
            patch("integrations.zabbix.zabbix_service.clear_token_cache"),
        ):
            fts.objects.filter.return_value.order_by.return_value.first.return_value = record
            if backup_raises:
                call_command.side_effect = backup_raises
            else:
                call_command.return_value = backup_cmd
            result = uc.update_configuration(data)
        return result, persist, call_command, restart

    def test_missing_required_fields_raise(self):
        rc = _runtime_config()  # sem nada configurado na base
        with (
            patch.object(uc.runtime_settings, "get_runtime_config", return_value=rc),
            patch.object(uc, "FirstTimeSetup") as fts,
        ):
            fts.objects.filter.return_value.order_by.return_value.first.return_value = None
            with self.assertRaises(uc.MissingRequiredFields) as ctx:
                uc.update_configuration({"ZABBIX_API_URL": "http://z"})
        self.assertIn("DB_HOST", str(ctx.exception))
        self.assertNotIn("ZABBIX_API_URL", str(ctx.exception))

    def test_short_backup_password_raises(self):
        rc = _runtime_config(
            zabbix_api_url="http://z", db_host="db", db_port="1", db_name="n", db_user="u"
        )
        with (
            patch.object(uc.runtime_settings, "get_runtime_config", return_value=rc),
            patch.object(uc, "FirstTimeSetup") as fts,
        ):
            fts.objects.filter.return_value.order_by.return_value.first.return_value = None
            with self.assertRaises(uc.ConfigError):
                uc.update_configuration({"BACKUP_ZIP_PASSWORD": "curta"})

    def test_no_password_change_persists_without_backup(self):
        result, persist, call_command, restart = self._run({"MAP_THEME": "dark"})
        persist.assert_called_once()
        payload = persist.call_args.args[0]
        self.assertEqual(payload["MAP_THEME"], "dark")
        call_command.assert_not_called()
        restart.assert_not_called()  # sem SERVICE_RESTART_COMMANDS não há restart
        self.assertEqual(
            result,
            {
                "restart_triggered": False,
                "backup_created": False,
                "backup_filename": "",
                "gdrive_upload": {},
                "ftp_upload": {},
                "backup_error": "",
            },
        )

    def test_stale_db_authoritative_keys_are_purged_from_env(self):
        self.env_contents = {"MAP_PROVIDER": "google", "MAP_DEFAULT_LAT": "-15.78", "DEBUG": "1"}
        self._run({"MAP_THEME": "dark"})
        self.write_values.assert_called_once_with({"MAP_PROVIDER": "", "MAP_DEFAULT_LAT": ""})

    def test_env_without_stale_keys_is_not_touched(self):
        self.env_contents = {"DEBUG": "1"}
        self._run({"MAP_THEME": "dark"})
        self.write_values.assert_not_called()

    def test_distance_thresholds_in_payload(self):
        _, persist, _, _ = self._run(
            {"OPTICAL_THRESHOLDS_BY_DISTANCE": {"80": {"warning": "-25", "critical": -31}}}
        )
        payload = persist.call_args.args[0]
        parsed = json.loads(payload["OPTICAL_THRESHOLDS_BY_DISTANCE"])
        self.assertEqual(parsed["80"], {"warning": -25.0, "critical": -31.0})
        self.assertEqual(parsed["10"], uc.DEFAULT_DISTANCE_THRESHOLDS["10"])

    def test_new_password_triggers_backup(self):
        result, _, call_command, _ = self._run(
            {"BACKUP_ZIP_PASSWORD": "senha-nova-8"}, backup_cmd="bk.zip"
        )
        call_command.assert_called_once_with("make_backup")
        self.assertTrue(result["backup_created"])
        self.assertEqual(result["backup_filename"], "bk.zip")
        self.assertEqual(result["backup_error"], "")

    def test_same_password_does_not_backup(self):
        _, _, call_command, _ = self._run(
            {"BACKUP_ZIP_PASSWORD": "senha-igual"}, existing_password="senha-igual"
        )
        call_command.assert_not_called()

    def test_backup_failure_is_reported_not_raised(self):
        result, persist, _, _ = self._run(
            {"BACKUP_ZIP_PASSWORD": "senha-nova-8"}, backup_raises=RuntimeError("pg_dump")
        )
        persist.assert_called_once()
        self.assertFalse(result["backup_created"])
        self.assertEqual(result["backup_error"], "pg_dump")

    def test_restart_commands_trigger_restart(self):
        result, _, _, restart = self._run({"SERVICE_RESTART_COMMANDS": "systemctl restart x"})
        restart.assert_called_once()
        self.assertTrue(result["restart_triggered"])


class ParseDistanceThresholdsTests(TestCase):
    def test_defaults_for_empty_or_garbage(self):
        self.assertEqual(uc.parse_distance_thresholds(None), uc.DEFAULT_DISTANCE_THRESHOLDS)
        self.assertEqual(uc.parse_distance_thresholds("{nope"), uc.DEFAULT_DISTANCE_THRESHOLDS)
        self.assertEqual(uc.parse_distance_thresholds([1, 2]), uc.DEFAULT_DISTANCE_THRESHOLDS)

    def test_json_string_and_bad_entries(self):
        parsed = uc.parse_distance_thresholds(
            json.dumps({"10": {"warning": "-21"}, "40": "x", "100": {"critical": None}})
        )
        self.assertEqual(parsed["10"], {"warning": -21.0, "critical": -28.0})
        self.assertEqual(parsed["40"], uc.DEFAULT_DISTANCE_THRESHOLDS["40"])
        self.assertEqual(parsed["100"], uc.DEFAULT_DISTANCE_THRESHOLDS["100"])
        self.assertEqual(set(parsed), {"10", "40", "80", "100"})
