"""Tests for pure helper functions in core.api_users."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

from django.test import TestCase


class CoerceBoolTests(TestCase):
    def test_true_bool_passthrough(self):
        from core.api_users import _coerce_bool
        self.assertTrue(_coerce_bool(True))

    def test_false_bool_passthrough(self):
        from core.api_users import _coerce_bool
        self.assertFalse(_coerce_bool(False))

    def test_none_returns_none(self):
        from core.api_users import _coerce_bool
        self.assertIsNone(_coerce_bool(None))

    def test_string_true_variants(self):
        from core.api_users import _coerce_bool
        for val in ("1", "true", "True", "TRUE", "yes", "on"):
            self.assertTrue(_coerce_bool(val), f"Expected True for {val!r}")

    def test_string_false_variants(self):
        from core.api_users import _coerce_bool
        for val in ("0", "false", "False", "FALSE", "no", "off"):
            self.assertFalse(_coerce_bool(val), f"Expected False for {val!r}")

    def test_non_string_non_bool_returned_as_is(self):
        from core.api_users import _coerce_bool
        self.assertEqual(_coerce_bool(42), 42)


class ExtractProfileDataTests(TestCase):
    def test_extracts_nested_profile_dict(self):
        from core.api_users import _extract_profile_data
        raw = {"profile": {"phone_number": "123", "notify_via_email": "true"}}
        result = _extract_profile_data(raw)
        self.assertEqual(result["phone_number"], "123")
        self.assertTrue(result["notify_via_email"])

    def test_extracts_dotted_keys(self):
        from core.api_users import _extract_profile_data
        raw = {"profile.telegram_chat_id": "456", "other": "x"}
        result = _extract_profile_data(raw)
        self.assertEqual(result["telegram_chat_id"], "456")
        self.assertNotIn("other", result)

    def test_coerces_boolean_fields(self):
        from core.api_users import _extract_profile_data
        raw = {"profile": {"receive_critical_alerts": "1", "receive_warning_alerts": "0"}}
        result = _extract_profile_data(raw)
        self.assertTrue(result["receive_critical_alerts"])
        self.assertFalse(result["receive_warning_alerts"])

    def test_empty_data_returns_empty_dict(self):
        from core.api_users import _extract_profile_data
        self.assertEqual(_extract_profile_data({}), {})


class GenerateTotpSecretTests(TestCase):
    def test_returns_non_empty_string(self):
        from core.api_users import _generate_totp_secret
        secret = _generate_totp_secret()
        self.assertIsInstance(secret, str)
        self.assertTrue(len(secret) > 0)

    def test_returns_unique_values(self):
        from core.api_users import _generate_totp_secret
        secrets = {_generate_totp_secret() for _ in range(5)}
        self.assertEqual(len(secrets), 5)


class Base32DecodeTests(TestCase):
    def test_decodes_known_secret(self):
        from core.api_users import _base32_decode
        # "JBSWY3DPEHPK3PXP" is a well-known test secret
        result = _base32_decode("JBSWY3DPEHPK3PXP")
        self.assertIsInstance(result, bytes)
        self.assertTrue(len(result) > 0)

    def test_handles_padding(self):
        from core.api_users import _base32_decode
        # Secret without padding
        result = _base32_decode("MFRGG")
        self.assertIsInstance(result, bytes)


class TotpAtTests(TestCase):
    def test_returns_integer(self):
        from core.api_users import _totp_at
        result = _totp_at("JBSWY3DPEHPK3PXP", 1000)
        self.assertIsInstance(result, int)

    def test_result_in_range(self):
        from core.api_users import _totp_at
        result = _totp_at("JBSWY3DPEHPK3PXP", 1000)
        self.assertGreaterEqual(result, 0)
        self.assertLess(result, 1_000_000)

    def test_deterministic(self):
        from core.api_users import _totp_at
        r1 = _totp_at("JBSWY3DPEHPK3PXP", 99999)
        r2 = _totp_at("JBSWY3DPEHPK3PXP", 99999)
        self.assertEqual(r1, r2)


class VerifyTotpTests(TestCase):
    def test_empty_code_returns_false(self):
        from core.api_users import _verify_totp
        self.assertFalse(_verify_totp("JBSWY3DPEHPK3PXP", ""))

    def test_non_digit_code_returns_false(self):
        from core.api_users import _verify_totp
        self.assertFalse(_verify_totp("JBSWY3DPEHPK3PXP", "abcdef"))

    def test_wrong_code_returns_false(self):
        from core.api_users import _verify_totp
        self.assertFalse(_verify_totp("JBSWY3DPEHPK3PXP", "000000"))

    def test_correct_code_returns_true(self):
        from core.api_users import _totp_at, _verify_totp
        secret = "JBSWY3DPEHPK3PXP"
        counter = int(time.time() / 30)
        code = str(_totp_at(secret, counter)).zfill(6)
        self.assertTrue(_verify_totp(secret, code))


class BuildOtpauthUrlTests(TestCase):
    def test_returns_otpauth_url(self):
        from core.api_users import _build_otpauth_url
        url = _build_otpauth_url("SECRET123", "user@example.com", "MyApp")
        self.assertTrue(url.startswith("otpauth://totp/"))
        self.assertIn("SECRET123", url)
        self.assertIn("MyApp", url)

    def test_url_has_required_params(self):
        from core.api_users import _build_otpauth_url
        url = _build_otpauth_url("SECRET", "user", "Issuer")
        self.assertIn("secret=SECRET", url)
        self.assertIn("algorithm=SHA1", url)
        self.assertIn("digits=6", url)
        self.assertIn("period=30", url)


class IsStaffOrSuperuserTests(TestCase):
    def test_staff_user_returns_true(self):
        from core.api_users import is_staff_or_superuser
        user = MagicMock(is_staff=True, is_superuser=False)
        self.assertTrue(is_staff_or_superuser(user))

    def test_superuser_returns_true(self):
        from core.api_users import is_staff_or_superuser
        user = MagicMock(is_staff=False, is_superuser=True)
        self.assertTrue(is_staff_or_superuser(user))

    def test_regular_user_returns_false(self):
        from core.api_users import is_staff_or_superuser
        user = MagicMock(is_staff=False, is_superuser=False)
        self.assertFalse(is_staff_or_superuser(user))
