#!/usr/bin/env python
"""Script para verificar e atualizar token do Mapbox"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from setup_app.models import FirstTimeSetup

setup = FirstTimeSetup.objects.first()
if setup:
    token = setup.mapbox_token or ""
    print(f"Token atual completo: {token}")
    print(f"Tamanho: {len(token)} caracteres")
    
    if token and token.startswith('pk.'):
        print("✓ Token parece válido (começa com pk.)")
    else:
        print("✗ Token inválido ou vazio")
        print("\n🔧 Configure um token válido:")
        print("1. Acesse: https://account.mapbox.com/access-tokens/")
        print("2. Crie um novo token público (public token)")
        print("3. Configure no admin Django ou use este script")
else:
    print("✗ Nenhuma configuração FirstTimeSetup encontrada no banco")
    sys.exit(1)
