#!/usr/bin/env python
"""Script de teste simples para verificar hosts no Zabbix"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
sys.path.insert(0, '/app/backend')
django.setup()

from integrations.zabbix.zabbix_client import zabbix_request

print("=== TESTE DE CONEXÃO ZABBIX ===\n")

# 1. Testar autenticação básica
print("1. Testando autenticação...")
try:
    api_info = zabbix_request('apiinfo.version', {})
    print(f"   ✓ Zabbix API Version: {api_info}")
except Exception as e:
    print(f"   ✗ Erro: {e}")
    sys.exit(1)

# 2. Buscar hosts
print("\n2. Buscando hosts...")
try:
    hosts = zabbix_request('host.get', {
        'output': ['hostid', 'host', 'name', 'status'],
        'limit': 10
    })
    print(f"   Total de hosts retornados: {len(hosts) if hosts else 0}")
    
    if hosts:
        print("\n   Primeiros hosts:")
        for h in hosts[:5]:
            status = "Ativo" if h.get('status') == '0' else "Desabilitado"
            print(f"   - ID: {h.get('hostid'):<6} | Nome: {h.get('host'):<30} | Status: {status}")
    else:
        print("   ⚠ Nenhum host retornado!")
except Exception as e:
    print(f"   ✗ Erro ao buscar hosts: {e}")

# 3. Buscar grupos de hosts
print("\n3. Buscando grupos de hosts...")
try:
    groups = zabbix_request('hostgroup.get', {
        'output': ['groupid', 'name'],
        'limit': 10
    })
    print(f"   Total de grupos: {len(groups) if groups else 0}")
    
    if groups:
        print("\n   Grupos disponíveis:")
        for g in groups[:5]:
            print(f"   - ID: {g.get('groupid'):<6} | Nome: {g.get('name')}")
    else:
        print("   ⚠ Nenhum grupo retornado!")
except Exception as e:
    print(f"   ✗ Erro ao buscar grupos: {e}")

# 4. Verificar se existem hosts em grupos específicos
if 'groups' in locals() and groups:
    print("\n4. Verificando hosts por grupo...")
    first_group = groups[0]
    try:
        hosts_in_group = zabbix_request('host.get', {
            'output': ['hostid', 'host'],
            'groupids': [first_group['groupid']],
            'limit': 5
        })
        print(f"   Hosts no grupo '{first_group['name']}': {len(hosts_in_group) if hosts_in_group else 0}")
    except Exception as e:
        print(f"   ✗ Erro: {e}")

print("\n=== FIM DO TESTE ===")
