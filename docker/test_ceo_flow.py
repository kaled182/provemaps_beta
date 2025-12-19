#!/usr/bin/env python
"""Test CEO creation and cable attachment flow."""
import django
import os
import sys

sys.path.insert(0, '/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from inventory.models import FiberCable, FiberInfrastructure, InfrastructureCableAttachment
from django.contrib.gis.geos import Point

def test_ceo_creation_and_attachment():
    """Test creating a CEO and attaching a cable."""
    
    # Find a cable with path geometry
    cables_with_path = FiberCable.objects.exclude(path__isnull=True)
    
    if not cables_with_path.exists():
        print("❌ No cables with path geometry found!")
        return
    
    cable = cables_with_path.first()
    print(f"✓ Testing with cable: {cable.name} (ID: {cable.id})")
    print(f"  Path points: {len(cable.path.coords) if cable.path else 0}")
    print(f"  Length: {cable.length_km} km")
    
    # Get a point on the cable path (midpoint)
    if cable.path and len(cable.path.coords) >= 2:
        mid_idx = len(cable.path.coords) // 2
        lng, lat = cable.path.coords[mid_idx]
        print(f"  Mid-point: lat={lat}, lng={lng}")
        
        # 1. Simulate creating CEO via API
        test_point = Point(lng, lat, srid=4326)
        
        # Check if CEO already exists at this location
        existing = FiberInfrastructure.objects.filter(
            cable=cable,
            type='splice_box',
            location__distance_lte=(test_point, 10)  # Within 10 meters
        ).first()
        
        if existing:
            print(f"  ℹ CEO already exists: {existing.name} (ID: {existing.id})")
            ceo = existing
        else:
            # Create new CEO
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        ST_LineLocatePoint(
                            path,
                            ST_ClosestPoint(path, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                        ) as fraction,
                        ST_Length(path::geography) as cable_length_meters
                    FROM zabbix_api_fibercable
                    WHERE id = %s
                    """,
                    [lng, lat, cable.id]
                )
                row = cursor.fetchone()
                if row:
                    fraction = float(row[0])
                    total_meters = float(row[1])
                    distance_from_origin = fraction * total_meters
                else:
                    distance_from_origin = 0.0
            
            ceo = FiberInfrastructure.objects.create(
                cable=cable,
                type='splice_box',
                name=f'CEO-TEST-{cable.id}',
                location=test_point,
                distance_from_origin=distance_from_origin,
                metadata={}
            )
            print(f"  ✓ CEO created: {ceo.name} (ID: {ceo.id}) at {distance_from_origin:.1f}m")
        
        # 2. Try to attach cable
        try:
            attachment, created = InfrastructureCableAttachment.objects.update_or_create(
                infrastructure=ceo,
                cable=cable,
                port_type='oval',
                defaults={'is_pass_through': True}
            )
            
            status = "created" if created else "already existed"
            print(f"  ✓ Cable attachment {status}: ID={attachment.id}")
            print(f"    Port type: {attachment.port_type}")
            print(f"    Pass-through: {attachment.is_pass_through}")
            
            # Verify attachment
            verify = InfrastructureCableAttachment.objects.filter(
                infrastructure=ceo,
                cable=cable
            ).count()
            print(f"  ✓ Verification: {verify} attachment(s) found")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error creating attachment: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("  ❌ Cable has insufficient path points")
        return False


if __name__ == '__main__':
    print("=== Testing CEO Creation and Cable Attachment ===\n")
    try:
        success = test_ceo_creation_and_attachment()
        print("\n" + ("="*50))
        print("Result:", "✓ SUCCESS" if success else "✗ FAILED")
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
