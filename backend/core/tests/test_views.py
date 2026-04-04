"""Tests for core.views — healthz endpoint."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase


class HealthzViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _make_healthy_mocks(self, mock_conn, mock_caches, mock_disk):
        cursor = mock_conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1,)
        mock_conn.vendor = "postgresql"
        cache = MagicMock()
        cache.get.return_value = "ok"
        mock_caches.__getitem__.return_value = cache
        mock_disk.return_value = MagicMock(free=5 * 1024 ** 3)

    def test_healthy_returns_200(self):
        from core.views import healthz

        request = self.factory.get("/healthz")
        with patch("core.views.connection") as mc, \
             patch("core.views.caches") as mca, \
             patch("core.views.shutil.disk_usage") as md:
            self._make_healthy_mocks(mc, mca, md)
            response = healthz(request)
        self.assertEqual(response.status_code, 200)

    def test_healthy_response_has_ok_status(self):
        from core.views import healthz

        request = self.factory.get("/healthz")
        with patch("core.views.connection") as mc, \
             patch("core.views.caches") as mca, \
             patch("core.views.shutil.disk_usage") as md:
            self._make_healthy_mocks(mc, mca, md)
            response = healthz(request)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")

    def test_response_contains_expected_keys(self):
        from core.views import healthz

        request = self.factory.get("/healthz")
        with patch("core.views.connection") as mc, \
             patch("core.views.caches") as mca, \
             patch("core.views.shutil.disk_usage") as md:
            self._make_healthy_mocks(mc, mca, md)
            response = healthz(request)
        data = json.loads(response.content)
        for key in ("status", "checks", "django", "python", "latency_ms"):
            self.assertIn(key, data)

    def test_db_failure_returns_503(self):
        from core.views import healthz

        request = self.factory.get("/healthz")
        with patch("core.views.connection") as mc, \
             patch("core.views.caches") as mca, \
             patch("core.views.shutil.disk_usage") as md:
            mc.cursor.side_effect = Exception("DB down")
            cache = MagicMock()
            cache.get.return_value = "ok"
            mca.__getitem__.return_value = cache
            md.return_value = MagicMock(free=5 * 1024 ** 3)
            response = healthz(request)
        self.assertEqual(response.status_code, 503)

    def test_cache_failure_returns_503(self):
        from core.views import healthz

        request = self.factory.get("/healthz")
        with patch("core.views.connection") as mc, \
             patch("core.views.caches") as mca, \
             patch("core.views.shutil.disk_usage") as md:
            cursor = mc.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = (1,)
            mc.vendor = "postgresql"
            mca.__getitem__.side_effect = Exception("Cache down")
            md.return_value = MagicMock(free=5 * 1024 ** 3)
            response = healthz(request)
        self.assertEqual(response.status_code, 503)

    def test_low_disk_returns_503(self):
        from core.views import healthz

        request = self.factory.get("/healthz")
        with patch("core.views.connection") as mc, \
             patch("core.views.caches") as mca, \
             patch("core.views.shutil.disk_usage") as md:
            cursor = mc.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = (1,)
            mc.vendor = "postgresql"
            cache = MagicMock()
            cache.get.return_value = "ok"
            mca.__getitem__.return_value = cache
            md.return_value = MagicMock(free=0.5 * 1024 ** 3)
            response = healthz(request)
        data = json.loads(response.content)
        self.assertFalse(data["checks"]["storage"]["ok"])
        self.assertEqual(response.status_code, 503)

    def test_db_check_false_when_row_wrong(self):
        from core.views import healthz

        request = self.factory.get("/healthz")
        with patch("core.views.connection") as mc, \
             patch("core.views.caches") as mca, \
             patch("core.views.shutil.disk_usage") as md:
            cursor = mc.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = (0,)  # SELECT 1 returns wrong value
            mc.vendor = "sqlite3"
            cache = MagicMock()
            cache.get.return_value = "ok"
            mca.__getitem__.return_value = cache
            md.return_value = MagicMock(free=5 * 1024 ** 3)
            response = healthz(request)
        data = json.loads(response.content)
        self.assertFalse(data["checks"]["db"]["ok"])
