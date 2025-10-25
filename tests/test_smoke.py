import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from django.test import Client

def test_health():
    c = Client()
    r = c.get("/healthz")  # Sem trailing slash
    assert r.status_code in (200, 503)  # 200 ok ou 503 degraded são válidos
    data = r.json()
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data

def test_dashboard_route_exists():
    c = Client()
    r = c.get("/maps_view/dashboard/")
    assert r.status_code in (200, 302)  # 302 se exigir login
