"""Tests for core.views_metrics — system_health_metrics."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings


class StaffCheckTests(TestCase):
    def test_staff_returns_true(self):
        from core.views_metrics import _staff_check
        user = MagicMock(is_staff=True)
        self.assertTrue(_staff_check(user))

    def test_non_staff_returns_false(self):
        from core.views_metrics import _staff_check
        user = MagicMock(is_staff=False)
        self.assertFalse(_staff_check(user))


class SystemHealthMetricsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _make_request(self):
        request = self.factory.get("/api/system-health/")
        request.user = MagicMock(is_authenticated=True, is_staff=True)
        return request

    def _call(self, request=None, **patches):
        from core.views_metrics import system_health_metrics
        if request is None:
            request = self._make_request()

        defaults = {
            "core.views_metrics.psutil.cpu_percent": 10.0,
            "core.views_metrics.psutil.virtual_memory": MagicMock(
                percent=50.0, used=2 * 1024**3, total=8 * 1024**3
            ),
            "core.views_metrics.psutil.disk_usage": MagicMock(
                percent=30.0, used=50 * 1024**3, total=200 * 1024**3
            ),
        }
        defaults.update(patches)

        with patch("core.views_metrics.psutil.cpu_percent",
                   return_value=defaults.pop("core.views_metrics.psutil.cpu_percent")), \
             patch("core.views_metrics.psutil.virtual_memory",
                   return_value=defaults.pop("core.views_metrics.psutil.virtual_memory")), \
             patch("core.views_metrics.psutil.disk_usage",
                   return_value=defaults.pop("core.views_metrics.psutil.disk_usage")):
            response = system_health_metrics(request)
        return response

    def test_returns_200_with_all_mocked(self):
        with patch("core.views_metrics.connection") as mock_conn, \
             patch("core.views_metrics.psutil.cpu_percent", return_value=5.0), \
             patch("core.views_metrics.psutil.virtual_memory",
                   return_value=MagicMock(percent=40.0, used=1024**3, total=4 * 1024**3)), \
             patch("core.views_metrics.psutil.disk_usage",
                   return_value=MagicMock(percent=20.0, used=20 * 1024**3, total=100 * 1024**3)):
            cursor = mock_conn.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = ("PostgreSQL 16.0, ...",)
            request = self._make_request()
            from core.views_metrics import system_health_metrics
            response = system_health_metrics(request)
        self.assertEqual(response.status_code, 200)

    def test_response_has_services_and_system_keys(self):
        with patch("core.views_metrics.connection") as mock_conn, \
             patch("core.views_metrics.psutil.cpu_percent", return_value=5.0), \
             patch("core.views_metrics.psutil.virtual_memory",
                   return_value=MagicMock(percent=40.0, used=1024**3, total=4 * 1024**3)), \
             patch("core.views_metrics.psutil.disk_usage",
                   return_value=MagicMock(percent=20.0, used=20 * 1024**3, total=100 * 1024**3)):
            cursor = mock_conn.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = ("PostgreSQL 16.0",)
            request = self._make_request()
            from core.views_metrics import system_health_metrics
            response = system_health_metrics(request)
        data = json.loads(response.content)
        self.assertIn("services", data)
        self.assertIn("system", data)
        self.assertIn("timestamp", data)

    @override_settings(REDIS_URL="redis://localhost:6379/0")
    def test_redis_offline_when_connection_fails(self):
        with patch("core.views_metrics.connection") as mock_conn, \
             patch("core.views_metrics.psutil.cpu_percent", return_value=5.0), \
             patch("core.views_metrics.psutil.virtual_memory",
                   return_value=MagicMock(percent=40.0, used=1024**3, total=4 * 1024**3)), \
             patch("core.views_metrics.psutil.disk_usage",
                   return_value=MagicMock(percent=20.0, used=20 * 1024**3, total=100 * 1024**3)), \
             patch("core.views_metrics.redis.Redis") as mock_redis:
            mock_redis.return_value.info.side_effect = Exception("Connection refused")
            cursor = mock_conn.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = ("PostgreSQL 16.0",)
            request = self._make_request()
            from core.views_metrics import system_health_metrics
            response = system_health_metrics(request)
        data = json.loads(response.content)
        self.assertEqual(data["services"]["redis"]["status"], "offline")

    def test_db_offline_when_connection_fails(self):
        with patch("django.db.connection") as mock_conn, \
             patch("core.views_metrics.psutil.cpu_percent", return_value=5.0), \
             patch("core.views_metrics.psutil.virtual_memory",
                   return_value=MagicMock(percent=40.0, used=1024**3, total=4 * 1024**3)), \
             patch("core.views_metrics.psutil.disk_usage",
                   return_value=MagicMock(percent=20.0, used=20 * 1024**3, total=100 * 1024**3)):
            mock_conn.cursor.side_effect = Exception("DB down")
            request = self._make_request()
            from core.views_metrics import system_health_metrics
            response = system_health_metrics(request)
        data = json.loads(response.content)
        self.assertEqual(data["services"]["postgresql"]["status"], "offline")

    def test_zabbix_not_configured_when_no_url(self):
        with patch("core.views_metrics.connection") as mock_conn, \
             patch("core.views_metrics.psutil.cpu_percent", return_value=5.0), \
             patch("core.views_metrics.psutil.virtual_memory",
                   return_value=MagicMock(percent=40.0, used=1024**3, total=4 * 1024**3)), \
             patch("core.views_metrics.psutil.disk_usage",
                   return_value=MagicMock(percent=20.0, used=20 * 1024**3, total=100 * 1024**3)), \
             patch("core.views_metrics.settings") as mock_settings:
            mock_settings.ZABBIX_API_URL = ""
            mock_settings.REDIS_URL = ""
            cursor = mock_conn.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = ("PostgreSQL 16.0",)
            request = self._make_request()
            from core.views_metrics import system_health_metrics
            response = system_health_metrics(request)
        data = json.loads(response.content)
        self.assertEqual(data["services"]["zabbix"]["status"], "not_configured")

    def test_system_metrics_populated(self):
        with patch("core.views_metrics.connection") as mock_conn, \
             patch("core.views_metrics.psutil.cpu_percent", return_value=42.5), \
             patch("core.views_metrics.psutil.virtual_memory",
                   return_value=MagicMock(percent=60.0, used=4 * 1024**3, total=8 * 1024**3)), \
             patch("core.views_metrics.psutil.disk_usage",
                   return_value=MagicMock(percent=55.0, used=110 * 1024**3, total=200 * 1024**3)):
            cursor = mock_conn.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = ("PostgreSQL 16.0",)
            request = self._make_request()
            from core.views_metrics import system_health_metrics
            response = system_health_metrics(request)
        data = json.loads(response.content)
        system = data["system"]
        self.assertIn("cpu_percent", system)
        self.assertIn("memory_percent", system)
        self.assertIn("disk_percent", system)

    def test_celery_offline_when_inspect_fails(self):
        with patch("core.views_metrics.connection") as mock_conn, \
             patch("core.views_metrics.psutil.cpu_percent", return_value=5.0), \
             patch("core.views_metrics.psutil.virtual_memory",
                   return_value=MagicMock(percent=40.0, used=1024**3, total=4 * 1024**3)), \
             patch("core.views_metrics.psutil.disk_usage",
                   return_value=MagicMock(percent=20.0, used=20 * 1024**3, total=100 * 1024**3)):
            cursor = mock_conn.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = ("PostgreSQL 16.0",)
            with patch("celery.current_app") as mock_celery:
                mock_celery.control.inspect.return_value.stats.side_effect = Exception("no celery")
                request = self._make_request()
                from core.views_metrics import system_health_metrics
                response = system_health_metrics(request)
        data = json.loads(response.content)
        self.assertIn("celery", data["services"])
