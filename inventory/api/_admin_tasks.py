"""Shared helpers for secured task administration endpoints."""

from __future__ import annotations

import ipaddress
import json
import logging
import os
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Dict, Optional, Protocol, cast

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse

logger = logging.getLogger(__name__)

UserModel = get_user_model()


class SupportsApplyAsync(Protocol):
    def apply_async(
        self,
        *,
        args: Optional[Sequence[Any]] = ...,
        kwargs: Optional[Dict[str, Any]] = ...,
    ) -> Any:
        ...


def parse_ip_safelist() -> list[str]:
    raw = os.getenv("ADMIN_IP_SAFELIST", "").strip()
    if not raw:
        return []
    return [entry.strip() for entry in raw.split(",") if entry.strip()]


def is_ip_allowed(request: HttpRequest) -> bool:
    safelist = parse_ip_safelist()
    if not safelist:
        return True

    source = (
        request.META.get("HTTP_X_FORWARDED_FOR", "")
        or request.META.get("REMOTE_ADDR", "")
    )
    client_ip = source.split(",")[0].strip() if source else "0.0.0.0"

    try:
        ip_obj = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for entry in safelist:
        try:
            if "/" in entry:
                if ip_obj in ipaddress.ip_network(entry, strict=False):
                    return True
            else:
                if ip_obj == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            continue
    return False


def require_ip_allowlist(request: HttpRequest) -> JsonResponse | None:
    if not is_ip_allowed(request):
        return JsonResponse({"detail": "Forbidden by IP safelist"}, status=403)
    return None


def get_json_body(request: HttpRequest) -> Mapping[str, Any] | None:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None
    if isinstance(payload, Mapping):
        return cast(Mapping[str, Any], payload)
    return None


def as_int_list(value: object) -> list[int]:
    if value is None:
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        items: list[int] = []
        for item in cast(Iterable[object], value):
            if isinstance(item, int):
                items.append(item)
        return items
    return []


def rate_limit_key(request: HttpRequest, action: str) -> str:
    if request.user.is_authenticated:
        identifier = getattr(request.user, "pk", None)
        if identifier is None:
            identifier = request.user.get_username() or "anonymous"
    else:
        identifier = "anonymous"
    return f"rate_limit:{action}:{identifier}"


def check_rate_limit(
    request: HttpRequest,
    action: str,
    *,
    limit: int = 10,
    window: int = 60,
) -> bool:
    key = rate_limit_key(request, action)
    try:
        current = cache.get(key, 0)
        count = int(current) if isinstance(current, int) else 0
        if count >= limit:
            return False
        cache.set(key, count + 1, timeout=window)
    except Exception:  # pragma: no cover - cache failures should fail open
        logger.debug("Rate limit cache operation failed", exc_info=True)
    return True


def client_ip(request: HttpRequest) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def log_operation(request: HttpRequest, action: str, **context: Any) -> None:
    user = (
        request.user.get_username()
        if request.user.is_authenticated
        else "anonymous"
    )
    logger.info(
        "Admin operation: user=%s ip=%s action=%s %s",
        user,
        client_ip(request),
        action,
        " ".join(f"{key}={value}" for key, value in context.items()),
    )


def is_staff_user(user: Any) -> bool:
    if hasattr(user, "is_staff"):
        return bool(user.is_staff)
    if isinstance(user, UserModel):
        return bool(getattr(user, "is_staff", False))
    return False


def apply_async(
    task: SupportsApplyAsync,
    *,
    args: Optional[Sequence[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> Any:
    return task.apply_async(args=args, kwargs=kwargs)


def task_id(result: Any) -> str:
    value = getattr(result, "id", None)
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)
