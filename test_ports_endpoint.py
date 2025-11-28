#!/usr/bin/env python
"""
Script de teste para validar o endpoint de portas com filtro de device.

Testa:
1. GET /api/v1/ports/ (lista todas as portas)
2. GET /api/v1/ports/?device=<id> (filtra por device)
3. GET /api/v1/ports/?device=<id>&page_size=500 (com page_size maior)

Uso:
    python test_ports_endpoint.py
"""

import requests
import json
from typing import Any, Dict, List


BASE_URL = "http://localhost:8000"


def test_ports_list() -> None:
    """Testa listagem de todas as portas."""
    print("\n" + "="*60)
    print("TESTE 1: GET /api/v1/ports/")
    print("="*60)
    
    url = f"{BASE_URL}/api/v1/ports/"
    response = requests.get(url)
    
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nTotal de resultados: {data.get('count', 'N/A')}")
        
        if data.get('results'):
            print(f"\nPrimeira porta:")
            print(json.dumps(data['results'][0], indent=2, ensure_ascii=False))
            
            # Verifica campos necessários
            first_port = data['results'][0]
            required_fields = ['id', 'device', 'device_id', 'device_name', 
                             'site_id', 'site_name', 'name']
            missing_fields = [f for f in required_fields if f not in first_port]
            
            if missing_fields:
                print(f"\n⚠️  ATENÇÃO: Campos faltando: {missing_fields}")
            else:
                print("\n✅ Todos os campos necessários presentes!")
    else:
        print(f"\n❌ Erro: {response.text}")


def test_ports_filter_by_device(device_id: int) -> None:
    """Testa filtro de portas por device."""
    print("\n" + "="*60)
    print(f"TESTE 2: GET /api/v1/ports/?device={device_id}")
    print("="*60)
    
    url = f"{BASE_URL}/api/v1/ports/"
    params = {"device": device_id}
    response = requests.get(url, params=params)
    
    print(f"URL completa: {response.url}")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nTotal de portas do device {device_id}: {data.get('count', 0)}")
        
        if data.get('results'):
            print(f"\nExemplo de porta filtrada:")
            print(json.dumps(data['results'][0], indent=2, ensure_ascii=False))
            
            # Verifica se todas as portas são do device correto
            all_correct = all(
                port.get('device_id') == device_id 
                for port in data['results']
            )
            
            if all_correct:
                print(f"\n✅ Filtro funcionando! Todas as portas são do device {device_id}")
            else:
                print(f"\n❌ ERRO: Algumas portas não são do device {device_id}")
    else:
        print(f"\n❌ Erro: {response.text}")


def test_ports_with_page_size(device_id: int, page_size: int = 500) -> None:
    """Testa filtro com page_size customizado."""
    print("\n" + "="*60)
    print(f"TESTE 3: GET /api/v1/ports/?device={device_id}&page_size={page_size}")
    print("="*60)
    
    url = f"{BASE_URL}/api/v1/ports/"
    params = {"device": device_id, "page_size": page_size}
    response = requests.get(url, params=params)
    
    print(f"URL completa: {response.url}")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        count = data.get('count', 0)
        results_len = len(data.get('results', []))
        
        print(f"\nTotal no banco: {count}")
        print(f"Retornados nesta página: {results_len}")
        
        if results_len > 100:
            print(f"\n✅ Page size funcionando! Retornou {results_len} registros")
        else:
            print(f"\n⚠️  Retornou apenas {results_len} registros (esperado até {page_size})")
    else:
        print(f"\n❌ Erro: {response.text}")


def get_first_device_id() -> int | None:
    """Pega o ID do primeiro device disponível."""
    url = f"{BASE_URL}/api/v1/devices/"
    try:
        response = requests.get(url, params={"page_size": 1})
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                return data['results'][0]['id']
    except Exception as e:
        print(f"Erro ao buscar device: {e}")
    return None


def main() -> None:
    """Executa todos os testes."""
    print("\n🔍 TESTANDO ENDPOINT DE PORTAS")
    print("="*60)
    
    # Teste 1: Lista geral
    test_ports_list()
    
    # Busca um device para os próximos testes
    device_id = get_first_device_id()
    
    if device_id:
        print(f"\n📌 Usando device_id={device_id} para os próximos testes")
        
        # Teste 2: Filtro por device
        test_ports_filter_by_device(device_id)
        
        # Teste 3: Com page_size
        test_ports_with_page_size(device_id, 500)
    else:
        print("\n⚠️  Não foi possível encontrar um device para testar o filtro")
    
    print("\n" + "="*60)
    print("TESTES CONCLUÍDOS!")
    print("="*60)
    print("\n💡 ENDPOINTS DISPONÍVEIS:")
    print("   GET /api/v1/ports/")
    print("   GET /api/v1/ports/?device=<id>")
    print("   GET /api/v1/ports/?device=<id>&page_size=500")
    print("\n📦 CAMPOS RETORNADOS:")
    print("   - id (port ID)")
    print("   - device (device ID - para write)")
    print("   - device_id (device ID - read-only)")
    print("   - device_name (nome do device)")
    print("   - site_id (ID do site)")
    print("   - site_name (nome do site)")
    print("   - name (nome da porta)")
    print()


if __name__ == "__main__":
    main()
