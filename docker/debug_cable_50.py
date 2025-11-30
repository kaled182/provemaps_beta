#!/usr/bin/env python
"""Debug script for cable 50 fiber allocation issues."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import FiberCable, FiberInfrastructure, FiberProfile

# Get cable 50
cable = FiberCable.objects.get(id=50)
print(f"=== Cabo: {cable.name} (ID: {cable.id}) ===")
print(f"Profile: {cable.profile}")

if cable.profile:
    print(f"Total fibers: {cable.profile.total_fibers}")
    print(f"Tube count: {cable.profile.tube_count}")
    print(f"Fibers per tube: {cable.profile.fibers_per_tube}")
else:
    print("ERRO: Cabo sem profile!")

# Get infrastructure points
infras = FiberInfrastructure.objects.filter(cable=cable).order_by('distance_from_origin')
print(f"\n=== Infraestrutura ({infras.count()} pontos) ===")
for infra in infras:
    print(f"\nID: {infra.id} - {infra.name}")
    print(f"  Tipo: {infra.get_type_display()}")
    print(f"  Distância: {infra.distance_from_origin:.2f}m")
    print(f"  Metadata: {infra.metadata}")
    
    # Check fiber allocations if in metadata
    if infra.metadata:
        if 'fiber_allocations' in infra.metadata:
            allocations = infra.metadata['fiber_allocations']
            print(f"  Fibras alocadas: {len(allocations)}")
            
            # Count by status
            from collections import Counter
            statuses = Counter([f['status'] for f in allocations])
            print(f"  Status breakdown: {dict(statuses)}")
            
            # Show first few allocations
            print("  Primeiras alocações:")
            for i, alloc in enumerate(allocations[:5]):
                print(f"    Tubo {alloc.get('tube')}, Fibra {alloc.get('fiber')}: {alloc.get('status')} - {alloc.get('label', 'sem label')}")
        else:
            print("  SEM fiber_allocations no metadata!")

print("\n=== Verificação do Profile ===")
if cable.profile:
    expected_fibers = cable.profile.total_fibers
    print(f"Fibras esperadas: {expected_fibers}")
    
    # Check each infrastructure
    for infra in infras:
        if infra.metadata and 'fiber_allocations' in infra.metadata:
            actual = len(infra.metadata['fiber_allocations'])
            print(f"{infra.name}: {actual}/{expected_fibers} fibras {'✓' if actual == expected_fibers else '✗ ERRO'}")
