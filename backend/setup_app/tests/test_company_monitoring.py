"""Perfil da empresa e servidores de monitorização (EV-0017e): usecases e views."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from setup_app.models import CompanyProfile, MonitoringServer
from setup_app.usecases import company as company_uc, monitoring as mon_uc


class CompanyUsecaseTests(TestCase):
    def test_get_or_create_is_singleton(self):
        a = company_uc.get_or_create_company_profile()
        b = company_uc.get_or_create_company_profile()
        self.assertEqual(a.id, b.id)
        self.assertEqual(CompanyProfile.objects.count(), 1)

    def test_serialize_keys_and_order(self):
        profile = company_uc.get_or_create_company_profile()
        data = company_uc.serialize_company_profile(profile)
        keys = list(data)
        self.assertEqual(keys[:3], ["company_legal_name", "company_trade_name", "company_doc"])
        self.assertEqual(keys[10:12], ["company_active", "company_reports_active"])
        self.assertEqual(keys[-3:], ["assets_logo", "assets_cert_file", "updated_at"])
        self.assertEqual(data["assets_logo"], {"name": "", "url": ""})
        self.assertEqual(data["address_country"], "Brasil")

    def test_update_partial_bools_files_and_cert_password(self):
        profile = company_uc.get_or_create_company_profile()
        profile.company_fistel = "F1"
        profile.assets_cert_password = "old"
        profile.save()
        company_uc.update_company_profile(
            profile,
            {
                "company_legal_name": "  ACME ",
                "company_active": "false",
                "assets_cert_password": "",
            },
            {"assets_logo": SimpleUploadedFile("logo.png", b"png")},
        )
        profile.refresh_from_db()
        self.assertEqual(profile.company_legal_name, "ACME")
        self.assertFalse(profile.company_active)
        self.assertEqual(profile.company_fistel, "F1")  # não enviado → mantém
        self.assertEqual(profile.assets_cert_password, "old")  # vazio → mantém
        self.assertTrue(profile.assets_logo.name)
        company_uc.update_company_profile(profile, {"assets_cert_password": "new"})
        self.assertEqual(CompanyProfile.objects.get(id=profile.id).assets_cert_password, "new")


class MonitoringUsecaseTests(TestCase):
    def test_create_validates_and_hides_token(self):
        with self.assertRaises(mon_uc.MonitoringError):
            mon_uc.create_server({"name": "x"})
        data = mon_uc.create_server(
            {"name": "Z", "url": "http://z", "auth_token": "tok", "extra_config": "bad"}
        )
        self.assertEqual(data["server_type"], "zabbix")
        self.assertTrue(data["has_auth_token"])
        self.assertEqual(data["auth_token"], "")
        self.assertEqual(data["extra_config"], {})

    def test_list_order_get_update_delete(self):
        b = MonitoringServer.objects.create(name="B", url="http://b", is_active=False)
        a = MonitoringServer.objects.create(name="A", url="http://a", auth_token="t")
        self.assertEqual([s["name"] for s in mon_uc.list_servers()], ["A", "B"])
        self.assertEqual(mon_uc.get_server(a.id), a)
        with self.assertRaises(mon_uc.MonitoringServerNotFound) as ctx:
            mon_uc.get_server(99999)
        self.assertEqual(ctx.exception.status, 404)

        mon_uc.update_server(a, {"auth_token": mon_uc.TOKEN_MASK, "name": ""})
        a.refresh_from_db()
        self.assertEqual((a.auth_token, a.name), ("t", "A"))  # máscara e nome vazio mantêm
        mon_uc.update_server(
            a, {"auth_token": "novo", "is_active": False, "extra_config": {"k": 1}}
        )
        a.refresh_from_db()
        self.assertEqual((a.auth_token, a.is_active, a.extra_config), ("novo", False, {"k": 1}))
        mon_uc.update_server(a, {"auth_token": ""})
        a.refresh_from_db()
        self.assertIsNone(a.auth_token)
        mon_uc.delete_server(b)
        self.assertFalse(MonitoringServer.objects.filter(id=b.id).exists())


class CompanyAndMonitoringApiTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="cm_staff", password="pass", email="c@t.com", is_staff=True, is_active=True
        )
        self.client.force_login(self.staff)

    def test_company_profile_get_and_update_json(self):
        resp = self.client.get("/setup_app/api/company-profile/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("company_legal_name", json.loads(resp.content)["profile"])
        resp = self.client.post(
            "/setup_app/api/company-profile/update/",
            json.dumps({"company_trade_name": "Simples", "company_reports_active": False}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["message"], "Cadastro atualizado.")
        self.assertEqual(data["profile"]["company_trade_name"], "Simples")
        self.assertFalse(data["profile"]["company_reports_active"])
        resp = self.client.post(
            "/setup_app/api/company-profile/update/", "{bad", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "JSON inválido.")

    def test_company_profile_update_multipart_with_logo(self):
        resp = self.client.post(
            "/setup_app/api/company-profile/update/",
            {"company_doc": "123", "assets_logo": SimpleUploadedFile("logo.png", b"png")},
        )
        self.assertEqual(resp.status_code, 200)
        profile = json.loads(resp.content)["profile"]
        self.assertEqual(profile["company_doc"], "123")
        self.assertTrue(profile["assets_logo"]["name"])
        self.assertTrue(profile["assets_logo"]["url"].startswith("http://testserver/"))

    def test_company_profile_server_error(self):
        with patch(
            "setup_app.api.company.usecase.get_or_create_company_profile",
            side_effect=RuntimeError("x"),
        ):
            self.assertEqual(self.client.get("/setup_app/api/company-profile/").status_code, 500)

    def test_monitoring_servers_routes(self):
        resp = self.client.post(
            "/setup_app/api/monitoring-servers/",
            json.dumps({"name": "Z", "url": "http://z"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        sid = json.loads(resp.content)["server"]["id"]
        self.assertEqual(
            len(
                json.loads(self.client.get("/setup_app/api/monitoring-servers/").content)["servers"]
            ),
            1,
        )
        url = f"/setup_app/api/monitoring-servers/{sid}/"
        self.assertEqual(json.loads(self.client.get(url).content)["server"]["name"], "Z")
        resp = self.client.patch(url, json.dumps({"name": "Y"}), content_type="application/json")
        self.assertEqual(json.loads(resp.content)["server"]["name"], "Y")
        self.assertEqual(
            self.client.patch(url, "{bad", content_type="application/json").status_code, 400
        )
        self.assertEqual(json.loads(self.client.delete(url).content)["message"], "Server removed.")
        self.assertEqual(self.client.get(url).status_code, 404)
        resp = self.client.post(
            "/setup_app/api/monitoring-servers/",
            json.dumps({"name": "x"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "Name and URL are required.")
