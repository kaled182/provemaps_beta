"""Usecases dos testes de ligação (EV-0017e): Zabbix, PostgreSQL, Redis, FTP, SMTP, SMS."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase

from setup_app.usecases import connections as uc

UC = "setup_app.usecases.connections"


def _resp(payload: dict, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    return r


class ZabbixTests(SimpleTestCase):
    def test_url_required(self):
        with self.assertRaises(uc.ConnectionTestError) as ctx:
            uc.test_zabbix({})
        self.assertEqual(str(ctx.exception), "Zabbix URL is required")
        self.assertIsNone(ctx.exception.audit)

    def test_login_ok(self):
        with patch(f"{UC}.requests.post") as post:
            post.side_effect = [_resp({"result": "7.0.1"}), _resp({"result": "sessiontoken"})]
            result = uc.test_zabbix(
                {
                    "zabbix_api_url": "http://z/api",
                    "zabbix_api_user": "u",
                    "zabbix_api_password": "p",
                }
            )
        self.assertEqual(
            result,
            {"message": "Serviço online. Zabbix v7.0.1.", "version": "7.0.1", "status": "online"},
        )
        self.assertEqual(post.call_args_list[1].kwargs["json"]["method"], "user.login")
        self.assertEqual(post.call_args_list[0].kwargs["timeout"], uc.ZABBIX_TIMEOUT)

    def test_login_missing_credentials(self):
        with patch(f"{UC}.requests.post", return_value=_resp({"result": "7.0"})):
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_zabbix({"zabbix_api_url": "http://z"})
        self.assertEqual(ctx.exception.audit, "Missing username/password")
        self.assertEqual(ctx.exception.extra, {"status": "auth_missing", "version": "7.0"})

    def test_login_failed(self):
        with patch(f"{UC}.requests.post") as post:
            post.side_effect = [_resp({"result": "7.0"}), _resp({"error": {"message": "bad"}})]
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_zabbix(
                    {
                        "zabbix_api_url": "http://z",
                        "zabbix_api_user": "u",
                        "zabbix_api_password": "p",
                    }
                )
        self.assertEqual(str(ctx.exception), "Conexão OK, mas a autenticação falhou.")
        self.assertEqual(ctx.exception.audit, "Login failed")

    def test_token_bearer_header_and_invalid(self):
        with patch(f"{UC}.requests.post") as post:
            post.side_effect = [
                _resp({"result": "7.0"}),
                _resp({"error": {"message": "Not authorized"}}),
            ]
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_zabbix(
                    {"zabbix_api_url": "http://z", "auth_type": "token", "zabbix_api_key": "K"}
                )
        self.assertEqual(post.call_args_list[1].kwargs["headers"]["Authorization"], "Bearer K")
        self.assertEqual(ctx.exception.extra["status"], "auth_failed")
        self.assertEqual(ctx.exception.extra["error_detail"], "Not authorized")
        self.assertEqual(ctx.exception.audit, "Invalid API token: Not authorized")

    def test_api_error_and_offline(self):
        with patch(f"{UC}.requests.post", return_value=_resp({"error": {"data": "boom"}})):
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_zabbix({"zabbix_api_url": "http://z"})
        self.assertEqual(str(ctx.exception), "Serviço respondeu com erro: boom")
        self.assertEqual(ctx.exception.extra, {"status": "api_error"})
        with patch(f"{UC}.requests.post", side_effect=requests.ConnectionError("refused")):
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_zabbix({"zabbix_api_url": "http://z"})
        self.assertEqual(str(ctx.exception), "Serviço offline: refused")
        self.assertEqual(ctx.exception.extra, {"status": "offline"})


class DatabaseRedisFtpTests(SimpleTestCase):
    def test_database_validation_and_success(self):
        with self.assertRaises(uc.ConnectionTestError):
            uc.test_database({"db_host": "h"})
        fake = types.SimpleNamespace()
        conn = MagicMock()
        conn.cursor.return_value.fetchone.return_value = (
            "PostgreSQL 16.1 on x86, compiled by gcc",
        )
        fake.connect = MagicMock(return_value=conn)
        with patch.dict(sys.modules, {"psycopg2": fake}):
            result = uc.test_database(
                {
                    "db_host": "h",
                    "db_port": "5432",
                    "db_name": "n",
                    "db_user": "u",
                    "db_password": "p",
                }
            )
        self.assertEqual(
            result,
            {
                "message": "Connection successful! PostgreSQL 16.1 on x86",
                "version": "PostgreSQL 16.1 on x86",
            },
        )
        self.assertEqual(fake.connect.call_args.kwargs["connect_timeout"], uc.DB_CONNECT_TIMEOUT)
        fake.connect.side_effect = RuntimeError("auth")
        with patch.dict(sys.modules, {"psycopg2": fake}):
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_database({"db_host": "h", "db_port": "1", "db_name": "n", "db_user": "u"})
        self.assertEqual(str(ctx.exception), "Connection failed: auth")
        self.assertEqual(ctx.exception.audit, "auth")

    def test_redis(self):
        with self.assertRaises(uc.ConnectionTestError):
            uc.test_redis({})
        fake = types.SimpleNamespace()
        client = MagicMock()
        client.info.return_value = {"redis_version": "7.2"}
        fake.Redis = MagicMock(return_value=client)
        with patch.dict(sys.modules, {"redis": fake}):
            result = uc.test_redis({"redis_url": "redis://:pw@cache:6380/3"})
        self.assertEqual(result["version"], "7.2")
        kwargs = fake.Redis.call_args.kwargs
        self.assertEqual(
            (kwargs["host"], kwargs["port"], kwargs["db"], kwargs["password"]),
            ("cache", 6380, 3, "pw"),
        )
        client.ping.side_effect = RuntimeError("down")
        with patch.dict(sys.modules, {"redis": fake}):
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_redis({"redis_url": "redis://x"})
        self.assertEqual(ctx.exception.audit, "down")

    def test_ftp_env_fallback_and_errors(self):
        with patch(f"{UC}.env_manager.read_values", return_value={}):
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_ftp({})
        self.assertEqual(str(ctx.exception), "FTP host is required.")
        ftp = MagicMock()
        ftp.pwd.return_value = "/backups"
        env = {
            "FTP_HOST": "ftp.local",
            "FTP_PORT": "x",
            "FTP_USER": "u",
            "FTP_PASSWORD": "p",
            "FTP_PATH": "/backups",
        }
        with (
            patch(f"{UC}.env_manager.read_values", return_value=env),
            patch(f"{UC}.ftplib.FTP", return_value=ftp),
        ):
            result = uc.test_ftp({})
        self.assertEqual(result, {"message": "Connection successful! PWD: /backups"})
        ftp.connect.assert_called_once_with(host="ftp.local", port=21, timeout=uc.FTP_TIMEOUT)
        ftp.login.assert_called_once_with(user="u", passwd="p")
        ftp.cwd.assert_called_once_with("/backups")
        ftp.connect.side_effect = OSError("refused")
        with patch(f"{UC}.ftplib.FTP", return_value=ftp):
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_ftp({"ftp_host": "h", "ftp_port": "2121"})
        self.assertEqual(ctx.exception.audit, "refused")


class SmtpTests(SimpleTestCase):
    def setUp(self):
        patch(f"{UC}.env_manager.read_values", return_value={}).start()
        self.addCleanup(patch.stopall)

    def test_missing_fields(self):
        with self.assertRaises(uc.ConnectionTestError) as ctx:
            uc.test_smtp({"smtp_host": "h"})
        self.assertEqual(
            str(ctx.exception), "Campos obrigatórios ausentes: remetente, destinatário."
        )

    def test_oauth_validation_before_connecting(self):
        base = {
            "smtp_host": "h",
            "smtp_from_email": "a@b",
            "smtp_test_recipient": "c@d",
            "smtp_auth_mode": "oauth",
        }
        with patch(f"{UC}.smtplib.SMTP") as smtp:
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_smtp(base)
            self.assertIn("usuário (email)", str(ctx.exception))
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_smtp({**base, "smtp_user": "u@b"})
            self.assertIn("Client ID", str(ctx.exception))
        smtp.assert_not_called()

    def test_tls_login_and_send(self):
        server = MagicMock()
        with patch(f"{UC}.smtplib.SMTP", return_value=server) as smtp:
            result = uc.test_smtp(
                {
                    "smtp_host": "mail",
                    "smtp_security": "TLS",
                    "smtp_user": "u@b",
                    "smtp_password": "pw",
                    "smtp_test_recipient": "c@d",
                    "smtp_from_name": "Prove",
                }
            )
        self.assertEqual(result, {"message": "Email enviado com sucesso."})
        smtp.assert_called_once_with(host="mail", port=587, timeout=uc.SMTP_TIMEOUT)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("u@b", "pw")
        msg = server.send_message.call_args.args[0]
        self.assertEqual(msg["From"], "Prove <u@b>")  # remetente cai no utilizador
        self.assertEqual(msg["To"], "c@d")

    def test_ssl_default_port_and_gmail_hint(self):
        server = MagicMock()
        server.send_message.side_effect = RuntimeError(
            "535 5.7.8 Username and Password not accepted"
        )
        with patch(f"{UC}.smtplib.SMTP_SSL", return_value=server) as smtp_ssl:
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_smtp(
                    {
                        "smtp_host": "smtp.gmail.com",
                        "smtp_security": "ssl",
                        "smtp_from_email": "a@b",
                        "smtp_test_recipient": "c@d",
                    }
                )
        self.assertEqual(smtp_ssl.call_args.kwargs["port"], 465)
        self.assertEqual(
            str(ctx.exception), f"Falha ao enviar email: {uc.GMAIL_BAD_CREDENTIALS_HINT}"
        )
        self.assertIn("5.7.8", ctx.exception.audit)


class SmsTests(SimpleTestCase):
    def setUp(self):
        patch(f"{UC}.env_manager.read_values", return_value={}).start()
        self.addCleanup(patch.stopall)

    def test_normalize_br_phone(self):
        self.assertEqual(uc.normalize_br_phone("(11) 99999-8888"), "5511999998888")
        self.assertEqual(uc.normalize_br_phone("+55 11 99999-8888"), "5511999998888")
        self.assertEqual(uc.normalize_br_phone("1133334444"), "551133334444")
        self.assertEqual(uc.normalize_br_phone("123"), "")
        self.assertEqual(uc.normalize_br_phone(""), "")

    def test_invalid_phone(self):
        with self.assertRaises(uc.ConnectionTestError) as ctx:
            uc.test_sms({"sms_test_recipient": "12"})
        self.assertIn("Telefone inválido", str(ctx.exception))

    def test_smsnet_requires_credentials_and_sends(self):
        with self.assertRaises(uc.ConnectionTestError) as ctx:
            uc.test_sms({"sms_test_recipient": "11999998888"})
        self.assertEqual(str(ctx.exception), "Usuário e senha são obrigatórios para SMSNET.")
        with patch(f"{UC}.requests.get", return_value=_resp({}, 200)) as get:
            result = uc.test_sms(
                {
                    "sms_test_recipient": "11999998888",
                    "sms_username": "u",
                    "sms_password": "p",
                    "sms_priority": "1",
                }
            )
        self.assertEqual(result, {"success": True, "message": "SMS enviado com sucesso (SMSNET)."})
        self.assertEqual(get.call_args.args[0], uc.SMSNET_DEFAULT_URL)
        self.assertEqual(get.call_args.kwargs["params"]["to"], "5511999998888")
        self.assertEqual(get.call_args.kwargs["params"]["priority"], "1")
        with patch(f"{UC}.requests.get", return_value=_resp({}, 500)):
            with self.assertRaises(uc.ConnectionTestError) as ctx:
                uc.test_sms(
                    {"sms_test_recipient": "11999998888", "sms_username": "u", "sms_password": "p"}
                )
        self.assertEqual(str(ctx.exception), "Falha no envio SMSNET: HTTP 500.")

    def test_pending_providers_and_unknown(self):
        base = {"sms_test_recipient": "11999998888"}
        result = uc.test_sms({**base, "sms_provider": "zenvia"})
        self.assertFalse(result["success"])
        self.assertIn("Zenvia", result["message"])
        with self.assertRaises(uc.ConnectionTestError) as ctx:
            uc.test_sms({**base, "sms_provider": "aws_sns", "sms_aws_region": "us-east-1"})
        self.assertEqual(
            str(ctx.exception), "Campos obrigatórios ausentes: access key, secret key."
        )
        result = uc.test_sms(
            {
                **base,
                "sms_provider": "infobip",
                "sms_infobip_base_url": "http://i",
                "sms_api_token": "t",
            }
        )
        self.assertIn("Infobip", result["message"])
        with self.assertRaises(uc.ConnectionTestError) as ctx:
            uc.test_sms({**base, "sms_provider": "pigeon"})
        self.assertEqual(str(ctx.exception), "Provedor SMS não reconhecido.")
