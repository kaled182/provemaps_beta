"""EV-0023 / ADR 0008: tokens de conta de serviço autenticam pedidos à API."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from service_accounts.authentication import ServiceAccountPrincipal, authenticate_bearer
from service_accounts.models import ServiceAccount, ServiceAccountToken


@pytest.fixture
def account_and_token(db):
    account = ServiceAccount.objects.create(name="Zabbix Sync Bot")
    plain, token = account.create_token(note="test")
    return account, token, plain


def _bearer(plain: str) -> dict[str, str]:
    return {"HTTP_AUTHORIZATION": f"Bearer {plain}"}


@pytest.mark.django_db
def test_valid_token_authenticates_drf_endpoint_without_session(account_and_token):
    _, _, plain = account_and_token
    response = Client().get(reverse("site-list"), **_bearer(plain))
    assert response.status_code == 200, response.content[:200]


@pytest.mark.django_db
def test_no_header_is_still_rejected(account_and_token):
    assert Client().get(reverse("site-list")).status_code in (401, 403)
    assert Client().get("/api/config/").status_code == 401


@pytest.mark.django_db
def test_revoked_token_is_rejected_with_bearer_challenge(account_and_token):
    _, token, plain = account_and_token
    token.revoke(reason="rotated")
    response = Client().get(reverse("site-list"), **_bearer(plain))
    assert response.status_code == 401
    assert response["WWW-Authenticate"].startswith("Bearer")


@pytest.mark.django_db
def test_expired_token_is_rejected(account_and_token):
    _, token, plain = account_and_token
    token.expires_at = timezone.now() - timedelta(minutes=1)
    token.save(update_fields=["expires_at"])
    assert Client().get(reverse("site-list"), **_bearer(plain)).status_code == 401


@pytest.mark.django_db
def test_inactive_account_is_rejected(account_and_token):
    account, _, plain = account_and_token
    account.is_active = False
    account.save(update_fields=["is_active"])
    assert Client().get(reverse("site-list"), **_bearer(plain)).status_code == 401


@pytest.mark.django_db
def test_unknown_and_malformed_headers_never_500(account_and_token):
    client = Client()
    assert client.get(reverse("site-list"), HTTP_AUTHORIZATION="Bearer nope").status_code == 401
    assert client.get(reverse("site-list"), HTTP_AUTHORIZATION="Basic abc").status_code in (
        401,
        403,
    )
    assert client.get(reverse("site-list"), HTTP_AUTHORIZATION="Bearer").status_code in (401, 403)
    assert client.get("/api/config/", HTTP_AUTHORIZATION="Bearer nope").status_code == 401


@pytest.mark.django_db
def test_middleware_guarded_api_path_accepts_bearer(account_and_token):
    """`/api/config/` não é rota DRF: é o middleware (EV-0002) que a guarda."""
    _, _, plain = account_and_token
    response = Client().get("/api/config/", **_bearer(plain))
    assert response.status_code == 200, response.content[:200]


@pytest.mark.django_db
def test_post_with_bearer_is_not_blocked_by_csrf(account_and_token):
    _, _, plain = account_and_token
    client = Client(enforce_csrf_checks=True)
    response = client.post(
        reverse("site-list"), data="{}", content_type="application/json", **_bearer(plain)
    )
    assert response.status_code != 403, response.content[:200]


@pytest.mark.django_db
def test_last_used_at_is_recorded_but_not_rewritten_every_request(account_and_token):
    _, token, plain = account_and_token
    assert token.last_used_at is None
    Client().get(reverse("site-list"), **_bearer(plain))
    token.refresh_from_db()
    first = token.last_used_at
    assert first is not None
    Client().get(reverse("site-list"), **_bearer(plain))
    token.refresh_from_db()
    assert token.last_used_at == first  # dentro da janela de 60 s não reescreve


@pytest.mark.django_db
def test_principal_is_authenticated_but_has_no_privileges(account_and_token):
    account, token, plain = account_and_token
    principal, resolved = authenticate_bearer(f"Bearer {plain}")
    assert isinstance(principal, ServiceAccountPrincipal)
    assert resolved.pk == token.pk
    assert principal.is_authenticated and not principal.is_anonymous
    assert principal.is_staff is False and principal.is_superuser is False
    assert principal.has_perm("inventory.delete_site") is False
    assert principal.get_username() == f"svc:{account.name}"
    assert ServiceAccountToken.objects.get(pk=token.pk).last_used_at is not None
