#!/usr/bin/env python
"""
Cria estrutura de tubos e fibras para o cabo TESTE.
"""
import os
import sys
import django

sys.path.insert(0, '/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import FiberCable, BufferTube, FiberStrand

def main():
    cabo = FiberCable.objects.filter(name='TESTE').first()
    
    if not cabo:
        print("❌ Cabo 'TESTE' não encontrado!")
        return
    
    print(f"✓ Cabo encontrado: {cabo.name}")
    
    # Verificar se já tem estrutura
    existing_tubes = cabo.tubes.count()
    existing_strands = FiberStrand.objects.filter(tube__cable=cabo).count()
    
    print(f"Estado atual: {existing_tubes} tubos, {existing_strands} fibras")
    
    if existing_tubes > 0:
        print("⚠️  Removendo estrutura antiga...")
        cabo.tubes.all().delete()  # Deleta tubos e fibras em cascata
    
    # Criar estrutura: 4 tubos × 12 fibras = 48FO
    cores = ['azul', 'laranja', 'verde', 'marrom']
    fiber_colors = [
        'azul', 'laranja', 'verde', 'marrom', 
        'cinza', 'branco', 'vermelho', 'preto',
        'amarelo', 'violeta', 'rosa', 'turquesa'
    ]
    
    total_created = 0
    
    for i, cor_tubo in enumerate(cores, 1):
        tubo = BufferTube.objects.create(
            cable=cabo,
            number=i,
            color=cor_tubo
        )
        print(f"  ✓ Tubo {i} ({cor_tubo}): criado")
        
        for j, cor_fibra in enumerate(fiber_colors, 1):
            FiberStrand.objects.create(
                tube=tubo,
                number=j,
                absolute_number=(i-1)*12 + j,
                color=cor_fibra,
                color_hex='#FFFFFF'
            )
            total_created += 1
    
    print(f"\n✅ Estrutura criada: {len(cores)} tubos × 12 fibras = {total_created} fibras")
    print(f"   Perfil do cabo: {cabo.profile.name if cabo.profile else 'N/A'}")

if __name__ == '__main__':
    main()
