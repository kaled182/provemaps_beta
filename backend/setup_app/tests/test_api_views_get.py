"""Integration tests for GET-style views in setup_app.api_views.

Covers: get_configuration, get_company_profile, get_audit_history,
        monitoring_servers GET, messaging_gateways GET.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase


class GetConfigurationViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="cfg_staff", password="pass", email="cfg@test.com",
            is_staff=True, is_active=True,
        )
        self.client.force_login(self.staff)

    def test_returns_200_with_configuration_dict(self):
        with patch("setup_app.api_views.env_manager") as mock_em:
            mock_em.read_values.return_value = {}
            resp = self.client.get("/setup_app/api/config/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get("success"))
        self.assertIn("configuration", data)
        self.assertIsInstance(data["configuration"], dict)

    def test_returns_all_expected_keys(self):
        with patch("setup_app.api_views.env_manager") as mock_em:
            mock_em.read_values.return_value = {
                "ZABBIX_API_URL": "http://zabbix.test",
                "GOOGLE_MAPS_API_KEY": "AIza123",
                "BACKUP_ZIP_PASSWORD": "secret123",
            }
            resp = self.client.get("/setup_app/api/config/")
        data = json.loads(resp.content)
        config = data["configuration"]
        self.assertEqual(config.get("ZABBIX_API_URL"), "http://zabbix.test")
        self.assertEqual(config.get("GOOGLE_MAPS_API_KEY"), "AIza123")

    def test_unauthenticated_returns_redirect(self):
        self.client.logout()
        resp = self.client.get("/setup_app/api/config/")
        self.assertIn(resp.status_code, (302, 403))

    def test_non_staff_returns_redirect(self):
        regular = User.objects.create_user(
            username="regular_cfg", password="pass", email="r@test.com"
        )
        self.client.force_login(regular)
        resp = self.client.get("/setup_app/api/config/")
        self.assertIn(resp.status_code, (302, 403))

    def test_gdrive_oauth_connected_field_present(self):
        with patch("setup_app.api_views.env_manager") as mock_em:
            mock_em.read_values.return_value = {}
            resp = self.client.get("/setup_app/api/config/")
        data = json.loads(resp.content)
        self.assertIn("GDRIVE_OAUTH_CONNECTED", data["configuration"])


class GetCompanyProfileViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="cp_staff", password="pass", email="cp@test.com",
            is_staff=True, is_active=True,
        )
        self.client.force_login(self.staff)

    def test_returns_200_with_profile(self):
        resp = self.client.get("/setup_app/api/company-profile/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get("success"))
        self.assertIn("profile", data)

    def test_profile_has_expected_fields(self):
        resp = self.client.get("/setup_app/api/company-profile/")
        data = json.loads(resp.content)
        profile = data["profile"]
        self.assertIn("company_legal_name", profile)
        self.assertIn("address_city", profile)
        self.assertIn("assets_logo", profile)


class GetAuditHistoryViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="ah_staff", password="pass", email="ah@test.com",
            is_staff=True, is_active=True,
        )
        self.client.force_login(self.staff)

    def test_returns_200_with_empty_audits(self):
        resp = self.client.get("/setup_app/api/audit-history/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get("success"))
        self.assertIn("audits", data)
        self.assertIsInstance(data["audits"], list)

    def test_section_filter_applied(self):
        resp = self.client.get("/setup_app/api/audit-history/", {"section": "Zabbix", "limit": 10})
        self.assertEqual(resp.status_code, 200)

    def test_limit_parameter_respected(self):
        resp = self.client.get("/setup_app/api/audit-history/", {"limit": 5})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertLessEqual(len(data["audits"]), 5)


class MonitoringServersGetTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="ms_staff", password="pass", email="ms@test.com",
            is_staff=True, is_active=True,
        )
        self.client.force_login(self.staff)

    def test_get_returns_servers_list(self):
        resp = self.client.get("/setup_app/api/monitoring-servers/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get("success"))
        self.assertIn("servers", data)

    def test_post_creates_server(self):
        resp = self.client.post(
            "/setup_app/api/monitoring-servers/",
            json.dumps({"name": "Zabbix Prod", "url": "http://z.example.com"}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (200, 201))
        data = json.loads(resp.content)
        self.assertTrue(data.get("success"))

    def test_post_missing_name_returns_400(self):
        resp = self.client.post(
            "/setup_app/api/monitoring-servers/",
            json.dumps({"url": "http://z.example.com"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_invalid_json_returns_400(self):
        resp = self.client.post(
            "/setup_app/api/monitoring-servers/",
            "not-json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class MessagingGatewaysGetTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="gw_super", password="pass", email="gw@test.com",
        )
        self.client.force_login(self.superuser)

    def _mock_runtime(self):
        rt = MagicMock()
        rt.sms_provider = ""
        rt.sms_username = ""
        rt.sms_api_url = ""
        rt.sms_sender_id = ""
        rt.sms_enabled = False
        rt.smtp_host = ""
        rt.smtp_user = ""
        rt.smtp_from_email = ""
        rt.smtp_enabled = False
        return rt

    def test_superuser_get_returns_all_gateways(self):
        with patch("setup_app.api_views.runtime_settings") as mock_rs:
            mock_rs.get_runtime_config.return_value = self._mock_runtime()
            resp = self.client.get("/setup_app/api/gateways/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn("gateways", data)

    def test_post_invalid_gateway_type_returns_400(self):
        resp = self.client.post(
            "/setup_app/api/gateways/",
            json.dumps({"gateway_type": "invalid_type", "name": "Test"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_missing_name_returns_400(self):
        resp = self.client.post(
            "/setup_app/api/gateways/",
            json.dumps({"gateway_type": "sms"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_creates_sms_gateway(self):
        with patch("setup_app.api_views._sync_gateway_env"):
            resp = self.client.post(
                "/setup_app/api/gateways/",
                json.dumps({"gateway_type": "sms", "name": "SMS Test"}),
                content_type="application/json",
            )
        self.assertIn(resp.status_code, (200, 201))
        data = json.loads(resp.content)
        self.assertTrue(data.get("success"))

    def test_post_invalid_json_returns_400(self):
        resp = self.client.post(
            "/setup_app/api/gateways/",
            "not-json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
