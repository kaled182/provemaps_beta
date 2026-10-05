"""Bearer-token authentication for service accounts (EV-0023, ADR 0008).

Until this module existed the app issued, rotated and audited tokens that no
code path ever consumed. A token is accepted as::

    Authorization: Bearer <plain token shown once by the admin>

Two consumers share ``authenticate_bearer``:

* :class:`ServiceAccountTokenAuthentication` — DRF authenticator, placed before
  ``SessionAuthentication`` so an API client with a token is not subject to
  CSRF (which is a session concern).
* ``core.middleware.auth_required.AuthRequiredMiddleware`` — the middleware that
  guards every non-whitelisted path lets a request through when the header
  carries a valid token, setting ``request.user`` to the principal.

The principal is deliberately **not** a Django ``User``: it cannot log in, has
no staff/superuser flags and ``has_perm`` is always ``False``. It only satisfies
``is_authenticated`` so that ``IsAuthenticated`` / ``@login_required`` pass.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.http import HttpRequest
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header

from .models import ServiceAccount, ServiceAccountToken

logger = logging.getLogger(__name__)

AUTH_SCHEME = "bearer"
# Avoid one UPDATE per request: ``last_used_at`` moves at most once per window.
LAST_USED_WRITE_INTERVAL = timedelta(seconds=60)


class ServiceAccountPrincipal:
    """Request principal for a token-authenticated service account."""

    is_authenticated = True
    is_anonymous = False
    is_staff = False
    is_superuser = False

    def __init__(self, account: ServiceAccount, token: ServiceAccountToken):
        self.account = account
        self.token = token

    @property
    def pk(self) -> int:
        return self.account.pk

    id = pk

    @property
    def is_active(self) -> bool:
        return self.account.is_active

    @property
    def username(self) -> str:
        return f"svc:{self.account.name}"

    def get_username(self) -> str:
        return self.username

    def has_perm(self, perm: str, obj: Any = None) -> bool:
        return False

    def has_perms(self, perm_list: Any, obj: Any = None) -> bool:
        return False

    def has_module_perms(self, app_label: str) -> bool:
        return False

    def __str__(self) -> str:
        return self.username


def _extract_bearer(header: bytes | str) -> str | None:
    if isinstance(header, bytes):
        header = header.decode("latin-1", errors="replace")
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != AUTH_SCHEME:
        return None
    return parts[1]


def authenticate_bearer(
    header: bytes | str,
) -> tuple[ServiceAccountPrincipal, ServiceAccountToken] | None:
    """Resolve an ``Authorization`` header value to a principal, or ``None``.

    ``None`` means "this header is not a Bearer token" — the caller falls back to
    the next mechanism. A Bearer header that does not match an active token
    raises ``AuthenticationFailed`` so a bad credential is never silently
    downgraded to anonymous.
    """

    plain = _extract_bearer(header)
    if plain is None:
        return None

    token = (
        ServiceAccountToken.objects.select_related("account")
        .filter(token_hash=ServiceAccount.hash_token(plain))
        .first()
    )
    if token is None or not token.is_active or not token.account.is_active:
        logger.info(
            "service_account.auth_failed",
            extra={"last_four": plain[-4:], "reason": _failure_reason(token)},
        )
        raise exceptions.AuthenticationFailed("Invalid or inactive service account token.")

    _touch_last_used(token)
    return ServiceAccountPrincipal(token.account, token), token


def authenticate_request(request: HttpRequest) -> ServiceAccountPrincipal | None:
    """Middleware helper: principal for a request carrying a valid Bearer token."""

    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header:
        return None
    try:
        result = authenticate_bearer(header)
    except exceptions.AuthenticationFailed:
        return None
    return result[0] if result else None


def _failure_reason(token: ServiceAccountToken | None) -> str:
    if token is None:
        return "unknown"
    if token.is_revoked:
        return "revoked"
    if token.is_expired:
        return "expired"
    if not token.account.is_active:
        return "account_inactive"
    return "unknown"


def _touch_last_used(token: ServiceAccountToken) -> None:
    now = timezone.now()
    if token.last_used_at and now - token.last_used_at < LAST_USED_WRITE_INTERVAL:
        return
    token.last_used_at = now
    ServiceAccountToken.objects.filter(pk=token.pk).update(last_used_at=now)


class ServiceAccountTokenAuthentication(BaseAuthentication):
    """DRF authenticator: ``Authorization: Bearer <token>`` → service account."""

    def authenticate(self, request):  # type: ignore[override]
        # The middleware may already have resolved the token for this request.
        principal = getattr(request._request, "service_account_principal", None)
        if principal is not None:
            return principal, principal.token
        header = get_authorization_header(request)
        if not header:
            return None
        return authenticate_bearer(header)

    def authenticate_header(self, request) -> str:  # type: ignore[override]
        return "Bearer"
