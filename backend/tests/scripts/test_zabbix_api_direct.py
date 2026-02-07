"""Teste direto da API do Zabbix para diagnosticar o problema da API Key"""
import os
import django
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from setup_app.models import FirstTimeSetup

# Obter configuração do banco
setup = FirstTimeSetup.objects.filter(configured=True).order_by('-configured_at').first()

if not setup:
    print("❌ Nenhuma configuração encontrada!")
    exit(1)

api_key = setup.zabbix_api_key
zabbix_url = setup.zabbix_url

print("="*70)
print("TESTE DIRETO DA API DO ZABBIX")
print("="*70)
print(f"URL: {zabbix_url}")
print(f"API Key: {api_key[:20]}... (len={len(api_key)})")
print()

def test_method(description, method, params, auth=None, headers=None):
    """Testa um método específico do Zabbix"""
    print(f"\n{'='*70}")
    print(f"TESTE: {description}")
    print(f"{'='*70}")
    
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    
    if auth:
        payload["auth"] = auth
    
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)
    
    print(f"Method: {method}")
    print(f"Auth in payload: {'Yes' if auth else 'No'}")
    print(f"Custom headers: {headers or 'None'}")
    
    try:
        response = requests.post(zabbix_url, json=payload, headers=default_headers, timeout=10)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        
        if "result" in result:
            print(f"✅ SUCCESS")
            print(f"Result: {json.dumps(result['result'], indent=2)[:200]}")
            return True
        elif "error" in result:
            error = result["error"]
            print(f"❌ ERROR")
            print(f"Code: {error.get('code')}")
            print(f"Message: {error.get('message')}")
            print(f"Data: {error.get('data', 'N/A')}")
            return False
        else:
            print(f"⚠️  UNEXPECTED RESPONSE")
            print(f"Response: {json.dumps(result, indent=2)[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False

# Teste 1: apiinfo.version sem autenticação (deve funcionar)
test_method(
    "apiinfo.version (sem autenticação)",
    "apiinfo.version",
    {}
)

# Teste 2: user.get com API key no campo auth
test_method(
    "user.get com API key no campo 'auth'",
    "user.get",
    {"output": ["userid"]},
    auth=api_key
)

# Teste 3: user.get com Bearer token
test_method(
    "user.get com Authorization: Bearer header",
    "user.get",
    {"output": ["userid"]},
    headers={"Authorization": f"Bearer {api_key}"}
)

# Teste 4: host.get com API key no campo auth
test_method(
    "host.get com API key no campo 'auth'",
    "host.get",
    {"output": ["hostid", "host"], "limit": 1},
    auth=api_key
)

# Teste 5: host.get com Bearer token
test_method(
    "host.get com Authorization: Bearer header",
    "host.get",
    {"output": ["hostid", "host"], "limit": 1},
    headers={"Authorization": f"Bearer {api_key}"}
)

# Teste 6: apiinfo.version com API key (para ver se aceita auth desnecessário)
test_method(
    "apiinfo.version com API key no campo 'auth' (desnecessário)",
    "apiinfo.version",
    {},
    auth=api_key
)

print(f"\n{'='*70}")
print("RESUMO")
print(f"{'='*70}")
print("Se TODOS os testes falharem, a API Key pode estar:")
print("  - Expirada ou revogada no Zabbix")
print("  - Com permissões insuficientes")
print("  - Malformada ou corrompida")
print()
print("Se apiinfo.version funcionar mas user.get falhar:")
print("  - API Key tem permissões limitadas")
print("  - Tente com outro método (host.get, item.get, etc.)")
print()
print("Se host.get funcionar:")
print("  - API Key está válida!")
print("  - Problema pode ser nas permissões de user.get")
