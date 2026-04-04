"""Integration tests for core.api_users view functions.

Covers: list_departments, department_detail, remove_department,
        list_users, get_user, create_user, update_user, delete_user,
        list_groups, me_user.
"""
from __future__ import annotations

import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse, NoReverseMatch


def _post_json(client, url, data, **kwargs):
    return client.post(url, json.dumps(data), content_type="application/json", **kwargs)


def _patch_json(client, url, data, **kwargs):
    return client.patch(url, json.dumps(data), content_type="application/json", **kwargs)


def _put_json(client, url, data, **kwargs):
    return client.put(url, json.dumps(data), content_type="application/json", **kwargs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dept_list_url():
    try:
        return reverse("api_list_departments")
    except NoReverseMatch:
        return "/api/users/departments/"


def _dept_detail_url(pk):
    try:
        return reverse("api_department_detail", args=[pk])
    except NoReverseMatch:
        return f"/api/users/departments/{pk}/"


def _dept_remove_url(pk):
    try:
        return reverse("api_remove_department", args=[pk])
    except NoReverseMatch:
        return f"/api/users/departments/{pk}/remove/"


def _users_url():
    try:
        return reverse("api_list_users")
    except NoReverseMatch:
        return "/api/users/"


def _user_url(pk):
    try:
        return reverse("api_get_user", args=[pk])
    except NoReverseMatch:
        return f"/api/users/{pk}/"


def _create_user_url():
    try:
        return reverse("api_create_user")
    except NoReverseMatch:
        return "/api/users/create/"


def _update_user_url(pk):
    try:
        return reverse("api_update_user", args=[pk])
    except NoReverseMatch:
        return f"/api/users/{pk}/update/"


def _delete_user_url(pk):
    try:
        return reverse("api_delete_user", args=[pk])
    except NoReverseMatch:
        return f"/api/users/{pk}/delete/"


def _groups_url():
    try:
        return reverse("api_list_groups")
    except NoReverseMatch:
        return "/api/users/groups/"


def _me_url():
    try:
        return reverse("api_me_user")
    except NoReverseMatch:
        return "/api/users/me/"


# ---------------------------------------------------------------------------
# Helper functions (non-view) tests
# ---------------------------------------------------------------------------

class CoerceBoolTests(TestCase):
    def test_bool_passthrough(self):
        from core.api_users import _coerce_bool
        self.assertTrue(_coerce_bool(True))
        self.assertFalse(_coerce_bool(False))

    def test_none_returns_none(self):
        from core.api_users import _coerce_bool
        self.assertIsNone(_coerce_bool(None))

    def test_truthy_strings(self):
        from core.api_users import _coerce_bool
        for v in ("1", "true", "yes", "on", "TRUE", "Yes"):
            self.assertTrue(_coerce_bool(v), f"Expected True for {v!r}")

    def test_falsy_strings(self):
        from core.api_users import _coerce_bool
        for v in ("0", "false", "no", "off", "FALSE"):
            self.assertFalse(_coerce_bool(v), f"Expected False for {v!r}")

    def test_unrecognised_string_returned_as_is(self):
        from core.api_users import _coerce_bool
        self.assertEqual(_coerce_bool("maybe"), "maybe")


class ExtractProfileDataTests(TestCase):
    def test_extracts_nested_profile_dict(self):
        from core.api_users import _extract_profile_data
        raw = {"profile": {"phone_number": "123", "notify_via_email": "true"}}
        result = _extract_profile_data(raw)
        self.assertEqual(result["phone_number"], "123")
        self.assertTrue(result["notify_via_email"])

    def test_extracts_dotted_profile_keys(self):
        from core.api_users import _extract_profile_data
        raw = {"profile.phone_number": "+5511", "profile.notify_via_whatsapp": "false"}
        result = _extract_profile_data(raw)
        self.assertEqual(result["phone_number"], "+5511")
        self.assertFalse(result["notify_via_whatsapp"])

    def test_empty_raw_returns_empty(self):
        from core.api_users import _extract_profile_data
        self.assertEqual(_extract_profile_data({}), {})


class TotpHelpersTests(TestCase):
    def test_generate_secret_is_base32(self):
        from core.api_users import _generate_totp_secret
        import base64
        secret = _generate_totp_secret()
        self.assertTrue(len(secret) > 0)
        # Should be decodeable as base32 (padded)
        padding = "=" * ((8 - len(secret) % 8) % 8)
        base64.b32decode(secret + padding)

    def test_totp_at_returns_int(self):
        from core.api_users import _generate_totp_secret, _totp_at
        secret = _generate_totp_secret()
        code = _totp_at(secret, 1000)
        self.assertIsInstance(code, int)
        self.assertTrue(0 <= code < 1_000_000)

    def test_verify_totp_rejects_nonnumeric(self):
        from core.api_users import _generate_totp_secret, _verify_totp
        secret = _generate_totp_secret()
        self.assertFalse(_verify_totp(secret, "abc"))

    def test_verify_totp_rejects_empty(self):
        from core.api_users import _generate_totp_secret, _verify_totp
        secret = _generate_totp_secret()
        self.assertFalse(_verify_totp(secret, ""))

    def test_build_otpauth_url_contains_secret(self):
        from core.api_users import _build_otpauth_url
        url = _build_otpauth_url("MYSECRET", "alice", "Acme")
        self.assertIn("MYSECRET", url)
        self.assertIn("otpauth://totp/", url)


class IsStaffOrSuperuserTests(TestCase):
    def test_staff_returns_true(self):
        from core.api_users import is_staff_or_superuser
        from unittest.mock import MagicMock
        user = MagicMock(is_staff=True, is_superuser=False)
        self.assertTrue(is_staff_or_superuser(user))

    def test_superuser_returns_true(self):
        from core.api_users import is_staff_or_superuser
        from unittest.mock import MagicMock
        user = MagicMock(is_staff=False, is_superuser=True)
        self.assertTrue(is_staff_or_superuser(user))

    def test_regular_user_returns_false(self):
        from core.api_users import is_staff_or_superuser
        from unittest.mock import MagicMock
        user = MagicMock(is_staff=False, is_superuser=False)
        self.assertFalse(is_staff_or_superuser(user))


# ---------------------------------------------------------------------------
# Department views (integrated with real DB)
# ---------------------------------------------------------------------------

class ListDepartmentsViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_dept", password="pass123", email="admin_dept@test.com"
        )
        self.client.force_login(self.superuser)

    def _get(self):
        return self.client.get(_dept_list_url())

    def _post(self, data):
        return _post_json(self.client, _dept_list_url(), data)

    def test_get_returns_200(self):
        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn("departments", data)

    def test_post_creates_department(self):
        resp = self._post({"name": "Engineering", "description": "Eng dept"})
        self.assertIn(resp.status_code, (200, 201))
        data = json.loads(resp.content)
        self.assertTrue(data.get("success"))
        self.assertEqual(data["department"]["name"], "Engineering")

    def test_post_missing_name_returns_400(self):
        resp = self._post({"name": ""})
        self.assertEqual(resp.status_code, 400)

    def test_post_invalid_json_returns_400(self):
        resp = self.client.post(_dept_list_url(), "not-json", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_post_duplicate_name_returns_400(self):
        self._post({"name": "Finance"})
        resp = self._post({"name": "Finance"})
        self.assertEqual(resp.status_code, 400)

    def test_unauthenticated_returns_redirect_or_403(self):
        self.client.logout()
        resp = self._get()
        self.assertIn(resp.status_code, (302, 403))


class DepartmentDetailViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_det", password="pass123", email="admin_det@test.com"
        )
        self.client.force_login(self.superuser)
        # Create a dept via the view
        resp = _post_json(self.client, _dept_list_url(), {"name": "Sales"})
        self.dept_id = json.loads(resp.content)["department"]["id"]

    def test_patch_updates_name(self):
        resp = _patch_json(self.client, _dept_detail_url(self.dept_id), {"name": "Sales Renamed"})
        self.assertIn(resp.status_code, (200, 201))
        data = json.loads(resp.content)
        self.assertTrue(data.get("success"))

    def test_patch_invalid_json_returns_400(self):
        resp = self.client.patch(
            _dept_detail_url(self.dept_id), "bad", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_patch_empty_name_returns_400(self):
        resp = _patch_json(self.client, _dept_detail_url(self.dept_id), {"name": ""})
        self.assertEqual(resp.status_code, 400)

    def test_delete_removes_department(self):
        resp = self.client.delete(_dept_detail_url(self.dept_id))
        self.assertIn(resp.status_code, (200, 204))

    def test_delete_nonexistent_returns_404(self):
        resp = self.client.delete(_dept_detail_url(99999))
        self.assertEqual(resp.status_code, 404)

    def test_patch_nonexistent_returns_404(self):
        resp = _patch_json(self.client, _dept_detail_url(99999), {"name": "X"})
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# User management views
# ---------------------------------------------------------------------------

class ListUsersViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_lu", password="pass123", email="admin_lu@test.com"
        )
        self.regular = User.objects.create_user(
            username="alice", password="pass123", email="alice@test.com"
        )
        self.client.force_login(self.superuser)

    def test_returns_200_with_users_list(self):
        resp = self.client.get(_users_url())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn("users", data)

    def test_search_filter(self):
        resp = self.client.get(_users_url() + "?search=alice")
        self.assertEqual(resp.status_code, 200)

    def test_is_active_filter(self):
        resp = self.client.get(_users_url() + "?is_active=true")
        self.assertEqual(resp.status_code, 200)


class GetUserViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_gu", password="pass123", email="admin_gu@test.com"
        )
        self.target = User.objects.create_user(
            username="bob", password="pass123", email="bob@test.com"
        )
        self.client.force_login(self.superuser)

    def test_returns_user_detail(self):
        resp = self.client.get(_user_url(self.target.pk))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["user"]["username"], "bob")

    def test_nonexistent_user_returns_404(self):
        resp = self.client.get(_user_url(99999))
        self.assertEqual(resp.status_code, 404)


class CreateUserViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_cu", password="pass123", email="admin_cu@test.com"
        )
        self.client.force_login(self.superuser)

    def test_creates_user_successfully(self):
        payload = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "Str0ng!pass",
        }
        resp = _post_json(self.client, _create_user_url(), payload)
        self.assertIn(resp.status_code, (200, 201))
        data = json.loads(resp.content)
        self.assertTrue(data.get("success"))

    def test_missing_username_returns_400(self):
        resp = _post_json(self.client, _create_user_url(), {
            "email": "x@test.com", "password": "pass"
        })
        self.assertEqual(resp.status_code, 400)

    def test_missing_email_returns_400(self):
        resp = _post_json(self.client, _create_user_url(), {
            "username": "x", "password": "pass"
        })
        self.assertEqual(resp.status_code, 400)

    def test_missing_password_returns_400(self):
        resp = _post_json(self.client, _create_user_url(), {
            "username": "x", "email": "x@test.com"
        })
        self.assertEqual(resp.status_code, 400)

    def test_invalid_email_returns_400(self):
        resp = _post_json(self.client, _create_user_url(), {
            "username": "x", "email": "not-an-email", "password": "pass"
        })
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_username_returns_400(self):
        payload = {"username": "admin_cu", "email": "dup@test.com", "password": "pass"}
        resp = _post_json(self.client, _create_user_url(), payload)
        self.assertEqual(resp.status_code, 400)

    def test_invalid_json_returns_400(self):
        resp = self.client.post(_create_user_url(), "bad", content_type="application/json")
        self.assertEqual(resp.status_code, 400)


class UpdateUserViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_uu", password="pass123", email="admin_uu@test.com"
        )
        self.target = User.objects.create_user(
            username="charlie", password="pass123", email="charlie@test.com"
        )
        self.client.force_login(self.superuser)

    def test_updates_first_name(self):
        resp = _patch_json(self.client, _update_user_url(self.target.pk), {
            "first_name": "Charles"
        })
        self.assertIn(resp.status_code, (200, 201))
        data = json.loads(resp.content)
        self.assertTrue(data.get("success"))

    def test_nonexistent_user_returns_404(self):
        resp = _patch_json(self.client, _update_user_url(99999), {"first_name": "X"})
        self.assertEqual(resp.status_code, 404)

    def test_invalid_json_returns_400(self):
        resp = self.client.patch(
            _update_user_url(self.target.pk), "bad", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_email_returns_400(self):
        resp = _patch_json(self.client, _update_user_url(self.target.pk), {
            "email": "not-valid"
        })
        self.assertEqual(resp.status_code, 400)

    def test_patch_profile_with_empty_departments_list(self):
        resp = _patch_json(self.client, _update_user_url(self.target.pk), {
            "profile": {"departments": []},
        })
        self.assertIn(resp.status_code, (200, 201))

    def test_patch_profile_with_nonexistent_department_name(self):
        resp = _patch_json(self.client, _update_user_url(self.target.pk), {
            "profile": {"department": "NonExistentDept"},
        })
        self.assertIn(resp.status_code, (200, 201))

    def test_patch_profile_with_empty_department_name(self):
        resp = _patch_json(self.client, _update_user_url(self.target.pk), {
            "profile": {"department": ""},
        })
        self.assertIn(resp.status_code, (200, 201))


class DeleteUserViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_du", password="pass123", email="admin_du@test.com"
        )
        self.target = User.objects.create_user(
            username="dave", password="pass123", email="dave@test.com"
        )
        self.client.force_login(self.superuser)

    def test_deletes_user_successfully(self):
        resp = self.client.delete(_delete_user_url(self.target.pk))
        self.assertIn(resp.status_code, (200, 204))
        data = json.loads(resp.content)
        self.assertTrue(data.get("success"))

    def test_cannot_delete_own_account(self):
        resp = self.client.delete(_delete_user_url(self.superuser.pk))
        self.assertEqual(resp.status_code, 403)

    def test_nonexistent_returns_404(self):
        resp = self.client.delete(_delete_user_url(99999))
        self.assertEqual(resp.status_code, 404)

    def test_non_superuser_gets_403(self):
        staff = User.objects.create_user(
            username="staffonly", password="pass", email="s@test.com", is_staff=True
        )
        self.client.force_login(staff)
        resp = self.client.delete(_delete_user_url(self.target.pk))
        self.assertEqual(resp.status_code, 403)


class ListGroupsViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_lg", password="pass123", email="admin_lg@test.com"
        )
        self.client.force_login(self.superuser)

    def test_returns_groups_list(self):
        resp = self.client.get(_groups_url())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn("groups", data)


class MeUserViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="meuser", password="pass123", email="me@test.com"
        )
        self.client.force_login(self.user)

    def test_get_returns_own_user(self):
        resp = self.client.get(_me_url())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["user"]["username"], "meuser")

    def test_patch_updates_first_name(self):
        resp = _patch_json(self.client, _me_url(), {"first_name": "MeName"})
        self.assertIn(resp.status_code, (200, 201))

    def test_patch_invalid_email_returns_400(self):
        resp = _patch_json(self.client, _me_url(), {"email": "bad-email"})
        self.assertEqual(resp.status_code, 400)

    def test_patch_invalid_json_returns_400(self):
        resp = self.client.patch(
            _me_url(), "bad", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_unauthenticated_returns_redirect_or_403(self):
        self.client.logout()
        resp = self.client.get(_me_url())
        self.assertIn(resp.status_code, (302, 403))


# ---------------------------------------------------------------------------
# me_avatar
# ---------------------------------------------------------------------------

def _me_avatar_url():
    try:
        return reverse("api_me_avatar")
    except NoReverseMatch:
        return "/api/users/me/avatar/"


class MeAvatarViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="avatar_user", password="pass", email="avatar@test.com"
        )
        self.client.force_login(self.user)

    def test_post_without_file_returns_400(self):
        resp = self.client.post(_me_avatar_url(), {})
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertFalse(data["success"])

    def test_post_with_avatar_returns_200(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        avatar = SimpleUploadedFile("avatar.png", b"\x89PNG\r\n", content_type="image/png")
        resp = self.client.post(_me_avatar_url(), {"avatar": avatar})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertIn("avatar_url", data)

    def test_unauthenticated_returns_redirect(self):
        self.client.logout()
        resp = self.client.post(_me_avatar_url(), {})
        self.assertIn(resp.status_code, (302, 403))


# ---------------------------------------------------------------------------
# me_totp
# ---------------------------------------------------------------------------

def _me_totp_url():
    try:
        return reverse("api_me_totp")
    except NoReverseMatch:
        return "/api/users/me/totp/"


def _me_totp_verify_url():
    try:
        return reverse("api_me_totp_verify")
    except NoReverseMatch:
        return "/api/users/me/totp/verify/"


def _me_totp_disable_url():
    try:
        return reverse("api_me_totp_disable")
    except NoReverseMatch:
        return "/api/users/me/totp/disable/"


class MeTotpViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="totp_user", password="pass", email="totp@test.com"
        )
        self.client.force_login(self.user)

    def test_get_returns_totp_status(self):
        resp = self.client.get(_me_totp_url())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertIn("enabled", data)
        self.assertIn("configured", data)

    def test_get_setup_true_returns_secret(self):
        resp = self.client.get(_me_totp_url(), {"setup": "true"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertIn("secret", data)
        self.assertIn("otpauth_url", data)
        self.assertIn("issuer", data)

    def test_get_setup_reset_generates_new_secret(self):
        # First setup to create secret
        self.client.get(_me_totp_url(), {"setup": "true"})
        # Reset generates new secret
        resp = self.client.get(_me_totp_url(), {"setup": "true", "reset": "true"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn("secret", data)
        self.assertTrue(bool(data["secret"]))

    def test_unauthenticated_returns_redirect(self):
        self.client.logout()
        resp = self.client.get(_me_totp_url())
        self.assertIn(resp.status_code, (302, 403))


class MeTotpVerifyViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="totp_verify_user", password="pass", email="totpv@test.com"
        )
        self.client.force_login(self.user)

    def test_post_without_secret_returns_400(self):
        resp = _post_json(self.client, _me_totp_verify_url(), {"code": "123456"})
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertFalse(data["success"])
        self.assertIn("not configured", data["error"])

    def test_post_invalid_json_returns_400(self):
        resp = self.client.post(
            _me_totp_verify_url(), "not-json", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_wrong_code_returns_400(self):
        # First create a secret
        self.client.get(_me_totp_url(), {"setup": "true"})
        resp = _post_json(self.client, _me_totp_verify_url(), {"code": "000000"})
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertFalse(data["success"])

    def test_post_valid_code_enables_totp(self):
        from unittest.mock import patch
        # Create a secret first
        self.client.get(_me_totp_url(), {"setup": "true"})
        # Patch _verify_totp to return True
        with patch("core.api_users._verify_totp", return_value=True):
            resp = _post_json(self.client, _me_totp_verify_url(), {"code": "123456"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertTrue(data["enabled"])

    def test_unauthenticated_returns_redirect(self):
        self.client.logout()
        resp = _post_json(self.client, _me_totp_verify_url(), {"code": "123456"})
        self.assertIn(resp.status_code, (302, 403))


class MeTotpDisableViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="totp_disable_user", password="pass", email="totpd@test.com"
        )
        self.client.force_login(self.user)

    def test_post_disables_totp(self):
        resp = _post_json(self.client, _me_totp_disable_url(), {})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertFalse(data["enabled"])

    def test_post_with_reset_clears_secret(self):
        # First create a secret
        self.client.get(_me_totp_url(), {"setup": "true"})
        resp = _post_json(self.client, _me_totp_disable_url(), {"reset": "true"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.assertFalse(data["configured"])

    def test_post_invalid_json_uses_defaults(self):
        resp = self.client.post(
            _me_totp_disable_url(), "not-json", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])

    def test_unauthenticated_returns_redirect(self):
        self.client.logout()
        resp = _post_json(self.client, _me_totp_disable_url(), {})
        self.assertIn(resp.status_code, (302, 403))
