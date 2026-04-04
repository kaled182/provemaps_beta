"""Tests for core.checks_gis — GIS system check."""
from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings


class GisEnvironmentCheckTests(TestCase):
    def _run_check(self):
        from core.checks_gis import gis_environment_check
        return gis_environment_check()

    @override_settings(SPATIAL_SUPPORT_ENABLED=False)
    def test_returns_critical_when_spatial_disabled(self):
        messages = self._run_check()
        self.assertTrue(
            any(m.id == "core.E001" for m in messages),
            msg=f"Expected E001 in {messages}",
        )

    @override_settings(
        SPATIAL_SUPPORT_ENABLED=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
    )
    def test_returns_warning_when_not_postgis(self):
        messages = self._run_check()
        self.assertTrue(
            any(m.id == "core.W001" for m in messages),
            msg=f"Expected W001 in {messages}",
        )

    @override_settings(
        SPATIAL_SUPPORT_ENABLED=True,
        DATABASES={
            "default": {
                "ENGINE": "django.contrib.gis.db.backends.postgis",
                "NAME": "app",
                "USER": "app",
                "PASSWORD": "app",
                "HOST": "127.0.0.1",
                "PORT": "5432",
            }
        },
    )
    def test_passes_when_postgis_available(self):
        with patch("core.checks_gis.connections") as mock_conns:
            mock_cursor = mock_conns.__getitem__.return_value.cursor.return_value.__enter__.return_value
            mock_cursor.execute.return_value = None
            mock_cursor.fetchone.return_value = ("3.4.0",)
            messages = self._run_check()
        self.assertEqual(messages, [])
