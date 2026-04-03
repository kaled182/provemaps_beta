#!/usr/bin/env python
"""
Testa a API de context para CEO-9519 (ID 31) diretamente.
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.api.splice_matrix import BoxContextView
from django.test import RequestFactory

# Create a mock request
factory = RequestFactory()
request = factory.get('/api/v1/inventory/splice-boxes/31/context/')

# Call the view
view = BoxContextView()
response = view.get(request, id=31)

# Print response
print("="*80)
print("API Response for CEO-9519 (ID: 31)")
print("="*80)
print(json.dumps(response.data, indent=2))

# Analyze
print("\n" + "="*80)
print("ANÁLISE")
print("="*80)
if not response.data:
    print("❌ ERRO: Response vazio!")
else:
    print(f"✓ {len(response.data)} item(s) retornado(s)")
    for idx, item in enumerate(response.data):
        print(f"\n Item #{idx+1}:")
        print(f"   Nome: {item.get('name')}")
        print(f"   Port type: {item.get('port_type')}")
        print(f"   Tubos: {len(item.get('tubes', []))}")
        for tube in item.get('tubes', []):
            print(f"      Tubo #{tube['number']}: {len(tube.get('strands', []))} fibras")
