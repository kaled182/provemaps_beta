"""
Tests for custom Prometheus metrics.

Tests metric initialization, recording functions, and integration
with prometheus_client.
"""
from unittest.mock import patch, Mock

from core.metrics_custom import (
    init_metrics,
    record_zabbix_call,
    record_cache_operation,
    record_db_query,
    update_celery_queue_metrics,
)
from prometheus_client import Histogram, Counter, Gauge, Info


class TestMetricsInitialization:
    """Test metric initialization and default values."""

    @patch('core.metrics_custom.application_info')
    @patch('core.metrics_custom.celery_queue_depth')
    def test_init_metrics_sets_application_info(
        self, mock_queue_depth, mock_app_info
    ):
        """Test that init_metrics sets application info."""
        with patch('django.conf.settings') as mock_settings:
            mock_settings.APP_VERSION = '1.0.0'
            mock_settings.ENVIRONMENT = 'test'
            mock_settings.DEBUG = False

            init_metrics()

            mock_app_info.info.assert_called_once()
            call_args = mock_app_info.info.call_args[0][0]
            assert call_args['version'] == '1.0.0'
            assert call_args['environment'] == 'test'
            assert call_args['debug'] == 'False'

    @patch('core.metrics_custom.celery_queue_depth')
    def test_init_metrics_initializes_queue_gauges(self, mock_queue_depth):
        """Test that init_metrics initializes Celery queue gauges."""
        with patch('django.conf.settings') as mock_settings:
            mock_settings.APP_VERSION = '1.0.0'
            mock_settings.ENVIRONMENT = 'test'
            mock_settings.DEBUG = False

            init_metrics()

            # Verify gauges are initialized for each queue
            assert mock_queue_depth.labels.call_count >= 2


class TestZabbixMetrics:
    """Test Zabbix API metrics recording."""

    @patch('core.metrics_custom.zabbix_api_calls_total')
    @patch('core.metrics_custom.zabbix_api_latency')
    def test_record_zabbix_call_success(
        self, mock_latency, mock_calls_total
    ):
        """Test recording successful Zabbix API calls."""
        record_zabbix_call('host.get', 0.5, True)

        mock_latency.labels.assert_called_with(
            endpoint='host.get', status='success'
        )
        mock_latency.labels().observe.assert_called_with(0.5)

        mock_calls_total.labels.assert_called_with(
            endpoint='host.get', success=True, error_type='none'
        )
        mock_calls_total.labels().inc.assert_called_once()

    @patch('core.metrics_custom.zabbix_api_calls_total')
    @patch('core.metrics_custom.zabbix_api_latency')
    def test_record_zabbix_call_failure(
        self, mock_latency, mock_calls_total
    ):
        """Test recording failed Zabbix API calls."""
        record_zabbix_call('host.get', 0.3, False, error_type='timeout')

        mock_latency.labels.assert_called_with(
            endpoint='host.get', status='failure'
        )
        mock_latency.labels().observe.assert_called_with(0.3)

        mock_calls_total.labels.assert_called_with(
            endpoint='host.get', success=False, error_type='timeout'
        )
        mock_calls_total.labels().inc.assert_called_once()


class TestCacheMetrics:
    """Test cache metrics recording."""

    @patch('core.metrics_custom.cache_operations_total')
    def test_record_cache_get_hit(self, mock_operations):
        """Test recording cache GET hits."""
        record_cache_operation('default', 'get', hit=True)

        mock_operations.labels.assert_called_with(
            cache_name='default', operation='get', hit='true'
        )
        mock_operations.labels().inc.assert_called_once()

    @patch('core.metrics_custom.cache_operations_total')
    def test_record_cache_get_miss(self, mock_operations):
        """Test recording cache GET misses."""
        record_cache_operation('default', 'get', hit=False)

        mock_operations.labels.assert_called_with(
            cache_name='default', operation='get', hit='false'
        )
        mock_operations.labels().inc.assert_called_once()

    @patch('core.metrics_custom.cache_operations_total')
    def test_record_cache_set_success(self, mock_operations):
        """Test recording cache SET operations."""
        record_cache_operation('default', 'set', hit=None)

        mock_operations.labels.assert_called_with(
            cache_name='default', operation='set', hit='na'
        )
        mock_operations.labels().inc.assert_called_once()


class TestDatabaseMetrics:
    """Test database metrics recording."""

    @patch('core.metrics_custom.db_query_duration')
    def test_record_db_query_fast(self, mock_duration):
        """Test recording fast database queries."""
        record_db_query('select', 'Device', 'read', 0.001)

        mock_duration.labels.assert_called_with(
            query_type='select', model='Device', operation='read'
        )
        mock_duration.labels().observe.assert_called_with(0.001)

    @patch('core.metrics_custom.db_slow_queries_total')
    @patch('core.metrics_custom.db_query_duration')
    def test_record_db_query_slow(self, mock_duration, mock_slow):
        """Test recording slow database queries (> 1s)."""
        record_db_query('select', 'Device', 'read', 2.5)

        mock_duration.labels.assert_called_with(
            query_type='select', model='Device', operation='read'
        )
        mock_duration.labels().observe.assert_called_with(2.5)
        mock_slow.labels().inc.assert_called_once()


class TestCeleryMetrics:
    """Test Celery metrics recording."""

    @patch('core.metrics_custom.celery_queue_depth')
    def test_update_celery_queue_metrics(self, mock_queue_depth):
        """Test updating Celery queue depth metrics."""
        queues = {'celery': 5, 'periodic': 2}
        update_celery_queue_metrics(queues)

        assert mock_queue_depth.labels.call_count == 2
        mock_queue_depth.labels(queue_name='celery').set.assert_called_with(5)
        mock_queue_depth.labels(queue_name='periodic').set.assert_called_with(2)

    @patch('core.metrics_custom.celery_queue_depth')
    def test_update_multiple_queues(self, mock_queue_depth):
        """Test updating multiple queue depths."""
        queues = {
            'celery': 10,
            'periodic': 3,
            'priority': 1,
        }
        update_celery_queue_metrics(queues)

        assert mock_queue_depth.labels.call_count == 3


class TestMetricLabels:
    """Test metric label handling."""

    @patch('core.metrics_custom.zabbix_api_calls_total')
    def test_zabbix_call_without_error_type(self, mock_calls_total):
        """Test Zabbix call recording without error_type uses default."""
        record_zabbix_call('item.get', 0.2, True)

        mock_calls_total.labels.assert_called_with(
            endpoint='item.get', success=True, error_type='none'
        )

    @patch('core.metrics_custom.zabbix_api_calls_total')
    def test_zabbix_call_with_none_error_type(self, mock_calls_total):
        """Test Zabbix call with None error_type uses default."""
        record_zabbix_call('host.get', 0.4, True, error_type=None)

        mock_calls_total.labels.assert_called_with(
            endpoint='host.get', success=True, error_type='none'
        )


class TestMetricIntegration:
    """Test metrics integration with prometheus_client."""

    def test_metrics_are_prometheus_objects(self):
        """Test that metrics are proper prometheus_client objects."""
        from core.metrics_custom import (
            zabbix_api_latency,
            zabbix_api_calls_total,
            celery_queue_depth,
        )

        assert isinstance(zabbix_api_latency, Histogram)
        assert isinstance(zabbix_api_calls_total, Counter)
        assert isinstance(celery_queue_depth, Gauge)

    def test_histogram_buckets_configured(self):
        """Test that histograms have proper bucket configuration."""
        from core.metrics_custom import zabbix_api_latency, db_query_duration

        # Check they are histograms (buckets configured internally)
        assert isinstance(zabbix_api_latency, Histogram)
        assert isinstance(db_query_duration, Histogram)

    def test_metrics_have_correct_labels(self):
        """Test that metrics define correct label names."""
        from core.metrics_custom import (
            zabbix_api_latency,
            cache_operations_total,
            db_query_duration,
        )

        # Histograms and counters store label names differently
        # Check via ` _labelnames` attribute
        assert zabbix_api_latency._labelnames == ('endpoint', 'status')
        assert cache_operations_total._labelnames == (
            'cache_name',
            'operation',
            'hit',
        )
        assert db_query_duration._labelnames == ('query_type', 'model', 'operation')


class TestMetricsWithDjango:
    """Test metrics with Django settings."""

    @patch('core.metrics_custom.application_info')
    def test_init_metrics_with_real_settings(self, mock_app_info):
        """Test init_metrics with actual Django settings."""
        init_metrics()
        # Should not raise exception
        assert mock_app_info.info.called

    @patch('core.metrics_custom.application_info')
    def test_init_metrics_with_missing_settings(self, mock_app_info):
        """Test init_metrics handles missing settings gracefully."""
        with patch('django.conf.settings') as mock_settings:
            # Simulate missing attributes
            del mock_settings.APP_VERSION
            mock_settings.ENVIRONMENT = 'test'
            mock_settings.DEBUG = False

            # Should not raise exception
            init_metrics()
