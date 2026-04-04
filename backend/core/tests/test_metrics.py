"""Tests for core metrics — metrics_custom and metrics_celery."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase, override_settings


# ---------------------------------------------------------------------------
# metrics_custom
# ---------------------------------------------------------------------------

class MetricsCustomTests(TestCase):
    def test_record_zabbix_call_success(self):
        from core.metrics_custom import record_zabbix_call
        # Should not raise
        record_zabbix_call("host.get", 0.25, True)

    def test_record_zabbix_call_error(self):
        from core.metrics_custom import record_zabbix_call
        record_zabbix_call("user.login", 1.5, False, error_type="timeout")

    def test_record_zabbix_call_no_error_type(self):
        from core.metrics_custom import record_zabbix_call
        record_zabbix_call("item.get", 0.1, False)

    def test_record_cache_operation_hit(self):
        from core.metrics_custom import record_cache_operation
        record_cache_operation("default", "get", hit=True)

    def test_record_cache_operation_miss(self):
        from core.metrics_custom import record_cache_operation
        record_cache_operation("default", "get", hit=False)

    def test_record_cache_operation_set_success(self):
        from core.metrics_custom import record_cache_operation
        record_cache_operation("default", "set", hit=True)

    def test_record_cache_operation_set_error(self):
        from core.metrics_custom import record_cache_operation
        record_cache_operation("default", "set", hit=False)

    def test_record_db_query_fast(self):
        from core.metrics_custom import record_db_query
        record_db_query("SELECT", "Device", "list", 0.05)

    def test_record_db_query_slow(self):
        from core.metrics_custom import record_db_query
        # >1s triggers slow query counter
        record_db_query("SELECT", "Device", "list", 1.5)

    def test_record_db_query_exactly_at_threshold(self):
        from core.metrics_custom import record_db_query
        record_db_query("UPDATE", "Site", "update", 1.0)

    def test_update_celery_queue_metrics(self):
        from core.metrics_custom import update_celery_queue_metrics
        update_celery_queue_metrics("default", 5)
        update_celery_queue_metrics("priority", 0)

    @override_settings(
        APP_VERSION="1.0.0",
        ENVIRONMENT="test",
        DEBUG=False,
    )
    def test_init_metrics(self):
        from core.metrics_custom import init_metrics
        # Should not raise
        init_metrics()


# ---------------------------------------------------------------------------
# metrics_celery
# ---------------------------------------------------------------------------

class MetricsCeleryTests(TestCase):
    def _make_payload(self, available=True, latency=50.0, stats=None):
        return {
            "latency_ms": latency,
            "worker": {
                "available": available,
                "stats": stats,
            },
        }

    def test_sum_task_dict_empty(self):
        from core.metrics_celery import _sum_task_dict
        self.assertEqual(_sum_task_dict({}), 0)

    def test_sum_task_dict_none(self):
        from core.metrics_celery import _sum_task_dict
        self.assertEqual(_sum_task_dict(None), 0)

    def test_sum_task_dict_with_tasks(self):
        from core.metrics_celery import _sum_task_dict
        d = {"w1": [1, 2], "w2": [3]}
        self.assertEqual(_sum_task_dict(d), 3)

    def test_update_metrics_not_enabled_noop(self):
        from core.metrics_celery import update_metrics
        with patch("core.metrics_celery.METRICS_ENABLED", False):
            # Should return immediately without raising
            update_metrics(self._make_payload())

    def test_update_metrics_enabled_available(self):
        from core.metrics_celery import update_metrics
        stats = {
            "workers": ["w1", "w2"],
            "active_tasks": {"w1": [{"id": "t1"}]},
            "scheduled_tasks": {},
            "reserved_tasks": {"w2": [{"id": "t2"}, {"id": "t3"}]},
        }
        payload = self._make_payload(available=True, latency=100.0, stats=stats)
        # Should not raise regardless of prometheus availability
        update_metrics(payload)

    def test_update_metrics_unavailable_worker(self):
        from core.metrics_celery import update_metrics
        payload = self._make_payload(available=False, stats=None)
        update_metrics(payload)

    def test_update_metrics_none_stats(self):
        from core.metrics_celery import update_metrics
        payload = self._make_payload(available=True, stats=None)
        update_metrics(payload)

    def test_update_metrics_non_dict_stats(self):
        from core.metrics_celery import update_metrics
        payload = self._make_payload(available=True, stats="string_stat")
        update_metrics(payload)

    def test_update_metrics_workers_non_list(self):
        from core.metrics_celery import update_metrics
        payload = self._make_payload(
            available=True,
            stats={"workers": "not-a-list"},
        )
        update_metrics(payload)

    def test_update_metrics_missing_latency(self):
        from core.metrics_celery import update_metrics
        payload = {"worker": {"available": True, "stats": None}}
        update_metrics(payload)
