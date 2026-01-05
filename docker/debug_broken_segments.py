#!/usr/bin/env python
"""Debug script para ver dados reais dos segmentos BROKEN"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import FiberCable, CableSegment
from inventory.serializers import CableSegmentSerializer
import json

# Buscar cabo "teste" que tem 13 rompimentos
cable = FiberCable.objects.filter(name__icontains='teste').first()
if cable:
    print(f"Cabo: {cable.name} (ID: {cable.id})")
    segments = cable.segments.filter(status='broken')
    print(f"Segmentos BROKEN: {segments.count()}")
    
    if segments.exists():
        seg = segments.first()
        print(f"\nPrimeiro segmento BROKEN:")
        print(f"  - Nome: {seg.name}")
        print(f"  - Status: {seg.status}")
        print(f"  - start_infrastructure: {seg.start_infrastructure}")
        print(f"  - end_infrastructure: {seg.end_infrastructure}")
        
        # Serializar para ver o JSON completo
        serializer = CableSegmentSerializer(seg)
        print(f"\nJSON Serializado:")
        print(json.dumps(serializer.data, indent=2, default=str))
else:
    print("Cabo 'teste' não encontrado")
    print("\nCabos disponíveis:")
    for c in FiberCable.objects.all()[:5]:
        segs = c.segments.filter(status='broken').count()
        print(f"  - {c.name} (ID: {c.id}) - {segs} BROKEN")
