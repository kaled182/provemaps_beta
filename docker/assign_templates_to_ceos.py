#!/usr/bin/env python
"""
Script para associar templates SVT às CEOs existentes.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import FiberInfrastructure, SpliceBoxTemplate

def main():
    # Pegar template padrão (SVT 24 Fibras)
    template = SpliceBoxTemplate.objects.filter(name__icontains='24').first()
    
    if not template:
        print("❌ Nenhum template encontrado! Execute: python manage.py seed_fibracem")
        return
    
    print(f"✓ Template encontrado: {template.name} ({template.max_trays}x{template.splices_per_tray} = {template.total_capacity}FO)")
    
    # Buscar CEOs sem template
    ceos = FiberInfrastructure.objects.filter(
        type='splice_box',
        box_template__isnull=True
    )
    
    count = ceos.count()
    print(f"\n📦 CEOs sem template: {count}")
    
    if count == 0:
        print("✓ Todas as CEOs já têm template associado!")
        return
    
    # Atualizar
    updated = ceos.update(
        box_template=template,
        installed_trays=1  # 1 bandeja instalada por padrão
    )
    
    print(f"✓ CEOs atualizados: {updated}")
    
    # Verificar resultado
    print("\n🔍 Verificando primeiras 5 CEOs:")
    for ceo in FiberInfrastructure.objects.filter(type='splice_box')[:5]:
        print(f"  • {ceo.name}")
        print(f"    - Cabo: {ceo.cable.name}")
        print(f"    - Template: {ceo.box_template.name if ceo.box_template else 'N/A'}")
        print(f"    - Bandejas instaladas: {ceo.installed_trays}")
        print()

if __name__ == '__main__':
    main()
