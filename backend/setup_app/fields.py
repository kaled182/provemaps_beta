from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core import checks
from django.core.exceptions import ValidationError
from django.db import models


@lru_cache(maxsize=None)
def _get_fernets() -> list[Fernet]:
    keys: list[Fernet] = []
    raw_keys = getattr(settings, "FERNET_KEYS", []) or []
    for raw in raw_keys:
        if not raw:
            continue
        digest = hashlib.sha256(raw.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
        keys.append(Fernet(key))
    if not keys:
        raise RuntimeError("FERNET_KEYS is not configured")
    return keys


def encrypt_string(value: str) -> str:
    return _get_fernets()[0].encrypt(value.encode()).decode()


def decrypt_string(value: str) -> str:
    for fernet in _get_fernets():
        try:
            return fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            continue
    return value


class EncryptedCharField(models.TextField):
    """Field that stores values encrypted with Fernet."""

    description = "Text stored with symmetric encryption (Fernet)."

    def __init__(self, *args, max_plain_length: int = 255, **kwargs):
        self.max_plain_length = max_plain_length
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["max_plain_length"] = self.max_plain_length
        return name, path, args, kwargs

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        if self.max_plain_length <= 0:
            errors.append(checks.Error("max_plain_length must be greater than zero", obj=self))
        return errors

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        if len(value) > self.max_plain_length:
            raise ValidationError(f"Value exceeds the limit of {self.max_plain_length} characters")
        return encrypt_string(value)

    def to_python(self, value):
        if value in (None, ""):
            return value
        if isinstance(value, str):
            try:
                return decrypt_string(value)
            except (InvalidToken, ValueError):
                return value
        return value

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return decrypt_string(value)
        except (InvalidToken, ValueError):
            return value

