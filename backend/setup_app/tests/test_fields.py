"""Tests for setup_app.fields — EncryptedCharField and helpers."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings


FERNET_KEYS_SETTING = ["test-secret-key-that-is-at-least-16-chars"]


class EncryptDecryptHelpersTests(TestCase):
    @override_settings(FERNET_KEYS=FERNET_KEYS_SETTING)
    def test_encrypt_returns_string(self):
        from setup_app.fields import encrypt_string, _get_fernets
        _get_fernets.cache_clear()
        result = encrypt_string("hello world")
        self.assertIsInstance(result, str)
        self.assertNotEqual(result, "hello world")

    @override_settings(FERNET_KEYS=FERNET_KEYS_SETTING)
    def test_decrypt_round_trips(self):
        from setup_app.fields import encrypt_string, decrypt_string, _get_fernets
        _get_fernets.cache_clear()
        original = "secret value 123"
        encrypted = encrypt_string(original)
        decrypted = decrypt_string(encrypted)
        self.assertEqual(decrypted, original)

    @override_settings(FERNET_KEYS=[])
    def test_get_fernets_raises_when_no_keys(self):
        from setup_app.fields import _get_fernets
        _get_fernets.cache_clear()
        with self.assertRaises(RuntimeError, msg="FERNET_KEYS is not configured"):
            _get_fernets()

    @override_settings(FERNET_KEYS=FERNET_KEYS_SETTING)
    def test_decrypt_falls_back_to_plaintext_on_invalid_token(self):
        from setup_app.fields import decrypt_string, _get_fernets
        _get_fernets.cache_clear()
        result = decrypt_string("not-encrypted-value")
        self.assertEqual(result, "not-encrypted-value")


class EncryptedCharFieldTests(TestCase):
    @override_settings(FERNET_KEYS=FERNET_KEYS_SETTING)
    def setUp(self):
        from setup_app.fields import _get_fernets
        _get_fernets.cache_clear()

    @override_settings(FERNET_KEYS=FERNET_KEYS_SETTING)
    def test_get_prep_value_encrypts(self):
        from setup_app.fields import EncryptedCharField, _get_fernets
        _get_fernets.cache_clear()
        field = EncryptedCharField()
        result = field.get_prep_value("my secret")
        self.assertNotEqual(result, "my secret")
        self.assertIsInstance(result, str)

    def test_get_prep_value_none_returns_none(self):
        from setup_app.fields import EncryptedCharField
        field = EncryptedCharField()
        self.assertIsNone(field.get_prep_value(None))

    def test_get_prep_value_empty_returns_empty(self):
        from setup_app.fields import EncryptedCharField
        field = EncryptedCharField()
        self.assertEqual(field.get_prep_value(""), "")

    @override_settings(FERNET_KEYS=FERNET_KEYS_SETTING)
    def test_get_prep_value_exceeds_max_length_raises(self):
        from setup_app.fields import EncryptedCharField, _get_fernets
        _get_fernets.cache_clear()
        field = EncryptedCharField(max_plain_length=5)
        with self.assertRaises(ValidationError):
            field.get_prep_value("too long value")

    def test_to_python_none_returns_none(self):
        from setup_app.fields import EncryptedCharField
        field = EncryptedCharField()
        self.assertIsNone(field.to_python(None))

    def test_to_python_empty_returns_empty(self):
        from setup_app.fields import EncryptedCharField
        field = EncryptedCharField()
        self.assertEqual(field.to_python(""), "")

    @override_settings(FERNET_KEYS=FERNET_KEYS_SETTING)
    def test_to_python_decrypts(self):
        from setup_app.fields import (
            EncryptedCharField,
            encrypt_string,
            _get_fernets,
        )
        _get_fernets.cache_clear()
        field = EncryptedCharField()
        encrypted = encrypt_string("hello")
        self.assertEqual(field.to_python(encrypted), "hello")

    def test_to_python_non_string_returns_as_is(self):
        from setup_app.fields import EncryptedCharField
        field = EncryptedCharField()
        self.assertEqual(field.to_python(42), 42)

    @override_settings(FERNET_KEYS=FERNET_KEYS_SETTING)
    def test_from_db_value_decrypts(self):
        from setup_app.fields import (
            EncryptedCharField,
            encrypt_string,
            _get_fernets,
        )
        _get_fernets.cache_clear()
        field = EncryptedCharField()
        encrypted = encrypt_string("db value")
        self.assertEqual(field.from_db_value(encrypted, None, None), "db value")

    def test_from_db_value_none_returns_none(self):
        from setup_app.fields import EncryptedCharField
        field = EncryptedCharField()
        self.assertIsNone(field.from_db_value(None, None, None))

    def test_from_db_value_empty_returns_empty(self):
        from setup_app.fields import EncryptedCharField
        field = EncryptedCharField()
        self.assertEqual(field.from_db_value("", None, None), "")

    def test_check_invalid_max_plain_length(self):
        from setup_app.fields import EncryptedCharField
        field = EncryptedCharField(max_plain_length=0)
        errors = field.check()
        self.assertTrue(any("max_plain_length" in str(e) for e in errors))

    def test_check_valid_max_plain_length(self):
        from setup_app.fields import EncryptedCharField
        field = EncryptedCharField(max_plain_length=255)
        errors = field.check()
        self.assertEqual(
            [e for e in errors if "max_plain_length" in str(e)], []
        )

    def test_deconstruct_includes_max_plain_length(self):
        from setup_app.fields import EncryptedCharField
        field = EncryptedCharField(max_plain_length=128)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(kwargs["max_plain_length"], 128)
