#!/usr/bin/env python
"""
Workaround para sincronizar grupos dos dispositivos usando busca reversa.
Como selectGroups não funciona, vamos buscar hosts por grupo.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.dev")
django.setup()

from django.db import transaction
from integrations.zabbix.zabbix_service import zabbix_request
from inventory.models import Device, DeviceGroup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sync_groups_reverse_lookup():
    """
    Sincroniza grupos usando busca reversa (hosts por grupo ao invés de grupos por host).
    
    Como selectGroups não está funcionando na API do Zabbix, vamos:
    1. Buscar todos os grupos
    2. Para cada grupo, buscar todos os hosts que pertencem a ele
    3. Associar os hosts aos grupos no banco de dados
    """
    print("\n" + "="*70)
    print("Sincronizando grupos com busca reversa (workaround)")
    print("="*70 + "\n")
    
    try:
        # 1. Buscar todos os grupos do Zabbix
        print("📂 Buscando grupos do Zabbix...")
        groups = zabbix_request("hostgroup.get", {
            "output": ["groupid", "name"]
        })
        
        print(f"✅ Encontrados {len(groups)} grupos\n")
        
        # Estatísticas
        total_associations = 0
        devices_updated = set()
        
        # 2. Para cada grupo, buscar hosts que pertencem a ele
        for group in groups:
            group_id = group.get("groupid")
            group_name = group.get("name")
            
            print(f"🔍 Processando grupo: {group_name} (ID: {group_id})")
            
            # Buscar hosts do grupo
            hosts = zabbix_request("host.get", {
                "output": ["hostid", "host", "name"],
                "groupids": [group_id]
            })
            
            if not hosts:
                print(f"   └─ Nenhum host encontrado")
                continue
            
            print(f"   └─ Encontrados {len(hosts)} hosts")
            
            # Buscar DeviceGroup no banco
            try:
                device_group = DeviceGroup.objects.get(zabbix_groupid=group_id)
            except DeviceGroup.DoesNotExist:
                print(f"   ⚠️  Grupo {group_name} não existe no banco (pulando)")
                continue
            
            # Associar os hosts ao grupo
            for host in hosts:
                host_id = host.get("hostid")
                host_name = host.get("name")
                
                try:
                    # Buscar device no banco
                    device = Device.objects.get(zabbix_hostid=host_id)
                    
                    # Adicionar ao grupo (se já não estiver)
                    if not device.groups.filter(id=device_group.id).exists():
                        device.groups.add(device_group)
                        total_associations += 1
                        devices_updated.add(device.id)
                        print(f"   ├─ ✅ {host_name} → {group_name}")
                    else:
                        print(f"   ├─ ⏭️  {host_name} (já estava no grupo)")
                        
                except Device.DoesNotExist:
                    print(f"   ├─ ⚠️  Host {host_name} (ID: {host_id}) não está no banco")
                    continue
            
            print()  # Linha em branco entre grupos
        
        # Resumo
        print("="*70)
        print("RESUMO")
        print("="*70)
        print(f"✅ Dispositivos atualizados: {len(devices_updated)}")
        print(f"✅ Associações criadas: {total_associations}")
        print()
        
        # Listar alguns exemplos
        if devices_updated:
            print("Exemplos de dispositivos com grupos:")
            for device_id in list(devices_updated)[:5]:
                device = Device.objects.get(id=device_id)
                group_names = ", ".join([g.name for g in device.groups.all()])
                print(f"  - {device.name}: {group_names}")
        
        return {
            "devices_updated": len(devices_updated),
            "associations_created": total_associations
        }
        
    except Exception as e:
        logger.exception(f"Erro ao sincronizar grupos: {e}")
        raise


if __name__ == "__main__":
    result = sync_groups_reverse_lookup()
    print(f"\n✅ Concluído! {result['devices_updated']} dispositivos atualizados.")
