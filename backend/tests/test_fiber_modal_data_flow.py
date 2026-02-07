#!/usr/bin/env python3
"""
Script de validação end-to-end para o fluxo de dados do modal de edição de fibras.

Verifica:
1. Endpoint /api/v1/fiber-cables/<id>/ retorna campos enriquecidos
2. Campos necessários para o modal estão presentes
3. IDs de sites/devices/portas são válidos

Uso: python test_fiber_modal_data_flow.py
"""
import os
import sys
import requests

# Configuração
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
FIBER_CABLE_ID = 38  # Cable ID de exemplo (ajuste conforme seu ambiente)

# Campos enriquecidos esperados no response
EXPECTED_ENRICHED_FIELDS = [
    "origin_device_id",
    "origin_device_name", 
    "origin_port_name",
    "origin_site_id",
    "destination_device_id",
    "destination_device_name",
    "destination_port_name",
    "destination_site_id",
]

# Campos básicos necessários
REQUIRED_BASIC_FIELDS = [
    "id",
    "name",
    "origin_port",
    "destination_port",
    "status",
]


def validate_fiber_cable_detail():
    """Valida resposta do endpoint de detalhe de fiber cable."""
    url = f"{BASE_URL}/api/v1/fiber-cables/{FIBER_CABLE_ID}/"
    print(f"\n{'='*80}")
    print(f"Validando endpoint: {url}")
    print(f"{'='*80}\n")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code != 200:
            print(f"\n❌ FALHA: HTTP {response.status_code}")
            print(f"Response body: {response.text[:500]}")
            return False
        
        # Validar JSON
        try:
            data = response.json()
        except ValueError as e:
            print(f"\n❌ FALHA: Resposta não é JSON válido")
            print(f"Erro: {e}")
            print(f"Body: {response.text[:500]}")
            return False
        
        # Validar campos básicos
        print("\n[1] Validando campos básicos...")
        missing_basic = []
        for field in REQUIRED_BASIC_FIELDS:
            if field not in data:
                missing_basic.append(field)
            else:
                print(f"  ✅ {field}: {data[field]}")
        
        if missing_basic:
            print(f"\n❌ FALHA: Campos básicos faltando: {missing_basic}")
            return False
        
        # Validar campos enriquecidos
        print("\n[2] Validando campos enriquecidos...")
        missing_enriched = []
        for field in EXPECTED_ENRICHED_FIELDS:
            if field not in data:
                missing_enriched.append(field)
            else:
                value = data[field]
                print(f"  ✅ {field}: {value}")
        
        if missing_enriched:
            print(f"\n⚠️  AVISO: Campos enriquecidos faltando: {missing_enriched}")
            print("  Modal pode não popular selects automaticamente")
        
        # Validar dados para cascading selects
        print("\n[3] Validando dados para cascading selects (Site → Device → Port)...")
        
        # Origem
        origin_site_id = data.get("origin_site_id")
        origin_device_id = data.get("origin_device_id") 
        origin_port = data.get("origin_port")
        
        if origin_site_id and origin_device_id and origin_port:
            print(f"  ✅ Origem completa: Site {origin_site_id} → Device {origin_device_id} → Port {origin_port}")
        else:
            print(f"  ⚠️  Origem incompleta:")
            print(f"     - origin_site_id: {origin_site_id}")
            print(f"     - origin_device_id: {origin_device_id}")
            print(f"     - origin_port: {origin_port}")
        
        # Destino
        dest_site_id = data.get("destination_site_id")
        dest_device_id = data.get("destination_device_id")
        dest_port = data.get("destination_port")
        
        if dest_site_id and dest_device_id and dest_port:
            print(f"  ✅ Destino completo: Site {dest_site_id} → Device {dest_device_id} → Port {dest_port}")
        else:
            print(f"  ⚠️  Destino incompleto:")
            print(f"     - destination_site_id: {dest_site_id}")
            print(f"     - destination_device_id: {dest_device_id}")
            print(f"     - destination_port: {dest_port}")
        
        # Validar nomes para exibição
        print("\n[4] Validando nomes para exibição no modal...")
        origin_device_name = data.get("origin_device_name")
        origin_port_name = data.get("origin_port_name")
        dest_device_name = data.get("destination_device_name")
        dest_port_name = data.get("destination_port_name")
        
        if origin_device_name and origin_port_name:
            print(f"  ✅ Origem: Device '{origin_device_name}' → Port '{origin_port_name}'")
        else:
            print(f"  ⚠️  Nomes de origem incompletos (device={origin_device_name}, port={origin_port_name})")
        
        if dest_device_name and dest_port_name:
            print(f"  ✅ Destino: Device '{dest_device_name}' → Port '{dest_port_name}'")
        else:
            print(f"  ⚠️  Nomes de destino incompletos (device={dest_device_name}, port={dest_port_name})")
        
        # Resumo final
        print(f"\n{'='*80}")
        all_enriched_present = not missing_enriched
        all_cascading_complete = (
            origin_site_id and origin_device_id and origin_port and
            dest_site_id and dest_device_id and dest_port
        )
        
        if all_enriched_present and all_cascading_complete:
            print("✅ SUCESSO: Todos os campos necessários estão presentes!")
            print("   O modal deve popular os selects automaticamente.")
        else:
            print("⚠️  AVISO: Alguns campos estão faltando.")
            print("   O modal pode não funcionar completamente.")
        
        print(f"{'='*80}\n")
        
        return all_enriched_present and all_cascading_complete
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERRO de conexão: {e}")
        return False


def main():
    """Função principal."""
    print("\n" + "="*80)
    print("TESTE END-TO-END: Fluxo de dados do modal de edição de fibras")
    print("="*80)
    
    success = validate_fiber_cable_detail()
    
    if success:
        print("\n✅ Validação concluída com sucesso!")
        print("   Frontend deve conseguir popular o modal corretamente.")
        sys.exit(0)
    else:
        print("\n❌ Validação falhou!")
        print("   Verifique os campos faltantes acima.")
        sys.exit(1)


if __name__ == "__main__":
    main()
