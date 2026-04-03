"""
Prometheus metrics for Inventory API.

Instrumenta ViewSets e operações do inventory para coletar dados de uso.
Essencial para decisões de depreciação no Sprint 4.

Sprint 1, Week 2 - Legacy Code Removal Schedule
"""

import logging
import time
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ==============================================================================
# Prometheus Metrics (with graceful fallback)
# ==============================================================================

try:
    from prometheus_client import Counter, Histogram

    METRICS_ENABLED = True

    # ViewSet operation counters
    inventory_api_requests = Counter(
        "inventory_api_requests_total",
        "Total requests to Inventory API endpoints",
        ["viewset", "action", "method", "status"],
    )

    inventory_api_duration = Histogram(
        "inventory_api_duration_seconds",
        "Duration of Inventory API requests",
        ["viewset", "action"],
        buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    # Model-specific operations
    inventory_model_operations = Counter(
        "inventory_model_operations_total",
        "Total model operations (create, update, delete)",
        ["model", "operation"],
    )

    # Cache operations
    inventory_cache_operations = Counter(
        "inventory_cache_operations_total",
        "Total cache operations",
        ["cache_type", "operation", "result"],
    )

    # Specific endpoint usage tracking (for deprecation decisions)
    inventory_endpoint_usage = Counter(
        "inventory_endpoint_usage_total",
        "Usage tracking for specific endpoints (deprecation planning)",
        ["endpoint", "method"],
    )

    logger.info("✅ Inventory Prometheus metrics initialized")

except ImportError:
    METRICS_ENABLED = False
    logger.info("⚠️ prometheus_client not installed; Inventory metrics disabled")


# ==============================================================================
# Decorators for ViewSet instrumentation
# ==============================================================================


def track_viewset_action(viewset_name: str):
    """
    Decorator to track ViewSet action execution.
    
    Automatically records:
    - Request count by viewset/action/method/status
    - Request duration
    - Errors
    
    Usage:
        @track_viewset_action("SiteViewSet")
        def list(self, request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if not METRICS_ENABLED:
                return func(self, request, *args, **kwargs)
            
            action_name = func.__name__
            method = request.method
            start_time = time.time()
            
            try:
                response = func(self, request, *args, **kwargs)
                status_code = getattr(response, "status_code", 200)
                
                # Record metrics
                inventory_api_requests.labels(
                    viewset=viewset_name,
                    action=action_name,
                    method=method,
                    status=status_code,
                ).inc()
                
                duration = time.time() - start_time
                inventory_api_duration.labels(
                    viewset=viewset_name,
                    action=action_name,
                ).observe(duration)
                
                return response
                
            except Exception as e:
                # Record error metrics
                inventory_api_requests.labels(
                    viewset=viewset_name,
                    action=action_name,
                    method=method,
                    status="error",
                ).inc()
                raise
        
        return wrapper
    return decorator


def track_model_operation(model_name: str, operation: str):
    """
    Track model-level operations (create, update, delete).
    
    Usage:
        @track_model_operation("Site", "create")
        def perform_create(self, serializer):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if METRICS_ENABLED:
                inventory_model_operations.labels(
                    model=model_name,
                    operation=operation,
                ).inc()
            return func(*args, **kwargs)
        return wrapper
    return decorator


def track_endpoint_usage(endpoint: str):
    """
    Track specific endpoint usage for deprecation planning.
    
    Use this on endpoints that might be deprecated in future sprints.
    
    Usage:
        @action(detail=False)
        @track_endpoint_usage("/api/v1/inventory/sites/nearby/")
        def nearby(self, request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if METRICS_ENABLED:
                inventory_endpoint_usage.labels(
                    endpoint=endpoint,
                    method=request.method,
                ).inc()
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator


# ==============================================================================
# Cache metrics helpers
# ==============================================================================


def record_cache_hit(cache_type: str):
    """Record a cache hit."""
    if METRICS_ENABLED:
        inventory_cache_operations.labels(
            cache_type=cache_type,
            operation="get",
            result="hit",
        ).inc()


def record_cache_miss(cache_type: str):
    """Record a cache miss."""
    if METRICS_ENABLED:
        inventory_cache_operations.labels(
            cache_type=cache_type,
            operation="get",
            result="miss",
        ).inc()


def record_cache_set(cache_type: str, success: bool = True):
    """Record a cache set operation."""
    if METRICS_ENABLED:
        inventory_cache_operations.labels(
            cache_type=cache_type,
            operation="set",
            result="success" if success else "failure",
        ).inc()


def record_cache_invalidation(cache_type: str):
    """Record a cache invalidation."""
    if METRICS_ENABLED:
        inventory_cache_operations.labels(
            cache_type=cache_type,
            operation="invalidate",
            result="success",
        ).inc()


# ==============================================================================
# Utility functions
# ==============================================================================


def get_metrics_summary() -> dict[str, Any]:
    """
    Get a summary of current metrics state.
    
    Useful for debugging and monitoring.
    
    Returns:
        Dict with metrics status and availability.
    """
    return {
        "enabled": METRICS_ENABLED,
        "metrics": {
            "api_requests": "inventory_api_requests_total",
            "api_duration": "inventory_api_duration_seconds",
            "model_operations": "inventory_model_operations_total",
            "cache_operations": "inventory_cache_operations_total",
            "endpoint_usage": "inventory_endpoint_usage_total",
        } if METRICS_ENABLED else {},
        "endpoint": "/metrics/",
    }
