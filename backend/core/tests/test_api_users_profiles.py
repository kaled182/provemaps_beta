"""Tests for profile helpers in core.api_users."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

from django.test import TestCase


class SerializeProfileTests(TestCase):
    def _make_profile(self, **kwargs):
        profile = MagicMock()
        profile.avatar = kwargs.get("avatar", None)
        profile.phone_number = kwargs.get("phone_number", "")
        profile.telegram_chat_id = kwargs.get("telegram_chat_id", "")
        profile.notify_via_email = kwargs.get("notify_via_email", True)
        profile.notify_via_whatsapp = kwargs.get("notify_via_whatsapp", False)
        profile.notify_via_telegram = kwargs.get("notify_via_telegram", False)
        profile.receive_critical_alerts = kwargs.get("receive_critical_alerts", True)
        profile.receive_warning_alerts = kwargs.get("receive_warning_alerts", True)
        profile.department = kwargs.get("department", "")
        profile.departments.order_by.return_value.values.return_value = []
        profile.totp_enabled = kwargs.get("totp_enabled", False)
        profile.totp_secret = kwargs.get("totp_secret", "")
        return profile

    def test_returns_dict_with_expected_keys(self):
        from core.api_users import _serialize_profile

        profile = self._make_profile()
        result = _serialize_profile(profile)
        for key in ("phone_number", "notify_via_email", "totp_enabled", "totp_configured"):
            self.assertIn(key, result)

    def test_no_avatar_returns_none_url(self):
        from core.api_users import _serialize_profile

        profile = self._make_profile()
        profile.avatar = None
        result = _serialize_profile(profile)
        self.assertIsNone(result["avatar_url"])

    def test_avatar_with_name_returns_url(self):
        from core.api_users import _serialize_profile

        profile = self._make_profile()
        profile.avatar = MagicMock()
        profile.avatar.name = "avatars/user.jpg"
        profile.avatar.url = "/media/avatars/user.jpg"
        result = _serialize_profile(profile)
        self.assertEqual(result["avatar_url"], "/media/avatars/user.jpg")

    def test_avatar_url_exception_uses_media_base(self):
        from core.api_users import _serialize_profile

        profile = self._make_profile()
        profile.avatar = MagicMock()
        profile.avatar.name = "avatars/user.jpg"
        type(profile.avatar).url = PropertyMock(side_effect=ValueError("no url"))
        result = _serialize_profile(profile)
        self.assertIn("avatars/user.jpg", result["avatar_url"])

    def test_totp_configured_true_when_secret_set(self):
        from core.api_users import _serialize_profile

        profile = self._make_profile(totp_secret="MYSECRET", totp_enabled=True)
        result = _serialize_profile(profile)
        self.assertTrue(result["totp_configured"])

    def test_totp_configured_false_when_no_secret(self):
        from core.api_users import _serialize_profile

        profile = self._make_profile(totp_secret="", totp_enabled=False)
        result = _serialize_profile(profile)
        self.assertFalse(result["totp_configured"])

    def test_departments_list_populated(self):
        from core.api_users import _serialize_profile

        profile = self._make_profile()
        profile.departments.order_by.return_value.values.return_value = [
            {"id": 1, "name": "Sales"},
            {"id": 2, "name": "IT"},
        ]
        result = _serialize_profile(profile)
        self.assertEqual(len(result["departments"]), 2)

    def test_build_absolute_uri_called_when_request_provided(self):
        from core.api_users import _serialize_profile

        profile = self._make_profile()
        profile.avatar = MagicMock()
        profile.avatar.name = "avatars/user.jpg"
        profile.avatar.url = "/media/avatars/user.jpg"
        request = MagicMock()
        request.build_absolute_uri.return_value = "http://testserver/media/avatars/user.jpg"
        result = _serialize_profile(profile, request=request)
        self.assertEqual(result["avatar_url"], "http://testserver/media/avatars/user.jpg")
        request.build_absolute_uri.assert_called_once()


class GetOrCreateProfileTests(TestCase):
    def test_returns_existing_profile(self):
        from core.api_users import _get_or_create_profile

        user = MagicMock()
        user.profile = MagicMock()
        result = _get_or_create_profile(user)
        self.assertEqual(result, user.profile)

    def test_creates_profile_when_missing(self):
        from core.api_users import _get_or_create_profile
        from core.models import UserProfile

        user = MagicMock()
        type(user).profile = PropertyMock(side_effect=UserProfile.DoesNotExist)
        with patch.object(UserProfile.objects, "create") as mock_create:
            mock_create.return_value = MagicMock()
            result = _get_or_create_profile(user)
        mock_create.assert_called_once_with(user=user)


class ApplyProfileUpdatesTests(TestCase):
    def _make_profile(self):
        profile = MagicMock()
        profile.phone_number = ""
        profile.telegram_chat_id = ""
        profile.notify_via_email = True
        profile.notify_via_whatsapp = False
        profile.notify_via_telegram = False
        profile.receive_critical_alerts = True
        profile.receive_warning_alerts = True
        profile.department = ""
        profile.departments = MagicMock()
        return profile

    def test_updates_phone_number(self):
        from core.api_users import _apply_profile_updates

        profile = self._make_profile()
        _apply_profile_updates(profile, {"phone_number": "+5511999999999"})
        self.assertEqual(profile.phone_number, "+5511999999999")

    def test_ignores_non_profile_fields(self):
        from core.api_users import _apply_profile_updates

        profile = self._make_profile()
        original_phone = profile.phone_number
        _apply_profile_updates(profile, {"random_field": "value"})
        self.assertEqual(profile.phone_number, original_phone)

    def test_updates_notification_fields(self):
        from core.api_users import _apply_profile_updates

        profile = self._make_profile()
        _apply_profile_updates(profile, {"notify_via_email": False, "notify_via_whatsapp": True})
        self.assertFalse(profile.notify_via_email)
        self.assertTrue(profile.notify_via_whatsapp)

    def test_departments_data_handled(self):
        from core.api_users import _apply_profile_updates
        from core.models import Department

        profile = self._make_profile()
        with patch.object(Department.objects, "filter", return_value=[]):
            _apply_profile_updates(profile, {"phone_number": "123"})
        self.assertEqual(profile.phone_number, "123")


class TotpSecretEncryptedAtRestTests(TestCase):
    """EV-0016: o segredo TOTP nunca fica em texto puro na tabela."""

    def test_raw_column_is_ciphertext_and_model_decrypts(self):
        from django.contrib.auth import get_user_model
        from django.db import connection

        from core.models import UserProfile

        user = get_user_model().objects.create_user(username="totp_enc", password="x")
        user.profile.totp_secret = "JBSWY3DPEHPK3PXP"
        user.profile.save()

        with connection.cursor() as cur:
            cur.execute("SELECT totp_secret FROM core_userprofile WHERE id = %s", [user.profile.id])
            raw = cur.fetchone()[0]
        self.assertNotEqual(raw, "JBSWY3DPEHPK3PXP")
        self.assertTrue(raw.startswith("gAAAA"))  # token Fernet
        self.assertEqual(
            UserProfile.objects.get(pk=user.profile.pk).totp_secret, "JBSWY3DPEHPK3PXP"
        )

    def test_migration_0006_encrypts_plaintext_and_is_reversible(self):
        """O passo de dados da migração cifra o que está em texto puro e nada mais."""
        import importlib

        from django.contrib.auth import get_user_model
        from django.db import connection

        mig = importlib.import_module("core.migrations.0006_userprofile_totp_secret_encrypted")
        user = get_user_model().objects.create_user(username="totp_mig", password="x")
        already = get_user_model().objects.create_user(username="totp_mig2", password="x")
        already.profile.totp_secret = "ALREADYENCRYPTED"
        already.profile.save()

        def raw_secret(pk):
            with connection.cursor() as cur:
                cur.execute("SELECT totp_secret FROM core_userprofile WHERE id = %s", [pk])
                return cur.fetchone()[0]

        with connection.cursor() as cur:  # simula a coluna antes da migração
            cur.execute(
                "UPDATE core_userprofile SET totp_secret = %s WHERE id = %s",
                ["JBSWY3DPEHPK3PXP", user.profile.id],
            )
        ciphertext_before = raw_secret(already.profile.id)

        schema_editor = connection.schema_editor()
        mig.encrypt_existing(None, schema_editor)
        encrypted = raw_secret(user.profile.id)
        self.assertTrue(encrypted.startswith("gAAAA"))
        self.assertEqual(raw_secret(already.profile.id), ciphertext_before)  # não re-cifra

        mig.decrypt_existing(None, schema_editor)
        self.assertEqual(raw_secret(user.profile.id), "JBSWY3DPEHPK3PXP")
        self.assertEqual(raw_secret(already.profile.id), "ALREADYENCRYPTED")
