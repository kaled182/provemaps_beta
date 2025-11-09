from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple, cast

import requests
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import (
    ServiceAccount,
    ServiceAccountAuditLog,
    ServiceAccountToken,
)

logger = logging.getLogger(__name__)

_WEBHOOK_CONNECT_TIMEOUT = float(
    os.getenv("SERVICE_ACCOUNT_WEBHOOK_CONNECT_TIMEOUT", "3")
)
_WEBHOOK_READ_TIMEOUT = float(
    os.getenv("SERVICE_ACCOUNT_WEBHOOK_READ_TIMEOUT", "5")
)
_WEBHOOK_TIMEOUT: Tuple[float, float] = (
    _WEBHOOK_CONNECT_TIMEOUT,
    _WEBHOOK_READ_TIMEOUT,
)
_WEBHOOK_USER_AGENT = "mapsprovefiber-service-account-rotation/1.0"


def enforce_rotation_policies(
    *,
    reference: Optional[timezone.datetime] = None,
) -> Dict[str, Any]:
    """Evaluate auto-rotation and notification rules for service accounts."""

    now = reference or timezone.now()
    summary: Dict[str, Any] = {"rotations": 0, "notices": 0, "errors": []}

    candidate_accounts = (
        ServiceAccount.objects.filter(is_active=True)
        .filter(
            Q(auto_rotate_days__isnull=False)
            | (
                Q(notify_before_days__isnull=False)
                & ~Q(notification_webhook_url="")
            )
        )
        .prefetch_related("tokens")
    )

    for account in candidate_accounts:
        active_token = account.get_active_token()
        if not active_token or active_token.is_revoked:
            continue

        rotation_deadline = account.get_rotation_deadline()
        notice_deadline = account.get_notification_deadline()

        if _should_dispatch_notice(
            account=account,
            token=active_token,
            notice_deadline=notice_deadline,
            rotation_deadline=rotation_deadline,
            now=now,
        ):
            try:
                _send_rotation_notice(
                    account=account,
                    token=active_token,
                    deadline=rotation_deadline,
                    now=now,
                )
                summary["notices"] += 1
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning(
                    "Failed to dispatch rotation notice for account %s: %s",
                    account.pk,
                    exc,
                )
                summary["errors"].append(f"notice:{account.pk}")

        if rotation_deadline and rotation_deadline <= now:
            try:
                rotation_result = rotate_account_token(
                    account=account,
                    token=active_token,
                    now=now,
                )
                if rotation_result:
                    summary["rotations"] += 1
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error(
                    "Auto-rotation failed for account %s: %s",
                    account.pk,
                    exc,
                )
                summary["errors"].append(f"rotate:{account.pk}")

    return summary


def rotate_account_token(
    *,
    account: ServiceAccount,
    token: ServiceAccountToken,
    now: Optional[timezone.datetime] = None,
) -> Optional[ServiceAccountToken]:
    """Rotate the current token, optionally notifying webhook subscribers."""

    timestamp = now or timezone.now()

    with transaction.atomic():
        plain_token, new_token = account.create_token(
            note="Token auto-rotated via schedule",
        )
        token.revoke(
            reason="Token rotated automatically",
            mark_rotated=True,
        )
        ServiceAccountAuditLog.log(
            account=account,
            action=_action("TOKEN_ROTATED"),
            actor=None,
            message="Token auto-rotated by Celery schedule",
            extra_data={
                "new_token_id": new_token.pk,
                "previous_token_id": token.pk,
                "previous_last_four": token.last_four,
            },
        )

    if account.notification_webhook_url:
        try:
            _send_rotation_completion(
                account=account,
                new_token=new_token,
                plain_token=plain_token,
                timestamp=timestamp,
            )
        except Exception as exc:  # pragma: no cover - network failure path
            logger.warning(
                "Failed to deliver rotation completion for account %s: %s",
                account.pk,
                exc,
            )
    return new_token


def _should_dispatch_notice(
    *,
    account: ServiceAccount,
    token: ServiceAccountToken,
    notice_deadline: Optional[timezone.datetime],
    rotation_deadline: Optional[timezone.datetime],
    now: timezone.datetime,
) -> bool:
    if not (
        account.notification_webhook_url
        and notice_deadline
        and notice_deadline <= now
    ):
        return False
    if rotation_deadline and now >= rotation_deadline:
        return False
    if token.last_notified_at and token.last_notified_at >= notice_deadline:
        return False
    return True


def _send_rotation_notice(
    *,
    account: ServiceAccount,
    token: ServiceAccountToken,
    deadline: Optional[timezone.datetime],
    now: timezone.datetime,
) -> None:
    payload: Dict[str, Any] = {
        "event": "service_account.rotation_warning",
        "timestamp": now.isoformat(),
        "account": {"id": account.pk, "name": account.name},
        "token": {"id": token.pk, "last_four": token.last_four},
        "rotation_deadline": deadline.isoformat() if deadline else None,
        "notify_before_days": account.notify_before_days,
    }

    _dispatch_webhook(account.notification_webhook_url, payload)

    token.last_notified_at = now
    token.save(update_fields=["last_notified_at"])

    ServiceAccountAuditLog.log(
        account=account,
        action=_action("ROTATION_NOTICE"),
        actor=None,
        message="Rotation notice dispatched",
        extra_data={
            "token_id": token.pk,
            "rotation_deadline": payload["rotation_deadline"],
        },
    )


def _send_rotation_completion(
    *,
    account: ServiceAccount,
    new_token: ServiceAccountToken,
    plain_token: str,
    timestamp: timezone.datetime,
) -> None:
    payload: Dict[str, Any] = {
        "event": "service_account.token_rotated",
        "timestamp": timestamp.isoformat(),
        "account": {"id": account.pk, "name": account.name},
        "token": {
            "id": new_token.pk,
            "last_four": new_token.last_four,
        },
        "plain_token": plain_token,
    }

    _dispatch_webhook(account.notification_webhook_url, payload)


def _dispatch_webhook(url: str, payload: Dict[str, Any]) -> None:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": _WEBHOOK_USER_AGENT,
    }
    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=_WEBHOOK_TIMEOUT,
    )
    response.raise_for_status()


def _action(name: str) -> "ServiceAccountAuditLog.Action":
    return cast(
        "ServiceAccountAuditLog.Action",
        getattr(ServiceAccountAuditLog.Action, name),
    )
