"""EV-0046 — sondas de saúde isentas do redirect HTTPS; o resto continua redirecionado."""

import pytest
from django.conf import settings
from django.test import override_settings


@pytest.mark.django_db
@override_settings(SECURE_SSL_REDIRECT=True)
@pytest.mark.parametrize("path", ["/healthz", "/ready", "/live"])
def test_health_probes_not_redirected_to_https(client, path):
    response = client.get(path)
    assert response.status_code != 301, f"{path} redirecionou para {response.get('Location')}"


@pytest.mark.django_db
@override_settings(SECURE_SSL_REDIRECT=True)
def test_other_routes_still_redirect_to_https(client):
    response = client.get("/accounts/login/")
    assert response.status_code == 301
    assert response["Location"].startswith("https://")


def test_exempt_list_is_only_the_probes():
    assert settings.SECURE_REDIRECT_EXEMPT == [r"^healthz/?$", r"^ready/?$", r"^live/?$"]
