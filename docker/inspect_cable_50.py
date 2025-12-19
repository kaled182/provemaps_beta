#!/usr/bin/env python
"""Quick diagnostic script for cable 50 deletion blockers."""
import django
import os
import sys

sys.path.insert(0, '/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from inventory.models import FiberCable, FiberInfrastructure, CableSegment
from django.db.models import Q

try:
    cable = FiberCable.objects.get(id=50)
    print(f"Cable {cable.id}: {cable.name}")
    
    infras = list(FiberInfrastructure.objects.filter(cable=cable).values_list('id', flat=True))
    print(f"Infrastructures owned by cable 50: {infras}")
    
    if infras:
        ext_segs = CableSegment.objects.filter(
            Q(start_infrastructure_id__in=infras) | Q(end_infrastructure_id__in=infras)
        )
        print(f"\nTotal segments referencing these infrastructures: {ext_segs.count()}")
        for seg in ext_segs:
            print(f"  Segment {seg.id}: cable_id={seg.cable_id}, segment_number={seg.segment_number}")
            print(f"    start_infrastructure={seg.start_infrastructure_id}, end_infrastructure={seg.end_infrastructure_id}")
    
    # Check for other relations that might block
    print(f"\nBuffer tubes: {cable.tubes.count()}")
    print(f"Events: {cable.events.count()}")
    print(f"Attachments: {cable.attachments.count()}")
    
    # Try to identify the actual blocker by attempting delete with verbose error
    print("\n--- Attempting delete to capture error ---")
    try:
        cable.delete()
        print("SUCCESS: Cable deleted without error")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        
except FiberCable.DoesNotExist:
    print("Cable 50 not found")
except Exception as e:
    print(f"Unexpected error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
