"""
Tests for dashboard data API endpoint.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()


@pytest.fixture
def authenticated_client(db):
    """Create an authenticated test client."""
    User.objects.create_user(username="testuser", password="testpass")
    client = Client()
    client.login(username="testuser", password="testpass")
    return client


@pytest.mark.django_db
def test_dashboard_data_api_requires_login():
    """Ensure the API endpoint requires authentication."""
    client = Client()
    url = reverse("maps_view:dashboard_data_api")
    response = client.get(url)
    # Should redirect to login
    assert response.status_code == 302


@pytest.mark.django_db
def test_dashboard_data_api_returns_json(authenticated_client, monkeypatch):
    """Ensure the API endpoint returns JSON with expected structure."""

    # Mock the get_hosts_status_data to avoid Zabbix calls
    def mock_get_hosts_status_data():
        return {
            "hosts_status": [{"id": 1, "name": "Test Host", "status": "up"}],
            "hosts_summary": {
                "total": 1,
                "available": 1,
                "unavailable": 0,
                "unknown": 0,
                "availability_percentage": 100.0,
            },
        }

    # Patch the service function
    from maps_view import views

    monkeypatch.setattr(views, "get_hosts_status_data", mock_get_hosts_status_data)

    url = reverse("maps_view:dashboard_data_api")
    response = authenticated_client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    data = response.json()
    assert "hosts_status" in data
    assert "hosts_summary" in data
    assert "cache_metadata" in data
    assert len(data["hosts_status"]) == 1
    assert data["hosts_summary"]["total"] == 1


@pytest.mark.django_db
def test_dashboard_view_redirects_to_spa(authenticated_client):
    """O dashboard Django legado deixou de existir (main, v1.4.x): a rota redireciona
    de forma permanente para a raiz, onde vive o SPA."""
    url = reverse("maps_view:dashboard_view")
    response = authenticated_client.get(url)

    assert response.status_code == 301
    assert response["Location"] == "/"
