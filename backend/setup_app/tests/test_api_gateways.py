"""Views de gateways e QR WhatsApp (EV-0017c): acesso, códigos HTTP e tradução das exceções."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from setup_app.models import MessagingGateway
from setup_app.usecases import gateways as uc

API = "setup_app.api.gateways"


class GatewaysApiTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="gw_staff", password="pass", email="g@t.com", is_staff=True, is_active=True
        )
        self.client.force_login(self.staff)
        patch(f"{uc.__name__}.sync_gateway_env").start()
        patch(f"{uc.__name__}.ensure_default_gateways").start()
        self.addCleanup(patch.stopall)

    def _post(self, url, body):
        return self.client.post(url, json.dumps(body), content_type="application/json")

    def test_non_staff_refused(self):
        regular = User.objects.create_user(username="gw_user", password="pass", email="u@t.com")
        self.client.force_login(regular)
        self.assertIn(self.client.get("/setup_app/api/gateways/").status_code, (302, 403))

    def test_list(self):
        MessagingGateway.objects.create(name="S", gateway_type="sms")
        resp = self.client.get("/setup_app/api/gateways/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual([g["name"] for g in data["gateways"]], ["S"])

    def test_create_ok_and_errors(self):
        resp = self._post("/setup_app/api/gateways/", {"gateway_type": "sms", "name": "N"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["gateway"]["name"], "N")

        resp = self._post("/setup_app/api/gateways/", {"gateway_type": "nope", "name": "N"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "Tipo de gateway inválido.")

        resp = self.client.post("/setup_app/api/gateways/", "{bad", content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "Invalid JSON data")

    def test_detail_get_patch_delete(self):
        gw = MessagingGateway.objects.create(name="S", gateway_type="sms")
        url = f"/setup_app/api/gateways/{gw.id}/"
        self.assertEqual(json.loads(self.client.get(url).content)["gateway"]["id"], gw.id)

        resp = self.client.patch(url, json.dumps({"name": "T"}), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["gateway"]["name"], "T")

        resp = self.client.patch(url, "{bad", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

        resp = self.client.delete(url)
        self.assertEqual(json.loads(resp.content)["message"], "Gateway removido.")
        self.assertFalse(MessagingGateway.objects.filter(id=gw.id).exists())

    def test_detail_404_and_403(self):
        resp = self.client.get("/setup_app/api/gateways/99999/")
        self.assertEqual(resp.status_code, 404)
        with patch(
            f"{API}.usecase.get_gateway_for", side_effect=uc.GatewayForbidden("Sem permissão")
        ):
            resp = self.client.get("/setup_app/api/gateways/1/")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(json.loads(resp.content)["message"], "Sem permissão")


class WhatsappQrApiTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="qr_staff", password="pass", email="q@t.com", is_staff=True, is_active=True
        )
        self.client.force_login(self.staff)
        self.gw = MessagingGateway.objects.create(
            name="WA", gateway_type="whatsapp", config={"auth_mode": "qr"}
        )
        self.base = f"/setup_app/api/gateways/{self.gw.id}/whatsapp"

    def test_unknown_gateway_is_404(self):
        resp = self.client.post("/setup_app/api/gateways/99999/whatsapp/qr/")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(json.loads(resp.content)["message"], "Gateway WhatsApp não encontrado.")

    def test_not_qr_mode_is_400(self):
        self.gw.config = {"auth_mode": "token"}
        self.gw.save()
        resp = self.client.get(f"{self.base}/qr/status/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "Gateway não está em modo QR Code.")

    def test_start_passes_override_from_body_and_tolerates_bad_json(self):
        with patch(f"{API}.usecase.qr_start", return_value={"qr_status": "pending"}) as start:
            resp = self.client.post(
                f"{self.base}/qr/",
                json.dumps({"qr_service_url": " http://o "}),
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(json.loads(resp.content), {"success": True, "qr_status": "pending"})
            start.assert_called_once_with(self.gw, "http://o")

            resp = self.client.post(f"{self.base}/qr/", "{bad", content_type="application/json")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(start.call_args.args[1], "")

    def test_status_passes_override_from_query(self):
        with patch(f"{API}.usecase.qr_status", return_value={"qr_status": "connected"}) as status:
            resp = self.client.get(f"{self.base}/qr/status/?qr_service_url=http://q")
        self.assertEqual(resp.status_code, 200)
        status.assert_called_once_with(self.gw, "http://q")

    def test_service_error_is_400_with_message(self):
        with patch(
            f"{API}.usecase.qr_disconnect", side_effect=uc.QrServiceError("Falha ao desconectar: x")
        ):
            resp = self.client.post(f"{self.base}/qr/disconnect/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "Falha ao desconectar: x")

    def test_reset_and_test_message(self):
        with patch(f"{API}.usecase.qr_reset", return_value={"qr_status": "pending"}):
            resp = self.client.post(f"{self.base}/qr/reset/")
        self.assertEqual(json.loads(resp.content)["qr_status"], "pending")

        with patch(f"{API}.usecase.qr_test_message", return_value={"status": "sent"}) as test:
            resp = self.client.post(
                f"{self.base}/qr/test-message/",
                json.dumps({"recipient": "+55"}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200)
        test.assert_called_once_with(self.gw, {"recipient": "+55"})

    def test_test_message_without_recipient_is_400(self):
        resp = self.client.post(f"{self.base}/qr/test-message/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "Informe o telefone de teste.")

    def test_get_on_post_route_is_405(self):
        self.assertEqual(self.client.get(f"{self.base}/qr/").status_code, 405)
