#!/usr/bin/env python
"""Verificar fusões em uma CEO específica"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import FiberInfrastructure, FiberFusion, FiberCable

# CEO-2888 (ID 98)
try:
    ceo = FiberInfrastructure.objects.get(id=98)
    print(f"\n=== CEO: {ceo.name} (ID {ceo.id}) ===\n")
    
    # Listar fusões
    fusions = FiberFusion.objects.filter(infrastructure=ceo).select_related(
        'fiber_a__tube__cable', 'fiber_b__tube__cable'
    )
    print(f"Fusões totais: {fusions.count()}\n")
    
    for f in fusions:
        cable_a = f.fiber_a.tube.cable
        cable_b = f.fiber_b.tube.cable
        same_cable = cable_a.id == cable_b.id
        
        print(f"Fusão #{f.id}:")
        print(f"  FO{f.fiber_a.number} ({f.fiber_a.color}) - Cabo: {cable_a.name} (ID {cable_a.id})")
        print(f"  ↔")
        print(f"  FO{f.fiber_b.number} ({f.fiber_b.color}) - Cabo: {cable_b.name} (ID {cable_b.id})")
        print(f"  Mesmo cabo: {'SIM' if same_cable else 'NÃO'}")
        print()
    
    # Listar cabos nesta CEO
    cable = ceo.cable
    if cable:
        print(f"\n=== Cabo Principal: {cable.name} (ID {cable.id}) ===")
        print(f"Total de fibras: {sum(tube.strands.count() for tube in cable.tubes.all())}")
        
        # Contar fibras COM e SEM fusão
        all_strands = []
        for tube in cable.tubes.all():
            for strand in tube.strands.all():
                all_strands.append(strand)
        
        fused_fiber_ids = set()
        for f in fusions:
            if f.fiber_a.tube.cable_id == cable.id:
                fused_fiber_ids.add(f.fiber_a.id)
            if f.fiber_b.tube.cable_id == cable.id:
                fused_fiber_ids.add(f.fiber_b.id)
        
        print(f"Fibras COM fusão: {len(fused_fiber_ids)}")
        print(f"Fibras SEM fusão: {len(all_strands) - len(fused_fiber_ids)}")
        
        print("\nFibras COM fusão:")
        for strand_id in sorted(fused_fiber_ids):
            strand = next(s for s in all_strands if s.id == strand_id)
            print(f"  - FO{strand.number} ({strand.color})")
        
        print("\nFibras SEM fusão:")
        for strand in all_strands:
            if strand.id not in fused_fiber_ids:
                print(f"  - FO{strand.number} ({strand.color})")

except FiberInfrastructure.DoesNotExist:
    print("CEO-2888 (ID 98) não encontrada!")
except Exception as e:
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
