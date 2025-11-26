#!/usr/bin/env python
"""Test import rules validation"""
import django
django.setup()

from inventory.services.import_rules import apply_import_rules
import json

print("=== TESTE DE REGRAS DE AUTO-ASSOCIAÇÃO ===\n")

# Teste 1: Switch Huawei (deve casar com regex)
test1_name = "Huawei - Switch Teste"
result1 = apply_import_rules(test1_name)
print(f'Teste 1 - Nome: "{test1_name}"')
if result1:
    print(f"✅ CASOU - Regra #{result1.get('rule_id')}: {result1.get('rule_description')}")
    print(f"   Categoria: {result1.get('category')}")
    print(f"   Grupo ID: {result1.get('group_id')}")
else:
    print("❌ NÃO CASOU - Nenhuma regra aplicada")

print()

# Teste 2: OLT GPON (não deve casar)
test2_name = "OLT-GPON-Centro"
result2 = apply_import_rules(test2_name)
print(f'Teste 2 - Nome: "{test2_name}"')
if result2:
    print(f"✅ CASOU - Regra #{result2.get('rule_id')}: {result2.get('rule_description')}")
    print(f"   Categoria: {result2.get('category')}")
    print(f"   Grupo ID: {result2.get('group_id')}")
else:
    print("❌ NÃO CASOU - Nenhuma regra aplicada")

print()

# Teste 3: Switch Huawei variação (deve casar)
test3_name = "Switch Huawei ABC"
result3 = apply_import_rules(test3_name)
print(f'Teste 3 - Nome: "{test3_name}"')
if result3:
    print(f"✅ CASOU - Regra #{result3.get('rule_id')}: {result3.get('rule_description')}")
    print(f"   Categoria: {result3.get('category')}")
    print(f"   Grupo ID: {result3.get('group_id')}")
else:
    print("❌ NÃO CASOU - Nenhuma regra aplicada")

print("\n=== RESULTADO DETALHADO (JSON) ===\n")
print(f"Teste 1: {json.dumps(result1, indent=2) if result1 else 'null'}")
print(f"Teste 2: {json.dumps(result2, indent=2) if result2 else 'null'}")
print(f"Teste 3: {json.dumps(result3, indent=2) if result3 else 'null'}")
