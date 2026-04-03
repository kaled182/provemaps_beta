#!/usr/bin/env python
"""
Test CEO creation flow exactly as frontend does it.
Simulates the JavaScript flow in FiberRouteEditor.vue
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, "/app")
django.setup()

from inventory.models import FiberCable, FiberInfrastructure, InfrastructureCableAttachment
from inventory.api.infrastructure import api_create_infrastructure
from inventory.api.cable_attachment import CableAttachmentViewSet
from django.test import RequestFactory
from rest_framework.test import force_authenticate
from django.contrib.auth import get_user_model

User = get_user_model()

print("=== Testing Frontend CEO Flow ===\n")

# Get test cable
cable = FiberCable.objects.filter(path__isnull=False).first()
if not cable:
    print("❌ No cables with path found")
    sys.exit(1)

print(f"✓ Using cable: {cable.name} (ID: {cable.id})")
print(f"  Path has {len(cable.path.coords)} points")

# Get midpoint for CEO placement
coords = list(cable.path.coords)
mid_idx = len(coords) // 2
mid_lng, mid_lat = coords[mid_idx]

print(f"  Midpoint: lat={mid_lat}, lng={mid_lng}\n")

# Step 1: Create CEO via POST /api/v1/inventory/infrastructure/
print("Step 1: Creating CEO...")
factory = RequestFactory()
user = User.objects.first()

# Simulate POST request
request = factory.post('/api/v1/inventory/infrastructure/', {
    'cable': cable.id,
    'type': 'splice_box',
    'name': f'CEO-Frontend-Test-{cable.id}',
    'lat': mid_lat,
    'lng': mid_lng,
    'metadata': {}
})
force_authenticate(request, user=user)

try:
    response = api_create_infrastructure(request)
    if response.status_code == 201:
        ceo_data = response.data
        ceo_id = ceo_data['id']
        print(f"  ✓ CEO created: {ceo_data['name']} (ID: {ceo_id})")
        print(f"    Location: {ceo_data['location']}")
        print(f"    Distance from origin: {ceo_data.get('distance_from_origin', 'N/A')}m")
    else:
        print(f"  ❌ CEO creation failed: {response.status_code}")
        print(f"    Response: {response.data}")
        sys.exit(1)
except Exception as e:
    print(f"  ❌ Exception creating CEO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Attach cable to CEO via POST /api/v1/inventory/cable-attachments/attach/
print("\nStep 2: Attaching cable to CEO...")
request = factory.post('/api/v1/inventory/cable-attachments/attach/', {
    'cable_id': cable.id,
    'infrastructure_id': ceo_id,
    'port_type': 'oval',
    'is_pass_through': True
})
force_authenticate(request, user=user)

viewset = CableAttachmentViewSet()
viewset.format_kwarg = None

try:
    response = viewset.attach(request)
    if response.status_code == 200:
        attach_data = response.data
        print(f"  ✓ Cable attached: {attach_data}")
    else:
        print(f"  ❌ Attachment failed: {response.status_code}")
        print(f"    Response: {response.data}")
        sys.exit(1)
except Exception as e:
    print(f"  ❌ Exception attaching cable: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Verify attachment exists
print("\nStep 3: Verifying attachment...")
attachments = InfrastructureCableAttachment.objects.filter(
    cable=cable,
    infrastructure_id=ceo_id
)
print(f"  ✓ Found {attachments.count()} attachment(s)")
for att in attachments:
    print(f"    ID={att.id}, port_type={att.port_type}, pass_through={att.is_pass_through}")

print("\n" + "="*50)
print("Result: ✓ FRONTEND FLOW SUCCESS")
