#!/usr/bin/env python
"""
Verifica os attachments duplicados na CEO-2098 (ID 25).
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import (
    FiberInfrastructure,
    InfrastructureCableAttachment,
    CableSegment
)

ceo = FiberInfrastructure.objects.get(id=25)  # CEO-2098
print(f"=== {ceo.name} (ID: {ceo.id}) ===\n")

# Check segments
segs_in = CableSegment.objects.filter(end_infrastructure=ceo)
segs_out = CableSegment.objects.filter(start_infrastructure=ceo)

print("SEGMENTOS:")
print(f"  Entrada: {segs_in.count()}")
for s in segs_in:
    print(f"    - Seg#{s.segment_number}: {s.name} (cabo {s.cable_id})")

print(f"  Saída: {segs_out.count()}")
for s in segs_out:
    print(f"    - Seg#{s.segment_number}: {s.name} (cabo {s.cable_id})")

# Check attachments
atts = InfrastructureCableAttachment.objects.filter(infrastructure=ceo)
print(f"\nATTACHMENTS: {atts.count()}")
for a in atts:
    print(f"  - ID {a.id}: Cabo {a.cable_id} ({a.cable.name})")
    print(f"    Port: {a.get_port_type_display()}")
    print(f"    Pass-through: {a.is_pass_through}")

print("\n=== PROBLEMA ===")
print("Múltiplos attachments do MESMO cabo causam duplicação na UI!")
print("Solução: Usar APENAS segmentos, deletar attachments obsoletos.")

# Show deletion commands
if atts.exists():
    print(f"\n=== CORREÇÃO ===")
    print(f"InfrastructureCableAttachment.objects.filter(infrastructure_id={ceo.id}).delete()")
