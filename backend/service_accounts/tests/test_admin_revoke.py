"""EV-0073: revogar à mão tokens de conta de serviço pelo admin."""

from __future__ import annotations

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.test import Client, RequestFactory
from django.urls import reverse

from service_accounts.models import ServiceAccount, ServiceAccountAuditLog, ServiceAccountToken

ACTION = "revoke_selected_tokens"
CHANGELIST = "admin:service_accounts_serviceaccounttoken_changelist"


def _bearer(plain: str) -> dict[str, str]:
    return {"HTTP_AUTHORIZATION": f"Bearer {plain}"}


def _post_action(client: Client, tokens: list[ServiceAccountToken]):
    return client.post(
        reverse(CHANGELIST),
        {"action": ACTION, "_selected_action": [t.pk for t in tokens]},
    )


def _messages(response) -> list[str]:
    return [str(m) for m in get_messages(response.wsgi_request)]


def _staff(username: str, *perms: str):
    user = get_user_model().objects.create_user(
        username=username, password="secret123", is_staff=True
    )
    for codename in perms:
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="service_accounts", codename=codename)
        )
    return user


@pytest.fixture
def account(db):
    return ServiceAccount.objects.create(name="Integração NOC")


@pytest.mark.django_db
def test_manager_revokes_token_and_it_stops_authenticating(account) -> None:
    plain, token = account.create_token(note="test")
    assert Client().get(reverse("site-list"), **_bearer(plain)).status_code == 200

    manager = _staff("manager", "manage_tokens")
    client = Client()
    client.force_login(manager)
    response = _post_action(client, [token])

    assert response.status_code == 302
    token.refresh_from_db()
    assert token.revoked_at is not None
    assert token.is_active is False
    assert any("1 token(s) revogado(s)" in m for m in _messages(response))

    entry = ServiceAccountAuditLog.objects.get(account=account, action="token_revoked")
    assert entry.actor == manager
    assert entry.extra_data["token_id"] == token.pk

    denied = Client().get(reverse("site-list"), **_bearer(plain))
    assert denied.status_code == 401
    assert ServiceAccountToken.objects.filter(pk=token.pk).exists()  # revogado, não apagado


@pytest.mark.django_db
def test_superuser_can_revoke_several_tokens(admin_client: Client, account) -> None:
    _, first = account.create_token()
    _, second = account.create_token()

    response = _post_action(admin_client, [first, second])

    assert response.status_code == 302
    assert ServiceAccountToken.objects.filter(revoked_at__isnull=False).count() == 2
    assert any("2 token(s) revogado(s)" in m for m in _messages(response))


@pytest.mark.django_db
def test_already_revoked_token_keeps_original_revoked_at(admin_client: Client, account) -> None:
    _, old = account.create_token()
    _, fresh = account.create_token()
    old.revoke(reason="rotated")
    old.refresh_from_db()
    original_revoked_at = old.revoked_at

    response = _post_action(admin_client, [old, fresh])

    old.refresh_from_db()
    fresh.refresh_from_db()
    assert old.revoked_at == original_revoked_at
    assert fresh.revoked_at is not None
    msgs = _messages(response)
    assert any("1 token(s) revogado(s)" in m for m in msgs)
    assert any("1 token(s) já estavam revogados" in m for m in msgs)
    # Só uma entrada de auditoria por token, mesmo revogando duas vezes.
    revoked_ids = [
        e.extra_data["token_id"]
        for e in ServiceAccountAuditLog.objects.filter(account=account, action="token_revoked")
    ]
    assert sorted(revoked_ids) == sorted([old.pk, fresh.pk])


@pytest.mark.django_db
def test_only_already_revoked_does_not_claim_revocation(admin_client: Client, account) -> None:
    _, token = account.create_token()
    token.revoke()

    response = _post_action(admin_client, [token])

    msgs = _messages(response)
    assert not any("revogado(s)" in m for m in msgs)
    assert any("já estavam revogados" in m for m in msgs)


@pytest.mark.django_db
def test_staff_without_permission_cannot_reach_changelist(account) -> None:
    _, token = account.create_token()
    client = Client()
    client.force_login(_staff("plain"))

    response = _post_action(client, [token])

    assert response.status_code == 403
    token.refresh_from_db()
    assert token.revoked_at is None


@pytest.mark.django_db
def test_view_only_user_has_no_revoke_action(account) -> None:
    """Quem só pode ver tokens não vê a ação e um POST forjado não revoga."""
    _, token = account.create_token()
    viewer = _staff("viewer", "view_serviceaccounttoken")

    request = RequestFactory().get("/")
    request.user = viewer
    model_admin = admin.site._registry[ServiceAccountToken]
    assert ACTION not in model_admin.get_actions(request)

    client = Client()
    client.force_login(viewer)
    response = _post_action(client, [token])

    assert response.status_code in (200, 302)
    token.refresh_from_db()
    assert token.revoked_at is None
    assert ServiceAccountAuditLog.objects.filter(action="token_revoked").count() == 0


@pytest.mark.django_db
def test_manager_sees_revoke_action(account) -> None:
    request = RequestFactory().get("/")
    request.user = _staff("manager2", "manage_tokens")
    model_admin = admin.site._registry[ServiceAccountToken]
    assert ACTION in model_admin.get_actions(request)


# ── EV-0078: tokens e auditoria não se apagam no admin (nem por superuser) ──────────────


@pytest.mark.django_db
def test_superuser_cannot_delete_tokens(admin_client: Client, account) -> None:
    _, token = account.create_token()
    model_admin = admin.site._registry[ServiceAccountToken]
    request = RequestFactory().get("/")
    request.user = get_user_model().objects.get(username="admin")
    assert model_admin.has_delete_permission(request, token) is False
    assert "delete_selected" not in model_admin.get_actions(request)

    url = reverse("admin:service_accounts_serviceaccounttoken_delete", args=[token.pk])
    assert admin_client.post(url, {"post": "yes"}).status_code == 403
    assert ServiceAccountToken.objects.filter(pk=token.pk).exists()


@pytest.mark.django_db
def test_superuser_cannot_delete_audit_log(admin_client: Client, account) -> None:
    _, token = account.create_token()
    token.revoke(reason="teste")
    entry = ServiceAccountAuditLog.objects.filter(account=account).first()
    assert entry is not None
    url = reverse("admin:service_accounts_serviceaccountauditlog_delete", args=[entry.pk])
    assert admin_client.post(url, {"post": "yes"}).status_code == 403
    assert ServiceAccountAuditLog.objects.filter(pk=entry.pk).exists()
