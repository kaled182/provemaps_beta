from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from django.http import JsonResponse

logger = logging.getLogger("zabbix_api.views")

_F = TypeVar("_F", bound=Callable[..., Any])


def handle_api_errors(func: _F) -> _F:
    """Capture unexpected exceptions and return a JSON error response."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - protective guardrail
            logger.exception("Endpoint %s failed: %s", func.__name__, exc)
            return JsonResponse({"error": "Internal server error"}, status=500)

    return cast(_F, wrapper)


def api_login_required(func: _F) -> _F:
    """Ensure REST API endpoints enforce authentication with JSON errors."""

    @wraps(func)
    def wrapper(request: Any, *args: Any, **kwargs: Any):
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    "error": "Authentication required",
                    "detail": "You must be logged in to access this resource",
                },
                status=401,
            )
        return func(request, *args, **kwargs)

    return cast(_F, wrapper)


__all__ = ["handle_api_errors", "api_login_required"]

