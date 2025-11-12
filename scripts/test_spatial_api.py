#!/usr/bin/env python
"""Test script for PostGIS spatial API endpoints."""
import os
import sys

# Setup Django
sys.path.insert(0, '/app/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings.dev'

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

# Create test client
client = Client()

# Login
user = get_user_model().objects.get(username='testuser')
client.force_login(user)

# Test spatial endpoint without bbox
print("Testing /api/v1/inventory/segments/ (no bbox)...")
response = client.get('/api/v1/inventory/segments/')
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.get('Content-Type', 'not set')}")

if response.status_code == 200:
    import json
    try:
        data = json.loads(response.content)
        print(f"Response keys: {list(data.keys())}")
        print(f"Total segments: {data.get('count', 'N/A')}")
        if 'segments' in data and data['segments']:
            print(f"First segment: {data['segments'][0]}")
    except:
        print(f"Content (first 500 chars): {response.content[:500]}")
else:
    print(f"Error: {response.content[:300]}")

# Test with bbox
print("\nTesting with BBox (-48,-16,-47.5,-15.5)...")
response = client.get('/api/v1/inventory/segments/?bbox=-48,-16,-47.5,-15.5')
print(f"Status: {response.status_code}")

if response.status_code == 200:
    try:
        data = json.loads(response.content)
        print(f"Filtered segments: {data.get('count', 'N/A')}")
    except:
        print(f"Content: {response.content[:300]}")
else:
    print(f"Error: {response.content[:300]}")
