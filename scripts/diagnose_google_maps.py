#!/usr/bin/env python
"""Diagnostic script to check Google Maps API Key at all layers"""
import os
import sys
import django

# Add project root to path
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from setup_app.models import FirstTimeSetup
from setup_app.services.runtime_settings import get_runtime_config
from django.conf import settings

print("=" * 80)
print("GOOGLE MAPS API KEY - DIAGNOSTIC REPORT")
print("=" * 80)
print()

# Layer 1: Database
print("📊 LAYER 1: DATABASE (FirstTimeSetup model)")
print("-" * 80)
config_db = FirstTimeSetup.objects.filter(configured=True).order_by('-configured_at').first()
if config_db:
    key = config_db.maps_api_key
    print(f"✅ Config record exists: ID={config_db.id}, Company={config_db.company_name}")
    if key:
        print(f"✅ maps_api_key field: {key[:20]}...{key[-6:]} (length: {len(key)})")
    else:
        print("❌ maps_api_key field: EMPTY or NULL")
else:
    print("❌ No configured FirstTimeSetup record found")
print()

# Layer 2: Runtime Settings (Service Layer)
print("⚙️  LAYER 2: RUNTIME_SETTINGS (Service layer with cache)")
print("-" * 80)
try:
    config_runtime = get_runtime_config()
    key = config_runtime.google_maps_api_key
    if key:
        print(f"✅ google_maps_api_key: {key[:20]}...{key[-6:]} (length: {len(key)})")
    else:
        print("❌ google_maps_api_key: EMPTY")
except Exception as e:
    print(f"❌ ERROR loading runtime_settings: {e}")
print()

# Layer 3: Django Settings (.env)
print("📄 LAYER 3: DJANGO SETTINGS (from .env file)")
print("-" * 80)
key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
if key:
    print(f"✅ GOOGLE_MAPS_API_KEY: {key[:20]}...{key[-6:]} (length: {len(key)})")
else:
    print("❌ GOOGLE_MAPS_API_KEY: NOT SET in .env")
print()

# Layer 4: View Context (what gets passed to template)
print("🖼️  LAYER 4: VIEW CONTEXT (routes_builder.views.fiber_route_builder_view)")
print("-" * 80)
try:
    from routes_builder.views import fiber_route_builder_view
    from django.test import RequestFactory
    from django.contrib.auth.models import User
    
    factory = RequestFactory()
    request = factory.get('/routes/fiber-route-builder/')
    user = User.objects.first()
    if not user:
        print("⚠️  No user found, creating test user...")
        user = User.objects.create_user(username='diagnostic_user', password='test123')
    request.user = user
    
    response = fiber_route_builder_view(request)
    html = response.content.decode('utf-8')
    
    # Search for Google Maps script tag
    import re
    match = re.search(r'maps\.googleapis\.com/maps/api/js\?key=([^"&\s]+)', html)
    
    if match:
        key_in_html = match.group(1)
        if key_in_html:
            print(f"✅ Key in HTML: {key_in_html[:20]}...{key_in_html[-6:]} (length: {len(key_in_html)})")
        else:
            print("❌ Key parameter is EMPTY in HTML")
    else:
        print("❌ Google Maps script tag NOT FOUND in rendered HTML")
        # Show snippet for debugging
        snippet_start = html.find('maps.googleapis')
        if snippet_start > 0:
            snippet = html[snippet_start:snippet_start+100]
            print(f"   Found partial: {snippet}")
        
except Exception as e:
    print(f"❌ ERROR testing view: {e}")
    import traceback
    traceback.print_exc()
print()

# Summary
print("=" * 80)
print("📋 SUMMARY")
print("=" * 80)
has_db = config_db and config_db.maps_api_key
has_runtime = config_runtime and config_runtime.google_maps_api_key
has_settings = bool(getattr(settings, 'GOOGLE_MAPS_API_KEY', ''))
has_html = match and match.group(1) if 'match' in locals() else False

if all([has_db, has_runtime, has_html]):
    print("✅ ALL LAYERS OK - Google Maps API Key is properly configured")
else:
    print("❌ CONFIGURATION ISSUE DETECTED:")
    if not has_db:
        print("   ❌ Database: Key not saved in FirstTimeSetup")
    if not has_runtime:
        print("   ❌ Runtime Settings: Key not loaded by service layer")
    if not has_html:
        print("   ❌ View/Template: Key not injected into HTML")
    if not has_settings:
        print("   ℹ️  .env file: Key not set (OK if using setup_app)")

print()
print("=" * 80)
