#!/usr/bin/env python
"""
Script de diagnóstico detalhado para investigar por que os grupos dos hosts não estão sendo retornados.
"""
import os
import sys
import json
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.dev")
django.setup()

from integrations.zabbix.zabbix_service import zabbix_request
from inventory.models import Device

def diagnose_host_groups():
    """Diagnóstico completo da API do Zabbix para groups"""
    
    print("\n" + "="*70)
    print("DIAGNÓSTICO: Por que os grupos não aparecem nos hosts?")
    print("="*70 + "\n")
    
    # Pegar um device do banco para testar
    device = Device.objects.filter(zabbix_hostid__isnull=False).exclude(zabbix_hostid="").first()
    
    if not device:
        print("❌ Nenhum device com zabbix_hostid encontrado no banco")
        return
    
    print(f"📋 Testando com device: {device.name}")
    print(f"   Zabbix Host ID: {device.zabbix_hostid}\n")
    
    # ========================================================================
    # TESTE 1: Listar grupos (deve funcionar - já sabemos que funciona)
    # ========================================================================
    print("\n" + "-"*70)
    print("TESTE 1: Listar todos os grupos do Zabbix")
    print("-"*70)
    
    try:
        groups = zabbix_request("hostgroup.get", {
            "output": ["groupid", "name"]
        })
        print(f"✅ Encontrados {len(groups)} grupos no Zabbix")
        print("\nPrimeiros 5 grupos:")
        for group in groups[:5]:
            print(f"  - {group.get('name')} (ID: {group.get('groupid')})")
    except Exception as e:
        print(f"❌ Erro ao buscar grupos: {e}")
        return
    
    # ========================================================================
    # TESTE 2: Buscar host SEM selectGroups
    # ========================================================================
    print("\n" + "-"*70)
    print("TESTE 2: Buscar host SEM selectGroups")
    print("-"*70)
    
    try:
        hosts = zabbix_request("host.get", {
            "output": ["hostid", "host", "name"],
            "hostids": [device.zabbix_hostid]
        })
        
        if hosts:
            print(f"✅ Host encontrado: {hosts[0].get('name')}")
            print(f"\nDados retornados:")
            print(json.dumps(hosts[0], indent=2))
        else:
            print("❌ Host não encontrado")
            return
    except Exception as e:
        print(f"❌ Erro ao buscar host: {e}")
        return
    
    # ========================================================================
    # TESTE 3: Buscar host COM selectGroups (extend)
    # ========================================================================
    print("\n" + "-"*70)
    print("TESTE 3: Buscar host COM selectGroups (extend)")
    print("-"*70)
    
    try:
        hosts = zabbix_request("host.get", {
            "output": ["hostid", "host", "name"],
            "hostids": [device.zabbix_hostid],
            "selectGroups": "extend"  # Retorna todos os campos dos grupos
        })
        
        if hosts:
            host_data = hosts[0]
            groups = host_data.get("groups", [])
            
            print(f"✅ Host encontrado: {host_data.get('name')}")
            print(f"   Grupos encontrados: {len(groups)}")
            
            if groups:
                print("\n📂 Grupos associados ao host:")
                for group in groups:
                    print(f"  - {group.get('name')} (ID: {group.get('groupid')})")
                
                print("\n📄 Dados completos do primeiro grupo:")
                print(json.dumps(groups[0], indent=2))
            else:
                print("\n⚠️  PROBLEMA: Host não tem grupos associados!")
                print("\nDados completos do host:")
                print(json.dumps(host_data, indent=2))
        else:
            print("❌ Host não encontrado")
    except Exception as e:
        print(f"❌ Erro ao buscar host com grupos: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # TESTE 4: Buscar host COM selectGroups (campos específicos)
    # ========================================================================
    print("\n" + "-"*70)
    print("TESTE 4: Buscar host COM selectGroups (campos específicos)")
    print("-"*70)
    
    try:
        hosts = zabbix_request("host.get", {
            "output": ["hostid", "host", "name"],
            "hostids": [device.zabbix_hostid],
            "selectGroups": ["groupid", "name"]  # Código atual
        })
        
        if hosts:
            host_data = hosts[0]
            groups = host_data.get("groups", [])
            
            print(f"✅ Host encontrado: {host_data.get('name')}")
            print(f"   Grupos encontrados: {len(groups)}")
            
            if groups:
                print("\n📂 Grupos associados ao host:")
                for group in groups:
                    print(f"  - {group.get('name')} (ID: {group.get('groupid')})")
            else:
                print("\n⚠️  PROBLEMA: Host não tem grupos associados!")
                print("\nDados completos retornados:")
                print(json.dumps(host_data, indent=2))
        else:
            print("❌ Host não encontrado")
    except Exception as e:
        print(f"❌ Erro ao buscar host com grupos: {e}")
    
    # ========================================================================
    # TESTE 5: Buscar hosts por grupo (verificar relação inversa)
    # ========================================================================
    print("\n" + "-"*70)
    print("TESTE 5: Buscar hosts que pertencem a um grupo específico")
    print("-"*70)
    
    try:
        # Pegar o primeiro grupo
        first_group = groups[0]
        group_id = first_group.get('groupid')
        group_name = first_group.get('name')
        
        print(f"Buscando hosts do grupo: {group_name} (ID: {group_id})")
        
        hosts = zabbix_request("host.get", {
            "output": ["hostid", "host", "name"],
            "groupids": [group_id]
        })
        
        print(f"✅ Encontrados {len(hosts)} hosts no grupo '{group_name}'")
        
        if hosts:
            print("\nPrimeiros 5 hosts:")
            for host in hosts[:5]:
                print(f"  - {host.get('name')} (ID: {host.get('hostid')})")
            
            # Verificar se nosso device está na lista
            our_host_in_group = any(h.get('hostid') == device.zabbix_hostid for h in hosts)
            if our_host_in_group:
                print(f"\n✅ Device '{device.name}' ESTÁ neste grupo!")
            else:
                print(f"\n⚠️  Device '{device.name}' NÃO está neste grupo")
        else:
            print(f"⚠️  Nenhum host encontrado no grupo '{group_name}'")
            
    except Exception as e:
        print(f"❌ Erro ao buscar hosts por grupo: {e}")
    
    # ========================================================================
    # TESTE 6: Verificar permissões do usuário API
    # ========================================================================
    print("\n" + "-"*70)
    print("TESTE 6: Verificar informações do usuário API")
    print("-"*70)
    
    try:
        user = zabbix_request("user.get", {
            "output": ["userid", "username", "roleid"],
            "selectRole": ["name", "type"]
        })
        
        if user:
            user_data = user[0]
            print(f"✅ Usuário API: {user_data.get('username')}")
            print(f"   User ID: {user_data.get('userid')}")
            
            role = user_data.get('role', {})
            if role:
                print(f"   Role: {role.get('name')} (tipo: {role.get('type')})")
                # Tipo 3 = Super Admin, 2 = Admin, 1 = User
                role_type = int(role.get('type', 0))
                if role_type == 3:
                    print("   ✅ Super Admin - permissões completas")
                elif role_type == 2:
                    print("   ⚠️  Admin - pode ter restrições")
                else:
                    print("   ⚠️  User - permissões limitadas")
        else:
            print("❌ Erro ao buscar informações do usuário")
    except Exception as e:
        print(f"⚠️  Erro ao verificar usuário (pode não ter permissão): {e}")
    
    # ========================================================================
    # CONCLUSÃO
    # ========================================================================
    print("\n" + "="*70)
    print("CONCLUSÃO")
    print("="*70 + "\n")
    
    print("Se os TESTES 3 e 4 mostraram 0 grupos mas o TESTE 5 encontrou hosts")
    print("nos grupos, então:")
    print("  1. Os grupos EXISTEM no Zabbix")
    print("  2. Os hosts ESTÃO associados aos grupos")
    print("  3. A API do Zabbix NÃO está retornando os grupos na consulta host.get")
    print()
    print("Possíveis causas:")
    print("  - Versão do Zabbix incompatível com selectGroups")
    print("  - Usuário API sem permissão para ver grupos")
    print("  - Bug na implementação do Zabbix")
    print("  - Configuração de segurança bloqueando retorno de grupos")
    print()
    print("Ação recomendada:")
    print("  - Verificar versão do Zabbix Server")
    print("  - Testar com usuário Super Admin")
    print("  - Consultar documentação da API para esta versão específica")
    print()

if __name__ == "__main__":
    diagnose_host_groups()
