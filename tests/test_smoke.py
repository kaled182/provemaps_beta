import os

import django
from django.test import Client

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django.setup()


def test_health():
    c = Client()
    r = c.get("/healthz")  # Without trailing slash
    assert r.status_code in (200, 503)  # 200 OK or 503 degraded are valid
    data = r.json()
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data


def test_dashboard_route_exists():
    c = Client()
    r = c.get("/maps_view/dashboard/")
    assert r.status_code in (200, 302)  # 302 if authentication is required
