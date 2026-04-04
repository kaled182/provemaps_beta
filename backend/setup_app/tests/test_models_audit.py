"""Tests for setup_app.models_audit — ConfigurationAudit."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase


class ConfigurationAuditLogChangeTests(TestCase):
    def test_creates_entry_without_request(self):
        from setup_app.models_audit import ConfigurationAudit
        with patch.object(ConfigurationAudit.objects, "create") as mock_create:
            mock_create.return_value = MagicMock()
            ConfigurationAudit.log_change(
                user=None,
                action="update",
                section="Zabbix",
            )
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["action"], "update")
        self.assertEqual(call_kwargs["section"], "Zabbix")
        self.assertIsNone(call_kwargs["ip_address"])
        self.assertEqual(call_kwargs["user_agent"], "")

    def test_extracts_ip_from_x_forwarded_for(self):
        from setup_app.models_audit import ConfigurationAudit
        request = MagicMock()
        request.META = {
            "HTTP_X_FORWARDED_FOR": "203.0.113.1, 10.0.0.1",
            "HTTP_USER_AGENT": "TestAgent/1.0",
        }
        with patch.object(ConfigurationAudit.objects, "create") as mock_create:
            mock_create.return_value = MagicMock()
            ConfigurationAudit.log_change(
                user=None, action="test", section="Redis", request=request
            )
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["ip_address"], "203.0.113.1")

    def test_falls_back_to_remote_addr(self):
        from setup_app.models_audit import ConfigurationAudit
        request = MagicMock()
        request.META = MagicMock()
        request.META.get.side_effect = lambda key, default=None: {
            "HTTP_X_FORWARDED_FOR": None,
            "REMOTE_ADDR": "192.168.1.1",
            "HTTP_USER_AGENT": "TestAgent",
        }.get(key, default)
        with patch.object(ConfigurationAudit.objects, "create") as mock_create:
            mock_create.return_value = MagicMock()
            ConfigurationAudit.log_change(
                user=None, action="test", section="DB", request=request
            )
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["ip_address"], "192.168.1.1")

    def test_redacts_password_field(self):
        from setup_app.models_audit import ConfigurationAudit
        with patch.object(ConfigurationAudit.objects, "create") as mock_create:
            mock_create.return_value = MagicMock()
            ConfigurationAudit.log_change(
                user=None,
                action="update",
                section="SMTP",
                field_name="password",
                old_value="oldpassword",
                new_value="newpassword",
            )
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["old_value"], "***REDACTED***")
        self.assertEqual(call_kwargs["new_value"], "***REDACTED***")

    def test_redacts_api_key_field(self):
        from setup_app.models_audit import ConfigurationAudit
        with patch.object(ConfigurationAudit.objects, "create") as mock_create:
            mock_create.return_value = MagicMock()
            ConfigurationAudit.log_change(
                user=None,
                action="update",
                section="Zabbix",
                field_name="api_key",
                old_value="myoldkey",
                new_value="mynewkey",
            )
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["old_value"], "***REDACTED***")
        self.assertEqual(call_kwargs["new_value"], "***REDACTED***")

    def test_does_not_redact_non_sensitive_fields(self):
        from setup_app.models_audit import ConfigurationAudit
        with patch.object(ConfigurationAudit.objects, "create") as mock_create:
            mock_create.return_value = MagicMock()
            ConfigurationAudit.log_change(
                user=None,
                action="update",
                section="Zabbix",
                field_name="zabbix_url",
                old_value="http://old.zabbix",
                new_value="http://new.zabbix",
            )
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["old_value"], "http://old.zabbix")
        self.assertEqual(call_kwargs["new_value"], "http://new.zabbix")

    def test_empty_old_value_not_redacted_as_star(self):
        from setup_app.models_audit import ConfigurationAudit
        with patch.object(ConfigurationAudit.objects, "create") as mock_create:
            mock_create.return_value = MagicMock()
            ConfigurationAudit.log_change(
                user=None,
                action="update",
                section="Test",
                field_name="password",
                old_value="",
                new_value="newpass",
            )
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["old_value"], "")
        self.assertEqual(call_kwargs["new_value"], "***REDACTED***")

    def test_success_false_stored(self):
        from setup_app.models_audit import ConfigurationAudit
        with patch.object(ConfigurationAudit.objects, "create") as mock_create:
            mock_create.return_value = MagicMock()
            ConfigurationAudit.log_change(
                user=None,
                action="update",
                section="Redis",
                success=False,
                error_message="Connection failed",
            )
        call_kwargs = mock_create.call_args[1]
        self.assertFalse(call_kwargs["success"])
        self.assertEqual(call_kwargs["error_message"], "Connection failed")
