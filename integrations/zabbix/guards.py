from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from django.http import JsonResponse, HttpRequest

from setup_app.services import runtime_settings
from setup_app.utils import env_manager


logger = logging.getLogger("integrations.zabbix.guards")


@lru_cache(maxsize=1)
def _diagnostics_flag_enabled() -> bool:
    """Check if diagnostic endpoints are enabled via .env or runtime settings."""
    env_value = env_manager.read_values(["ENABLE_DIAGNOSTIC_ENDPOINTS"]).get(
        "ENABLE_DIAGNOSTIC_ENDPOINTS", ""
    )
    if env_value:
        return env_value.lower() == "true"
    config = runtime_settings.get_runtime_config()
    return bool(config.diagnostics_enabled)


def _username(request: HttpRequest) -> Optional[str]:
    user = getattr(request, "user", None)
    if user and hasattr(user, "get_username"):
        return user.get_username()
    return None


def staff_guard(request: HttpRequest):
    """Validate authentication + staff profile."""
    if not request.user.is_authenticated:
        logger.warning(
            "Denied protected endpoint: unauthenticated user",
            extra={"remote_addr": request.META.get("REMOTE_ADDR")},
        )
        return JsonResponse({"error": "Autenticacao necessaria"}, status=403)
    if not request.user.is_staff:
        logger.warning(
            "Denied protected endpoint: user lacks staff role",
            extra={
                "remote_addr": request.META.get("REMOTE_ADDR"),
                "username": _username(request),
            },
        )
        return JsonResponse({"error": "Permissao insuficiente"}, status=403)
    return None


def diagnostics_guard(request: HttpRequest):
    """Ensure diagnostics endpoints are guarded by feature flag and staff access."""
    base = staff_guard(request)
    if base is not None:
        return base
    if not _diagnostics_flag_enabled():
        logger.warning(
            "Denied diagnostics endpoint: feature flag disabled",
            extra={
                "remote_addr": request.META.get("REMOTE_ADDR"),
                "username": _username(request),
            },
        )
        return JsonResponse({"error": "Diagnosticos desabilitados"}, status=403)
    return None


def reload_diagnostics_flag_cache() -> None:
    """Invalidate cached diagnostics flag lookups."""
    _diagnostics_flag_enabled.cache_clear()


__all__ = ["diagnostics_guard", "staff_guard", "reload_diagnostics_flag_cache"]
