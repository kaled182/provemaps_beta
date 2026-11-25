from __future__ import annotations

import logging
import os
from typing import Any, cast

import requests
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import ServiceAccount, ServiceAccountAuditLog, ServiceAccountToken

logger = logging.getLogger(__name__)

_WEBHOOK_CONNECT_TIMEOUT = float(os.getenv("SERVICE_ACCOUNT_WEBHOOK_CONNECT_TIMEOUT", "3"))
_WEBHOOK_READ_TIMEOUT = float(os.getenv("SERVICE_ACCOUNT_WEBHOOK_READ_TIMEOUT", "5"))
_WEBHOOK_TIMEOUT: tuple[float, float] = (
    _WEBHOOK_CONNECT_TIMEOUT,
    _WEBHOOK_READ_TIMEOUT,
)
_WEBHOOK_USER_AGENT = "mapsprovefiber-service-account-rotation/1.0"


def enforce_rotation_policies(
    *,
    reference: timezone.datetime | None = None,
) -> dict[str, Any]:
    """Evaluate auto-rotation and notification rules for service accounts."""

    now = reference or timezone.now()
    summary: dict[str, Any] = {"rotations": 0, "notices": 0, "errors": []}

    candidate_accounts = (
        ServiceAccount.objects.filter(is_active=True)
        .filter(
            Q(auto_rotate_days__isnull=False)
            | (Q(notify_before_days__isnull=False) & ~Q(notification_webhook_url=""))
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
    now: timezone.datetime | None = None,
) -> ServiceAccountToken | None:
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


def revoke_tokens(
    *,
    token_ids: Any,
    actor: Any = None,
    reason: str | None = None,
    remote_addr: str | None = None,
) -> dict[str, int]:
    """Revoke the given tokens by hand (EV-0073); already revoked ones are skipped.

    Rows are locked and re-read inside the transaction, so a token revoked
    concurrently (e.g. by the rotation task) is counted as already revoked and
    its original ``revoked_at`` is kept. Each revocation goes through
    ``ServiceAccountToken.revoke`` and therefore writes a ``token_revoked``
    entry in ``ServiceAccountAuditLog``. Returns ``{"revoked", "already_revoked"}``.
    """

    revoked = 0
    already_revoked = 0
    with transaction.atomic():
        tokens = (
            ServiceAccountToken.objects.select_for_update(of=("self",))
            .select_related("account")
            .filter(pk__in=list(token_ids))
            .order_by("pk")
        )
        for token in tokens:
            if token.revoked_at is not None:
                already_revoked += 1
                continue
            token.revoke(
                actor=actor,
                reason=reason or "Token revoked manually via admin",
                remote_addr=remote_addr,
            )
            revoked += 1
    logger.info(
        "service_account.tokens_revoked",
        extra={
            "revoked": revoked,
            "already_revoked": already_revoked,
            "actor_id": getattr(actor, "pk", None),
        },
    )
    return {"revoked": revoked, "already_revoked": already_revoked}


def deactivate_accounts(
    *,
    account_ids: Any,
    actor: Any = None,
    reason: str | None = None,
    remote_addr: str | None = None,
) -> dict[str, int]:
    """Deactivate service accounts instead of deleting them (EV-0080).

    For each account: ``is_active=False``, every non-revoked token is revoked
    through :func:`revoke_tokens` (one ``token_revoked`` audit entry each) and a
    ``deactivated`` entry is written with the number of tokens actually revoked.
    Accounts that were already inactive are not re-audited, but any token they
    still hold unrevoked is revoked too. Returns
    ``{"deactivated", "already_inactive", "tokens_revoked"}``.
    """

    deactivated = 0
    already_inactive = 0
    tokens_revoked = 0
    with transaction.atomic():
        accounts = (
            ServiceAccount.objects.select_for_update()
            .filter(pk__in=list(account_ids))
            .order_by("pk")
        )
        for account in accounts:
            open_token_ids = list(
                account.tokens.filter(revoked_at__isnull=True).values_list("pk", flat=True)
            )
            result = revoke_tokens(
                token_ids=open_token_ids,
                actor=actor,
                reason="Token revogado ao desativar a conta",
                remote_addr=remote_addr,
            )
            tokens_revoked += result["revoked"]

            if not account.is_active:
                already_inactive += 1
                continue

            account.is_active = False
            update_fields = ["is_active", "updated_at"]
            if actor is not None:
                account.updated_by = actor
                update_fields.append("updated_by")
            account.save(update_fields=update_fields)
            ServiceAccountAuditLog.log(
                account=account,
                action=_action("DEACTIVATED"),
                actor=actor,
                message=reason or "Account deactivated",
                extra_data={"tokens_revoked": result["revoked"]},
                remote_addr=remote_addr,
            )
            deactivated += 1
    logger.info(
        "service_account.accounts_deactivated",
        extra={
            "deactivated": deactivated,
            "already_inactive": already_inactive,
            "tokens_revoked": tokens_revoked,
            "actor_id": getattr(actor, "pk", None),
        },
    )
    return {
        "deactivated": deactivated,
        "already_inactive": already_inactive,
        "tokens_revoked": tokens_revoked,
    }


def _should_dispatch_notice(
    *,
    account: ServiceAccount,
    token: ServiceAccountToken,
    notice_deadline: timezone.datetime | None,
    rotation_deadline: timezone.datetime | None,
    now: timezone.datetime,
) -> bool:
    if not (account.notification_webhook_url and notice_deadline and notice_deadline <= now):
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
    deadline: timezone.datetime | None,
    now: timezone.datetime,
) -> None:
    payload: dict[str, Any] = {
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
    payload: dict[str, Any] = {
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


def _dispatch_webhook(url: str, payload: dict[str, Any]) -> None:
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


def _action(name: str) -> ServiceAccountAuditLog.Action:
    return cast(
        "ServiceAccountAuditLog.Action",
        getattr(ServiceAccountAuditLog.Action, name),
    )
