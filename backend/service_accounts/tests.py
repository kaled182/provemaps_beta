from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from pytest import MonkeyPatch

from . import services as rotation_services
from .models import ServiceAccount, ServiceAccountAuditLog, ServiceAccountToken


@pytest.mark.django_db
def test_create_token_generates_hash_and_audit_log() -> None:
    user_model = get_user_model()
    creator = user_model.objects.create_user(
        username="creator",
        email="creator@example.com",
        password="secret123",
    )

    account = ServiceAccount.objects.create(name="CI Bot", created_by=creator)

    clear_token, stored_token = account.create_token(
        created_by=creator,
        note="Initial token",
    )

    assert len(clear_token) >= 8
    assert stored_token.token_hash == ServiceAccount.hash_token(clear_token)
    assert stored_token.last_four == clear_token[-4:]

    audit_entries = ServiceAccountAuditLog.objects.filter(
        account=account,
        action="token_created",
    )
    assert audit_entries.count() == 1
    entry = audit_entries.first()
    assert entry is not None
    assert entry.actor == creator


@pytest.mark.django_db
def test_revoke_token_sets_flag_and_logs_action() -> None:
    user_model = get_user_model()
    actor = user_model.objects.create_user(
        username="auditor",
        email="auditor@example.com",
        password="secret123",
    )

    account = ServiceAccount.objects.create(
        name="Automation",
        created_by=actor,
    )
    _, stored_token = account.create_token(created_by=actor)

    assert stored_token.is_active is True

    stored_token.revoke(actor=actor, reason="Credential rotated")

    stored_token.refresh_from_db()
    assert stored_token.revoked_at is not None
    assert stored_token.is_active is False

    audit_entries = ServiceAccountAuditLog.objects.filter(
        account=account,
        action="token_revoked",
    )
    assert audit_entries.count() == 1
    entry = audit_entries.first()
    assert entry is not None
    assert entry.actor == actor

    # Second revoke call should be a no-op
    stored_token.revoke(actor=actor)
    assert (
        ServiceAccountAuditLog.objects.filter(
            account=account,
            action="token_revoked",
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_token_expiry_flags_inactive() -> None:
    account = ServiceAccount.objects.create(name="Monitor")
    _, token = account.create_token()

    assert token.is_active is True

    token.expires_at = timezone.now() - timezone.timedelta(minutes=1)
    token.save(update_fields=["expires_at"])

    assert token.is_expired is True
    assert token.is_active is False


@pytest.mark.django_db
def test_admin_generate_token_view(admin_client: Client) -> None:
    account = ServiceAccount.objects.create(name="Web Bot")

    url = reverse(
        "admin:service_accounts_serviceaccount_generate_token",
        args=[account.pk],
    )

    get_response = admin_client.get(url)
    assert get_response.status_code == 200

    post_response = admin_client.post(url, {"note": "Token via admin"})
    assert post_response.status_code == 302

    account.refresh_from_db()
    token = ServiceAccountToken.objects.filter(account=account).first()
    assert token is not None
    assert token.is_active is True
    assert token.last_four


@pytest.mark.django_db
def test_admin_requires_manage_permission(client: Client) -> None:
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="staff",
        email="staff@example.com",
        password="secret123",
        is_staff=True,
    )

    client.force_login(user)

    changelist_url = reverse(
        "admin:service_accounts_serviceaccount_changelist"
    )
    response = client.get(changelist_url)
    assert response.status_code == 403

    manage_perm = Permission.objects.get(
        content_type__app_label="service_accounts",
        codename="manage_tokens",
    )

    user.user_permissions.add(manage_perm)
    response = client.get(changelist_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_enforce_rotation_policies_rotates_due_tokens() -> None:
    account = ServiceAccount.objects.create(
        name="Rotation Bot",
        auto_rotate_days=30,
    )
    _, token = account.create_token()

    token.created_at = timezone.now() - timezone.timedelta(days=31)
    token.save(update_fields=["created_at"])

    result = rotation_services.enforce_rotation_policies(
        reference=timezone.now()
    )
    assert result["rotations"] == 1

    tokens = list(
        ServiceAccountToken.objects.filter(account=account).order_by(
            "-created_at"
        )
    )
    assert len(tokens) == 2

    latest_token = tokens[0]
    previous_token = tokens[1]

    assert previous_token.revoked_at is not None
    assert previous_token.rotated_at is not None
    assert latest_token.revoked_at is None

    assert ServiceAccountAuditLog.objects.filter(
        account=account,
        action="token_rotated",
    ).exists()


@pytest.mark.django_db
def test_enforce_rotation_policies_sends_notice_once(
    monkeypatch: MonkeyPatch,
) -> None:
    account = ServiceAccount.objects.create(
        name="Notifier",
        auto_rotate_days=10,
        notify_before_days=3,
        notification_webhook_url="https://example.com/webhook",
    )
    _, token = account.create_token()

    token.created_at = timezone.now() - timezone.timedelta(days=8)
    token.save(update_fields=["created_at"])

    dispatched: list[dict[str, object]] = []

    def fake_dispatch(url: str, payload: dict[str, object]) -> None:
        dispatched.append({"url": url, "payload": payload})

    monkeypatch.setattr(rotation_services, "_dispatch_webhook", fake_dispatch)

    now = timezone.now()
    result = rotation_services.enforce_rotation_policies(reference=now)
    assert result["notices"] == 1
    assert len(dispatched) == 1

    token.refresh_from_db()
    assert token.last_notified_at is not None
    assert dispatched[0]["url"] == account.notification_webhook_url
    payload = dispatched[0]["payload"]
    assert isinstance(payload, dict)
    assert payload["event"] == "service_account.rotation_warning"

    again = rotation_services.enforce_rotation_policies(
        reference=now + timezone.timedelta(hours=1)
    )
    assert again["notices"] == 0
    assert len(dispatched) == 1

    assert ServiceAccountAuditLog.objects.filter(
        account=account,
        action="rotation_notice",
    ).count() == 1
