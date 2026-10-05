"""Usecases de gateways (EV-0017c): defaults do .env, espelho no .env, CRUD com RBAC, QR WhatsApp."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Department
from setup_app.models import MessagingGateway
from setup_app.usecases import gateways as uc

UC = "setup_app.usecases.gateways"


def _runtime(**over) -> MagicMock:
    rt = MagicMock()
    for attr in (
        "sms_provider",
        "sms_username",
        "sms_api_url",
        "sms_sender_id",
        "sms_password",
        "sms_api_token",
        "sms_test_recipient",
        "sms_test_message",
        "sms_aws_region",
        "sms_aws_access_key_id",
        "sms_aws_secret_access_key",
        "sms_infobip_base_url",
        "sms_provider_rank",
        "smtp_host",
        "smtp_user",
        "smtp_from_email",
        "smtp_port",
        "smtp_security",
        "smtp_password",
        "smtp_auth_mode",
        "smtp_from_name",
        "smtp_test_recipient",
        "smtp_oauth_client_id",
        "smtp_oauth_client_secret",
        "smtp_oauth_refresh_token",
    ):
        setattr(rt, attr, "")
    rt.sms_enabled = False
    rt.smtp_enabled = False
    for k, v in over.items():
        setattr(rt, k, v)
    return rt


class EnsureDefaultGatewaysTests(TestCase):
    def test_nothing_created_when_env_empty(self):
        with patch(f"{UC}.runtime_settings.get_runtime_config", return_value=_runtime()):
            uc.ensure_default_gateways()
        self.assertEqual(MessagingGateway.objects.count(), 0)

    def test_creates_sms_and_smtp_from_env(self):
        rt = _runtime(
            sms_provider="smsnet",
            sms_username="u",
            sms_enabled=True,
            sms_provider_rank="2",
            smtp_host="mail.test",
            smtp_from_email="a@b.c",
        )
        with patch(f"{UC}.runtime_settings.get_runtime_config", return_value=rt):
            uc.ensure_default_gateways()
        sms = MessagingGateway.objects.get(gateway_type="sms")
        self.assertEqual(sms.name, "SMSNET")
        self.assertEqual(sms.priority, 2)
        self.assertTrue(sms.enabled)
        self.assertEqual(sms.config["username"], "u")
        smtp = MessagingGateway.objects.get(gateway_type="smtp")
        self.assertEqual(smtp.name, "SMTP Principal")
        self.assertFalse(smtp.enabled)
        self.assertEqual(smtp.config["auth_mode"], "password")

    def test_does_not_duplicate_existing(self):
        MessagingGateway.objects.create(name="X", gateway_type="sms", provider="p")
        rt = _runtime(sms_provider="smsnet", sms_enabled=True)
        with patch(f"{UC}.runtime_settings.get_runtime_config", return_value=rt):
            uc.ensure_default_gateways()
        self.assertEqual(MessagingGateway.objects.filter(gateway_type="sms").count(), 1)


class SyncGatewayEnvTests(TestCase):
    def setUp(self):
        self.write = patch(f"{UC}.env_manager.write_values").start()
        self.clear = patch(f"{UC}.clear_runtime_config_cache").start()
        self.reload = patch(f"{UC}.runtime_settings.reload_config").start()
        self.addCleanup(patch.stopall)

    def test_ignores_other_types(self):
        uc.sync_gateway_env("whatsapp")
        uc.sync_gateway_env("video")
        self.write.assert_not_called()

    def test_no_gateway_of_type_writes_nothing(self):
        uc.sync_gateway_env("sms")
        self.write.assert_not_called()

    def test_all_disabled_turns_flag_off(self):
        MessagingGateway.objects.create(name="S", gateway_type="smtp", enabled=False)
        uc.sync_gateway_env("smtp")
        self.write.assert_called_once_with({"SMTP_ENABLED": "False"})
        self.clear.assert_called_once()
        self.reload.assert_called_once()

    def test_sms_active_lowest_priority_wins(self):
        MessagingGateway.objects.create(
            name="B", gateway_type="sms", provider="aws", priority=2, config={"username": "b"}
        )
        MessagingGateway.objects.create(
            name="A",
            gateway_type="sms",
            provider="smsnet",
            priority=1,
            config={"username": "a", "api_token": "t"},
        )
        uc.sync_gateway_env("sms")
        payload = self.write.call_args.args[0]
        self.assertEqual(payload["SMS_PROVIDER"], "smsnet")
        self.assertEqual(payload["SMS_USERNAME"], "a")
        self.assertEqual(payload["SMS_API_TOKEN"], "t")
        self.assertEqual(payload["SMS_ENABLED"], "True")
        self.assertEqual(payload["SMS_PROVIDER_RANK"], "1")

    def test_smtp_payload_mirrors_django_email_settings(self):
        MessagingGateway.objects.create(
            name="M",
            gateway_type="smtp",
            config={"host": "mail", "port": 465, "security": "SSL", "user": "u@x"},
        )
        uc.sync_gateway_env("smtp")
        payload = self.write.call_args.args[0]
        self.assertEqual(payload["SMTP_SECURITY"], "ssl")
        self.assertEqual(payload["EMAIL_USE_SSL"], "True")
        self.assertEqual(payload["EMAIL_USE_TLS"], "False")
        self.assertEqual(payload["EMAIL_PORT"], "465")
        self.assertEqual(payload["DEFAULT_FROM_EMAIL"], "u@x")  # cai no user sem from_email
        self.assertEqual(payload["EMAIL_BACKEND"], "django.core.mail.backends.smtp.EmailBackend")


class GatewayCrudTests(TestCase):
    def setUp(self):
        patch(f"{UC}.sync_gateway_env").start()
        patch(f"{UC}.ensure_default_gateways").start()
        self.stop_stream = patch(f"{UC}.video_gateway_service.stop_stream_for_gateway").start()
        patch(f"{UC}.video_gateway_service.build_playback_url", return_value="").start()
        self.addCleanup(patch.stopall)
        self.superuser = User.objects.create_superuser("su", "su@t.com", "p")
        self.user = User.objects.create_user("u1", "u1@t.com", "p", is_staff=True)
        self.dept_a = Department.objects.create(name="A")
        self.dept_b = Department.objects.create(name="B")
        self.user.profile.departments.add(self.dept_a)
        self.sms = MessagingGateway.objects.create(name="SMS", gateway_type="sms")
        self.cam_public = MessagingGateway.objects.create(name="Pub", gateway_type="video")
        self.cam_a = MessagingGateway.objects.create(name="CamA", gateway_type="video")
        self.cam_a.departments.add(self.dept_a)
        self.cam_b = MessagingGateway.objects.create(name="CamB", gateway_type="video")
        self.cam_b.departments.add(self.dept_b)

    def test_list_superuser_sees_all(self):
        names = [g["name"] for g in uc.list_gateways_for(self.superuser)]
        self.assertEqual(sorted(names), ["CamA", "CamB", "Pub", "SMS"])

    def test_list_user_sees_non_video_plus_own_and_public_cameras(self):
        names = [g["name"] for g in uc.list_gateways_for(self.user)]
        self.assertEqual(sorted(names), ["CamA", "Pub", "SMS"])

    def test_create_validates(self):
        with self.assertRaises(uc.GatewayError) as ctx:
            uc.create_gateway({"gateway_type": "fax", "name": "x"})
        self.assertEqual(ctx.exception.status, 400)
        with self.assertRaises(uc.GatewayError):
            uc.create_gateway({"gateway_type": "sms", "name": "  "})

    def test_create_normalizes_and_syncs(self):
        result = uc.create_gateway(
            {
                "gateway_type": "smtp",
                "name": " Mail ",
                "priority": "abc",
                "provider": "",
                "config": "not-a-dict",
            }
        )
        self.assertEqual(result["name"], "Mail")
        self.assertEqual(result["priority"], 1)
        self.assertEqual(result["provider"], "")
        self.assertEqual(result["config"], {})
        self.assertTrue(result["enabled"])
        uc.sync_gateway_env.assert_called_with("smtp")

    def test_get_gateway_for_rbac(self):
        self.assertEqual(uc.get_gateway_for(self.user, self.cam_a.id), self.cam_a)
        self.assertEqual(uc.get_gateway_for(self.user, self.cam_public.id), self.cam_public)
        self.assertEqual(uc.get_gateway_for(self.user, self.sms.id), self.sms)
        self.assertEqual(uc.get_gateway_for(self.superuser, self.cam_b.id), self.cam_b)
        with self.assertRaises(uc.GatewayForbidden) as ctx:
            uc.get_gateway_for(self.user, self.cam_b.id)
        self.assertEqual(ctx.exception.status, 403)
        with self.assertRaises(uc.GatewayNotFound) as ctx:
            uc.get_gateway_for(self.user, 99999)
        self.assertEqual(ctx.exception.status, 404)

    def test_delete_video_stops_stream_and_syncs(self):
        uc.delete_gateway(self.cam_a)
        self.stop_stream.assert_called_once()
        self.assertTrue(self.stop_stream.call_args.kwargs["clear_preview"])
        self.assertFalse(MessagingGateway.objects.filter(id=self.cam_a.id).exists())
        uc.sync_gateway_env.assert_called_with("video")

    def test_update_keeps_secret_when_empty_and_merges_config(self):
        self.sms.config = {"password": "old", "username": "u"}
        self.sms.save()
        result = uc.update_gateway(
            self.sms,
            {"name": "", "priority": 0, "config": {"password": "", "username": "v", "x": 1}},
        )
        self.assertEqual(result["name"], "SMS")  # nome vazio mantém o antigo
        self.assertEqual(result["priority"], 1)
        self.assertEqual(result["config"], {"password": "old", "username": "v", "x": 1})
        uc.sync_gateway_env.assert_called_with("sms")

    def test_update_video_stream_change_stops_and_drops_preview(self):
        self.cam_a.config = {"stream_url": "rtsp://a", "preview_url": "http://p"}
        self.cam_a.save()
        result = uc.update_gateway(self.cam_a, {"config": {"stream_url": "rtsp://b"}})
        self.stop_stream.assert_called_once_with(self.cam_a)
        self.assertNotIn("preview_url", result["config"])
        self.assertEqual(result["config"]["stream_url"], "rtsp://b")

    def test_update_video_disable_stops_stream(self):
        uc.update_gateway(self.cam_a, {"enabled": False})
        self.stop_stream.assert_called_once()
        self.assertFalse(MessagingGateway.objects.get(id=self.cam_a.id).enabled)

    def test_update_video_unchanged_stream_does_not_stop(self):
        self.cam_a.config = {"stream_url": "rtsp://a"}
        self.cam_a.save()
        uc.update_gateway(self.cam_a, {"config": {"stream_url": "rtsp://a"}, "name": "N"})
        self.stop_stream.assert_not_called()


class WhatsappQrTests(TestCase):
    def setUp(self):
        self.gw = MessagingGateway.objects.create(
            name="WA",
            gateway_type="whatsapp",
            config={"auth_mode": "qr", "qr_service_url": "http://qr.local/"},
        )
        self.requests = patch(f"{UC}.requests").start()
        self.addCleanup(patch.stopall)

    def _respond(self, payload: dict):
        resp = MagicMock()
        resp.content = b"x"
        resp.json.return_value = payload
        self.requests.request.return_value = resp
        return resp

    def test_get_qr_gateway_errors(self):
        with self.assertRaises(uc.GatewayNotFound):
            uc.get_qr_gateway(99999)
        other = MessagingGateway.objects.create(
            name="T", gateway_type="whatsapp", config={"auth_mode": "token"}
        )
        with self.assertRaises(uc.GatewayError) as ctx:
            uc.get_qr_gateway(other.id)
        self.assertEqual(str(ctx.exception), "Gateway não está em modo QR Code.")
        self.assertEqual(uc.get_qr_gateway(self.gw.id), self.gw)

    def test_service_url_from_config_then_env(self):
        self.assertEqual(uc.get_whatsapp_qr_service_url(self.gw), "http://qr.local/")
        self.gw.config = {"auth_mode": "qr"}
        with patch(
            f"{UC}.env_manager.read_values", return_value={"WHATSAPP_QR_SERVICE_URL": " http://e "}
        ):
            self.assertEqual(uc.get_whatsapp_qr_service_url(self.gw), "http://e")

    def test_start_requires_default_url_even_with_override(self):
        self.gw.config = {"auth_mode": "qr"}
        self.gw.save()
        with patch(f"{UC}.env_manager.read_values", return_value={}):
            with self.assertRaises(uc.GatewayError) as ctx:
                uc.qr_start(self.gw, "http://override")
        self.assertEqual(str(ctx.exception), "Serviço de QR Code não configurado.")
        self.requests.request.assert_not_called()

    def test_start_uses_override_and_persists_state(self):
        self._respond({"qr": "data:img", "status": "pending", "message": "ok"})
        result = uc.qr_start(self.gw, "http://other/")
        call = self.requests.request.call_args
        self.assertEqual(call.args, ("POST", "http://other/qr/start"))
        self.assertEqual(call.kwargs["json"], {"gateway_id": self.gw.id, "name": "WA"})
        self.assertEqual(call.kwargs["timeout"], uc.QR_START_TIMEOUT)
        self.assertEqual(result["qr_image_url"], "data:img")
        self.assertEqual(result["qr_status"], "pending")
        self.assertEqual(result["message"], "ok")
        self.gw.refresh_from_db()
        self.assertEqual(self.gw.config["qr_status"], "pending")
        self.assertEqual(self.gw.config["qr_image_url"], "data:img")

    def test_start_service_failure_is_qr_service_error(self):
        self.requests.request.side_effect = RuntimeError("down")
        with self.assertRaises(uc.QrServiceError) as ctx:
            uc.qr_start(self.gw)
        self.assertEqual(str(ctx.exception), "Falha ao gerar QR: down")
        self.assertEqual(ctx.exception.status, 400)

    def test_status_connected_without_image_clears_it(self):
        self.gw.config["qr_image_url"] = "old"
        self.gw.save()
        self._respond({"status": "connected"})
        result = uc.qr_status(self.gw)
        self.assertEqual(self.requests.request.call_args.args, ("GET", "http://qr.local/qr/status"))
        self.assertEqual(result["qr_image_url"], "")
        self.assertEqual(result["message"], "Status atualizado.")
        self.gw.refresh_from_db()
        self.assertEqual(self.gw.config["qr_image_url"], "")
        self.assertEqual(self.gw.config["qr_status"], "connected")

    def test_status_pending_keeps_missing_image_as_none(self):
        self._respond({})
        result = uc.qr_status(self.gw)
        self.assertIsNone(result["qr_image_url"])
        self.assertEqual(result["qr_status"], "pending")

    def test_disconnect_and_reset(self):
        self._respond({"message": "bye"})
        result = uc.qr_disconnect(self.gw)
        self.assertEqual(result["qr_status"], "disconnected")
        self.assertEqual(result["message"], "bye")
        self.gw.refresh_from_db()
        self.assertEqual(self.gw.config["qr_image_url"], "")

        self._respond({})
        result = uc.qr_reset(self.gw)
        self.assertEqual(result, {"qr_status": "pending", "message": "Sessão resetada."})
        self.assertEqual(self.requests.request.call_args.args, ("POST", "http://qr.local/qr/reset"))

    def test_test_message_validates_recipient(self):
        with self.assertRaises(uc.GatewayError) as ctx:
            uc.qr_test_message(self.gw, {})
        self.assertEqual(str(ctx.exception), "Informe o telefone de teste.")

    def test_test_message_defaults_and_override_url_without_default(self):
        self.gw.config = {"auth_mode": "qr", "test_recipient": "+5511", "test_message": ""}
        self.gw.save()
        self._respond({"status": "sent"})
        with patch(f"{UC}.env_manager.read_values", return_value={}):
            result = uc.qr_test_message(self.gw, {"qr_service_url": "http://o"})
        call = self.requests.request.call_args
        self.assertEqual(call.args, ("POST", "http://o/message/test"))
        self.assertEqual(
            call.kwargs["json"],
            {
                "gateway_id": self.gw.id,
                "recipient": "+5511",
                "message": "Teste WhatsApp ProveMaps.",
            },
        )
        self.assertEqual(
            result, {"message": "Mensagem enviada.", "status": "sent", "recipient": "+5511"}
        )

    def test_test_message_without_any_url(self):
        self.gw.config = {"auth_mode": "qr", "test_recipient": "+5511"}
        self.gw.save()
        with patch(f"{UC}.env_manager.read_values", return_value={}):
            with self.assertRaises(uc.GatewayError) as ctx:
                uc.qr_test_message(self.gw, {})
        self.assertEqual(str(ctx.exception), "Serviço de QR Code não configurado.")
