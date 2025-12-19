#!/usr/bin/env python
"""
Teste completo da API de infraestrutura simulando exatamente o frontend.
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, "/app")
django.setup()

import json
from django.test.client import Client
from django.contrib.auth import get_user_model
from inventory.models import FiberCable

User = get_user_model()

print("=== Test API Infrastructure Endpoint ===\n")

# Create authenticated client
client = Client()
user = User.objects.first()
if not user:
    print("❌ No user found")
    sys.exit(1)

client.force_login(user)
print(f"✓ Logged in as: {user.username}\n")

# Get test cable
cable = FiberCable.objects.filter(path__isnull=False).first()
if not cable:
    print("❌ No cables with path found")
    sys.exit(1)

print(f"✓ Using cable: {cable.name} (ID: {cable.id})")

# Get midpoint
coords = list(cable.path.coords)
mid_idx = len(coords) // 2
mid_lng, mid_lat = coords[mid_idx]

print(f"  Midpoint: lat={mid_lat}, lng={mid_lng}\n")

# Test 1: POST to create CEO
print("Test 1: Creating CEO via API...")
payload = {
    "cable": cable.id,
    "type": "splice_box",
    "name": f"CEO-API-TEST-{cable.id}",
    "lat": mid_lat,
    "lng": mid_lng,
    "metadata": {}
}

print(f"  Payload: {json.dumps(payload, indent=2)}")

response = client.post(
    '/api/v1/inventory/infrastructure/',
    data=json.dumps(payload),
    content_type='application/json'
)

print(f"\n  Response status: {response.status_code}")

if response.status_code == 201:
    data = response.json()
    print(f"  ✓ CEO created: {data['name']} (ID: {data['id']})")
    print(f"    Location: {data['location']}")
    print(f"    Distance from origin: {data.get('distance_from_origin', 'N/A')}m")
    
    # Test 2: Attach cable
    print("\nTest 2: Attaching cable to CEO...")
    attach_payload = {
        "cable_id": cable.id,
        "infrastructure_id": data['id'],
        "port_type": "oval",
        "is_pass_through": True
    }
    
    attach_response = client.post(
        '/api/v1/inventory/cable-attachments/attach/',
        data=json.dumps(attach_payload),
        content_type='application/json'
    )
    
    print(f"  Response status: {attach_response.status_code}")
    
    if attach_response.status_code == 200:
        attach_data = attach_response.json()
        print(f"  ✓ Cable attached: {attach_data}")
        print("\n" + "="*50)
        print("Result: ✓ API TEST SUCCESS")
    else:
        print(f"  ❌ Attachment failed")
        print(f"  Response: {attach_response.content.decode()}")
        sys.exit(1)
else:
    print(f"  ❌ CEO creation failed")
    print(f"  Response: {response.content.decode()}")
    sys.exit(1)
