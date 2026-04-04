"""Integration tests for setup_app.viewsets_alert_templates.AlertTemplateViewSet."""
from __future__ import annotations

import json

from django.contrib.auth.models import User
from django.test import TestCase

from setup_app.models import AlertTemplate


def _make_payload(**kwargs):
    defaults = {
        "name": "Test Template",
        "content": "Hello {{contact_name}}",
        "category": AlertTemplate.CATEGORY_GENERIC,
        "channel": AlertTemplate.CHANNEL_WHATSAPP,
    }
    defaults.update(kwargs)
    return defaults


class AlertTemplateViewSetListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="at_user", password="pass", email="at@test.com"
        )
        self.client.force_login(self.user)

    def test_list_returns_200_with_templates(self):
        resp = self.client.get("/setup_app/api/alert-templates/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertIn("templates", data)
        self.assertIsInstance(data["templates"], list)

    def test_list_returns_meta(self):
        resp = self.client.get("/setup_app/api/alert-templates/")
        data = json.loads(resp.content)
        self.assertIn("meta", data)
        self.assertIn("categories", data["meta"])
        self.assertIn("channels", data["meta"])

    def test_list_filter_by_category(self):
        AlertTemplate.objects.create(
            name="Generic Tmpl",
            content="msg",
            category=AlertTemplate.CATEGORY_GENERIC,
            channel=AlertTemplate.CHANNEL_WHATSAPP,
        )
        AlertTemplate.objects.create(
            name="Cable Tmpl",
            content="msg",
            category=AlertTemplate.CATEGORY_CABLE_BREAK,
            channel=AlertTemplate.CHANNEL_WHATSAPP,
        )
        resp = self.client.get(
            "/setup_app/api/alert-templates/",
            {"category": AlertTemplate.CATEGORY_GENERIC},
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        for tmpl in data["templates"]:
            self.assertEqual(tmpl["category"], AlertTemplate.CATEGORY_GENERIC)

    def test_list_filter_by_channel(self):
        AlertTemplate.objects.create(
            name="SMS Tmpl",
            content="msg",
            category=AlertTemplate.CATEGORY_GENERIC,
            channel=AlertTemplate.CHANNEL_SMS,
        )
        resp = self.client.get(
            "/setup_app/api/alert-templates/",
            {"channel": AlertTemplate.CHANNEL_SMS},
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        for tmpl in data["templates"]:
            self.assertEqual(tmpl["channel"], AlertTemplate.CHANNEL_SMS)

    def test_list_filter_by_is_active_false(self):
        AlertTemplate.objects.create(
            name="Inactive Tmpl",
            content="msg",
            category=AlertTemplate.CATEGORY_GENERIC,
            channel=AlertTemplate.CHANNEL_WHATSAPP,
            is_active=False,
        )
        resp = self.client.get(
            "/setup_app/api/alert-templates/",
            {"is_active": "false"},
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        for tmpl in data["templates"]:
            self.assertFalse(tmpl["is_active"])

    def test_unauthenticated_returns_redirect(self):
        self.client.logout()
        resp = self.client.get("/setup_app/api/alert-templates/")
        self.assertIn(resp.status_code, (302, 401, 403))


class AlertTemplateViewSetCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="at_create_user", password="pass", email="atc@test.com"
        )
        self.client.force_login(self.user)

    def test_create_returns_201(self):
        resp = self.client.post(
            "/setup_app/api/alert-templates/",
            json.dumps(_make_payload()),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertIn("template", data)

    def test_create_missing_name_returns_400(self):
        payload = {"content": "msg", "category": "generic", "channel": "whatsapp"}
        resp = self.client.post(
            "/setup_app/api/alert-templates/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_sets_created_by(self):
        resp = self.client.post(
            "/setup_app/api/alert-templates/",
            json.dumps(_make_payload(name="Created By Test")),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        tmpl = AlertTemplate.objects.get(name="Created By Test")
        self.assertEqual(tmpl.created_by, self.user)
        self.assertEqual(tmpl.updated_by, self.user)


class AlertTemplateViewSetUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="at_update_user", password="pass", email="atu@test.com"
        )
        self.client.force_login(self.user)
        self.template = AlertTemplate.objects.create(
            name="Original Name",
            content="Original content",
            category=AlertTemplate.CATEGORY_GENERIC,
            channel=AlertTemplate.CHANNEL_WHATSAPP,
        )

    def test_patch_updates_name(self):
        resp = self.client.patch(
            f"/setup_app/api/alert-templates/{self.template.pk}/",
            json.dumps({"name": "Updated Name"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, "Updated Name")

    def test_put_full_update(self):
        resp = self.client.put(
            f"/setup_app/api/alert-templates/{self.template.pk}/",
            json.dumps(_make_payload(name="Full Update")),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])

    def test_update_sets_updated_by(self):
        self.client.patch(
            f"/setup_app/api/alert-templates/{self.template.pk}/",
            json.dumps({"name": "Updated By Test"}),
            content_type="application/json",
        )
        self.template.refresh_from_db()
        self.assertEqual(self.template.updated_by, self.user)


class AlertTemplateViewSetDestroyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="at_del_user", password="pass", email="atd@test.com"
        )
        self.client.force_login(self.user)
        self.template = AlertTemplate.objects.create(
            name="To Delete",
            content="bye",
            category=AlertTemplate.CATEGORY_GENERIC,
            channel=AlertTemplate.CHANNEL_WHATSAPP,
        )

    def test_delete_returns_200(self):
        resp = self.client.delete(
            f"/setup_app/api/alert-templates/{self.template.pk}/"
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])

    def test_delete_removes_record(self):
        pk = self.template.pk
        self.client.delete(f"/setup_app/api/alert-templates/{pk}/")
        self.assertFalse(AlertTemplate.objects.filter(pk=pk).exists())
