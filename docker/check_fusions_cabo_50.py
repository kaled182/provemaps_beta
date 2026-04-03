#!/usr/bin/env python
"""
Verifica fusões incorretas no cabo 50.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import FiberStrand, FiberInfrastructure

cable_id = 50

print("="*80)
print("VERIFICAÇÃO DE FUSÕES NO CABO 50")
print("="*80)

# Get all strands from cable 50
strands = FiberStrand.objects.filter(tube__cable_id=cable_id).select_related(
    'fused_to', 'fusion_infrastructure'
)

total = strands.count()
fusionadas = strands.filter(fused_to__isnull=False).count()

print(f"\nTotal de fibras: {total}")
print(f"Fibras fusionadas: {fusionadas}")
print(f"Fibras livres: {total - fusionadas}")

if fusionadas > 0:
    print("\n" + "="*80)
    print("FUSÕES ENCONTRADAS")
    print("="*80)
    
    for strand in strands.filter(fused_to__isnull=False):
        print(f"\nFibra #{strand.absolute_number} (Tubo {strand.tube.number}, Fibra {strand.number})")
        print(f"   Cor: {strand.color}")
        print(f"   Fusionada com: Fibra #{strand.fused_to.absolute_number if strand.fused_to else 'N/A'}")
        print(f"   CEO: {strand.fusion_infrastructure.name if strand.fusion_infrastructure else 'N/A'}")
        print(f"   Bandeja/Slot: {strand.fusion_tray}/{strand.fusion_slot}")

# Check for "orphan" fusion metadata (fused but no pair)
print("\n" + "="*80)
print("INCONSISTÊNCIAS")
print("="*80)

orphans = strands.filter(fused_to__isnull=True, fusion_infrastructure__isnull=False)
if orphans.exists():
    print(f"\n❌ ERRO: {orphans.count()} fibras com CEO mas sem par de fusão:")
    for strand in orphans:
        print(f"   Fibra #{strand.absolute_number}: CEO {strand.fusion_infrastructure.name}")
else:
    print("\n✓ Sem fibras órfãs (CEO sem par)")

# Check for fused without CEO
no_ceo = strands.filter(fused_to__isnull=False, fusion_infrastructure__isnull=True)
if no_ceo.exists():
    print(f"\n❌ ERRO: {no_ceo.count()} fibras fusionadas mas sem CEO:")
    for strand in no_ceo:
        print(f"   Fibra #{strand.absolute_number} fusionada com #{strand.fused_to.absolute_number}")
else:
    print("✓ Todas as fusões têm CEO definida")

# Check for mismatched pairs
print("\n" + "="*80)
print("VALIDAÇÃO DE PARES BIDIRECIONAIS")
print("="*80)

mismatches = 0
for strand in strands.filter(fused_to__isnull=False):
    pair = strand.fused_to
    if pair and pair.fused_to_id != strand.id:
        print(f"❌ Par inconsistente: Fibra #{strand.absolute_number} → #{pair.absolute_number}, mas reverso aponta para #{pair.fused_to.absolute_number if pair.fused_to else 'NULL'}")
        mismatches += 1

if mismatches == 0:
    print("✓ Todos os pares estão bidirecionalmente consistentes")
else:
    print(f"\n❌ TOTAL: {mismatches} pares inconsistentes")
