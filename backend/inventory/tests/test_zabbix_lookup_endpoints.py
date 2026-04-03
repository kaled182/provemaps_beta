from django.test import TestCase, Client
from django.contrib.auth import get_user_model


class ZabbixLookupEndpointsTests(TestCase):
    """Smoke tests for Zabbix lookup endpoints.

    These tests exercise the HTTP endpoints to ensure they require
    authentication and return the expected JSON shape when called
    by an authenticated user. They are intentionally lightweight and
    safe for local development.
    """

    def setUp(self):
        User = get_user_model()
        # create a temporary superuser for authenticated calls
        self.username = "tmp_test_admin"
        self.password = "tmp_password_123"
        self.user = User.objects.create_superuser(self.username, "tmp@test.local", self.password)
        self.client = Client()

    def tearDown(self):
        try:
            self.user.delete()
        except Exception:
            pass

    def test_host_groups_requires_login(self):
        res = self.client.get("/api/v1/inventory/zabbix/lookup/host-groups/?exclude_empty=1")
        # unauthenticated requests are expected to redirect to login (302)
        self.assertIn(res.status_code, (302, 401))

    def test_host_groups_authenticated_returns_list(self):
        login_ok = self.client.login(username=self.username, password=self.password)
        self.assertTrue(login_ok)
        res = self.client.get("/api/v1/inventory/zabbix/lookup/host-groups/?exclude_empty=1")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertIsInstance(payload, dict)
        self.assertIn("data", payload)
        self.assertIsInstance(payload["data"], list)

    def test_hosts_grouped_authenticated_returns_groups(self):
        login_ok = self.client.login(username=self.username, password=self.password)
        self.assertTrue(login_ok)
        res = self.client.get("/api/v1/inventory/zabbix/lookup/hosts/grouped/")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertIsInstance(payload, dict)
        self.assertIn("data", payload)
import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.fixture
def auth_client(client):
    user = User.objects.create_user(username="tester", password="tester123", is_staff=True)
    client.force_login(user)
    return client


def _mock_host_groups(*args, **kwargs):
    # Mimic Zabbix API response structure
    return [
        {"groupid": "10", "name": "Core", "hosts": 5},
        {"groupid": "20", "name": "Access", "hosts": 0},
    ]


def _mock_hosts(*args, **kwargs):
    return [
        {
            "hostid": "10101",
            "name": "sw-core-01",
            "interfaces": [
                {"interfaceid": "1", "ip": "10.0.0.1", "dns": "", "port": "161", "type": 2, "main": 1, "useip": 1},
            ],
            "available": "1",
        },
        {
            "hostid": "10102",
            "name": "sw-access-01",
            "interfaces": [
                {"interfaceid": "2", "ip": "10.0.1.1", "dns": "", "port": "161", "type": 2, "main": 1, "useip": 1},
            ],
            "available": "2",
        },
    ]


@patch("inventory.api.zabbix_lookup.zabbix_request", side_effect=_mock_host_groups)
def test_lookup_host_groups_returns_data(mock_req, auth_client):
    url = reverse("inventory-api:zabbix-lookup-host-groups")
    resp = auth_client.get(url + "?exclude_empty=1")
    assert resp.status_code == 200
    payload = resp.json()
    assert "data" in payload
    assert payload["data"][0]["groupid"] == "10"
    assert payload["data"][0]["name"] == "Core"
    # group with hosts=0 should be filtered by exclude_empty
    assert all(item["groupid"] != "20" for item in payload["data"])


@patch("inventory.api.zabbix_lookup.zabbix_request", side_effect=_mock_hosts)
def test_lookup_hosts_returns_normalized_hosts(mock_req, auth_client):
    url = reverse("inventory-api:zabbix-lookup-hosts")
    resp = auth_client.get(url + "?groupids=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    host = body["data"][0]
    assert host["hostid"] == "10101"
    assert host["availability"]["value"] == "1"
    assert host["interfaces"][0]["ip"] == "10.0.0.1"
