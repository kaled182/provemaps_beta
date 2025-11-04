#!/usr/bin/env python
"""Diagnostic script to check Google Maps API Key at all layers"""
import os
import sys
from typing import Any, Callable, Optional, cast
import django

# Add project root to path
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from setup_app.models import FirstTimeSetup  # noqa: E402
from setup_app.services.runtime_settings import (  # noqa: E402
    get_runtime_config,
)
from django.conf import settings  # noqa: E402

print("=" * 80)
print("GOOGLE MAPS API KEY - DIAGNOSTIC REPORT")
print("=" * 80)
print()

# Layer 1: Database
print("== LAYER 1: DATABASE (FirstTimeSetup model)")
print("-" * 80)
config_db = (
    FirstTimeSetup.objects.filter(configured=True)
    .order_by('-configured_at')
    .first()
)
config_runtime: Optional[Any] = None
match: Optional[Any] = None
if config_db:
    key = config_db.maps_api_key
    config_id = getattr(config_db, "id", "unknown")
    company_name = getattr(config_db, "company_name", "unknown")
    print(f"OK: Config record exists: ID={config_id}, Company={company_name}")
    if key:
        print(
            f"OK: maps_api_key field value {key[:20]}...{key[-6:]} "
            f"(length {len(key)})"
        )
    else:
        print("ERROR: maps_api_key field is empty or null")
else:
    print("ERROR: No configured FirstTimeSetup record found")
print()

# Layer 2: Runtime Settings (Service Layer)
print("== LAYER 2: RUNTIME_SETTINGS (service layer with cache)")
print("-" * 80)
try:
    config_runtime = get_runtime_config()
    key = getattr(config_runtime, 'google_maps_api_key', '')
    if key:
        print(
            f"OK: google_maps_api_key value {key[:20]}...{key[-6:]} "
            f"(length {len(key)})"
        )
    else:
        print("ERROR: google_maps_api_key is empty")
except Exception as e:
    print(f"ERROR: Failed to load runtime_settings ({e})")
print()

# Layer 3: Django Settings (.env)
print("== LAYER 3: DJANGO SETTINGS (from .env file)")
print("-" * 80)
key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
if key:
    print(
        f"OK: GOOGLE_MAPS_API_KEY value {key[:20]}...{key[-6:]} "
        f"(length {len(key)})"
    )
else:
    print("ERROR: GOOGLE_MAPS_API_KEY not set in .env")
print()

# Layer 4: View Context (what gets passed to template)
print("== LAYER 4: VIEW CONTEXT (routes_builder fiber route view)")
print("-" * 80)
try:
    from routes_builder.views import (  # type: ignore[attr-defined]
        fiber_route_builder_view,
    )
    from django.test import RequestFactory
    from django.contrib.auth.models import User
    
    factory = RequestFactory()
    request = factory.get('/routes/fiber-route-builder/')
    user = User.objects.first()
    if not user:
        print("WARN: No user found; creating test user for diagnostic")
        user = User.objects.create_user(
            username='diagnostic_user',
            password='test123',
        )
    request.user = user

    fiber_route_fn = cast(Callable[[Any], Any], fiber_route_builder_view)
    response = fiber_route_fn(request)
    html = response.content.decode('utf-8')
    
    # Search for Google Maps script tag
    import re
    match = re.search(
        r'maps\.googleapis\.com/maps/api/js\?key=([^"&\s]+)',
        html,
    )
    
    if match:
        key_in_html = match.group(1)
        if key_in_html:
            print(
                "OK: Key in HTML "
                f"{key_in_html[:20]}...{key_in_html[-6:]} "
                f"(length {len(key_in_html)})"
            )
        else:
            print("ERROR: Key parameter is empty in HTML")
    else:
        print("ERROR: Google Maps script tag not found in rendered HTML")
        # Show snippet for debugging
        snippet_start = html.find('maps.googleapis')
        if snippet_start > 0:
            snippet = html[snippet_start:snippet_start+100]
            print(f"    HTML snippet: {snippet}")
        
except Exception as e:
    print(f"ERROR: Exception while testing view ({e})")
    import traceback
    traceback.print_exc()
print()

# Summary
print("=" * 80)
print("SUMMARY")
print("=" * 80)
has_db = bool(config_db and getattr(config_db, 'maps_api_key', ''))
has_runtime = bool(
    config_runtime and getattr(config_runtime, 'google_maps_api_key', '')
)
has_settings = bool(getattr(settings, 'GOOGLE_MAPS_API_KEY', ''))
has_html = match and match.group(1) if 'match' in locals() else False

if all([has_db, has_runtime, has_html]):
    print("OK: All layers report the Google Maps API Key is configured")
else:
    print("ERROR: Configuration issue detected")
    if not has_db:
        print("    Database: Key not saved in FirstTimeSetup")
    if not has_runtime:
        print("    Runtime Settings: Key not loaded by service layer")
    if not has_html:
        print("    View/Template: Key not injected into HTML")
    if not has_settings:
        print("    .env file: Key not set (setup_app may manage it)")

print()
print("=" * 80)
