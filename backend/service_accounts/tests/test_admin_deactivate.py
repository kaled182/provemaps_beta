"""EV-0080: contas de serviço desativam-se, não se apagam (tokens e auditoria ficam)."""

from __future__ import annotations

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.db.models import ProtectedError
from django.test import Client, RequestFactory
from django.urls import reverse

from service_accounts.models import ServiceAccount, ServiceAccountAuditLog, ServiceAccountToken

ACTION = "deactivate_selected_accounts"
CHANGELIST = "admin:service_accounts_serviceaccount_changelist"


def _bearer(plain: str) -> dict[str, str]:
    return {"HTTP_AUTHORIZATION": f"Bearer {plain}"}


def _post_action(client: Client, accounts: list[ServiceAccount]):
    return client.post(
        reverse(CHANGELIST),
        {"action": ACTION, "_selected_action": [a.pk for a in accounts]},
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


def _request_for(user):
    request = RequestFactory().get("/")
    request.user = user
    return request


@pytest.fixture
def account(db):
    return ServiceAccount.objects.create(name="Integração CRM")


# ── apagar ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_superuser_cannot_delete_account_in_admin(admin_client: Client, account) -> None:
    account.create_token()
    model_admin = admin.site._registry[ServiceAccount]
    request = _request_for(get_user_model().objects.get(username="admin"))
    assert model_admin.has_delete_permission(request, account) is False
    assert "delete_selected" not in model_admin.get_actions(request)

    url = reverse("admin:service_accounts_serviceaccount_delete", args=[account.pk])
    assert admin_client.post(url, {"post": "yes"}).status_code == 403
    assert ServiceAccount.objects.filter(pk=account.pk).exists()
    assert ServiceAccountToken.objects.filter(account=account).count() == 1
    assert ServiceAccountAuditLog.objects.filter(account=account).exists()


@pytest.mark.django_db
def test_manager_cannot_delete_account_in_admin(account) -> None:
    manager = _staff("manager", "manage_tokens")
    model_admin = admin.site._registry[ServiceAccount]
    assert model_admin.has_delete_permission(_request_for(manager), account) is False

    client = Client()
    client.force_login(manager)
    url = reverse("admin:service_accounts_serviceaccount_delete", args=[account.pk])
    assert client.post(url, {"post": "yes"}).status_code == 403
    assert ServiceAccount.objects.filter(pk=account.pk).exists()


@pytest.mark.django_db
def test_orm_delete_of_account_with_audit_is_protected(account) -> None:
    account.create_token(note="gera auditoria")
    assert ServiceAccountAuditLog.objects.filter(account=account).exists()

    with pytest.raises(ProtectedError):
        account.delete()

    assert ServiceAccount.objects.filter(pk=account.pk).exists()
    assert ServiceAccountToken.objects.filter(account=account).count() == 1


# ── desativar ──────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_manager_deactivates_account_revokes_tokens_and_audits(account) -> None:
    plain, token = account.create_token(note="test")
    assert Client().get(reverse("site-list"), **_bearer(plain)).status_code == 200

    manager = _staff("manager", "manage_tokens")
    client = Client()
    client.force_login(manager)
    response = _post_action(client, [account])

    assert response.status_code == 302
    account.refresh_from_db()
    token.refresh_from_db()
    assert account.is_active is False
    assert account.updated_by == manager
    assert token.revoked_at is not None
    msgs = _messages(response)
    assert any("1 conta(s) desativada(s)" in m for m in msgs)
    assert any("1 token(s) revogado(s)" in m for m in msgs)

    entry = ServiceAccountAuditLog.objects.get(account=account, action="deactivated")
    assert entry.actor == manager
    assert entry.extra_data["tokens_revoked"] == 1
    revoked = ServiceAccountAuditLog.objects.get(account=account, action="token_revoked")
    assert revoked.extra_data["token_id"] == token.pk

    assert Client().get(reverse("site-list"), **_bearer(plain)).status_code == 401
    assert ServiceAccount.objects.filter(pk=account.pk).exists()  # desativada, não apagada


@pytest.mark.django_db
def test_already_inactive_account_is_not_reaudited(admin_client: Client, account) -> None:
    account.is_active = False
    account.save(update_fields=["is_active"])

    response = _post_action(admin_client, [account])

    msgs = _messages(response)
    assert not any("desativada(s)" in m for m in msgs)
    assert not any("revogado(s)" in m for m in msgs)
    assert any("já estavam inativas" in m for m in msgs)
    assert not ServiceAccountAuditLog.objects.filter(action="deactivated").exists()


@pytest.mark.django_db
def test_already_inactive_account_still_gets_leftover_tokens_revoked(
    admin_client: Client, account
) -> None:
    _, token = account.create_token()
    account.is_active = False
    account.save(update_fields=["is_active"])

    response = _post_action(admin_client, [account])

    token.refresh_from_db()
    assert token.revoked_at is not None
    assert any("1 token(s) revogado(s)" in m for m in _messages(response))


@pytest.mark.django_db
def test_staff_without_permission_cannot_deactivate(account) -> None:
    client = Client()
    client.force_login(_staff("plain"))

    response = _post_action(client, [account])

    assert response.status_code == 403
    account.refresh_from_db()
    assert account.is_active is True


@pytest.mark.django_db
def test_view_only_user_has_no_deactivate_action(account) -> None:
    """Quem só pode ver contas não vê a ação e um POST forjado não desativa."""
    _, token = account.create_token()
    viewer = _staff("viewer", "view_serviceaccount")
    model_admin = admin.site._registry[ServiceAccount]
    assert ACTION not in model_admin.get_actions(_request_for(viewer))

    client = Client()
    client.force_login(viewer)
    response = _post_action(client, [account])

    assert response.status_code in (200, 302)
    account.refresh_from_db()
    token.refresh_from_db()
    assert account.is_active is True
    assert token.revoked_at is None
    assert not ServiceAccountAuditLog.objects.filter(action="deactivated").exists()


@pytest.mark.django_db
def test_manager_sees_deactivate_action() -> None:
    model_admin = admin.site._registry[ServiceAccount]
    request = _request_for(_staff("manager2", "manage_tokens"))
    assert ACTION in model_admin.get_actions(request)
