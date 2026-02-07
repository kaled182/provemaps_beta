"""Script de diagnóstico para executar dentro do container Docker"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from setup_app.models import FirstTimeSetup
from setup_app.services import runtime_settings
from integrations.zabbix.client import ResilientZabbixClient

print('='*70)
print('DIAGNÓSTICO: API Key do Zabbix')
print('='*70)

# 1. Banco de dados
print('\n1. BANCO DE DADOS (FirstTimeSetup):')
setup = FirstTimeSetup.objects.filter(configured=True).order_by('-configured_at').first()
if setup:
    print(f'   ✅ Configuração encontrada (ID: {setup.id})')
    print(f'   - Company: {setup.company_name}')
    print(f'   - Zabbix URL: {setup.zabbix_url}')
    print(f'   - Auth Type: {setup.auth_type}')
    if setup.auth_type == 'token':
        if setup.zabbix_api_key:
            preview = setup.zabbix_api_key[:20] + '...' if len(setup.zabbix_api_key) > 20 else setup.zabbix_api_key
            print(f'   ✅ API Key: {preview} (len={len(setup.zabbix_api_key)})')
        else:
            print(f'   ❌ API Key está vazio!')
    else:
        user_status = "(set)" if setup.zabbix_user else "(empty)"
        pass_status = "(set)" if setup.zabbix_password else "(empty)"
        print(f'   - User: {user_status}')
        print(f'   - Password: {pass_status}')
else:
    print('   ❌ Nenhuma configuração encontrada!')

# 2. Runtime settings
print('\n2. RUNTIME SETTINGS:')
config = runtime_settings.get_runtime_config()
print(f'   - URL: {config.zabbix_api_url or "(not set)"}')
print(f'   - User: {config.zabbix_api_user or "(not set)"}')
pass_status = "(set)" if config.zabbix_api_password else "(not set)"
print(f'   - Password: {pass_status}')
if config.zabbix_api_key:
    preview = config.zabbix_api_key[:20] + '...' if len(config.zabbix_api_key) > 20 else config.zabbix_api_key
    print(f'   ✅ API Key: {preview} (len={len(config.zabbix_api_key)})')
else:
    print(f'   ❌ API Key: (not set)')

# 3. Zabbix Client
print('\n3. ZABBIX CLIENT:')
client = ResilientZabbixClient()
zabbix_config = client._get_config()
print(f'   - URL: {zabbix_config.url}')
print(f'   - User: {zabbix_config.user or "(not set)"}')
pass_status = "(set)" if zabbix_config.password else "(not set)"
print(f'   - Password: {pass_status}')
if zabbix_config.api_key:
    preview = zabbix_config.api_key[:20] + '...' if len(zabbix_config.api_key) > 20 else zabbix_config.api_key
    print(f'   ✅ API Key: {preview} (len={len(zabbix_config.api_key)})')
    
    print('\n   Testando autenticação...')
    try:
        token = client._get_token()
        if token:
            token_preview = token[:20] + '...' if len(token) > 20 else token
            print(f'   ✅ Token obtido: {token_preview}')
            if token == zabbix_config.api_key:
                print(f'   ℹ️  Token é a própria API Key')
            else:
                print(f'   ℹ️  Token é diferente da API Key (sessão)')
        else:
            print(f'   ❌ Falha ao obter token')
    except Exception as e:
        print(f'   ❌ Erro: {e}')
else:
    print(f'   ❌ API Key: (not set)')

print('\n' + '='*70)
