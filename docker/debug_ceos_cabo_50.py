#!/usr/bin/env python
"""
Investiga como as CEOs do cabo 50 estão anexadas e quais fibras deveriam aparecer.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import (
    FiberCable, 
    FiberInfrastructure,
    CableSegment,
    InfrastructureCableAttachment,
    FiberStrand
)

cable = FiberCable.objects.get(id=50)
print(f"=== Cabo: {cable.name} (ID: {cable.id}) ===\n")

# Get all CEOs for this cable
ceos = FiberInfrastructure.objects.filter(
    cable=cable,
    type='splice_box'
).order_by('distance_from_origin')

print(f"📦 CEOs encontradas: {ceos.count()}\n")

for ceo in ceos:
    print(f"\n{'='*80}")
    print(f"CEO: {ceo.name} (ID: {ceo.id})")
    print(f"Distância: {ceo.distance_from_origin:.2f}m")
    print(f"{'='*80}")
    
    # Check CableSegments
    print("\n1️⃣  CABLE SEGMENTS:")
    segs_entrada = CableSegment.objects.filter(end_infrastructure=ceo)
    segs_saida = CableSegment.objects.filter(start_infrastructure=ceo)
    print(f"   Entrada: {segs_entrada.count()} segmentos")
    for seg in segs_entrada:
        print(f"      - Segmento #{seg.segment_number}: {seg.name}")
    print(f"   Saída: {segs_saida.count()} segmentos")
    for seg in segs_saida:
        print(f"      - Segmento #{seg.segment_number}: {seg.name}")
    
    # Check Attachments
    print("\n2️⃣  ATTACHMENTS (Fallback):")
    atts = InfrastructureCableAttachment.objects.filter(infrastructure=ceo)
    print(f"   Total: {atts.count()} attachments")
    for att in atts:
        print(f"      - {att.cable.name} (ID: {att.cable_id}) - {att.get_port_type_display()}")
    
    # Check if it's on the cable
    print("\n3️⃣  CABO PROPRIETÁRIO:")
    if ceo.cable_id == cable.id:
        print(f"   ✓ CEO pertence ao cabo {cable.name}")
    else:
        print(f"   ✗ CEO pertence a outro cabo (ID: {ceo.cable_id})")
    
    # Count strands
    total_strands = FiberStrand.objects.filter(tube__cable=cable).count()
    print(f"\n📊 FIBRAS DO CABO:")
    print(f"   Total de fibras no cabo: {total_strands}")
    
    # Check fusões
    fusoes = FiberStrand.objects.filter(
        tube__cable=cable,
        fusion_infrastructure=ceo
    ).count()
    print(f"   Fusões nesta CEO: {fusoes}")

print("\n" + "="*80)
print("RESUMO GERAL")
print("="*80)
print(f"Total de tubos: {cable.tubes.count()}")
print(f"Total de fibras: {FiberStrand.objects.filter(tube__cable=cable).count()}")
print(f"Profile: {cable.profile.name if cable.profile else 'SEM PROFILE'}")
if cable.profile:
    print(f"   - {cable.profile.total_fibers} fibras esperadas")
    print(f"   - {cable.profile.tube_count} tubos")
    print(f"   - {cable.profile.fibers_per_tube} fibras/tubo")
