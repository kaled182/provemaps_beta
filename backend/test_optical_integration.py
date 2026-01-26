#!/usr/bin/env python
"""
Script de teste simplificado para endpoint de dados ópticos
Testa contra banco de produção com cabo 84
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from inventory.models import FiberCable
import requests

def test_optical_endpoint():
    """Testa endpoint /api/v1/inventory/fibers/84/cached-status/"""
    cable_id = 84
    
    print(f"\n{'='*60}")
    print(f"TESTE DE INTEGRAÇÃO - ENDPOINT OPTICAL STATUS")
    print(f"{'='*60}\n")
    
    # 1. Verificar se cabo existe no banco
    print(f"1. Verificando cabo {cable_id} no banco...")
    try:
        cable = FiberCable.objects.select_related(
            'origin_port__device',
            'destination_port__device'
        ).get(id=cable_id)
        print(f"   ✅ Cabo encontrado: {cable.name}")
        print(f"   - Origem: {cable.origin_port.name if cable.origin_port else 'N/A'}")
        print(f"   - Destino: {cable.destination_port.name if cable.destination_port else 'N/A'}")
    except FiberCable.DoesNotExist:
        print(f"   ❌ Cabo {cable_id} não encontrado!")
        return False
    
    # 2. Verificar dados ópticos nas portas
    print(f"\n2. Verificando dados ópticos nas portas...")
    if cable.origin_port:
        print(f"   Porta origem ({cable.origin_port.name}):")
        print(f"   - RX: {cable.origin_port.last_rx_power} dBm")
        print(f"   - TX: {cable.origin_port.last_tx_power} dBm")
        print(f"   - Última verificação: {cable.origin_port.last_optical_check}")
    
    if cable.destination_port:
        print(f"   Porta destino ({cable.destination_port.name}):")
        print(f"   - RX: {cable.destination_port.last_rx_power} dBm")
        print(f"   - TX: {cable.destination_port.last_tx_power} dBm")
        print(f"   - Última verificação: {cable.destination_port.last_optical_check}")
    
    # 3. Testar endpoint via requests
    print(f"\n3. Testando endpoint via HTTP...")
    
    try:
        # Fazer requisição com autenticação de superuser
        from django.contrib.auth.models import User
        from django.conf import settings
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            print("   ⚠️ Nenhum superuser encontrado, criando...")
            user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
        
        # Fazer requisição autenticada
        from django.test import Client, override_settings
        
        # Adicionar 'testserver' ao ALLOWED_HOSTS temporariamente
        with override_settings(ALLOWED_HOSTS=settings.ALLOWED_HOSTS + ['testserver']):
            client = Client()
            client.force_login(user)
            
            response = client.get(f'/api/v1/inventory/fibers/{cable_id}/cached-status/')
        
        if response.status_code == 200:
            print(f"   ✅ Status Code: {response.status_code}")
            data = response.json()
            
            # 4. Validar estrutura da resposta
            print(f"\n4. Validando estrutura da resposta JSON...")
            required_fields = ['cable_id', 'status', 'origin_optical', 'destination_optical']
            for field in required_fields:
                if field in data:
                    print(f"   ✅ Campo '{field}' presente")
                else:
                    print(f"   ❌ Campo '{field}' AUSENTE!")
                    return False
            
            # 5. Exibir dados retornados
            print(f"\n5. Dados retornados pelo endpoint:")
            print(f"   Cable ID: {data.get('cable_id')}")
            print(f"   Status: {data.get('status')}")
            
            origin = data.get('origin_optical')
            if origin:
                print(f"\n   Dados ópticos da origem:")
                print(f"   - RX: {origin.get('rx_dbm')} dBm")
                print(f"   - TX: {origin.get('tx_dbm')} dBm")
                print(f"   - Última verificação: {origin.get('last_check')}")
            else:
                print(f"\n   ⚠️ Dados ópticos da origem: None")
            
            dest = data.get('destination_optical')
            if dest:
                print(f"\n   Dados ópticos do destino:")
                print(f"   - RX: {dest.get('rx_dbm')} dBm")
                print(f"   - TX: {dest.get('tx_dbm')} dBm")
                print(f"   - Última verificação: {dest.get('last_check')}")
            else:
                print(f"\n   ⚠️ Dados ópticos do destino: None")
            
            # 6. Calcular atenuação (se houver dados completos)
            if origin and dest and origin.get('tx_dbm') and dest.get('rx_dbm'):
                attenuation = origin['tx_dbm'] - dest['rx_dbm']
                print(f"\n6. Cálculo de atenuação:")
                print(f"   TX origem ({origin['tx_dbm']} dBm) - RX destino ({dest['rx_dbm']} dBm)")
                print(f"   = {attenuation:.2f} dB")
            
            print(f"\n{'='*60}")
            print(f"✅ TESTE CONCLUÍDO COM SUCESSO!")
            print(f"{'='*60}\n")
            return True
            
        else:
            print(f"   ❌ Status Code: {response.status_code}")
            print(f"   Resposta: {response.content}")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro ao fazer requisição: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_optical_endpoint()
    sys.exit(0 if success else 1)
