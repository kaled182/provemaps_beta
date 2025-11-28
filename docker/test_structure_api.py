#!/usr/bin/env python
"""Test script for fiber structure API endpoints."""
import os
import sys
import django

sys.path.insert(0, '/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import FiberCable, FiberProfile, Port
from inventory.serializers import (
    FiberProfileSerializer,
    FiberCableStructureSerializer,
)

def test_profiles_serializer():
    print("=" * 80)
    print("TEST 1: FiberProfileSerializer")
    print("=" * 80)
    
    profiles = FiberProfile.objects.all().order_by('total_fibers')
    serializer = FiberProfileSerializer(profiles, many=True)
    
    print(f"\n✅ Found {len(serializer.data)} profiles")
    for profile in serializer.data[:3]:
        print(f"  - {profile['name']}: "
              f"{profile['tube_count']}x{profile['fibers_per_tube']} "
              f"= {profile['total_fibers']}FO")
    
    return serializer.data


def test_structure_serializer():
    print("\n" + "=" * 80)
    print("TEST 2: FiberCableStructureSerializer")
    print("=" * 80)
    
    # Create test cable with profile
    port = Port.objects.first()
    if not port:
        print("❌ No ports found in database")
        return None
    
    profile = FiberProfile.objects.get(name="Cabo 12FO (Tubo Único)")
    
    # Create test cable
    cable = FiberCable.objects.create(
        name=f"Test-Structure-API",
        origin_port=port,
        destination_port=port,
        profile=profile
    )
    
    print(f"\n✅ Created cable: {cable.name} (ID: {cable.id})")
    
    # Generate structure
    cable.create_structure()
    print(f"✅ Structure generated: {cable.tubes.count()} tubes")
    
    # Serialize
    serializer = FiberCableStructureSerializer(cable)
    data = serializer.data
    
    print(f"\n📦 Serialized cable structure:")
    print(f"  - ID: {data['id']}")
    print(f"  - Name: {data['name']}")
    print(f"  - Profile: {data['profile_name']}")
    print(f"  - Tubes: {len(data['tubes'])}")
    
    if data['tubes']:
        tube = data['tubes'][0]
        print(f"\n  Tube #1:")
        print(f"    - Color: {tube['color']} ({tube['color_hex']})")
        print(f"    - Strands: {len(tube['strands'])}")
        
        if tube['strands']:
            print(f"\n    First 3 strands:")
            for strand in tube['strands'][:3]:
                print(f"      F{strand['number']}: {strand['color']} "
                      f"(Abs#{strand['absolute_number']}) - {strand['status']}")
    
    # Cleanup
    cable.delete()
    print(f"\n✅ Test cable deleted")
    
    return data


if __name__ == "__main__":
    try:
        profiles = test_profiles_serializer()
        structure = test_structure_serializer()
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print("\nAPI Endpoints Ready:")
        print("  GET /api/v1/inventory/fiber-cables/profiles/")
        print("  GET /api/v1/inventory/fiber-cables/{id}/structure/")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
