from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable

from django.http import JsonResponse

logger = logging.getLogger("zabbix_api.views")


def handle_api_errors(func: Callable) -> Callable:
    """Captura exce??es inesperadas e retorna resposta JSON padronizada."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - prote??o extra
            logger.exception("Erro no endpoint %s: %s", func.__name__, exc)
            return JsonResponse({"error": "Erro interno do servidor"}, status=500)

    return wrapper


def api_login_required(func: Callable) -> Callable:
    """
    Decorador para APIs REST que verifica autenticação.
    Retorna JSON 401 em vez de redirecionar para página de login.
    """

    @wraps(func)
    def wrapper(request, *args: Any, **kwargs: Any):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Authentication required", "detail": "You must be logged in to access this resource"},
                status=401
            )
        return func(request, *args, **kwargs)

    return wrapper


__all__ = ["handle_api_errors", "api_login_required"]

