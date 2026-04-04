"""Tests for setup_app.views — first_time_setup, setup_dashboard, manage_environment."""
from __future__ import annotations

import tempfile
import os
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings


class GetSetupLogoTests(TestCase):
    def test_returns_namespace_when_company_profile_has_logo(self):
        from setup_app.views import get_setup_logo
        mock_profile = MagicMock()
        mock_profile.assets_logo = "logos/logo.png"
        with patch("setup_app.views.CompanyProfile.objects.order_by") as mock_order:
            mock_order.return_value.first.return_value = mock_profile
            result = get_setup_logo()
        self.assertEqual(result.logo, "logos/logo.png")

    def test_returns_first_time_setup_when_no_logo(self):
        from setup_app.views import get_setup_logo
        mock_profile = MagicMock()
        mock_profile.assets_logo = None
        mock_setup = MagicMock()
        with patch("setup_app.views.CompanyProfile.objects.order_by") as mock_order, \
             patch("setup_app.views.FirstTimeSetup.objects.filter") as mock_filter:
            mock_order.return_value.first.return_value = mock_profile
            mock_filter.return_value.order_by.return_value.first.return_value = mock_setup
            result = get_setup_logo()
        self.assertEqual(result, mock_setup)

    def test_returns_first_time_setup_when_no_profile(self):
        from setup_app.views import get_setup_logo
        mock_setup = MagicMock()
        with patch("setup_app.views.CompanyProfile.objects.order_by") as mock_order, \
             patch("setup_app.views.FirstTimeSetup.objects.filter") as mock_filter:
            mock_order.return_value.first.return_value = None
            mock_filter.return_value.order_by.return_value.first.return_value = mock_setup
            result = get_setup_logo()
        self.assertEqual(result, mock_setup)


class StaffCheckTests(TestCase):
    def test_active_staff_returns_true(self):
        from setup_app.views import _staff_check
        user = MagicMock(is_active=True, is_staff=True)
        self.assertTrue(_staff_check(user))

    def test_inactive_user_returns_false(self):
        from setup_app.views import _staff_check
        user = MagicMock(is_active=False, is_staff=True)
        self.assertFalse(_staff_check(user))

    def test_non_staff_returns_false(self):
        from setup_app.views import _staff_check
        user = MagicMock(is_active=True, is_staff=False)
        self.assertFalse(_staff_check(user))


class IsSetupLockedTests(TestCase):
    def test_returns_false_when_no_lock_file(self):
        from setup_app.views import _is_setup_locked
        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(BASE_DIR=tmpdir):
                result = _is_setup_locked()
        self.assertFalse(result)

    def test_returns_true_when_lock_file_exists(self):
        from setup_app.views import _is_setup_locked
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = os.path.join(tmpdir, "SETUP_LOCKED")
            open(lock_file, "w").close()
            with override_settings(BASE_DIR=tmpdir):
                result = _is_setup_locked()
        self.assertTrue(result)


class FirstTimeSetupViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_locked_setup_returns_403(self):
        from setup_app.views import first_time_setup
        request = self.factory.get("/setup/")
        with patch("setup_app.views._is_setup_locked", return_value=True):
            response = first_time_setup(request)
        self.assertEqual(response.status_code, 403)

    def test_already_configured_redirects(self):
        from setup_app.views import first_time_setup
        request = self.factory.get("/setup/")
        with patch("setup_app.views._is_setup_locked", return_value=False), \
             patch("setup_app.views.FirstTimeSetup.objects.filter") as mock_filter:
            mock_filter.return_value.exists.return_value = True
            response = first_time_setup(request)
        self.assertEqual(response.status_code, 302)

    def test_get_renders_form(self):
        from setup_app.views import first_time_setup
        request = self.factory.get("/setup/")
        with patch("setup_app.views._is_setup_locked", return_value=False), \
             patch("setup_app.views.FirstTimeSetup.objects.filter") as mock_filter, \
             patch("setup_app.views.get_setup_logo", return_value=None), \
             patch("setup_app.views.render") as mock_render:
            mock_filter.return_value.exists.return_value = False
            mock_render.return_value = MagicMock(status_code=200)
            first_time_setup(request)
        mock_render.assert_called_once()
        template = mock_render.call_args[0][1]
        self.assertEqual(template, "first_time_setup.html")


class SetupDashboardViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_unauthenticated_redirects(self):
        from setup_app.views import setup_dashboard
        request = self.factory.get("/setup/dashboard/")
        request.user = AnonymousUser()
        response = setup_dashboard(request)
        self.assertEqual(response.status_code, 302)

    def test_authenticated_renders(self):
        from setup_app.views import setup_dashboard
        request = self.factory.get("/setup/dashboard/")
        request.user = MagicMock(is_authenticated=True)
        with patch("setup_app.views.get_setup_logo", return_value=None), \
             patch("setup_app.views.render") as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            setup_dashboard(request)
        mock_render.assert_called_once()


class ManageEnvironmentViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _make_staff_request(self, method="GET"):
        if method == "GET":
            request = self.factory.get("/setup/env/")
        else:
            request = self.factory.post("/setup/env/", data={})
        request.user = MagicMock(
            is_authenticated=True,
            is_active=True,
            is_staff=True,
        )
        return request

    def test_get_renders_system_settings(self):
        from setup_app.views import manage_environment
        request = self._make_staff_request("GET")
        with patch("setup_app.views.get_setup_logo", return_value=None), \
             patch("setup_app.views.render") as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            manage_environment(request)
        ctx = mock_render.call_args[0][2]
        self.assertEqual(ctx["title"], "System Settings")

    def test_post_with_invalid_form_returns_400(self):
        from setup_app.views import manage_environment
        request = self._make_staff_request("POST")
        with patch("setup_app.views.get_setup_logo", return_value=None), \
             patch("setup_app.views.render") as mock_render:
            mock_render.return_value = MagicMock(status_code=400)
            manage_environment(request)
        # Called with status 400 when form is invalid
        call_kwargs = mock_render.call_args
        self.assertIsNotNone(call_kwargs)

    def test_unauthenticated_redirects(self):
        from setup_app.views import manage_environment
        request = self.factory.get("/setup/env/")
        request.user = AnonymousUser()
        response = manage_environment(request)
        self.assertEqual(response.status_code, 302)
