"""Tests for helper functions in setup_app.viewsets_contacts."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase


class SendEmailViaGatewayTests(TestCase):
    def _make_gateway(self, **config_kwargs):
        gw = MagicMock()
        gw.name = config_kwargs.pop("name", "Test Gateway")
        gw.config = config_kwargs
        return gw

    def test_raises_when_host_missing(self):
        from setup_app.viewsets_contacts import _send_email_via_gateway
        gw = self._make_gateway(host="", from_email="noreply@test.com")
        contact = MagicMock()
        contact.email = "user@example.com"
        with self.assertRaises(ValueError) as ctx:
            _send_email_via_gateway(gw, contact, "Hello")
        self.assertIn("host", str(ctx.exception).lower())

    def test_raises_when_from_email_missing(self):
        from setup_app.viewsets_contacts import _send_email_via_gateway
        gw = self._make_gateway(host="smtp.test.com", from_email="", user="")
        contact = MagicMock()
        contact.email = "user@example.com"
        with self.assertRaises(ValueError) as ctx:
            _send_email_via_gateway(gw, contact, "Hello")
        self.assertIn("remetente", str(ctx.exception).lower())

    def test_raises_when_recipient_missing(self):
        from setup_app.viewsets_contacts import _send_email_via_gateway
        gw = self._make_gateway(
            host="smtp.test.com",
            from_email="noreply@test.com",
            user="noreply@test.com",
        )
        contact = MagicMock()
        contact.email = ""
        with self.assertRaises(ValueError) as ctx:
            _send_email_via_gateway(gw, contact, "Hello")
        self.assertIn("e-mail", str(ctx.exception).lower())

    def test_raises_when_none_config(self):
        from setup_app.viewsets_contacts import _send_email_via_gateway
        gw = MagicMock()
        gw.config = None
        gw.name = "GW"
        contact = MagicMock()
        contact.email = "user@example.com"
        with self.assertRaises(ValueError):
            _send_email_via_gateway(gw, contact, "Hello")

    def test_port_defaults_ssl(self):
        """Verify port defaults to 465 for SSL security."""
        from setup_app.viewsets_contacts import _send_email_via_gateway
        import smtplib
        gw = self._make_gateway(
            host="smtp.test.com",
            from_email="noreply@test.com",
            security="ssl",
            port="",
        )
        contact = MagicMock()
        contact.email = "user@test.com"
        with patch("setup_app.viewsets_contacts.smtplib.SMTP_SSL") as mock_ssl:
            mock_server = MagicMock()
            mock_ssl.return_value = mock_server
            mock_server.__enter__ = MagicMock(return_value=mock_server)
            mock_server.__exit__ = MagicMock(return_value=False)
            _send_email_via_gateway(gw, contact, "Test message")
        mock_ssl.assert_called_once()
        call_kwargs = mock_ssl.call_args
        self.assertEqual(call_kwargs[1].get("port") or call_kwargs[0][1], 465)

    def test_port_defaults_tls(self):
        """Verify port defaults to 587 for TLS/non-SSL security."""
        from setup_app.viewsets_contacts import _send_email_via_gateway
        gw = self._make_gateway(
            host="smtp.test.com",
            from_email="noreply@test.com",
            security="tls",
            port="",
        )
        contact = MagicMock()
        contact.email = "user@test.com"
        with patch("setup_app.viewsets_contacts.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            _send_email_via_gateway(gw, contact, "Test message")
        mock_smtp.assert_called_once()
        call_kwargs = mock_smtp.call_args
        self.assertEqual(call_kwargs[1].get("port") or call_kwargs[0][1], 587)
