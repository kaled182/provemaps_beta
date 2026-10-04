"""
Middleware to enforce authentication on all routes.
Redirects unauthenticated users to login page.
"""

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect


class AuthRequiredMiddleware:
    """
    Middleware that requires authentication for all views except
    whitelisted paths.

    Whitelisted paths:
    - /accounts/login/ (login page)
    - /accounts/logout/ (logout)
    - /admin/ (Django admin has its own auth)
    - /static/ (static files)
    - /media/ (media files)
    - /metrics/ (Prometheus metrics)
    - /healthz, /ready, /live (health checks)
    - /api/v1/ (API endpoints - protected by DRF permissions)

    Any other /api/* path without a session gets a 401 JSON response instead of
    a redirect to the login page (EV-0002).
    """

    WHITELIST_PATHS = [
        "/accounts/login/",
        "/accounts/logout/",
        "/accounts/password_reset/",
        "/accounts/otp/",
        "/admin/",
        "/static/",
        "/media/",
        "/metrics/",
        "/healthz",
        "/ready",
        "/live",
        "/favicon.ico",
        "/celery/status",
        # EV-0002: '/api/config/' saiu daqui. Entregava as chaves Google/Mapbox/Esri
        # a qualquer visitante. Pedidos a /api/* sem sessão recebem 401 JSON abaixo.
    ]

    WHITELIST_PREFIXES = [
        "/api/v1/",  # API endpoints have their own auth (DRF)
        "/setup_app/docs/",
        "/setup_app/first_time/",  # wizard de setup + página "restarting" (sem auth)
    ]

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # When system is not yet configured, let FirstTimeSetupRedirectMiddleware
        # handle the redirect — don't intercept with auth check first.
        try:
            from setup_app.models import FirstTimeSetup

            force_flow = getattr(settings, "FORCE_FIRST_TIME_FLOW", False)
            if force_flow and not FirstTimeSetup.objects.filter(configured=True).exists():
                return self.get_response(request)
        except Exception:
            pass

        # Check if path is whitelisted
        if self._is_whitelisted(request.path):
            return self.get_response(request)

        # EV-0023: integrações autenticam por token de conta de serviço
        # (`Authorization: Bearer`). O principal não é um User do Django — só
        # satisfaz `is_authenticated`; o DRF reaproveita-o em vez de validar de novo.
        if not request.user.is_authenticated and request.META.get("HTTP_AUTHORIZATION"):
            from service_accounts.authentication import authenticate_request

            principal = authenticate_request(request)
            if principal is not None:
                request.user = principal
                request.service_account_principal = principal
                return self.get_response(request)

        # Check if user is authenticated
        if not request.user.is_authenticated:
            # Chamadas de API (fetch do SPA) recebem 401 JSON, não a página de login
            # em HTML — o cliente consegue distinguir «sem sessão» de «config inválida».
            if request.path.startswith("/api/"):
                return JsonResponse(
                    {"detail": "Authentication required."},
                    status=401,
                )
            # Store the requested URL to redirect after login
            login_url = settings.LOGIN_URL
            if request.path != "/":
                # Add 'next' parameter to preserve the requested URL
                return redirect(f"{login_url}?next={request.path}")
            else:
                # Root path: just redirect to login
                return redirect(login_url)

        return self.get_response(request)

    def _is_whitelisted(self, path: str) -> bool:
        """Check if the path is in the whitelist."""
        # Exact match
        if path in self.WHITELIST_PATHS:
            return True

        # Prefix match
        for prefix in self.WHITELIST_PREFIXES:
            if path.startswith(prefix):
                return True

        # Check for static/media paths with trailing parts
        if path.startswith("/static/") or path.startswith("/media/"):
            return True

        return False
