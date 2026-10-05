"""Views de configuração (EV-0017b): acesso, códigos HTTP, auditoria e tradução das exceções."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from setup_app.usecases import config as uc

API = "setup_app.api.config"


class ConfigApiTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="cfg_staff", password="pass", email="c@test.com", is_staff=True, is_active=True
        )
        self.client.force_login(self.staff)
        self._audit_patch = patch(f"{API}.ConfigurationAudit")
        self.audit = self._audit_patch.start()

    def tearDown(self):
        self._audit_patch.stop()

    def _audit_actions(self):
        return [c.kwargs["action"] for c in self.audit.log_change.call_args_list]

    # ── acesso ───────────────────────────────────────────────────────────────

    def test_non_staff_is_refused_everywhere(self):
        regular = User.objects.create_user(username="cfg_user", password="pass", email="u@t.com")
        self.client.force_login(regular)
        for url in (
            "/setup_app/api/env/",
            "/setup_app/api/config/",
            "/setup_app/api/audit-history/",
        ):
            self.assertIn(self.client.get(url).status_code, (302, 403), url)
        self.assertIn(
            self.client.post("/setup_app/api/env/update/", "{}", "application/json").status_code,
            (302, 403),
        )

    # ── .env ─────────────────────────────────────────────────────────────────

    def test_get_env_file(self):
        with patch(f"{API}.usecase.read_env_file", return_value="A=1\n"):
            resp = self.client.get("/setup_app/api/env/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {"success": True, "content": "A=1\n"})

    def test_get_env_file_too_large_is_400(self):
        with patch(f"{API}.usecase.read_env_file", side_effect=uc.EnvTooLarge("grande")):
            resp = self.client.get("/setup_app/api/env/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "grande")

    def test_update_env_file_writes_and_audits(self):
        with patch(f"{API}.usecase.write_env_file") as write:
            resp = self.client.post(
                "/setup_app/api/env/update/",
                json.dumps({"content": "A=1"}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["message"], "Env file updated.")
        write.assert_called_once_with("A=1")
        self.assertEqual(self._audit_actions(), ["update"])
        self.assertEqual(self.audit.log_change.call_args.kwargs["section"], "Env File")

    def test_update_env_file_invalid_payload_is_400(self):
        with patch(f"{API}.usecase.write_env_file", side_effect=uc.ConfigError("Invalid")):
            resp = self.client.post(
                "/setup_app/api/env/update/",
                json.dumps({"content": 5}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 400)
        self.audit.log_change.assert_not_called()

    def test_update_env_file_invalid_json_is_400(self):
        resp = self.client.post(
            "/setup_app/api/env/update/", "{nope", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "Invalid JSON data")

    def test_update_env_file_unexpected_error_is_500_and_audited(self):
        with patch(f"{API}.usecase.write_env_file", side_effect=OSError("disk")):
            resp = self.client.post(
                "/setup_app/api/env/update/",
                json.dumps({"content": "A=1"}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 500)
        self.assertIn("Failed to update env file", json.loads(resp.content)["message"])
        self.assertFalse(self.audit.log_change.call_args.kwargs["success"])

    def test_import_env_backup_uses_env_file_field(self):
        with patch(f"{API}.usecase.write_env_file") as write:
            resp = self.client.post(
                "/setup_app/api/env/import/",
                json.dumps({"env_file": "B=2"}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["message"], "Env file importado.")
        write.assert_called_once_with("B=2")
        self.assertEqual(self._audit_actions(), ["import"])

    # ── configuração ─────────────────────────────────────────────────────────

    def test_get_configuration(self):
        with patch(f"{API}.usecase.get_configuration", return_value={"DEBUG": False}):
            resp = self.client.get("/setup_app/api/config/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["configuration"], {"DEBUG": False})

    def test_get_configuration_error_is_500(self):
        with patch(f"{API}.usecase.get_configuration", side_effect=RuntimeError("x")):
            resp = self.client.get("/setup_app/api/config/")
        self.assertEqual(resp.status_code, 500)

    def _result(self, **over):
        base = {
            "restart_triggered": False,
            "backup_created": False,
            "backup_filename": "",
            "gdrive_upload": {},
            "ftp_upload": {},
            "backup_error": "",
        }
        base.update(over)
        return base

    def _update(self, body):
        return self.client.post(
            "/setup_app/api/config/update/", json.dumps(body), content_type="application/json"
        )

    def test_update_configuration_ok(self):
        with patch(f"{API}.usecase.update_configuration", return_value=self._result()) as upd:
            resp = self._update({"MAP_THEME": "dark"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["message"], "Configuration updated successfully")
        self.assertFalse(data["backup_warning"])
        upd.assert_called_once_with({"MAP_THEME": "dark"})
        self.assertEqual(self._audit_actions(), ["update"])

    def test_update_configuration_missing_fields_is_400(self):
        with patch(
            f"{API}.usecase.update_configuration",
            side_effect=uc.MissingRequiredFields(["DB_HOST"]),
        ):
            resp = self._update({})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("DB_HOST", json.loads(resp.content)["message"])
        self.audit.log_change.assert_not_called()

    def test_update_configuration_backup_error_is_warning_200(self):
        with patch(
            f"{API}.usecase.update_configuration",
            return_value=self._result(backup_error="pg_dump não encontrado"),
        ):
            resp = self._update({"BACKUP_ZIP_PASSWORD": "senha-nova-8"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["backup_warning"])
        self.assertIn("pg_dump não encontrado", data["backup_message"])
        self.assertIn("pg_dump não encontrado", data["message"])
        self.assertEqual(self._audit_actions(), ["backup", "update"])

    def test_update_configuration_invalid_json_is_400(self):
        resp = self.client.post(
            "/setup_app/api/config/update/", "{nope", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_update_configuration_unexpected_error_is_500(self):
        with patch(f"{API}.usecase.update_configuration", side_effect=RuntimeError("boom")):
            resp = self._update({})
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(self.audit.log_change.call_args.kwargs["success"])

    # ── export / import ──────────────────────────────────────────────────────

    def test_export_is_attachment_and_redacted(self):
        with patch.object(
            uc.env_manager,
            "read_values",
            return_value={"ZABBIX_API_URL": "http://z", "ZABBIX_API_PASSWORD": "s3cr3t"},
        ):
            resp = self.client.get("/setup_app/api/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/json")
        self.assertIn('filename="mapsprove_config.json"', resp["Content-Disposition"])
        data = json.loads(resp.content)
        self.assertEqual(data["exported_by"], "cfg_staff")
        self.assertEqual(data["configuration"]["ZABBIX_API_PASSWORD"], uc.REDACTED)
        self.assertNotIn("s3cr3t", resp.content.decode())
        self.assertEqual(self._audit_actions(), ["export"])

    def test_import_without_file_is_400(self):
        resp = self.client.post("/setup_app/api/import/", {})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "No file uploaded")

    def test_import_invalid_json_file_is_400(self):
        upload = SimpleUploadedFile("c.json", b"{nope", content_type="application/json")
        resp = self.client.post("/setup_app/api/import/", {"config_file": upload})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "Invalid JSON file")

    def test_import_wrong_shape_is_400(self):
        upload = SimpleUploadedFile("c.json", json.dumps({"x": 1}).encode())
        with patch.object(uc.env_manager, "write_values") as write:
            resp = self.client.post("/setup_app/api/import/", {"config_file": upload})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "Invalid configuration file format")
        write.assert_not_called()

    def test_import_writes_filtered_keys_and_audits(self):
        payload = {"configuration": {"MAP_THEME": "dark", "SECRET_KEY": uc.REDACTED, "X": ""}}
        upload = SimpleUploadedFile("c.json", json.dumps(payload).encode())
        with patch.object(uc.env_manager, "write_values") as write:
            resp = self.client.post("/setup_app/api/import/", {"config_file": upload})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["imported_keys"], ["MAP_THEME"])
        self.assertIn("1 settings updated", data["message"])
        write.assert_called_once_with({"MAP_THEME": "dark"})
        self.assertEqual(self._audit_actions(), ["import"])
        self.assertEqual(self.audit.log_change.call_args.kwargs["new_value"], "Imported 1 settings")

    # ── auditoria ────────────────────────────────────────────────────────────

    def test_audit_history_passes_limit_and_section(self):
        with patch(f"{API}.usecase.get_audit_history", return_value=[]) as hist:
            resp = self.client.get("/setup_app/api/audit-history/?limit=5&section=Backups")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {"success": True, "audits": []})
        hist.assert_called_once_with(5, "Backups")

    def test_audit_history_bad_limit_is_500(self):
        resp = self.client.get("/setup_app/api/audit-history/?limit=abc")
        self.assertEqual(resp.status_code, 500)
