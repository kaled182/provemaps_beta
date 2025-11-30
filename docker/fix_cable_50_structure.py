#!/usr/bin/env python
"""
Correção da estrutura física do cabo 50.
Cria tubos e fibras baseado no profile (12FO).
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import FiberCable, BufferTube, FiberStrand

# Get cable 50
cable = FiberCable.objects.get(id=50)
print(f"=== Cabo: {cable.name} (ID: {cable.id}) ===")
print(f"Profile: {cable.profile.name}")
print(f"Total fibers: {cable.profile.total_fibers}")
print(f"Tubes: {cable.profile.tube_count}")
print(f"Fibers per tube: {cable.profile.fibers_per_tube}")

# Check existing structure
existing_tubes = cable.tubes.count()
existing_fibers = FiberStrand.objects.filter(tube__cable=cable).count()

print(f"\n=== Estrutura Atual ===")
print(f"Tubos: {existing_tubes}")
print(f"Fibras: {existing_fibers}")

if existing_tubes > 0:
    print("\n⚠️  ESTRUTURA JÁ EXISTE! Deseja recriar? (Apagará tudo)")
    response = input("Digite 'SIM' para confirmar: ")
    if response != "SIM":
        print("Operação cancelada.")
        exit(0)
    
    print("\n🗑️  Apagando estrutura antiga...")
    cable.tubes.all().delete()  # Cascade deleta as fibras também
    print("✓ Estrutura antiga removida")

print("\n🔧 Criando nova estrutura...")
result = cable.create_structure()

if result:
    print("✓ Estrutura criada com sucesso!")
    
    # Verify
    tubes = cable.tubes.all()
    total_fibers = FiberStrand.objects.filter(tube__cable=cable).count()
    
    print(f"\n=== Nova Estrutura ===")
    print(f"📦 Tubos criados: {tubes.count()}")
    for tube in tubes:
        fibers_count = tube.fibers.count()
        print(f"   Tubo #{tube.number}: {tube.color} ({tube.color_hex}) - {fibers_count} fibras")
    
    print(f"\n🔵 Total de fibras: {total_fibers}")
    
    if total_fibers == cable.profile.total_fibers:
        print(f"✅ SUCESSO! {total_fibers} fibras criadas conforme profile")
    else:
        print(f"❌ ERRO! Esperado {cable.profile.total_fibers}, criado {total_fibers}")
    
    # Show sample fibers from first tube
    first_tube = tubes.first()
    if first_tube:
        print(f"\n=== Exemplo: Fibras do Tubo #{first_tube.number} ===")
        sample_fibers = first_tube.fibers.all()[:6]
        for fiber in sample_fibers:
            print(f"   F#{fiber.number} (Abs#{fiber.absolute_number}): {fiber.color} ({fiber.color_hex}) - {fiber.get_status_display()}")
        if first_tube.fibers.count() > 6:
            print(f"   ... e mais {first_tube.fibers.count() - 6} fibras")
else:
    print("❌ ERRO: Falha ao criar estrutura")
