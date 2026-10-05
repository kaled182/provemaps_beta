"""Regressão: `update_configuration` devolvia 500 depois de gravar.

A view comparava a senha de backup nova com `existing_backup_password`, que nunca
era definida — `NameError` no passo 5, apanhado pelo `except Exception` genérico,
e o utilizador via «Server error» depois de a configuração já estar escrita.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase


class UpdateConfigurationRegressionTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="upd_staff",
            password="pass",
            email="upd@test.com",
            is_staff=True,
            is_active=True,
        )
        self.client.force_login(self.staff)

    def _post(self, body):
        runtime_config = MagicMock()
        runtime_config.zabbix_api_url = "http://zabbix.test"
        runtime_config.db_host = "db"
        runtime_config.db_port = "5432"
        runtime_config.db_name = "app"
        runtime_config.db_user = "app"
        for attr in (
            "gdrive_oauth_refresh_token",
            "gdrive_oauth_user_email",
            "gdrive_oauth_client_id",
            "gdrive_oauth_client_secret",
            "smtp_password",
            "smtp_auth_mode",
            "smtp_oauth_client_id",
            "smtp_oauth_client_secret",
            "smtp_oauth_refresh_token",
            "sms_password",
            "sms_api_token",
            "sms_aws_secret_access_key",
        ):
            setattr(runtime_config, attr, "")

        with (
            patch("setup_app.usecases.config.env_manager") as mock_em,
            patch("setup_app.usecases.config.runtime_settings") as mock_rs,
            patch("setup_app.usecases.config.FirstTimeSetup") as mock_fts,
            patch("setup_app.usecases.config.clear_runtime_config_cache"),
            patch("setup_app.usecases.config.reload_diagnostics_flag_cache"),
            patch("setup_app.usecases.config.trigger_restart", return_value=False),
            patch("setup_app.usecases.config.call_command", return_value="backup.zip") as mock_cmd,
            patch(
                "setup_app.usecases.config.upload_backup_if_enabled",
                return_value={"success": False},
            ),
            patch(
                "setup_app.usecases.config.upload_backup_via_ftp", return_value={"success": False}
            ),
            patch("setup_app.api.config.ConfigurationAudit"),
            patch("integrations.zabbix.zabbix_service.clear_token_cache"),
        ):
            mock_em.read_values.return_value = {}
            mock_rs.get_runtime_config.return_value = runtime_config
            mock_fts.objects.filter.return_value.order_by.return_value.first.return_value = None
            resp = self.client.post(
                "/setup_app/api/config/update/",
                data=json.dumps(body),
                content_type="application/json",
            )
        return resp, mock_cmd

    def test_update_without_password_change_returns_200(self):
        resp, mock_cmd = self._post({"ZABBIX_API_URL": "http://zabbix.test", "DB_HOST": "db"})
        self.assertEqual(resp.status_code, 200, resp.content)
        data = json.loads(resp.content)
        self.assertTrue(data.get("success"), data)
        # Sem senha nova (e sem registo anterior) não há backup a gerar
        mock_cmd.assert_not_called()

    def test_new_backup_password_triggers_backup(self):
        resp, mock_cmd = self._post(
            {"ZABBIX_API_URL": "http://zabbix.test", "BACKUP_ZIP_PASSWORD": "segredo-forte-123"}
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        mock_cmd.assert_called_once_with("make_backup")
