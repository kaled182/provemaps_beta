from __future__ import annotations

from typing import Iterable, Set

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from setup_app.models import FirstTimeSetup


class FirstTimeSetupRedirectMiddleware:
    """
    Redirect all requests to the initial setup screen until the system is configured.
    Static/media assets, health endpoints and the setup view itself remain accessible.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.setup_path = reverse("setup_app:first_time_setup")
        self.safe_exact_paths: Set[str] = {
            self.setup_path,
            "/favicon.ico",
        }
        prefix_candidates = [
            getattr(settings, "STATIC_URL", ""),
            getattr(settings, "MEDIA_URL", ""),
            "/static/",
            "/media/",
            "/setup_app/static/",
        ]
        self.safe_prefixes: Iterable[str] = tuple(filter(None, prefix_candidates))
        # Health and metrics endpoints should stay accessible for monitoring
        extra_safe = ["healthz", "healthz_ready", "healthz_live", "celery_status"]
        for name in extra_safe:
            try:
                self.safe_exact_paths.add(reverse(name))
            except Exception:
                continue

    def __call__(self, request):
        if getattr(settings, "TESTING", False) and not getattr(settings, "FORCE_FIRST_TIME_FLOW", False):
            return self.get_response(request)

        path = request.path
        if self._is_always_allowed(path):
            return self.get_response(request)

        if not self._is_configured():
            return redirect(self.setup_path)

        return self.get_response(request)

    def _is_configured(self) -> bool:
        return FirstTimeSetup.objects.filter(configured=True).exists()

    def _is_always_allowed(self, path: str) -> bool:
        if path.startswith(self.setup_path):
            return True
        if path in self.safe_exact_paths:
            return True
        if any(path.startswith(prefix) for prefix in self.safe_prefixes):
            return True
        return False
