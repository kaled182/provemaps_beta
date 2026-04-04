"""Tests for core middleware — auth_required, first_time_setup,
request_id, security_headers."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings


# ---------------------------------------------------------------------------
# AuthRequiredMiddleware
# ---------------------------------------------------------------------------

class AuthRequiredMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=MagicMock(status_code=200))
        from core.middleware.auth_required import AuthRequiredMiddleware
        self.mw = AuthRequiredMiddleware(self.get_response)

    def _anon_request(self, path):
        req = self.factory.get(path)
        req.user = AnonymousUser()
        return req

    def _auth_request(self, path):
        from django.contrib.auth.models import User
        req = self.factory.get(path)
        req.user = MagicMock(spec=User, is_authenticated=True)
        return req

    def test_authenticated_passes_through(self):
        req = self._auth_request("/some/protected/")
        self.mw(req)
        self.get_response.assert_called_once()

    def test_anon_root_redirects_to_login(self):
        req = self._anon_request("/")
        resp = self.mw(req)
        self.assertEqual(resp.status_code, 302)

    def test_anon_subpath_redirects_with_next(self):
        req = self._anon_request("/maps/dashboard/")
        resp = self.mw(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("next=", resp["Location"])

    def test_login_path_whitelisted(self):
        req = self._anon_request("/accounts/login/")
        self.mw(req)
        self.get_response.assert_called_once()

    def test_static_path_whitelisted(self):
        req = self._anon_request("/static/app.js")
        self.mw(req)
        self.get_response.assert_called_once()

    def test_media_path_whitelisted(self):
        req = self._anon_request("/media/logo.png")
        self.mw(req)
        self.get_response.assert_called_once()

    def test_healthz_whitelisted(self):
        req = self._anon_request("/healthz")
        self.mw(req)
        self.get_response.assert_called_once()

    def test_api_v1_prefix_whitelisted(self):
        req = self._anon_request("/api/v1/inventory/")
        self.mw(req)
        self.get_response.assert_called_once()

    def test_metrics_whitelisted(self):
        req = self._anon_request("/metrics/")
        self.mw(req)
        self.get_response.assert_called_once()

    def test_admin_whitelisted(self):
        req = self._anon_request("/admin/")
        self.mw(req)
        self.get_response.assert_called_once()

    def test_is_whitelisted_exact_match(self):
        self.assertTrue(self.mw._is_whitelisted("/healthz"))
        self.assertTrue(self.mw._is_whitelisted("/accounts/login/"))

    def test_is_whitelisted_prefix_match(self):
        self.assertTrue(self.mw._is_whitelisted("/api/v1/anything"))
        self.assertTrue(self.mw._is_whitelisted("/static/foo/bar.css"))

    def test_is_whitelisted_not_matched(self):
        self.assertFalse(self.mw._is_whitelisted("/secret/data/"))

    def test_setup_path_whitelisted(self):
        req = self._anon_request("/setup_app/first_time/")
        self.mw(req)
        self.get_response.assert_called_once()


# ---------------------------------------------------------------------------
# FirstTimeSetupRedirectMiddleware
# ---------------------------------------------------------------------------

class FirstTimeSetupMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=MagicMock(status_code=200))

    def _make_mw(self):
        from core.middleware.first_time_setup import (
            FirstTimeSetupRedirectMiddleware,
        )
        return FirstTimeSetupRedirectMiddleware(self.get_response)

    @override_settings(TESTING=True, FORCE_FIRST_TIME_FLOW=False)
    def test_testing_mode_skips_check(self):
        mw = self._make_mw()
        req = self.factory.get("/some/page/")
        mw(req)
        self.get_response.assert_called_once()

    @override_settings(TESTING=False, FORCE_FIRST_TIME_FLOW=True)
    def test_unconfigured_redirects_to_setup(self):
        mw = self._make_mw()
        req = self.factory.get("/maps/dashboard/")
        with patch(
            "core.middleware.first_time_setup.FirstTimeSetup"
            ".objects.filter"
        ) as mock_filter:
            mock_filter.return_value.exists.return_value = False
            resp = mw(req)
        self.assertEqual(resp.status_code, 302)

    @override_settings(TESTING=False, FORCE_FIRST_TIME_FLOW=True)
    def test_configured_passes_through(self):
        mw = self._make_mw()
        req = self.factory.get("/maps/dashboard/")
        with patch(
            "core.middleware.first_time_setup.FirstTimeSetup"
            ".objects.filter"
        ) as mock_filter:
            mock_filter.return_value.exists.return_value = True
            mw(req)
        self.get_response.assert_called_once()

    @override_settings(TESTING=False, FORCE_FIRST_TIME_FLOW=True)
    def test_static_always_allowed(self):
        mw = self._make_mw()
        req = self.factory.get("/static/app.css")
        with patch(
            "core.middleware.first_time_setup.FirstTimeSetup"
            ".objects.filter"
        ) as mock_filter:
            mock_filter.return_value.exists.return_value = False
            mw(req)
        self.get_response.assert_called_once()

    def test_is_always_allowed_setup_prefix(self):
        mw = self._make_mw()
        self.assertTrue(mw._is_always_allowed("/setup_app/first_time/"))

    def test_is_always_allowed_favicon(self):
        mw = self._make_mw()
        self.assertTrue(mw._is_always_allowed("/favicon.ico"))

    def test_is_configured_queries_db(self):
        mw = self._make_mw()
        with patch(
            "core.middleware.first_time_setup.FirstTimeSetup"
            ".objects.filter"
        ) as mock_filter:
            mock_filter.return_value.exists.return_value = True
            self.assertTrue(mw._is_configured())

    def test_is_not_configured_queries_db(self):
        mw = self._make_mw()
        with patch(
            "core.middleware.first_time_setup.FirstTimeSetup"
            ".objects.filter"
        ) as mock_filter:
            mock_filter.return_value.exists.return_value = False
            self.assertFalse(mw._is_configured())


# ---------------------------------------------------------------------------
# RequestIDMiddleware
# ---------------------------------------------------------------------------

class RequestIDMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=MagicMock(status_code=200))
        from core.middleware.request_id import RequestIDMiddleware
        self.mw = RequestIDMiddleware(self.get_response)

    def test_generates_request_id(self):
        req = self.factory.get("/any/")
        self.mw.process_request(req)
        self.assertTrue(hasattr(req, "request_id"))
        self.assertIsNotNone(req.request_id)

    def test_uses_existing_x_request_id_header(self):
        req = self.factory.get("/any/", HTTP_X_REQUEST_ID="test-id-123")
        self.mw.process_request(req)
        self.assertEqual(req.request_id, "test-id-123")

    def test_process_response_adds_header(self):
        req = self.factory.get("/any/")
        self.mw.process_request(req)
        from django.http import HttpResponse
        resp = HttpResponse("ok")
        result = self.mw.process_response(req, resp)
        self.assertIn("X-Request-ID", result)

    def test_process_response_no_request_id_attribute(self):
        req = self.factory.get("/any/")
        from django.http import HttpResponse
        resp = HttpResponse("ok")
        # Should not raise even if request_id missing
        result = self.mw.process_response(req, resp)
        self.assertNotIn("X-Request-ID", result)

    def test_process_exception_logs_with_request_id(self):
        req = self.factory.get("/any/")
        self.mw.process_request(req)
        exc = ValueError("test error")
        result = self.mw.process_exception(req, exc)
        self.assertIsNone(result)

    def test_process_exception_without_request_id(self):
        req = self.factory.get("/any/")
        exc = ValueError("test error")
        result = self.mw.process_exception(req, exc)
        self.assertIsNone(result)

    def test_get_client_ip_direct(self):
        req = self.factory.get("/", REMOTE_ADDR="1.2.3.4")
        ip = self.mw._get_client_ip(req)
        self.assertEqual(ip, "1.2.3.4")

    def test_get_client_ip_from_forwarded_for(self):
        req = self.factory.get(
            "/", HTTP_X_FORWARDED_FOR="5.6.7.8, 10.0.0.1"
        )
        ip = self.mw._get_client_ip(req)
        self.assertEqual(ip, "5.6.7.8")

    def test_process_request_returns_none(self):
        req = self.factory.get("/any/")
        result = self.mw.process_request(req)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=MagicMock(status_code=200))
        from core.middleware.security_headers import SecurityHeadersMiddleware
        self.mw = SecurityHeadersMiddleware(self.get_response)

    def _make_response(self):
        from django.http import HttpResponse
        return HttpResponse("ok")

    def test_adds_x_frame_options(self):
        req = self.factory.get("/")
        resp = self._make_response()
        result = self.mw.process_response(req, resp)
        self.assertEqual(result["X-Frame-Options"], "DENY")

    def test_adds_x_content_type_options(self):
        req = self.factory.get("/")
        resp = self._make_response()
        result = self.mw.process_response(req, resp)
        self.assertEqual(result["X-Content-Type-Options"], "nosniff")

    def test_adds_x_xss_protection(self):
        req = self.factory.get("/")
        resp = self._make_response()
        result = self.mw.process_response(req, resp)
        self.assertEqual(result["X-XSS-Protection"], "1; mode=block")

    def test_does_not_override_existing_x_frame_options(self):
        from django.http import HttpResponse
        req = self.factory.get("/")
        resp = HttpResponse("ok")
        resp["X-Frame-Options"] = "SAMEORIGIN"
        result = self.mw.process_response(req, resp)
        self.assertEqual(result["X-Frame-Options"], "SAMEORIGIN")

    @override_settings(CONTENT_SECURITY_POLICY={"default-src": ["'self'"]})
    def test_adds_csp_header_when_configured(self):
        req = self.factory.get("/")
        resp = self._make_response()
        result = self.mw.process_response(req, resp)
        self.assertIn("Content-Security-Policy", result)
        self.assertIn("default-src", result["Content-Security-Policy"])

    @override_settings(CONTENT_SECURITY_POLICY={})
    def test_no_csp_when_empty(self):
        req = self.factory.get("/")
        resp = self._make_response()
        result = self.mw.process_response(req, resp)
        self.assertNotIn("Content-Security-Policy", result)

    @override_settings(SECURE_REFERRER_POLICY="no-referrer")
    def test_adds_referrer_policy(self):
        req = self.factory.get("/")
        resp = self._make_response()
        result = self.mw.process_response(req, resp)
        self.assertEqual(result["Referrer-Policy"], "no-referrer")
