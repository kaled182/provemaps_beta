"""Prometheus metrics for feature flags and runtime configuration.

Exposes gauges indicating the on/off status of key feature flags defined
in Django settings, allowing operators to monitor configuration drift and
validate feature rollouts via Prometheus/Grafana.
"""
from django.conf import settings
from prometheus_client import Gauge

# Feature flag status (1 = enabled, 0 = disabled)
feature_flag_status = Gauge(
    "mapsprovefiber_feature_flag_status",
    "Status of feature flags (1=enabled, 0=disabled)",
    ["flag_name"],
)


def collect_feature_flags() -> None:
    """Register current feature flag states as Prometheus metrics."""
    flags = {
        "debug_mode": settings.DEBUG,
        "diagnostic_endpoints": settings.ENABLE_DIAGNOSTIC_ENDPOINTS,
        "ssl_redirect": getattr(settings, "SECURE_SSL_REDIRECT", False),
        "hsts_enabled": getattr(settings, "SECURE_HSTS_SECONDS", 0) > 0,
        "redis_available": bool(
            getattr(settings, "REDIS_URL", "").strip()
        ),
        "channel_layer_redis": (
            settings.CHANNEL_LAYERS.get("default", {})
            .get("BACKEND", "")
            .startswith("channels_redis")
        ),
        "session_cache_backed": (
            settings.SESSION_ENGINE == "django.contrib.sessions.backends.cache"
        ),
        "file_logging": (
            "file"
            in getattr(settings, "LOGGING", {}).get("handlers", {})
        ),
        "sentry_enabled": bool(getattr(settings, "SENTRY_DSN", "")),
    }
    for flag_name, enabled in flags.items():
        feature_flag_status.labels(flag_name=flag_name).set(
            1 if enabled else 0
        )


# Auto-collect on module import (happens once per worker startup)
collect_feature_flags()
