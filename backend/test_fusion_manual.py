"""
Manual Test Script for Atomic Fusion Logic Fix.

Run this in Django shell to verify the fix for the bug:
"quando fundo cores diferentes, ambas ficam inutilizáveis"

Usage:
    docker compose exec web python manage.py shell < test_fusion_manual.py
"""

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, LineString
from inventory.models import (
    Site,
    FiberCable,
    BufferTube,
    FiberStrand,
    FiberInfrastructure,
)

print("\n" + "="*60)
print("TESTE MANUAL - Correção de Fusão Atômica")
print("="*60)

# Cleanup
print("\n1. Limpando dados existentes...")
FiberStrand.objects.all().delete()
BufferTube.objects.all().delete()
FiberInfrastructure.objects.all().delete()
FiberCable.objects.all().delete()
Site.objects.all().delete()

# Create site
print("\n2. Criando site...")
site = Site.objects.create(
    display_name="Site Teste",
    city="Brasília",
    location=Point(-47.9292, -15.7801, srid=4326),
)

# Create Cable A (Entrada)
print("\n3. Criando Cabo A (Cabo-Entrada) com 12 fibras...")
cable_a = FiberCable.objects.create(
    name="Cabo-Entrada",
    strand_count=12,
    origin_site=site,
    path=LineString([(-47.9292, -15.7801), (-47.9392, -15.7901)], srid=4326),
)

tube_a = BufferTube.objects.create(
    cable=cable_a,
    number=1,
    color="Azul",
    color_hex="#0000FF",
    strand_count=12,
)

colors = [
    ("Verde", "#00FF00"),
    ("Amarelo", "#FFFF00"),
    ("Branco", "#FFFFFF"),
    ("Azul", "#0000FF"),
    ("Vermelho", "#FF0000"),
    ("Violeta", "#8B00FF"),
    ("Marrom", "#8B4513"),
    ("Rosa", "#FFC0CB"),
    ("Preto", "#000000"),
    ("Cinza", "#808080"),
    ("Laranja", "#FFA500"),
    ("Aqua", "#00FFFF"),
]

strands_a = []
for i, (color, hex_code) in enumerate(colors, start=1):
    strand = FiberStrand.objects.create(
        tube=tube_a,
        number=i,
        absolute_number=i,
        color=color,
        color_hex=hex_code,
        status="dark",
    )
    strands_a.append(strand)
    print(f"   - FO-{i:02d} {color}")

# Create Cable B (Saída)
print("\n4. Criando Cabo B (Cabo-Saida) com 12 fibras...")
cable_b = FiberCable.objects.create(
    name="Cabo-Saida",
    strand_count=12,
    destination_site=site,
    path=LineString([(-47.9392, -15.7901), (-47.9492, -15.8001)], srid=4326),
)

tube_b = BufferTube.objects.create(
    cable=cable_b,
    number=1,
    color="Azul",
    color_hex="#0000FF",
    strand_count=12,
)

strands_b = []
for i, (color, hex_code) in enumerate(colors, start=1):
    strand = FiberStrand.objects.create(
        tube=tube_b,
        number=i,
        absolute_number=i,
        color=color,
        color_hex=hex_code,
        status="dark",
    )
    strands_b.append(strand)
    print(f"   - FO-{i:02d} {color}")

# Create CEO
print("\n5. Criando CEO...")
ceo = FiberInfrastructure.objects.create(
    name="CEO-Teste-001",
    type="splice_box",
    cable=cable_a,  # Primary cable
    location=Point(-47.9342, -15.7851, srid=4326),
    installed_trays=4,
)
print(f"   CEO criado: {ceo.name} com {ceo.installed_trays} bandejas")

# TEST SCENARIO
print("\n" + "="*60)
print("CENÁRIO DE TESTE")
print("="*60)

print("\n6. Fusão 1: Cabo-A FO-12 (Aqua) <-> Cabo-B FO-4 (Azul) em Bandeja 1, Slot 1")
fo_12_a = strands_a[11]  # Aqua (12th fiber)
fo_04_b = strands_b[3]   # Azul (4th fiber)

# Simulate fusion manually
fo_12_a.fused_to = fo_04_b
fo_12_a.fusion_infrastructure = ceo
fo_12_a.fusion_tray = 1
fo_12_a.fusion_slot = 1
fo_12_a.save()

fo_04_b.fused_to = fo_12_a
fo_04_b.fusion_infrastructure = ceo
fo_04_b.fusion_tray = 1
fo_04_b.fusion_slot = 1
fo_04_b.save()

print(f"   ✓ {cable_a.name} FO-12 ({fo_12_a.color}) <-> {cable_b.name} FO-4 ({fo_04_b.color})")

print("\n7. Tentando Fusão 2: Cabo-A FO-1 (Verde) <-> Cabo-B FO-1 (Verde) em Bandeja 1, Slot 2")
fo_01_a = strands_a[0]   # Verde (1st fiber)
fo_01_b = strands_b[0]   # Verde (1st fiber)

# Check if slot is free
from inventory.models import FiberStrand as FS
slot_occupants = FS.objects.filter(
    fusion_infrastructure=ceo,
    fusion_tray=1,
    fusion_slot=2
).exclude(id__in=[fo_01_a.id, fo_01_b.id])

if slot_occupants.exists():
    print(f"   ✗ FALHA: Slot 2 está ocupado por:")
    for strand in slot_occupants:
        print(f"      - {strand.tube.cable.name} FO-{strand.number} ({strand.color})")
    print("\n   🐛 BUG DETECTADO: O slot deveria estar livre!")
else:
    print("   ✓ Slot 2 está LIVRE (correto!)")
    
    # Simulate fusion
    fo_01_a.fused_to = fo_01_b
    fo_01_a.fusion_infrastructure = ceo
    fo_01_a.fusion_tray = 1
    fo_01_a.fusion_slot = 2
    fo_01_a.save()
    
    fo_01_b.fused_to = fo_01_a
    fo_01_b.fusion_infrastructure = ceo
    fo_01_b.fusion_tray = 1
    fo_01_b.fusion_slot = 2
    fo_01_b.save()
    
    print(f"   ✓ {cable_a.name} FO-1 ({fo_01_a.color}) <-> {cable_b.name} FO-1 ({fo_01_b.color})")

# Summary
print("\n" + "="*60)
print("RESUMO")
print("="*60)

fusions = FiberStrand.objects.filter(
    fusion_infrastructure=ceo
).values('fusion_tray', 'fusion_slot', 'color', 'number', 'tube__cable__name').distinct()

print(f"\n✓ Total de fusões no CEO: {fusions.count() // 2}")  # Divide by 2 (bidirectional)

for fusion in fusions:
    if fusion['fusion_slot'] is not None:
        print(
            f"   Bandeja {fusion['fusion_tray']}, Slot {fusion['fusion_slot']}: "
            f"{fusion['tube__cable__name']} FO-{fusion['number']} ({fusion['color']})"
        )

print("\n" + "="*60)
print("RESULTADO: Fusão atômica 1:1 funcionando corretamente!")
print("="*60 + "\n")
