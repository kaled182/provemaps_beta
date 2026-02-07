"""
Teste de diagnóstico do fluxo da API Key do Zabbix
Verifica se a chave está sendo salva e consumida corretamente
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from setup_app.models import FirstTimeSetup, MonitoringServer
from setup_app.services import runtime_settings
from setup_app.utils import env_manager
from integrations.zabbix.client import ResilientZabbixClient
from django.conf import settings


def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def test_database_config():
    """Verificar configuração no banco de dados"""
    print_section("1. CONFIGURAÇÃO NO BANCO DE DADOS (FirstTimeSetup)")
    
    setup = FirstTimeSetup.objects.filter(configured=True).order_by('-configured_at').first()
    
    if not setup:
        print("❌ Nenhuma configuração encontrada em FirstTimeSetup!")
        return False
    
    print(f"✅ Configuração encontrada (ID: {setup.id})")
    print(f"   - Company: {setup.company_name}")
    print(f"   - Zabbix URL: {setup.zabbix_url}")
    print(f"   - Auth Type: {setup.auth_type}")
    
    if setup.auth_type == "token":
        if setup.zabbix_api_key:
            key_preview = setup.zabbix_api_key[:16] + "..." if len(setup.zabbix_api_key) > 16 else setup.zabbix_api_key
            print(f"   - API Key (encrypted): {key_preview} (comprimento: {len(setup.zabbix_api_key)})")
            return True
        else:
            print("   ❌ Auth type é 'token' mas zabbix_api_key está vazio!")
            return False
    else:
        print(f"   - Zabbix User: {'(set)' if setup.zabbix_user else '(empty)'}")
        print(f"   - Zabbix Password: {'(set)' if setup.zabbix_password else '(empty)'}")
        return bool(setup.zabbix_user and setup.zabbix_password)


def test_monitoring_server():
    """Verificar configuração no MonitoringServer"""
    print_section("2. SERVIDOR DE MONITORAMENTO (MonitoringServer)")
    
    server = MonitoringServer.objects.filter(server_type='zabbix', is_active=True).first()
    
    if not server:
        print("⚠️  Nenhum MonitoringServer do tipo Zabbix ativo encontrado")
        print("   (Isso pode ser normal se usar apenas FirstTimeSetup)")
        return None
    
    print(f"✅ Servidor Zabbix encontrado (ID: {server.id})")
    print(f"   - Name: {server.name}")
    print(f"   - URL: {server.url}")
    
    if server.api_key:
        key_preview = server.api_key[:16] + "..." if len(server.api_key) > 16 else server.api_key
        print(f"   - API Key: {key_preview} (comprimento: {len(server.api_key)})")
        return True
    else:
        print(f"   - Username: {'(set)' if server.username else '(empty)'}")
        print(f"   - Password: {'(set)' if server.password else '(empty)'}")
        return bool(server.username and server.password)


def test_runtime_settings():
    """Verificar runtime settings (config loader)"""
    print_section("3. RUNTIME SETTINGS (config_loader)")
    
    config = runtime_settings.get_runtime_config()
    
    print(f"   - Zabbix API URL: {config.zabbix_api_url or '(not set)'}")
    print(f"   - Zabbix API User: {config.zabbix_api_user or '(not set)'}")
    print(f"   - Zabbix API Password: {'(set)' if config.zabbix_api_password else '(not set)'}")
    
    if config.zabbix_api_key:
        key_preview = config.zabbix_api_key[:16] + "..." if len(config.zabbix_api_key) > 16 else config.zabbix_api_key
        print(f"   ✅ Zabbix API Key: {key_preview} (comprimento: {len(config.zabbix_api_key)})")
        return True
    else:
        print(f"   ❌ Zabbix API Key: (not set)")
        return False


def test_django_settings():
    """Verificar Django settings.py"""
    print_section("4. DJANGO SETTINGS")
    
    print(f"   - ZABBIX_API_URL: {getattr(settings, 'ZABBIX_API_URL', '(not set)')}")
    print(f"   - ZABBIX_API_USER: {getattr(settings, 'ZABBIX_API_USER', '(not set)')}")
    print(f"   - ZABBIX_API_PASSWORD: {'(set)' if getattr(settings, 'ZABBIX_API_PASSWORD', '') else '(not set)'}")
    
    api_key = getattr(settings, 'ZABBIX_API_KEY', '')
    if api_key:
        key_preview = api_key[:16] + "..." if len(api_key) > 16 else api_key
        print(f"   ✅ ZABBIX_API_KEY: {key_preview} (comprimento: {len(api_key)})")
        return True
    else:
        print(f"   ❌ ZABBIX_API_KEY: (not set)")
        return False


def test_env_file():
    """Verificar arquivo .env"""
    print_section("5. ARQUIVO .env")
    
    values = env_manager.read_values([
        'ZABBIX_API_URL',
        'ZABBIX_API_USER',
        'ZABBIX_API_PASSWORD',
        'ZABBIX_API_KEY'
    ])
    
    print(f"   - ZABBIX_API_URL: {values.get('ZABBIX_API_URL', '(not set)')}")
    print(f"   - ZABBIX_API_USER: {values.get('ZABBIX_API_USER', '(not set)')}")
    print(f"   - ZABBIX_API_PASSWORD: {'(set)' if values.get('ZABBIX_API_PASSWORD') else '(not set)'}")
    
    api_key = values.get('ZABBIX_API_KEY', '')
    if api_key:
        key_preview = api_key[:16] + "..." if len(api_key) > 16 else api_key
        print(f"   ✅ ZABBIX_API_KEY: {key_preview} (comprimento: {len(api_key)})")
        return True
    else:
        print(f"   ❌ ZABBIX_API_KEY: (not set)")
        return False


def test_zabbix_client():
    """Verificar ResilientZabbixClient"""
    print_section("6. RESILIENT ZABBIX CLIENT")
    
    client = ResilientZabbixClient()
    config = client._get_config()
    
    print(f"   - URL: {config.url}")
    print(f"   - User: {config.user or '(not set)'}")
    print(f"   - Password: {'(set)' if config.password else '(not set)'}")
    
    if config.api_key:
        key_preview = config.api_key[:16] + "..." if len(config.api_key) > 16 else config.api_key
        print(f"   ✅ API Key: {key_preview} (comprimento: {len(config.api_key)})")
        
        # Tentar obter token
        print("\n   Tentando autenticar com API Key...")
        try:
            token = client._get_token()
            if token:
                token_preview = token[:16] + "..." if len(token) > 16 else token
                print(f"   ✅ Token obtido: {token_preview}")
                
                # Verificar se o token é a própria API key ou um token de sessão
                if token == config.api_key:
                    print(f"   ℹ️  Token é a própria API Key (autenticação direta)")
                else:
                    print(f"   ℹ️  Token é um token de sessão diferente da API Key")
                
                return True
            else:
                print(f"   ❌ Falha ao obter token!")
                return False
        except Exception as e:
            print(f"   ❌ Erro ao autenticar: {e}")
            return False
    else:
        print(f"   ⚠️  API Key: (not set)")
        if config.user and config.password:
            print(f"   ℹ️  Usando autenticação por usuário/senha")
            
            # Tentar login
            print("\n   Tentando autenticar com user/password...")
            try:
                token = client._get_token()
                if token:
                    token_preview = token[:16] + "..." if len(token) > 16 else token
                    print(f"   ✅ Token obtido: {token_preview}")
                    return True
                else:
                    print(f"   ❌ Falha ao obter token!")
                    return False
            except Exception as e:
                print(f"   ❌ Erro ao autenticar: {e}")
                return False
        else:
            print(f"   ❌ Nem API Key nem credenciais user/password estão configurados!")
            return False


def main():
    print("\n" + "="*70)
    print("  DIAGNÓSTICO COMPLETO: Fluxo da API Key do Zabbix")
    print("="*70)
    
    results = {
        "Database (FirstTimeSetup)": test_database_config(),
        "MonitoringServer": test_monitoring_server(),
        "Runtime Settings": test_runtime_settings(),
        "Django Settings": test_django_settings(),
        "Arquivo .env": test_env_file(),
        "Zabbix Client": test_zabbix_client(),
    }
    
    print_section("RESUMO DOS TESTES")
    
    for test_name, result in results.items():
        if result is None:
            icon = "⚠️"
            status = "OPCIONAL"
        elif result:
            icon = "✅"
            status = "PASSOU"
        else:
            icon = "❌"
            status = "FALHOU"
        
        print(f"{icon} {test_name}: {status}")
    
    # Contagem de falhas
    failures = sum(1 for r in results.values() if r is False)
    
    if failures == 0:
        print("\n🎉 Todos os testes passaram! O sistema está configurado corretamente.")
        print_section("PRÓXIMOS PASSOS")
        print("""
1. Verifique se o formulário de configuração salva corretamente:
   - Abra http://localhost:8000/setup_app/config/
   - Na aba "Monitoramento", clique em "Zabbix Principal"
   - Confirme que a API Key está visível (parcialmente mascarada)
   - Clique em "Testar Conexão" e verifique mensagem de sucesso

2. Se o teste falhar com "token inválido":
   - Verifique se a API Key do Zabbix está correta
   - Confirme que o usuário do Zabbix tem permissões adequadas
   - Teste a API Key diretamente no Zabbix UI
        """)
    else:
        print(f"\n⚠️  {failures} teste(s) falharam. Veja detalhes acima.")
        print_section("AÇÕES RECOMENDADAS")
        
        if not results["Database (FirstTimeSetup)"]:
            print("""
❌ PROBLEMA: API Key não está no banco de dados

SOLUÇÃO:
1. Acesse: http://localhost:8000/setup_app/config/
2. Vá para aba "Monitoramento"
3. Clique em "Zabbix Principal" ou "Adicionar Servidor"
4. Selecione "Zabbix API token" como método de autenticação
5. Cole sua API Key do Zabbix
6. Clique em "Testar Conexão"
7. Se passar, clique em "Salvar"
            """)
        
        if not results["Runtime Settings"] or not results["Django Settings"]:
            print("""
❌ PROBLEMA: API Key não está sendo carregada pelo sistema

POSSÍVEIS CAUSAS:
1. Configuração não foi salva corretamente no banco
2. config_loader.py não está lendo FirstTimeSetup
3. Django settings não está usando runtime_settings

VERIFICAÇÃO:
cd d:\\provemaps_beta
python backend/manage.py shell

>>> from setup_app.services import runtime_settings
>>> config = runtime_settings.get_runtime_config()
>>> print(f"API Key: {config.zabbix_api_key[:20] if config.zabbix_api_key else 'NOT SET'}")
            """)
        
        if not results["Zabbix Client"]:
            print("""
❌ PROBLEMA: Cliente Zabbix não consegue autenticar

POSSÍVEIS CAUSAS:
1. API Key inválida ou expirada
2. Zabbix URL incorreta
3. Firewall bloqueando conexão
4. Zabbix API desabilitada

TESTE MANUAL:
curl -X POST http://seu-zabbix:8080/api_jsonrpc.php \\
  -H "Content-Type: application/json" \\
  -d '{
    "jsonrpc": "2.0",
    "method": "user.get",
    "params": {"output": ["userid"]},
    "auth": "SUA_API_KEY_AQUI",
    "id": 1
  }'
            """)


if __name__ == "__main__":
    main()
