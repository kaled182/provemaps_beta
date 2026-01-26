#!/usr/bin/env python3
"""
Script de validação dos dados do cabo 84
Testa se o endpoint retorna dados no formato esperado
"""
import sys
import os
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from inventory.models import FiberCable
import json

User = get_user_model()

def main():
    print("=" * 80)
    print("VALIDAÇÃO DO ENDPOINT DE STATUS ÓPTICO")
    print("=" * 80)
    
    # 1. Verificar se cabo 84 existe
    print("\n1. Verificando cabo 84...")
    try:
        cable = FiberCable.objects.select_related(
            'origin_port__device', 
            'destination_port__device'
        ).get(id=84)
        print(f"   ✅ Cabo encontrado: {cable.name}")
        print(f"   - Status: {cable.status}")
        print(f"   - Origin Port: {cable.origin_port}")
        print(f"   - Destination Port: {cable.destination_port}")
    except FiberCable.DoesNotExist:
        print("   ❌ Cabo 84 não encontrado!")
        return 1
    
    # 2. Verificar dados ópticos nas portas
    print("\n2. Verificando dados ópticos...")
    if cable.origin_port:
        op = cable.origin_port
        print(f"   Origin Port ({op.name}):")
        print(f"     - RX: {op.last_rx_power} dBm")
        print(f"     - TX: {op.last_tx_power} dBm")
        print(f"     - Last Check: {op.last_optical_check}")
    else:
        print("   ⚠️  Sem porta de origem")
    
    if cable.destination_port:
        dp = cable.destination_port
        print(f"   Destination Port ({dp.name}):")
        print(f"     - RX: {dp.last_rx_power} dBm")
        print(f"     - TX: {dp.last_tx_power} dBm")
        print(f"     - Last Check: {dp.last_optical_check}")
    else:
        print("   ⚠️  Sem porta de destino")
    
    # 3. Testar endpoint
    print("\n3. Testando endpoint /api/v1/inventory/fibers/84/cached-status/...")
    
    client = Client()
    
    # Login
    user = User.objects.filter(is_staff=True).first()
    if not user:
        print("   ❌ Nenhum usuário staff encontrado")
        return 1
    
    client.force_login(user)
    print(f"   ✅ Logado como: {user.username}")
    
    # Fazer requisição
    response = client.get('/api/v1/inventory/fibers/84/cached-status/')
    
    print(f"\n   Status Code: {response.status_code}")
    print(f"   Content-Type: {response.get('Content-Type', 'unknown')}")
    
    if response.status_code != 200:
        print(f"   ❌ Erro na requisição:")
        print(f"   {response.content.decode('utf-8')}")
        return 1
    
    # 4. Validar resposta JSON
    print("\n4. Validando resposta JSON...")
    try:
        data = response.json()
        print(f"   ✅ JSON válido")
        print(f"\n   Estrutura:")
        print(json.dumps(data, indent=2, default=str))
    except Exception as e:
        print(f"   ❌ Erro ao parsear JSON: {e}")
        return 1
    
    # 5. Validar campos obrigatórios
    print("\n5. Validando campos obrigatórios...")
    required_fields = ['cable_id', 'status', 'origin_optical', 'destination_optical']
    
    for field in required_fields:
        if field in data:
            print(f"   ✅ {field}: presente")
        else:
            print(f"   ❌ {field}: AUSENTE")
            return 1
    
    # 6. Validar valores ópticos
    print("\n6. Validando valores ópticos...")
    
    if data.get('origin_optical'):
        origin = data['origin_optical']
        print(f"   Origin Optical:")
        print(f"     ✅ rx_dbm: {origin.get('rx_dbm')} dBm")
        print(f"     ✅ tx_dbm: {origin.get('tx_dbm')} dBm")
        print(f"     ✅ last_check: {origin.get('last_check')}")
        
        # Validar tipos
        if not isinstance(origin.get('rx_dbm'), (int, float, type(None))):
            print(f"     ❌ rx_dbm deve ser número, é {type(origin.get('rx_dbm'))}")
            return 1
    else:
        print(f"   ⚠️  origin_optical é None")
    
    if data.get('destination_optical'):
        dest = data['destination_optical']
        print(f"   Destination Optical:")
        print(f"     ✅ rx_dbm: {dest.get('rx_dbm')} dBm")
        print(f"     ✅ tx_dbm: {dest.get('tx_dbm')} dBm")
        print(f"     ✅ last_check: {dest.get('last_check')}")
    else:
        print(f"   ⚠️  destination_optical é None")
    
    # 7. Gerar payload de teste para frontend
    print("\n7. Gerando payload de teste para frontend...")
    
    if data.get('origin_optical') and data.get('destination_optical'):
        # Simular histórico como o frontend faz
        test_history = {
            'rx_history': [
                {'clock': 1706212800, 'value': data['origin_optical']['rx_dbm'] or -18},
                {'clock': 1706216400, 'value': (data['origin_optical']['rx_dbm'] or -18) + 0.5},
                {'clock': 1706220000, 'value': (data['origin_optical']['rx_dbm'] or -18) - 0.3}
            ],
            'tx_history': [
                {'clock': 1706212800, 'value': data['origin_optical']['tx_dbm'] or -18},
                {'clock': 1706216400, 'value': (data['origin_optical']['tx_dbm'] or -18) + 0.4},
                {'clock': 1706220000, 'value': (data['origin_optical']['tx_dbm'] or -18) - 0.2}
            ]
        }
        
        print(f"   ✅ Histórico simulado gerado:")
        print(json.dumps(test_history, indent=2))
        
        # Calcular stats
        rx_values = [p['value'] for p in test_history['rx_history']]
        tx_values = [p['value'] for p in test_history['tx_history']]
        
        stats = {
            'rx': {
                'avg': sum(rx_values) / len(rx_values),
                'min': min(rx_values),
                'max': max(rx_values)
            },
            'tx': {
                'avg': sum(tx_values) / len(tx_values),
                'min': min(tx_values),
                'max': max(tx_values)
            }
        }
        
        print(f"\n   ✅ Estatísticas calculadas:")
        print(json.dumps(stats, indent=2))
        
        # Valores que serão exibidos no modal
        avg_optical = (stats['rx']['avg'] + stats['tx']['avg']) / 2
        min_optical = min(stats['rx']['min'], stats['tx']['min'])
        max_optical = max(stats['rx']['max'], stats['tx']['max'])
        
        print(f"\n   📊 Valores que aparecerão no modal:")
        print(f"     - Nível Médio: {avg_optical:.2f} dBm")
        print(f"     - Mínimo: {min_optical:.2f} dBm")
        print(f"     - Máximo: {max_optical:.2f} dBm")
    
    print("\n" + "=" * 80)
    print("✅ VALIDAÇÃO COMPLETA - ENDPOINT FUNCIONANDO CORRETAMENTE")
    print("=" * 80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
