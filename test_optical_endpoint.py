#!/usr/bin/env python
"""
Script para testar endpoint de status óptico
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
import json

User = get_user_model()

# Criar cliente de teste
client = Client()

# Fazer login (assumindo que existe um usuário admin)
try:
    user = User.objects.filter(is_staff=True).first()
    if not user:
        print("❌ Nenhum usuário staff encontrado")
        sys.exit(1)
    
    client.force_login(user)
    print(f"✅ Logado como: {user.username}")
    
    # Testar endpoint
    cable_id = 84
    response = client.get(f'/api/v1/inventory/fibers/{cable_id}/cached-status/')
    
    print(f"\n📊 Status Code: {response.status_code}")
    print(f"📝 Content-Type: {response.get('Content-Type', 'unknown')}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Resposta do endpoint:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Verificar estrutura esperada
        print(f"\n🔍 Validação da estrutura:")
        print(f"  - cable_id: {data.get('cable_id')}")
        print(f"  - status: {data.get('status')}")
        print(f"  - origin_optical: {data.get('origin_optical')}")
        print(f"  - destination_optical: {data.get('destination_optical')}")
        
        if data.get('origin_optical'):
            origin = data['origin_optical']
            print(f"\n📡 Origin Port:")
            print(f"  - RX: {origin.get('rx_dbm')} dBm")
            print(f"  - TX: {origin.get('tx_dbm')} dBm")
            print(f"  - Last Check: {origin.get('last_check')}")
        
        if data.get('destination_optical'):
            dest = data['destination_optical']
            print(f"\n📡 Destination Port:")
            print(f"  - RX: {dest.get('rx_dbm')} dBm")
            print(f"  - TX: {dest.get('tx_dbm')} dBm")
            print(f"  - Last Check: {dest.get('last_check')}")
    else:
        print(f"\n❌ Erro na requisição:")
        print(response.content.decode('utf-8'))
        
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
