#!/usr/bin/env python
"""
Test script to validate Google Maps API Key is being passed to routes_builder template
"""
import django
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from routes_builder.views import fiber_route_builder_view
from django.test import RequestFactory
from django.contrib.auth.models import User
import re

# Create mock request
factory = RequestFactory()
request = factory.get('/routes/fiber-route-builder/')

# Get or create a test user
user = User.objects.first()
if not user:
    user = User.objects.create_user(username='testuser', password='testpass')
request.user = user

# Call the view
try:
    response = fiber_route_builder_view(request)
    html = response.content.decode('utf-8')
    
    # Extract Google Maps URL
    match = re.search(r'maps\.googleapis\.com/maps/api/js\?key=([^"&]+)', html)
    
    if match:
        key = match.group(1)
        print(f"✅ SUCCESS: Google Maps API Key found in HTML")
        print(f"   Key: {key[:20]}...{key[-4:]}")
        print(f"   Length: {len(key)} characters")
        sys.exit(0)
    else:
        print("❌ FAILED: Google Maps URL not found or key is empty")
        print("   Searching for: maps.googleapis.com/maps/api/js?key=")
        # Print first 500 chars to debug
        print(f"   HTML snippet: {html[:500]}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
