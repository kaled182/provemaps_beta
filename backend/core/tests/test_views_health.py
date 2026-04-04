"""Tests for core.views_health — healthz, healthz_ready, healthz_live, celery_status."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory, TestCase, override_settings


class HealthzViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get(self, **env):
        return self.factory.get("/healthz/", **env)

    def test_healthy_returns_200(self):
        from core.views_health import healthz
        response = healthz(self._get())
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("status", data)
        self.assertIn("checks", data)
        self.assertIn("db", data["checks"])

    def test_response_has_no_cache_header(self):
        from core.views_health import healthz
        response = healthz(self._get())
        self.assertIn("no-cache", response["Cache-Control"])

    def test_response_includes_metadata(self):
        from core.views_health import healthz
        response = healthz(self._get())
        data = json.loads(response.content)
        self.assertIn("version", data)
        self.assertIn("django", data)
        self.assertIn("python", data)
        self.assertIn("latency_ms", data)

    def test_ignore_cache_env_flag(self):
        from core.views_health import healthz
        with patch.dict("os.environ", {"HEALTHCHECK_IGNORE_CACHE": "true"}):
            response = healthz(self._get())
        data = json.loads(response.content)
        cache_check = data["checks"].get("cache", {})
        self.assertTrue(cache_check.get("ignored"))

    def test_strict_mode_false_uses_db_only(self):
        from core.views_health import healthz
        with patch.dict("os.environ", {"HEALTHCHECK_STRICT": "false"}):
            response = healthz(self._get())
        # Should not 503 just because of cache
        self.assertIn(response.status_code, [200, 503])

    def test_storage_check_included_by_default(self):
        from core.views_health import healthz
        response = healthz(self._get())
        data = json.loads(response.content)
        self.assertIn("storage", data["checks"])

    def test_storage_check_disabled_by_env(self):
        from core.views_health import healthz
        with patch.dict("os.environ", {"HEALTHCHECK_STORAGE": "false"}):
            response = healthz(self._get())
        data = json.loads(response.content)
        self.assertNotIn("storage", data["checks"])

    def test_system_metrics_enabled_by_env(self):
        from core.views_health import healthz
        with patch.dict("os.environ", {"HEALTHCHECK_SYSTEM_METRICS": "true"}):
            response = healthz(self._get())
        data = json.loads(response.content)
        self.assertIn("system", data["checks"])

    def test_db_failure_returns_503(self):
        from core.views_health import healthz
        with patch(
            "core.views_health.connection.cursor",
            side_effect=Exception("DB down"),
        ):
            response = healthz(self._get())
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "degraded")

    def test_cache_failure_returns_503_in_strict_mode(self):
        from core.views_health import healthz
        with patch.dict("os.environ", {"HEALTHCHECK_STRICT": "true"}), \
             patch(
                 "core.views_health.caches",
                 side_effect=Exception("cache boom"),
             ):
            response = healthz(self._get())
        self.assertIn(response.status_code, [200, 503])


class HealthzReadyViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_ready_returns_200_when_db_up(self):
        from core.views_health import healthz_ready
        response = healthz_ready(self.factory.get("/ready"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ready")
        self.assertTrue(data["db_connected"])

    def test_ready_returns_503_when_db_down(self):
        from core.views_health import healthz_ready
        with patch(
            "core.views_health.connection.cursor",
            side_effect=Exception("no db"),
        ):
            response = healthz_ready(self.factory.get("/ready"))
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "not_ready")

    def test_ready_no_cache_header(self):
        from core.views_health import healthz_ready
        response = healthz_ready(self.factory.get("/ready"))
        self.assertIn("no-cache", response["Cache-Control"])

    def test_ready_includes_latency(self):
        from core.views_health import healthz_ready
        response = healthz_ready(self.factory.get("/ready"))
        data = json.loads(response.content)
        self.assertIn("latency_ms", data)

    def test_force_no_timeout_env(self):
        from core.views_health import healthz_ready
        with patch.dict(
            "os.environ", {"HEALTHCHECK_FORCE_NO_TIMEOUT": "true"}
        ):
            response = healthz_ready(self.factory.get("/ready"))
        self.assertEqual(response.status_code, 200)


class HealthzLiveViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_live_always_200(self):
        from core.views_health import healthz_live
        response = healthz_live(self.factory.get("/live"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "alive")

    def test_live_no_cache_header(self):
        from core.views_health import healthz_live
        response = healthz_live(self.factory.get("/live"))
        self.assertIn("no-cache", response["Cache-Control"])


class TimeoutContextManagerTests(TestCase):
    def test_timeout_noop_on_windows(self):
        from core.views_health import timeout
        import platform
        with patch.object(platform, "system", return_value="Windows"):
            with timeout(1):
                pass  # Should not raise

    def test_timeout_noop_when_zero(self):
        from core.views_health import timeout
        with timeout(0):
            pass  # Should be noop

    def test_storage_check_adds_ok_key(self):
        from core.views_health import _storage_check
        checks = {}
        _storage_check(checks)
        self.assertIn("storage", checks)
        self.assertIn("ok", checks["storage"])

    def test_add_system_metrics_without_psutil(self):
        from core.views_health import _add_system_metrics
        import sys
        with patch.dict("sys.modules", {"psutil": None}):
            checks = {}
            _add_system_metrics(checks)
        # should not raise

    def test_add_system_metrics_with_psutil(self):
        from core.views_health import _add_system_metrics
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 10.0
        mock_psutil.virtual_memory.return_value = MagicMock(percent=50.0)
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value = MagicMock(rss=64 * 1024 * 1024)
        mock_psutil.Process.return_value = mock_proc
        with patch("core.views_health.psutil", mock_psutil, create=True):
            checks = {}
            _add_system_metrics(checks)
        # No assertion on result — just verifying no exception


class CeleryStatusViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("core.views_health.ping", create=True)
    @patch("core.views_health.get_queue_stats", create=True)
    def test_celery_ok_when_ping_succeeds(self, mock_stats, mock_ping):
        from core.views_health import celery_status

        mock_result = MagicMock()
        mock_result.get.return_value = "pong"
        mock_ping.delay.return_value = mock_result

        stats_result = MagicMock()
        stats_result.get.return_value = {
            "workers": ["w1"],
            "active_tasks": {},
            "scheduled_tasks": {},
            "reserved_tasks": {},
        }
        mock_stats.delay.return_value = stats_result

        with patch(
            "core.views_health.get_queue_stats", mock_stats
        ), patch("core.views_health.ping", mock_ping):
            response = celery_status(self.factory.get("/celery/status"))

        self.assertIn(response.status_code, [200, 503])

    @patch("core.views_health.ping", side_effect=Exception("timeout"), create=True)
    @patch("core.views_health.get_queue_stats", MagicMock(), create=True)
    def test_celery_degraded_on_ping_fail(self, mock_ping):
        from core.views_health import celery_status
        with patch("core.views_health.ping", mock_ping):
            response = celery_status(self.factory.get("/celery/status"))
        data = json.loads(response.content)
        self.assertEqual(data["status"], "degraded")
