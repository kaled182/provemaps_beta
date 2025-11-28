#!/usr/bin/env python
"""Teste rápido do endpoint /api/v1/fiber-cables/<id>/

Valida presença dos campos enriquecidos adicionados ao FiberCableSerializer.
"""
import requests
import json

BASE_URL = "http://localhost:8000"

ENRICHED_FIELDS = [
    "origin_port_name",
    "destination_port_name",
    "origin_device_id",
    "origin_device_name",
    "destination_device_id",
    "destination_device_name",
    "origin_site_id",
    "origin_site_name",
    "destination_site_id",
    "destination_site_name",
]

def get_first_fiber_id():
    url = f"{BASE_URL}/api/v1/fiber-cables/"
    r = requests.get(url)
    if r.status_code != 200:
        print("❌ Falha listando fiber-cables:", r.status_code, r.text)
        return None
    data = r.json()
    results = data.get("results") or []
    if not results:
        print("⚠️ Nenhum fiber cable encontrado.")
        return None
    return results[0]["id"]

def test_detail(cable_id: int):
    url = f"{BASE_URL}/api/v1/fiber-cables/{cable_id}/"
    r = requests.get(url)
    print("\nGET", url, "->", r.status_code)
    if r.status_code != 200:
        print("❌ Erro:", r.text)
        return
    data = r.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    missing = [f for f in ENRICHED_FIELDS if f not in data]
    if missing:
        print("\n⚠️ Campos ausentes:", missing)
    else:
        print("\n✅ Todos os campos enriquecidos presentes!")

if __name__ == "__main__":
    print("🔍 Testando fiber-cables detail")
    fid = get_first_fiber_id()
    if fid:
        test_detail(fid)
    else:
        print("Encerrando sem teste de detalhe.")
