"""Tests for setup_app.serializers_alert_templates."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase


class AlertTemplateSerializerValidatePlaceholdersTests(TestCase):
    def _get_serializer(self):
        from setup_app.serializers_alert_templates import AlertTemplateSerializer
        return AlertTemplateSerializer()

    def test_none_returns_empty_list(self):
        s = self._get_serializer()
        result = s.validate_placeholders(None)
        self.assertEqual(result, [])

    def test_empty_list_returns_empty_list(self):
        s = self._get_serializer()
        result = s.validate_placeholders([])
        self.assertEqual(result, [])

    def test_valid_list_returned_cleaned(self):
        s = self._get_serializer()
        result = s.validate_placeholders(["  key1  ", "key2"])
        self.assertEqual(result, ["key1", "key2"])

    def test_duplicates_removed(self):
        s = self._get_serializer()
        result = s.validate_placeholders(["key1", "key1", "key2"])
        self.assertEqual(result, ["key1", "key2"])

    def test_empty_strings_skipped(self):
        s = self._get_serializer()
        result = s.validate_placeholders(["key1", "  ", "key2"])
        self.assertEqual(result, ["key1", "key2"])

    def test_non_list_raises_validation_error(self):
        from rest_framework.exceptions import ValidationError
        s = self._get_serializer()
        with self.assertRaises(ValidationError):
            s.validate_placeholders("not-a-list")

    def test_non_string_item_raises_validation_error(self):
        from rest_framework.exceptions import ValidationError
        s = self._get_serializer()
        with self.assertRaises(ValidationError):
            s.validate_placeholders([123])


class AlertTemplateSerializerValidateTests(TestCase):
    def _get_serializer(self, instance=None):
        from setup_app.serializers_alert_templates import AlertTemplateSerializer
        s = AlertTemplateSerializer()
        s.instance = instance
        return s

    def test_email_channel_without_subject_raises(self):
        from rest_framework.exceptions import ValidationError
        from setup_app.models import AlertTemplate
        s = self._get_serializer()
        with self.assertRaises(ValidationError) as ctx:
            s.validate({
                "channel": AlertTemplate.CHANNEL_EMAIL,
                "subject": "",
                "content": "Hello",
                "is_active": True,
                "is_default": False,
            })
        self.assertIn("subject", str(ctx.exception.detail))

    def test_inactive_default_raises(self):
        from rest_framework.exceptions import ValidationError
        from setup_app.models import AlertTemplate
        s = self._get_serializer()
        with self.assertRaises(ValidationError) as ctx:
            s.validate({
                "channel": AlertTemplate.CHANNEL_WHATSAPP,
                "subject": "",
                "content": "Hello",
                "is_active": False,
                "is_default": True,
            })
        self.assertIn("is_default", str(ctx.exception.detail))

    def test_valid_attrs_returned_unchanged(self):
        from setup_app.models import AlertTemplate
        s = self._get_serializer()
        attrs = {
            "channel": AlertTemplate.CHANNEL_WHATSAPP,
            "subject": "",
            "content": "Hello",
            "is_active": True,
            "is_default": False,
        }
        result = s.validate(attrs)
        self.assertEqual(result, attrs)


class AlertTemplateSerializerPreparePlaceholdersTests(TestCase):
    def _get_serializer(self):
        from setup_app.serializers_alert_templates import AlertTemplateSerializer
        return AlertTemplateSerializer()

    def test_extracts_placeholders_from_content_when_missing(self):
        from setup_app.models import AlertTemplate
        s = self._get_serializer()
        with patch.object(AlertTemplate, "extract_placeholders", return_value=["name"]) as mock_ep:
            result = s._prepare_placeholders({"content": "Hello {name}", "placeholders": []})
        mock_ep.assert_called_once_with("Hello {name}")
        self.assertEqual(result["placeholders"], ["name"])

    def test_keeps_existing_placeholders_if_set(self):
        s = self._get_serializer()
        result = s._prepare_placeholders({
            "content": "Hello",
            "placeholders": ["existing_key"],
        })
        self.assertEqual(result["placeholders"], ["existing_key"])
