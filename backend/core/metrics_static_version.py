"""Prometheus metrics for static asset versioning.

This module exposes STATIC_ASSET_VERSION as an Info metric,
making it observable in Grafana dashboards and helping diagnose stale assets.
Safe to import even if prometheus_client isn't available.
"""
from __future__ import annotations
import os
import logging

logger = logging.getLogger(__name__)

METRICS_ENABLED = (
    os.getenv("PROMETHEUS_METRICS_ENABLED", "true").lower() == "true"
)

try:
    from prometheus_client import Info  # type: ignore
except Exception:
    Info = None  # type: ignore
    METRICS_ENABLED = False

if METRICS_ENABLED and Info:
    STATIC_ASSET_VERSION_INFO = Info(
        "static_asset_version",
        "Current static asset version (SHA + timestamp for cache busting)"
    )
else:
    STATIC_ASSET_VERSION_INFO = None  # type: ignore


def update_static_version_metric(version: str) -> None:
    """Update the static version Info metric with STATIC_ASSET_VERSION.

    Args:
        version: String like "abc123-20251026142055" (sha-timestamp).
    """
    if not METRICS_ENABLED or not STATIC_ASSET_VERSION_INFO:
        return

    try:
        # Parse version into components if possible
        parts = version.split("-", 1)
        if len(parts) == 2:
            sha, timestamp = parts
        else:
            sha, timestamp = version, "unknown"

        STATIC_ASSET_VERSION_INFO.info({
            "version": version,
            "git_sha": sha,
            "timestamp": timestamp,
        })
        logger.info(f"[PROMETHEUS] static_asset_version={version}")
    except Exception as e:
        logger.warning(
            f"Failed to update static_asset_version metric: {e}"
        )


def init_static_version_metric() -> None:
    """Init metric at Django startup with STATIC_ASSET_VERSION."""
    if not METRICS_ENABLED:
        return

    try:
        from django.conf import settings
        version = getattr(settings, "STATIC_ASSET_VERSION", "unknown")
        update_static_version_metric(version)
    except Exception as e:
        logger.warning(
            f"Could not initialize static_asset_version metric: {e}"
        )
