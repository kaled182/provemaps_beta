#!/usr/bin/env python
"""
Testa a API de context após as correções para verificar se todas as fibras aparecem.
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.api.splice_matrix import BoxContextView
from django.test import RequestFactory

# Test CEO-9519 (should show all 12 fibers)
factory = RequestFactory()
request = factory.get('/api/v1/inventory/splice-boxes/31/context/')
view = BoxContextView()
response = view.get(request, id=31)

print("="*80)
print("CEO-9519 (ID: 31) - Teste Após Correções")
print("="*80)

if response.data:
    for cable in response.data:
        print(f"\nCabo: {cable['name']}")
        print(f"Port type: {cable['port_type']}")
        print(f"Tubos: {len(cable.get('tubes', []))}")
        
        for tube in cable.get('tubes', []):
            strands = tube.get('strands', [])
            print(f"\n  Tubo #{tube['number']} ({tube['color']}): {len(strands)} fibras")
            
            # Show first 3 and last 3
            sample = strands[:3] + ['...'] + strands[-3:] if len(strands) > 6 else strands
            for s in sample:
                if s == '...':
                    print("      ...")
                else:
                    fused_info = f" [Fusionada em {s['fusion_ceo']}]" if s.get('fusion_ceo') else ""
                    print(f"      F#{s['number']} ({s['color']}){fused_info}")

print("\n" + "="*80)
print("RESULTADO ESPERADO")
print("="*80)
print("✓ 1 cabo (asdasdsa)")
print("✓ 1 tubo verde")
print("✓ 12 fibras (verde até aqua)")
print("✓ Todas as fibras devem estar presentes, mesmo se fusionadas em outras CEOs")
