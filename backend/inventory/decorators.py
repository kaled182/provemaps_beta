"""
Decorators for Prometheus instrumentation in ViewSets.

Fornece decorators para rastrear automaticamente métricas de performance
e uso em ViewSets do Django REST Framework.

Usage:
    from inventory.decorators import track_viewset_metrics
    
    class FiberCableViewSet(viewsets.ModelViewSet):
        @track_viewset_metrics(viewset_name='fiber_cable')
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)
"""

import logging
import time
from functools import wraps
from typing import Any, Callable

from django.conf import settings

logger = logging.getLogger(__name__)

# Lazy import to avoid import errors if prometheus_client not installed
METRICS_ENABLED = getattr(settings, 'PROMETHEUS_METRICS_ENABLED', False)


def track_viewset_metrics(
    viewset_name: str,
    counter_metric: str | None = None,
    histogram_metric: str | None = None,
):
    """
    Decorator para rastrear métricas de ViewSet methods.
    
    Args:
        viewset_name: Nome do ViewSet para labels (ex: 'fiber_cable', 'port', 'device')
        counter_metric: Nome da métrica Counter (default: auto-detect)
        histogram_metric: Nome da métrica Histogram (default: auto-detect)
    
    Example:
        @track_viewset_metrics(viewset_name='fiber_cable')
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)
    
    Metrics collected:
        - Total requests (counter) with labels: method, endpoint, status
        - Request latency (histogram) with labels: method, endpoint
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if not METRICS_ENABLED:
                # Metrics disabled - skip instrumentation
                return func(self, request, *args, **kwargs)
            
            # Lazy import metrics only if enabled
            try:
                from inventory.metrics import (
                    fiber_cable_requests,
                    fiber_cable_latency,
                    port_requests,
                    port_latency,
                    device_requests,
                    device_latency,
                )
            except ImportError:
                logger.warning(
                    "Prometheus metrics enabled but prometheus_client not installed. "
                    "Skipping instrumentation."
                )
                return func(self, request, *args, **kwargs)
            
            # Auto-select metrics based on viewset_name
            metrics_map = {
                'fiber_cable': (fiber_cable_requests, fiber_cable_latency),
                'port': (port_requests, port_latency),
                'device': (device_requests, device_latency),
            }
            
            counter, histogram = metrics_map.get(
                viewset_name,
                (None, None),
            )
            
            if counter is None or histogram is None:
                logger.warning(
                    f"No metrics defined for viewset '{viewset_name}'. "
                    "Skipping instrumentation."
                )
                return func(self, request, *args, **kwargs)
            
            # Extract method and endpoint from request
            method = request.method  # GET, POST, PUT, PATCH, DELETE
            endpoint = func.__name__  # list, retrieve, create, update, partial_update, destroy
            
            # Track latency
            start_time = time.perf_counter()
            
            try:
                response = func(self, request, *args, **kwargs)
                status = response.status_code
                
                # Increment counter with success status
                counter.labels(
                    method=method,
                    endpoint=endpoint,
                    status=status,
                ).inc()
                
                return response
                
            except Exception as exc:
                # Increment counter with error status
                counter.labels(
                    method=method,
                    endpoint=endpoint,
                    status='500',  # Internal server error
                ).inc()
                
                logger.error(
                    f"Error in {viewset_name}.{endpoint}: {exc}",
                    exc_info=True,
                )
                raise
                
            finally:
                # Record latency (always, even on error)
                duration = time.perf_counter() - start_time
                histogram.labels(
                    method=method,
                    endpoint=endpoint,
                ).observe(duration)
        
        return wrapper
    return decorator


def track_cache_operation(cache_key_prefix: str):
    """
    Decorator para rastrear operações de cache.
    
    Args:
        cache_key_prefix: Prefixo da chave de cache (ex: 'fiber_list', 'dashboard')
    
    Example:
        @track_cache_operation(cache_key_prefix='fiber_list')
        def get_cached_fibers():
            # ... cache logic ...
            pass
    
    Metrics collected:
        - Cache hits/misses (counters)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not METRICS_ENABLED:
                return func(*args, **kwargs)
            
            try:
                from inventory.metrics import cache_hits, cache_misses
            except ImportError:
                return func(*args, **kwargs)
            
            result = func(*args, **kwargs)
            
            # Detect cache hit/miss based on result
            # Convention: function returns (value, hit_status) or just value
            if isinstance(result, tuple) and len(result) == 2:
                value, is_hit = result
                if is_hit:
                    cache_hits.labels(cache_key_prefix=cache_key_prefix).inc()
                else:
                    cache_misses.labels(cache_key_prefix=cache_key_prefix).inc()
                return value
            else:
                # No hit/miss info - assume miss
                cache_misses.labels(cache_key_prefix=cache_key_prefix).inc()
                return result
        
        return wrapper
    return decorator


def track_business_operation(
    operation_type: str,  # 'cable_split', 'fusion', 'optical_fetch'
):
    """
    Decorator para rastrear operações de negócio complexas.
    
    Args:
        operation_type: Tipo de operação ('cable_split', 'fusion', 'optical_fetch')
    
    Example:
        @track_business_operation(operation_type='cable_split')
        def split_cable(cable_id, split_point):
            # ... business logic ...
            return result
    
    Metrics collected:
        - Operation count (counter) with status label
        - Operation duration (histogram)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not METRICS_ENABLED:
                return func(*args, **kwargs)
            
            try:
                from inventory.metrics import (
                    cable_split_operations,
                    cable_split_duration,
                    fusion_operations,
                    fusion_duration,
                    optical_data_fetches,
                    optical_data_latency,
                )
            except ImportError:
                return func(*args, **kwargs)
            
            # Select appropriate metrics
            metrics_map = {
                'cable_split': (cable_split_operations, cable_split_duration),
                'fusion': (fusion_operations, fusion_duration),
                'optical_fetch': (optical_data_fetches, optical_data_latency),
            }
            
            counter, histogram = metrics_map.get(operation_type, (None, None))
            
            if counter is None or histogram is None:
                logger.warning(
                    f"No metrics defined for operation '{operation_type}'. "
                    "Skipping instrumentation."
                )
                return func(*args, **kwargs)
            
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                
                # Increment success counter
                counter.labels(status='success').inc()
                
                return result
                
            except ValueError as exc:
                # Validation error
                counter.labels(status='validation_error').inc()
                logger.warning(
                    f"Validation error in {operation_type}: {exc}"
                )
                raise
                
            except Exception as exc:
                # Generic error (DB, timeout, etc.)
                counter.labels(status='error').inc()
                logger.error(
                    f"Error in {operation_type}: {exc}",
                    exc_info=True,
                )
                raise
                
            finally:
                # Record duration
                duration = time.perf_counter() - start_time
                histogram.observe(duration)
        
        return wrapper
    return decorator


__all__ = [
    'track_viewset_metrics',
    'track_cache_operation',
    'track_business_operation',
]
