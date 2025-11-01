from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, cast

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager

from django.conf import settings
from django.db import models
from django.utils import timezone


class ServiceAccountAuditLog(models.Model):
    """Tracks lifecycle events for service accounts and their tokens."""

    class Action(models.TextChoices):
        CREATED = "created", "Account Created"
        UPDATED = "updated", "Account Updated"
        TOKEN_CREATED = "token_created", "Token Created"
        TOKEN_REVOKED = "token_revoked", "Token Revoked"
        TOKEN_ROTATED = "token_rotated", "Token Rotated"
        TOKEN_EXPIRED = "token_expired", "Token Expired"
        ROTATION_NOTICE = "rotation_notice", "Rotation Notice Sent"

    account: models.ForeignKey["ServiceAccount"] = models.ForeignKey(
        "service_accounts.ServiceAccount",
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_account_audit_events",
    )
    message = models.TextField(blank=True)
    remote_addr = models.CharField(max_length=64, blank=True)
    extra_data: models.JSONField[Dict[str, Any]] = models.JSONField(
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Service Account Audit Log"
        verbose_name_plural = "Service Account Audit Logs"
        default_permissions = ("view",)

    def __str__(self) -> str:  # pragma: no cover - human readable helper
        label = ServiceAccountAuditLog.Action(self.action).label
        return f"{self.account} · {label}"

    @classmethod
    def log(
        cls,
        *,
        account: "ServiceAccount",
        action: "ServiceAccountAuditLog.Action",
        actor: Optional[models.Model] = None,
        message: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        remote_addr: Optional[str] = None,
    ) -> "ServiceAccountAuditLog":
        payload: Dict[str, Any] = extra_data or {}
        return cls.objects.create(
            account=account,
            action=action,
            actor=actor,
            message=message or "",
            extra_data=payload,
            remote_addr=remote_addr or "",
        )


class ServiceAccount(models.Model):
    """Represents a non-human account used for automations or integrations."""

    name = models.CharField(max_length=150, unique=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    auto_rotate_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Número de dias para rotacionar tokens automaticamente.",
    )
    notify_before_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Quantos dias antes da expiração avisar responsáveis "
            "sobre o token ativo."
        ),
    )
    notification_webhook_url = models.URLField(
        blank=True,
        help_text="Webhook opcional (ex.: Slack) para alertas automáticos.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_service_accounts",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_service_accounts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    if TYPE_CHECKING:
        tokens: "RelatedManager[ServiceAccountToken]"

    class Meta:
        ordering = ("name",)
        verbose_name = "Service Account"
        verbose_name_plural = "Service Accounts"
        permissions = (
            (
                "manage_tokens",
                "Can manage service account tokens and audit records",
            ),
        )

    def __str__(self) -> str:  # pragma: no cover - human readable helper
        return self.name

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_token(
        self,
        *,
        created_by: Optional[models.Model] = None,
        expires_at: Optional[timezone.datetime] = None,
        note: Optional[str] = None,
        remote_addr: Optional[str] = None,
    ) -> Tuple[str, "ServiceAccountToken"]:
        """Generate a token, store its hash, return the clear value once."""

        plain_token = secrets.token_urlsafe(32)
        token = ServiceAccountToken.objects.create(
            account=self,
            token_hash=self.hash_token(plain_token),
            last_four=plain_token[-4:],
            created_by=created_by,
            expires_at=expires_at,
        )

        token_created_action = cast(
            "ServiceAccountAuditLog.Action",
            getattr(ServiceAccountAuditLog.Action, "TOKEN_CREATED"),
        )
        ServiceAccountAuditLog.log(
            account=self,
            action=token_created_action,
            actor=created_by,
            message=note or "Token created",
            extra_data={"token_last_four": token.last_four},
            remote_addr=remote_addr,
        )

        return plain_token, token

    def get_active_token(self) -> Optional["ServiceAccountToken"]:
        if not self.pk:
            return None
        return (
            self.tokens.filter(revoked_at__isnull=True)
            .order_by("-created_at")
            .first()
        )

    def get_rotation_deadline(self) -> Optional[timezone.datetime]:
        if not self.auto_rotate_days:
            return None

        active_token = self.get_active_token()
        if not active_token:
            return timezone.now()

        return active_token.created_at + timedelta(days=self.auto_rotate_days)

    def get_notification_deadline(self) -> Optional[timezone.datetime]:
        deadline = self.get_rotation_deadline()
        if not deadline or not self.notify_before_days:
            return None
        return deadline - timedelta(days=self.notify_before_days)

    def requires_rotation(self) -> bool:
        deadline = self.get_rotation_deadline()
        if not deadline:
            return False
        return deadline <= timezone.now()


class ServiceAccountToken(models.Model):
    """Stores hashed credentials associated with a service account."""

    account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.CASCADE,
        related_name="tokens",
    )
    token_hash = models.CharField(max_length=128, unique=True)
    last_four = models.CharField(max_length=8)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_service_account_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    rotated_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Service Account Token"
        verbose_name_plural = "Service Account Tokens"
        default_permissions = ("view",)

    def __str__(self) -> str:  # pragma: no cover - human readable helper
        return f"Token ••••{self.last_four}"

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= timezone.now())

    @property
    def is_active(self) -> bool:
        return not self.is_revoked and not self.is_expired

    def revoke(
        self,
        *,
        actor: Optional[models.Model] = None,
        reason: Optional[str] = None,
        remote_addr: Optional[str] = None,
        mark_rotated: bool = False,
    ) -> None:
        if self.revoked_at:
            return

        now = timezone.now()
        self.revoked_at = now
        update_fields = ["revoked_at"]
        if mark_rotated:
            self.rotated_at = now
            update_fields.append("rotated_at")
        self.save(update_fields=update_fields)
        token_revoked_action = cast(
            "ServiceAccountAuditLog.Action",
            getattr(ServiceAccountAuditLog.Action, "TOKEN_REVOKED"),
        )
        ServiceAccountAuditLog.log(
            account=self.account,
            action=token_revoked_action,
            actor=actor,
            message=reason or "Token revoked",
            extra_data={"token_id": self.pk, "last_four": self.last_four},
            remote_addr=remote_addr,
        )

    @classmethod
    def hash_token(cls, token: str) -> str:
        return ServiceAccount.hash_token(token)
