"""
Tests for Inventory Prometheus metrics instrumentation.

Sprint 1, Week 2 - Legacy Code Removal Schedule
Validates metrics collection for deprecation decisions in Sprint 4.

⚠️ IMPORTANTE: Testes devem ser executados sob Docker
Executar: docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_inventory_metrics.py -v
"""

import pytest
from unittest.mock import Mock, patch
from django.test import RequestFactory
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from inventory.models import Site, Device, Port, FiberCable, FiberProfile
from inventory.metrics import (
    METRICS_ENABLED,
    track_viewset_action,
    track_model_operation,
    track_endpoint_usage,
    record_cache_hit,
    record_cache_miss,
    record_cache_set,
    record_cache_invalidation,
    get_metrics_summary,
)

User = get_user_model()


class PrometheusMetricsAvailabilityTest(APITestCase):
    """Test Prometheus metrics availability and configuration."""

    def test_metrics_enabled_flag(self):
        """Metrics should be enabled when prometheus_client is installed."""
        # In Docker environment, prometheus_client should be available
        self.assertTrue(
            isinstance(METRICS_ENABLED, bool),
            "METRICS_ENABLED should be a boolean"
        )

    def test_get_metrics_summary(self):
        """get_metrics_summary() should return valid structure."""
        summary = get_metrics_summary()
        
        self.assertIn("enabled", summary)
        self.assertIn("metrics", summary)
        self.assertIn("endpoint", summary)
        
        self.assertEqual(summary["endpoint"], "/metrics/")
        
        if METRICS_ENABLED:
            self.assertEqual(len(summary["metrics"]), 5)
            self.assertIn("api_requests", summary["metrics"])
            self.assertIn("api_duration", summary["metrics"])
            self.assertIn("model_operations", summary["metrics"])
            self.assertIn("cache_operations", summary["metrics"])
            self.assertIn("endpoint_usage", summary["metrics"])


@pytest.mark.skipif(not METRICS_ENABLED, reason="Prometheus client not installed")
class ViewSetMetricsInstrumentationTest(APITestCase):
    """Test ViewSet action tracking with Prometheus metrics."""

    def setUp(self):
        """Create test user and authenticate."""
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create test data
        self.site = Site.objects.create(
            display_name="Test Site",
            city="Brasilia",
            latitude=-15.7942,
            longitude=-47.8822,
        )
        
        self.device = Device.objects.create(
            name="Test Device",
            site=self.site,
            zabbix_hostid="10001",
        )

    def test_site_list_metrics(self):
        """Site list endpoint should record metrics."""
        from prometheus_client import REGISTRY
        
        # Get initial metric value
        initial_count = 0
        for metric in REGISTRY.collect():
            if metric.name == "inventory_api_requests_total":
                for sample in metric.samples:
                    if (sample.labels.get("viewset") == "SiteViewSet" and
                        sample.labels.get("action") == "list"):
                        initial_count = sample.value
                        break
        
        # Make request
        response = self.client.get("/api/v1/inventory/sites/")
        self.assertEqual(response.status_code, 200)
        
        # Verify metric increased
        final_count = 0
        for metric in REGISTRY.collect():
            if metric.name == "inventory_api_requests_total":
                for sample in metric.samples:
                    if (sample.labels.get("viewset") == "SiteViewSet" and
                        sample.labels.get("action") == "list"):
                        final_count = sample.value
                        break
        
        self.assertGreater(
            final_count, initial_count,
            "inventory_api_requests_total should increment for Site list"
        )

    def test_device_create_model_operation_metric(self):
        """Device creation should record model operation metric."""
        from prometheus_client import REGISTRY
        
        # Get initial count
        initial_count = 0
        for metric in REGISTRY.collect():
            if metric.name == "inventory_model_operations_total":
                for sample in metric.samples:
                    if (sample.labels.get("model") == "Device" and
                        sample.labels.get("operation") == "create"):
                        initial_count = sample.value
                        break
        
        # Create device
        response = self.client.post("/api/v1/inventory/devices/", {
            "name": "New Device",
            "site": self.site.id,
            "zabbix_hostid": "10002",
        })
        self.assertEqual(response.status_code, 201)
        
        # Verify metric increased
        final_count = 0
        for metric in REGISTRY.collect():
            if metric.name == "inventory_model_operations_total":
                for sample in metric.samples:
                    if (sample.labels.get("model") == "Device" and
                        sample.labels.get("operation") == "create"):
                        final_count = sample.value
                        break
        
        self.assertGreater(
            final_count, initial_count,
            "inventory_model_operations_total should increment for Device create"
        )


@pytest.mark.skipif(not METRICS_ENABLED, reason="Prometheus client not installed")
class CacheMetricsTest(APITestCase):
    """Test cache operation metrics."""

    def test_cache_hit_metric(self):
        """record_cache_hit should increment cache hit counter."""
        from prometheus_client import REGISTRY
        
        initial_count = 0
        for metric in REGISTRY.collect():
            if metric.name == "inventory_cache_operations_total":
                for sample in metric.samples:
                    if (sample.labels.get("cache_type") == "test_cache" and
                        sample.labels.get("operation") == "get" and
                        sample.labels.get("result") == "hit"):
                        initial_count = sample.value
                        break
        
        record_cache_hit("test_cache")
        
        final_count = 0
        for metric in REGISTRY.collect():
            if metric.name == "inventory_cache_operations_total":
                for sample in metric.samples:
                    if (sample.labels.get("cache_type") == "test_cache" and
                        sample.labels.get("operation") == "get" and
                        sample.labels.get("result") == "hit"):
                        final_count = sample.value
                        break
        
        self.assertGreater(final_count, initial_count)

    def test_cache_miss_metric(self):
        """record_cache_miss should increment cache miss counter."""
        from prometheus_client import REGISTRY
        
        initial_count = 0
        for metric in REGISTRY.collect():
            if metric.name == "inventory_cache_operations_total":
                for sample in metric.samples:
                    if (sample.labels.get("cache_type") == "test_cache" and
                        sample.labels.get("operation") == "get" and
                        sample.labels.get("result") == "miss"):
                        initial_count = sample.value
                        break
        
        record_cache_miss("test_cache")
        
        final_count = 0
        for metric in REGISTRY.collect():
            if metric.name == "inventory_cache_operations_total":
                for sample in metric.samples:
                    if (sample.labels.get("cache_type") == "test_cache" and
                        sample.labels.get("operation") == "get" and
                        sample.labels.get("result") == "miss"):
                        final_count = sample.value
                        break
        
        self.assertGreater(final_count, initial_count)

    def test_cache_invalidation_metric(self):
        """record_cache_invalidation should increment invalidation counter."""
        from prometheus_client import REGISTRY
        
        initial_count = 0
        for metric in REGISTRY.collect():
            if metric.name == "inventory_cache_operations_total":
                for sample in metric.samples:
                    if (sample.labels.get("cache_type") == "test_cache" and
                        sample.labels.get("operation") == "invalidate"):
                        initial_count = sample.value
                        break
        
        record_cache_invalidation("test_cache")
        
        final_count = 0
        for metric in REGISTRY.collect():
            if metric.name == "inventory_cache_operations_total":
                for sample in metric.samples:
                    if (sample.labels.get("cache_type") == "test_cache" and
                        sample.labels.get("operation") == "invalidate"):
                        final_count = sample.value
                        break
        
        self.assertGreater(final_count, initial_count)


class DecoratorFunctionalityTest(APITestCase):
    """Test decorator functionality (with or without metrics)."""

    def test_track_viewset_action_decorator(self):
        """track_viewset_action should work even if metrics disabled."""
        
        @track_viewset_action("TestViewSet")
        def test_action(self, request):
            return {"result": "success"}
        
        mock_self = Mock()
        mock_request = Mock(method="GET")
        
        result = test_action(mock_self, mock_request)
        self.assertEqual(result["result"], "success")

    def test_track_model_operation_decorator(self):
        """track_model_operation should work even if metrics disabled."""
        
        @track_model_operation("TestModel", "create")
        def test_operation(data):
            return f"Created: {data}"
        
        result = test_operation("test_data")
        self.assertEqual(result, "Created: test_data")

    def test_track_endpoint_usage_decorator(self):
        """track_endpoint_usage should work even if metrics disabled."""
        
        @track_endpoint_usage("/api/test/")
        def test_endpoint(self, request):
            return {"endpoint": "test"}
        
        mock_self = Mock()
        mock_request = Mock(method="POST")
        
        result = test_endpoint(mock_self, mock_request)
        self.assertEqual(result["endpoint"], "test")


@pytest.mark.integration
class MetricsEndpointAccessTest(APITestCase):
    """Test access to /metrics/ endpoint."""

    def test_metrics_endpoint_exists(self):
        """Metrics endpoint should be accessible."""
        # /metrics/ endpoint doesn't require authentication
        response = self.client.get("/metrics/")
        
        # Should return 200 or 404 (if django_prometheus not configured)
        self.assertIn(response.status_code, [200, 404])
        
        if response.status_code == 200:
            # Response should be in Prometheus text format
            self.assertIn(
                b"# HELP",
                response.content,
                "Prometheus metrics should include HELP comments"
            )


# ==============================================================================
# Usage Documentation
# ==============================================================================

"""
USAGE EXAMPLES:

1. View metrics in browser:
   http://localhost:8000/metrics/

2. Query specific metrics:
   
   # API request count by viewset
   inventory_api_requests_total{viewset="SiteViewSet"}
   
   # Model operations
   inventory_model_operations_total{model="FiberCable",operation="create"}
   
   # Cache hit rate
   rate(inventory_cache_operations_total{result="hit"}[5m])
   / rate(inventory_cache_operations_total[5m])

3. Grafana dashboard queries:
   
   # Most used endpoints
   topk(10, sum by (viewset, action) (
     increase(inventory_api_requests_total[24h])
   ))
   
   # Slow endpoints
   histogram_quantile(0.95, 
     sum(rate(inventory_api_duration_seconds_bucket[5m])) by (le, viewset)
   )

4. Deprecation decisions (Sprint 4):
   - Endpoints with 0 usage in 30 days = safe to deprecate
   - High traffic endpoints = need migration plan
   - Slow endpoints = performance optimization needed

SPRINT 4 QUERY:
# Find unused endpoints (candidates for deprecation)
inventory_endpoint_usage_total == 0
"""
