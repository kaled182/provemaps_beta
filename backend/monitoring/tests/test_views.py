"""Monitoring API view tests covering dashboard endpoints."""

from __future__ import annotations

from typing import Any, Dict, Type
from unittest.mock import patch

import pytest
from django.test.client import Client


@pytest.mark.django_db
def test_api_hosts_status_returns_cached_payload(
    client: Client,
    django_user_model: Type[Any],
):
    user: Any = django_user_model.objects.create_user(
        username="monitoring-user",
        password="secret",
    )
    client.force_login(user)

    cache_result: Dict[str, Any] = {
        "data": {
            "hosts_status": [
                {"device_id": 1, "hostid": "101", "available": "1"}
            ],
            "hosts_summary": {"total": 1, "available": 1, "unavailable": 0},
        },
        "is_stale": False,
        "timestamp": 1730793600.0,
        "cache_hit": True,
    }

    with patch(
        "monitoring.views.get_dashboard_cached",
        return_value=cache_result,
    ) as cache_mock:
        response = client.get("/api/v1/monitoring/hosts/status/")

    assert cache_mock.called
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["hosts"][0]["hostid"] == "101"
    assert payload["cache_metadata"]["cache_hit"] is True


@pytest.mark.django_db
def test_api_hosts_status_returns_404_without_hosts(
    client: Client,
    django_user_model: Type[Any],
):
    user: Any = django_user_model.objects.create_user(
        username="monitoring-empty",
        password="secret",
    )
    client.force_login(user)

    empty_cache: Dict[str, Any] = {
        "data": {"hosts_status": [], "hosts_summary": {"total": 0}},
        "is_stale": True,
        "timestamp": None,
        "cache_hit": False,
    }

    with patch(
        "monitoring.views.get_dashboard_cached",
        return_value=empty_cache,
    ):
        response = client.get("/api/v1/monitoring/hosts/status/")

    assert response.status_code == 404
    assert response.json()["error"] == "No devices configured with Zabbix"


@pytest.mark.django_db
def test_api_dashboard_snapshot_returns_snapshot(
    client: Client,
    django_user_model: Type[Any],
):
    user: Any = django_user_model.objects.create_user(
        username="monitoring-snapshot",
        password="secret",
    )
    client.force_login(user)

    snapshot: Dict[str, Any] = {
        "hosts_status": [
            {"device_id": 2, "hostid": "202", "available": "2"}
        ],
        "hosts_summary": {"total": 1, "available": 0, "unavailable": 1},
    }

    with patch(
        "monitoring.views.get_hosts_status_data",
        return_value=snapshot,
    ) as get_data:
        response = client.get("/api/v1/monitoring/dashboard/snapshot/")

    assert get_data.called
    assert response.status_code == 200
    assert response.json()["hosts_status"][0]["hostid"] == "202"


@pytest.mark.django_db
def test_api_dashboard_snapshot_handles_errors(
    client: Client,
    django_user_model: Type[Any],
):
    user: Any = django_user_model.objects.create_user(
        username="monitoring-error",
        password="secret",
    )
    client.force_login(user)

    with patch(
        "monitoring.views.get_hosts_status_data",
        side_effect=RuntimeError("boom"),
    ):
        response = client.get("/api/v1/monitoring/dashboard/snapshot/")

    assert response.status_code == 500
    assert response.json()["error"] == "Unable to fetch monitoring data"
