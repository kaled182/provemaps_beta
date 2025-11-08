"""Middleware to apply additional security headers and a basic CSP.

Configuration is driven by settings.CONTENT_SECURITY_POLICY and standard
SECURE_* settings already defined in Django settings.
"""
from __future__ import annotations
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


from django.http import HttpRequest, HttpResponse


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(  # type: ignore[override]
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        csp: dict[str, list[str]] = getattr(
            settings, "CONTENT_SECURITY_POLICY", {}
        )
        if csp:
            parts: list[str] = []
            for directive, sources in csp.items():
                parts.append(f"{directive} {' '.join(sources)}")
            response["Content-Security-Policy"] = "; ".join(parts)
        ref_pol: str | None = getattr(
            settings, "SECURE_REFERRER_POLICY", None
        )
        if ref_pol:
            response["Referrer-Policy"] = ref_pol
        if not response.has_header("X-Frame-Options"):
            response["X-Frame-Options"] = "DENY"
        if not response.has_header("X-Content-Type-Options"):
            response["X-Content-Type-Options"] = "nosniff"
        if not response.has_header("X-XSS-Protection"):
            response["X-XSS-Protection"] = "1; mode=block"
        return response
