"""Views dos testes de ligação (EV-0017e): auditoria, códigos HTTP e campos extra na resposta."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from setup_app.usecases import connections as uc

API = "setup_app.api.connections"


class ConnectionsApiTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="cx_staff", password="pass", email="c@t.com", is_staff=True, is_active=True
        )
        self.client.force_login(self.staff)
        self.audit = patch(f"{API}.ConfigurationAudit").start()
        self.addCleanup(patch.stopall)

    def _post(self, url, body):
        return self.client.post(url, json.dumps(body), content_type="application/json")

    def test_non_staff_refused_and_get_not_allowed(self):
        regular = User.objects.create_user(username="cx_user", password="pass", email="u@t.com")
        self.client.force_login(regular)
        self.assertIn(self._post("/setup_app/api/test-zabbix/", {}).status_code, (302, 403))
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/setup_app/api/test-zabbix/").status_code, 405)

    def test_success_audits_and_merges_result(self):
        with patch(
            f"{API}.usecase.test_zabbix",
            return_value={"message": "ok", "version": "7", "status": "online"},
        ):
            resp = self._post("/setup_app/api/test-zabbix/", {"zabbix_api_url": "http://z"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content),
            {"success": True, "message": "ok", "version": "7", "status": "online"},
        )
        kwargs = self.audit.log_change.call_args.kwargs
        self.assertEqual(
            (kwargs["action"], kwargs["section"], kwargs["success"]), ("test", "Zabbix", True)
        )

    def test_audited_failure_with_extra(self):
        err = uc.ConnectionTestError(
            "Conexão OK, mas a autenticação falhou.",
            audit="Login failed",
            status="auth_failed",
            version="7",
        )
        with patch(f"{API}.usecase.test_zabbix", side_effect=err):
            resp = self._post("/setup_app/api/test-zabbix/", {"zabbix_api_url": "http://z"})
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertEqual(data["status"], "auth_failed")
        self.assertEqual(data["version"], "7")
        kwargs = self.audit.log_change.call_args.kwargs
        self.assertFalse(kwargs["success"])
        self.assertEqual(kwargs["error_message"], "Login failed")

    def test_validation_failure_not_audited(self):
        with patch(
            f"{API}.usecase.test_database",
            side_effect=uc.ConnectionTestError("All database fields are required except password"),
        ):
            resp = self._post("/setup_app/api/test-database/", {})
        self.assertEqual(resp.status_code, 400)
        self.audit.log_change.assert_not_called()

    def test_sections_per_route(self):
        for url, fn, section in (
            ("/setup_app/api/test-database/", "test_database", "Database"),
            ("/setup_app/api/test-redis/", "test_redis", "Redis"),
            ("/setup_app/api/test-ftp/", "test_ftp", "FTP"),
            ("/setup_app/api/test-smtp/", "test_smtp", "SMTP"),
        ):
            self.audit.reset_mock()
            with patch(f"{API}.usecase.{fn}", return_value={"message": "ok"}):
                resp = self._post(url, {})
            self.assertEqual(resp.status_code, 200, url)
            self.assertEqual(self.audit.log_change.call_args.kwargs["section"], section)

    def test_invalid_json_and_server_error(self):
        resp = self.client.post(
            "/setup_app/api/test-redis/", "{bad", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "Invalid JSON data")
        with patch(f"{API}.usecase.test_redis", side_effect=RuntimeError("boom")):
            resp = self._post("/setup_app/api/test-redis/", {"redis_url": "redis://x"})
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(json.loads(resp.content)["message"], "Server error: boom")

    def test_sms_passthrough_without_audit(self):
        with patch(
            f"{API}.usecase.test_sms", return_value={"success": False, "message": "pendente"}
        ):
            resp = self._post("/setup_app/api/test-sms/", {})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {"success": False, "message": "pendente"})
        with patch(
            f"{API}.usecase.test_sms", side_effect=uc.ConnectionTestError("Telefone inválido.")
        ):
            resp = self._post("/setup_app/api/test-sms/", {})
        self.assertEqual(resp.status_code, 400)
        self.audit.log_change.assert_not_called()
