#!/usr/bin/env python
"""
Test script for fiber hierarchy structure generation.
Tests the create_structure() method with a 12FO profile.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import FiberCable, FiberProfile, Site, BufferTube, FiberStrand

def test_structure_generation():
    print("=" * 80)
    print("TESTE DE GERAÇÃO DE ESTRUTURA FÍSICA DE FIBRA")
    print("=" * 80)
    
    # Get or create a test site
    site_a, created = Site.objects.get_or_create(
        name="Site Teste Fibra",
        defaults={
            'address': 'Rua Teste, 123',
            'city': 'Brasília',
            'state': 'DF'
        }
    )
    print(f"\n✓ Site: {site_a.name} ({'criado' if created else 'existente'})")
    
    # Get the 12FO profile
    profile = FiberProfile.objects.get(name="Cabo 12FO (Tubo Único)")
    print(f"✓ Profile: {profile.name} ({profile.tube_count}x{profile.fibers_per_tube} = {profile.total_fibers}FO)")
    
    # Create a test fiber cable
    cable = FiberCable.objects.create(
        name="Cabo Teste 12FO - Estrutura",
        site_a=site_a,
        site_b=site_a,  # Same site for test
        profile=profile,
        cable_type="AERIAL"
    )
    print(f"✓ Cabo criado: {cable.name} (ID: {cable.id})")
    
    # Generate structure
    print("\n" + "-" * 80)
    print("GERANDO ESTRUTURA FÍSICA...")
    print("-" * 80)
    
    result = cable.create_structure()
    
    if result:
        print("✓ Estrutura gerada com sucesso!\n")
        
        # Verify tubes
        tubes = cable.tubes.all()
        print(f"📦 TUBOS CRIADOS: {tubes.count()}")
        for tube in tubes:
            print(f"   Tubo #{tube.number}: {tube.color} ({tube.color_hex})")
        
        # Verify fibers
        total_fibers = FiberStrand.objects.filter(tube__cable=cable).count()
        print(f"\n🔵 FIBRAS CRIADAS: {total_fibers}")
        
        # Show first tube fibers in detail
        first_tube = tubes.first()
        if first_tube:
            print(f"\n   Detalhes Tubo #{first_tube.number}:")
            fibers = first_tube.fibers.all()[:6]  # Show first 6
            for fiber in fibers:
                addr = fiber.full_address
                print(f"      Fibra #{fiber.number} (Abs #{fiber.absolute_number}): "
                      f"{fiber.color} ({fiber.color_hex}) - Status: {fiber.status}")
                print(f"         Notação: {addr['notation']}")
            
            if first_tube.fibers.count() > 6:
                print(f"      ... e mais {first_tube.fibers.count() - 6} fibras")
        
        print("\n" + "=" * 80)
        print("TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 80)
        
        # Cleanup
        print(f"\n🗑️  Removendo cabo de teste (ID: {cable.id})...")
        cable.delete()
        print("✓ Cabo removido (cascade delete de tubos e fibras)")
        
    else:
        print("❌ Falha ao gerar estrutura!")
        cable.delete()

if __name__ == "__main__":
    try:
        test_structure_generation()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
