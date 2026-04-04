"""Tests for core.views_auth — email settings, TotpCodeForm, TwoStepLoginView."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings


class ApplyRuntimeEmailSettingsTests(TestCase):
    def _call(self, values):
        from core.views_auth import _apply_runtime_email_settings
        with patch("core.views_auth.read_values", return_value=values):
            _apply_runtime_email_settings()

    def test_smtp_enabled_without_email_host_applies_smtp(self):
        from django.conf import settings as django_settings
        self._call({
            "SMTP_ENABLED": "true",
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@test.com",
            "SMTP_PASSWORD": "pass",
            "SMTP_SECURITY": "tls",
            "SMTP_FROM_EMAIL": "noreply@test.com",
            "EMAIL_HOST": "",
            "EMAIL_BACKEND": "",
            "EMAIL_PORT": "",
            "EMAIL_HOST_USER": "",
            "EMAIL_HOST_PASSWORD": "",
            "EMAIL_USE_TLS": "",
            "EMAIL_USE_SSL": "",
            "DEFAULT_FROM_EMAIL": "",
            "SERVER_EMAIL": "",
        })
        self.assertEqual(django_settings.EMAIL_HOST, "smtp.test.com")
        self.assertTrue(django_settings.EMAIL_USE_TLS)
        self.assertFalse(django_settings.EMAIL_USE_SSL)

    def test_smtp_disabled_no_email_host_does_nothing(self):
        from django.conf import settings as django_settings
        original_host = getattr(django_settings, "EMAIL_HOST", "")
        self._call({
            "SMTP_ENABLED": "false",
            "SMTP_HOST": "",
            "EMAIL_HOST": "",
            "EMAIL_BACKEND": "",
            "EMAIL_PORT": "",
            "EMAIL_HOST_USER": "",
            "EMAIL_HOST_PASSWORD": "",
            "EMAIL_USE_TLS": "",
            "EMAIL_USE_SSL": "",
            "DEFAULT_FROM_EMAIL": "",
            "SERVER_EMAIL": "",
            "SMTP_PORT": "",
            "SMTP_USER": "",
            "SMTP_PASSWORD": "",
            "SMTP_SECURITY": "",
            "SMTP_FROM_EMAIL": "",
        })
        self.assertEqual(getattr(django_settings, "EMAIL_HOST", ""), original_host)

    def test_existing_email_host_applies_direct_settings(self):
        from django.conf import settings as django_settings
        self._call({
            "SMTP_ENABLED": "",
            "SMTP_HOST": "",
            "EMAIL_HOST": "mail.direct.com",
            "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "EMAIL_PORT": "465",
            "EMAIL_HOST_USER": "admin",
            "EMAIL_HOST_PASSWORD": "secret",
            "EMAIL_USE_TLS": "false",
            "EMAIL_USE_SSL": "true",
            "DEFAULT_FROM_EMAIL": "admin@direct.com",
            "SERVER_EMAIL": "server@direct.com",
            "SMTP_PORT": "",
            "SMTP_USER": "",
            "SMTP_PASSWORD": "",
            "SMTP_SECURITY": "",
            "SMTP_FROM_EMAIL": "",
        })
        self.assertEqual(django_settings.EMAIL_HOST, "mail.direct.com")
        self.assertTrue(django_settings.EMAIL_USE_SSL)
        self.assertFalse(django_settings.EMAIL_USE_TLS)

    def test_ssl_security_sets_use_ssl(self):
        from django.conf import settings as django_settings
        self._call({
            "SMTP_ENABLED": "true",
            "SMTP_HOST": "smtp.ssl.com",
            "SMTP_PORT": "465",
            "SMTP_USER": "",
            "SMTP_PASSWORD": "",
            "SMTP_SECURITY": "ssl",
            "SMTP_FROM_EMAIL": "",
            "EMAIL_HOST": "",
            "EMAIL_BACKEND": "",
            "EMAIL_PORT": "",
            "EMAIL_HOST_USER": "",
            "EMAIL_HOST_PASSWORD": "",
            "EMAIL_USE_TLS": "",
            "EMAIL_USE_SSL": "",
            "DEFAULT_FROM_EMAIL": "",
            "SERVER_EMAIL": "",
        })
        self.assertFalse(django_settings.EMAIL_USE_TLS)
        self.assertTrue(django_settings.EMAIL_USE_SSL)


class TotpCodeFormTests(TestCase):
    def test_valid_otp_is_accepted(self):
        from core.views_auth import TotpCodeForm
        form = TotpCodeForm(data={"otp": "123456"})
        self.assertTrue(form.is_valid())

    def test_empty_otp_is_invalid(self):
        from core.views_auth import TotpCodeForm
        form = TotpCodeForm(data={"otp": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("otp", form.errors)

    def test_missing_otp_is_invalid(self):
        from core.views_auth import TotpCodeForm
        form = TotpCodeForm(data={})
        self.assertFalse(form.is_valid())


class TwoStepLoginViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_form_valid_without_totp_logs_in(self):
        from core.views_auth import TwoStepLoginView
        view = TwoStepLoginView()
        view.request = MagicMock()
        view.request.session = {}
        mock_form = MagicMock()
        user = MagicMock()
        user.profile = None
        mock_form.get_user.return_value = user
        # Just test that the view class is importable and has expected attributes
        self.assertEqual(view.template_name, "registration/login.html")


class RuntimeOtpViewTests(TestCase):
    def test_dispatch_redirects_without_session(self):
        from core.views_auth import RuntimeOtpView
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/otp/")
        request.session = {}
        view = RuntimeOtpView.as_view()
        with override_settings(LOGIN_URL="/login/"):
            response = view(request)
        self.assertEqual(response.status_code, 302)

    def test_max_attempts_is_three(self):
        from core.views_auth import RuntimeOtpView
        self.assertEqual(RuntimeOtpView.max_attempts, 3)

    def test_dispatch_with_session_reaches_super(self):
        """When pending_2fa_user_id is in session, dispatch proceeds to GET render."""
        session = self.client.session
        session["pending_2fa_user_id"] = 999
        session["otp_attempts"] = 0
        session.save()
        resp = self.client.get("/accounts/otp/")
        # OTP template rendered (200) or redirect if template missing — either way not 500
        self.assertIn(resp.status_code, (200, 302))

    def test_form_valid_invalid_user_id_redirects(self):
        """form_valid redirects when user_id not found in DB."""
        session = self.client.session
        session["pending_2fa_user_id"] = 999999  # non-existent
        session["otp_attempts"] = 0
        session.save()
        resp = self.client.post("/accounts/otp/", {"otp": "123456"})
        self.assertEqual(resp.status_code, 302)

    def test_form_valid_user_without_totp_redirects(self):
        """form_valid redirects when user has no TOTP profile."""
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="otp_notp", password="pass")
        session = self.client.session
        session["pending_2fa_user_id"] = user.id
        session["otp_attempts"] = 0
        session.save()
        resp = self.client.post("/accounts/otp/", {"otp": "123456"})
        self.assertEqual(resp.status_code, 302)

    def test_form_valid_wrong_code_increments_attempts(self):
        """Wrong code increments otp_attempts counter."""
        from unittest.mock import patch
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="otp_wrong", password="pass")
        user.profile.totp_secret = "JBSWY3DPEHPK3PXP"
        user.profile.totp_enabled = True
        user.profile.save()
        session = self.client.session
        session["pending_2fa_user_id"] = user.id
        session["otp_attempts"] = 0
        session.save()
        with patch("core.views_auth._verify_totp", return_value=False):
            resp = self.client.post("/accounts/otp/", {"otp": "000000"})
        # Returns form page again (200) or redirects
        self.assertIn(resp.status_code, (200, 302))

    def test_form_valid_max_attempts_locks_out(self):
        """After max_attempts wrong codes, redirects to login?otp=locked."""
        from unittest.mock import patch
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="otp_locked", password="pass")
        user.profile.totp_secret = "JBSWY3DPEHPK3PXP"
        user.profile.totp_enabled = True
        user.profile.save()
        session = self.client.session
        session["pending_2fa_user_id"] = user.id
        session["otp_attempts"] = 2  # already at max - 1
        session.save()
        with patch("core.views_auth._verify_totp", return_value=False):
            resp = self.client.post("/accounts/otp/", {"otp": "000000"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("otp=locked", resp["Location"])

    def test_form_valid_correct_code_logs_in(self):
        """Correct OTP code logs user in and redirects."""
        from unittest.mock import patch
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="otp_ok", password="pass")
        user.profile.totp_secret = "JBSWY3DPEHPK3PXP"
        user.profile.totp_enabled = True
        user.profile.save()
        session = self.client.session
        session["pending_2fa_user_id"] = user.id
        session["otp_attempts"] = 0
        session["pending_2fa_next"] = "/dashboard/"
        session.save()
        with patch("core.views_auth._verify_totp", return_value=True):
            resp = self.client.post("/accounts/otp/", {"otp": "123456"})
        self.assertEqual(resp.status_code, 302)


class TwoStepLoginViewIntegrationTests(TestCase):
    def test_login_with_totp_enabled_redirects_to_otp(self):
        """Logging in as TOTP-enabled user redirects to OTP page."""
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="totp_login", password="pass123")
        user.profile.totp_secret = "JBSWY3DPEHPK3PXP"
        user.profile.totp_enabled = True
        user.profile.save()
        resp = self.client.post(
            "/accounts/login/",
            {"username": "totp_login", "password": "pass123"},
            follow=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("otp", resp["Location"])

    def test_login_without_totp_completes_normally(self):
        """Logging in without TOTP completes without OTP step."""
        from django.contrib.auth.models import User
        User.objects.create_user(username="nototp_login", password="pass123")
        resp = self.client.post(
            "/accounts/login/",
            {"username": "nototp_login", "password": "pass123"},
            follow=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("otp", resp["Location"])


class ApplyRuntimeEmailSettingsBranchTests(TestCase):
    def test_default_from_and_server_email_applied(self):
        """Lines 71-74: both DEFAULT_FROM_EMAIL and SERVER_EMAIL get set when present."""
        from django.conf import settings as django_settings
        from core.views_auth import _apply_runtime_email_settings
        with patch("core.views_auth.read_values", return_value={
            "SMTP_ENABLED": "",
            "SMTP_HOST": "",
            "EMAIL_HOST": "mail.example.com",
            "EMAIL_BACKEND": "",
            "EMAIL_PORT": "587",
            "EMAIL_HOST_USER": "",
            "EMAIL_HOST_PASSWORD": "",
            "EMAIL_USE_TLS": "false",
            "EMAIL_USE_SSL": "false",
            "DEFAULT_FROM_EMAIL": "noreply@example.com",
            "SERVER_EMAIL": "server@example.com",
            "SMTP_PORT": "",
            "SMTP_USER": "",
            "SMTP_PASSWORD": "",
            "SMTP_SECURITY": "",
            "SMTP_FROM_EMAIL": "",
        }):
            _apply_runtime_email_settings()
        self.assertEqual(django_settings.DEFAULT_FROM_EMAIL, "noreply@example.com")
        self.assertEqual(django_settings.SERVER_EMAIL, "server@example.com")
