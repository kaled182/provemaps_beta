#!/usr/bin/env python
"""Integration test: validate Google Maps API Key in route builder view.
Skipped unless --integration flag provided.
"""
import os
import re
import pytest
import django
from django.test import RequestFactory
from django.contrib.auth.models import User

try:
    from routes_builder.views import fiber_route_builder_view
except ImportError:  # routes_builder removido
    fiber_route_builder_view = None

# Use test settings; avoid hitting production DB
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.test")
django.setup()

if fiber_route_builder_view is None:
    pytest.skip(
        "Teste de Google Maps não aplicável: routes_builder removido",
        allow_module_level=True,
    )

# Mark as integration (skipped unless --integration)
pytestmark = pytest.mark.integration

factory = RequestFactory()
request = factory.get("/routes/fiber-route-builder/")

try:
    user = User.objects.first()
    if not user:
        user = User.objects.create_user(
            username="testuser", password="testpass"
        )
    request.user = user
except Exception as e:  # DB connectivity issues → skip gracefully
    pytest.skip(
        f"Skipping Google Maps key test (DB issue): {e}",
        allow_module_level=True,
    )


def test_google_maps_key_present():
    assert fiber_route_builder_view is not None
    response = fiber_route_builder_view(request)
    html = response.content.decode("utf-8")
    match = re.search(
        r"maps\.googleapis\.com/maps/api/js\?key=([^\"&]+)", html
    )
    if not match:
        pytest.fail(
            "Google Maps URL not found or key missing. Snippet: " + html[:200]
        )
    key = match.group(1)
    # Basic sanity assertions
    assert len(key) > 10
    assert key.strip() == key
    # Emit summary lines (stdout)
    print("✅ SUCCESS: Google Maps API Key found in HTML")
    print(f"   Key prefix: {key[:12]}... len={len(key)}")
