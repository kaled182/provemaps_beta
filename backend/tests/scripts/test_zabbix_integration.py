#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from inventory.models import Device
from integrations.zabbix.zabbix_service import zabbix_request

print("\n" + "="*80)
print("TESTE DE INTEGRAÇÃO ZABBIX - DISPOSITIVOS FURACÃO")
print("="*80 + "\n")

# Buscar dispositivos do site Furacão
devices = Device.objects.filter(site__display_name__icontains='Furacão')

if not devices.exists():
    print("❌ Nenhum dispositivo encontrado no site Furacão")
    exit(1)

print(f"✅ Encontrados {devices.count()} dispositivos no site Furacão\n")

for device in devices:
    print(f"\n{'─'*80}")
    print(f"📱 DISPOSITIVO: {device.name}")
    print(f"{'─'*80}")
    print(f"   ID: {device.id}")
    print(f"   Zabbix Host ID: {device.zabbix_hostid}")
    print(f"   IP: {device.primary_ip}")
    print(f"\n   Item Keys Configurados:")
    print(f"   • CPU:    {device.cpu_usage_item_key or '(não configurado)'}")
    print(f"   • Memory: {device.memory_usage_item_key or '(não configurado)'}")
    print(f"   • Uptime: {device.uptime_item_key or '(não configurado)'}")
    
    if not device.zabbix_hostid:
        print(f"\n   ⚠️  Zabbix Host ID não configurado - pulando...")
        continue
    
    # Tentar buscar dados do Zabbix
    print(f"\n   🔍 Buscando dados no Zabbix...")
    
    try:
        # Buscar itens do Zabbix para este host
        items_to_fetch = []
        if device.cpu_usage_item_key:
            items_to_fetch.append(device.cpu_usage_item_key)
        if device.memory_usage_item_key:
            items_to_fetch.append(device.memory_usage_item_key)
        if device.uptime_item_key:
            items_to_fetch.append(device.uptime_item_key)
        
        if not items_to_fetch:
            print(f"   ⚠️  Nenhum item key configurado")
            continue
            
        print(f"   📊 Buscando {len(items_to_fetch)} item(s): {', '.join(items_to_fetch)}")
        
        response = zabbix_request(
            "item.get",
            {
                "output": ["key_", "lastvalue", "units", "name", "status"],
                "hostids": [device.zabbix_hostid],
                "filter": {"key_": items_to_fetch},
            },
        )
        
        if not response:
            print(f"   ❌ Nenhum item retornado pelo Zabbix")
            print(f"   💡 Possíveis causas:")
            print(f"      - Item keys não existem no Zabbix")
            print(f"      - Host ID incorreto")
            print(f"      - Items desabilitados no Zabbix")
        else:
            print(f"   ✅ Recebidos {len(response)} item(s) do Zabbix:\n")
            for item in response:
                key = item.get('key_', 'N/A')
                value = item.get('lastvalue', 'N/A')
                units = item.get('units', '')
                name = item.get('name', 'N/A')
                status = item.get('status', '0')
                status_text = '✅ Ativo' if status == '0' else '❌ Desabilitado'
                
                print(f"      📌 {key}")
                print(f"         Nome: {name}")
                print(f"         Status: {status_text}")
                print(f"         Último valor: {value} {units}")
                print()
                
                # Processar valor conforme o tipo
                if key == device.cpu_usage_item_key and value != 'N/A':
                    try:
                        cpu_val = float(value)
                        print(f"         ✅ CPU: {cpu_val}%")
                    except:
                        print(f"         ⚠️  Não foi possível converter valor de CPU")
                
                elif key == device.uptime_item_key and value != 'N/A':
                    try:
                        uptime_sec = int(float(value))
                        days = uptime_sec // 86400
                        hours = (uptime_sec % 86400) // 3600
                        minutes = (uptime_sec % 3600) // 60
                        print(f"         ✅ Uptime: {days}d {hours}h {minutes}m ({uptime_sec} segundos)")
                    except:
                        print(f"         ⚠️  Não foi possível converter valor de uptime")
                
                elif key == device.memory_usage_item_key and value != 'N/A':
                    try:
                        mem_val = float(value)
                        print(f"         ✅ Memória: {mem_val}%")
                    except:
                        print(f"         ⚠️  Não foi possível converter valor de memória")
        
        # Testar também via endpoint /metrics/
        print(f"\n   🌐 Testando endpoint /api/v1/devices/{device.id}/metrics/")
        from inventory.viewsets import DeviceViewSet
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        request = factory.get(f'/api/v1/devices/{device.id}/metrics/')
        view = DeviceViewSet()
        view.action = 'metrics'
        
        try:
            response = view.metrics(request, pk=device.id)
            print(f"   ✅ Endpoint retornou status {response.status_code}")
            print(f"   📦 Dados: {response.data}")
        except Exception as e:
            print(f"   ❌ Erro ao chamar endpoint: {e}")
            
    except Exception as e:
        print(f"   ❌ Erro ao buscar dados do Zabbix: {e}")
        import traceback
        print(f"\n   Stack trace:")
        print(traceback.format_exc())

print(f"\n{'='*80}")
print("TESTE CONCLUÍDO")
print("="*80 + "\n")
