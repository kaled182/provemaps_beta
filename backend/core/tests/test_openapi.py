"""EV-0030: esquema OpenAPI 3 e versionamento único (/api/v<N>/)."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse
from rest_framework import exceptions

from core.api_versioning import PathPrefixVersioning


@pytest.fixture
def logged_client(db):
    client = Client()
    client.force_login(get_user_model().objects.create_user(username="dev", password="x"))
    return client


@pytest.mark.django_db
def test_schema_requires_authentication():
    assert Client().get(reverse("openapi-schema")).status_code == 401
    assert Client().get(reverse("openapi-swagger")).status_code == 401


@pytest.mark.django_db
def test_schema_lists_router_endpoints_and_security_schemes(logged_client):
    response = logged_client.get(reverse("openapi-schema"), {"format": "json"})
    assert response.status_code == 200, response.content[:200]
    schema = response.json()
    assert schema["openapi"].startswith("3.")
    assert schema["info"] == {
        "title": "ProVeMaps API",
        "version": "v1",
        "description": schema["info"]["description"],
    }
    paths = schema["paths"]
    assert "/api/v1/sites/" in paths
    assert "/api/v1/fiber-cables/{id}/optical-history/" in paths
    assert set(schema["components"]["securitySchemes"]) == {"cookieAuth", "bearerAuth"}


@pytest.mark.django_db
def test_swagger_ui_is_self_hosted(logged_client):
    response = logged_client.get(reverse("openapi-swagger"))
    assert response.status_code == 200
    body = response.content.decode()
    assert "drf_spectacular_sidecar/swagger-ui-dist" in body
    for cdn in ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com"):
        assert cdn not in body, cdn


def test_version_comes_from_path_prefix_and_defaults_to_v1():
    versioning = PathPrefixVersioning()
    factory = RequestFactory()
    assert versioning.determine_version(factory.get("/api/v1/sites/")) == "v1"
    assert versioning.determine_version(factory.get("/api/users/me/")) == "v1"  # legado = v1
    with pytest.raises(exceptions.NotFound):
        versioning.determine_version(factory.get("/api/v2/sites/"))


@pytest.mark.django_db
def test_drf_requests_carry_the_version(logged_client):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(get_user_model().objects.create_user(username="v", password="x"))
    response = client.get("/api/v1/sites/")
    assert response.status_code == 200
    assert response.renderer_context["request"].version == "v1"
