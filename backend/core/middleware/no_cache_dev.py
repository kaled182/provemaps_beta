"""Middleware used in development to prevent caching of dynamic pages."""

from __future__ import annotations

from collections.abc import Callable
from django.conf import settings
from django.http import HttpRequest, HttpResponse


class NoCacheDevMiddleware:
    """Force no-cache headers on sensitive pages when DEBUG is enabled."""

    TARGET_PREFIXES: tuple[str, ...] = (
        "/static/js/fiber_route_builder",
    )

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if settings.DEBUG and any(
            request.path.startswith(prefix) for prefix in self.TARGET_PREFIXES
        ):
            response["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response
