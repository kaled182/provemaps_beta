from __future__ import annotations

from typing import Any, Dict

from celery import shared_task  # type: ignore[import-not-found]

from . import services


@shared_task(name="service_accounts.enforce_rotation_policies_task")
def enforce_rotation_policies_task() -> Dict[str, Any]:
    """Periodic task that enforces auto-rotation and notification policies."""

    return services.enforce_rotation_policies()
