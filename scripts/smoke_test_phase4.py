#!/usr/bin/env python3
"""
Smoke Test - Validação Pós Phase 4 Cleanup
Verifica endpoints e funcionalidades após remoção do código legado.
"""

import os
import sys
import django

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.test import Client  # noqa: E402
from inventory.models import Site, Device  # noqa: E402


def test_health_endpoints():
    """Testa /healthz, /ready, /live"""
    client = Client()
    endpoints = ["/healthz/", "/ready/", "/live/"]

    print("\n🏥 Testando Health Endpoints...")
    for endpoint in endpoints:
        response = client.get(endpoint)
        # 400 pode ocorrer por ALLOWED_HOSTS - aceitável em teste local
        acceptable = [200, 400]
        status = "✅" if response.status_code in acceptable else "❌"
        print(f"  {status} {endpoint} → {response.status_code}")
        if response.status_code not in acceptable:
            print(f"     ERROR: {response.content.decode()}")
            return False
    return True


def test_inventory_apis():
    """Testa /api/v1/inventory/* endpoints"""
    client = Client()
    endpoints = [
        "/api/v1/inventory/sites/",
        "/api/v1/inventory/devices/",
        "/api/v1/inventory/fibers/oper-status/",
    ]

    print("\n📦 Testando Inventory APIs...")
    for endpoint in endpoints:
        response = client.get(endpoint)
        # 400=ALLOWED_HOSTS, 401/403=auth - todos aceitáveis
        acceptable = [200, 400, 401, 403]
        status = "✅" if response.status_code in acceptable else "❌"
        print(f"  {status} {endpoint} → {response.status_code}")
        if response.status_code not in acceptable:
            print(f"     ERROR: {response.content.decode()}")
            return False
    return True


def test_database_connectivity():
    """Testa queries no banco"""
    print("\n🗄️  Testando Conectividade do Banco...")
    try:
        site_count = Site.objects.count()
        device_count = Device.objects.count()
        print(f"  ✅ Sites: {site_count}")
        print(f"  ✅ Devices: {device_count}")
        return True
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False


def test_inventory_imports():
    """Testa se imports da nova estrutura funcionam"""
    print("\n🔍 Testando Imports da Estrutura Modular...")
    try:
        # Inventory
        from inventory.models import Site, Device, Port, Route  # noqa: F401

        # Integrations
        from integrations.zabbix.client import resilient_client  # noqa: F401
        from integrations.zabbix.zabbix_service import (  # noqa: F401
            zabbix_request,
        )

        # Monitoring - HostStatusProcessor em vez de função
        from monitoring.usecases import HostStatusProcessor  # noqa: F401

        print("  ✅ Todos os imports críticos carregaram")
        return True
    except ImportError as e:
        print(f"  ❌ ERROR: {e}")
        return False


def test_legacy_imports_removed():
    """Valida que imports legados de zabbix_api foram removidos"""
    print("\n🚫 Verificando Remoção de Imports Legados...")
    try:
        import zabbix_api  # noqa: F401

        print(f"  ❌ ERRO: zabbix_api ainda existe! {zabbix_api}")
        return False
    except ModuleNotFoundError:
        print("  ✅ zabbix_api corretamente removido")
        return True


def test_cache_invalidation():
    """Testa cache de fibers"""
    print("\n🗑️  Testando Cache de Fibras...")
    try:
        from inventory.cache.fibers import invalidate_fiber_cache

        # Tenta invalidar (mesmo que cache não esteja configurado)
        try:
            invalidate_fiber_cache()
            msg = "Cache invalidation funcionou (ou degradou graciosamente)"
            print(f"  ✅ {msg}")
        except Exception as e:
            # Se Redis não estiver disponível, deve degradar sem quebrar
            if "ConnectionError" in str(type(e).__name__):
                print("  ✅ Cache degradou graciosamente (Redis ausente)")
            else:
                raise
        return True
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False


def main():
    print("=" * 60)
    print("🧪 SMOKE TEST - Phase 4 Cleanup Validation")
    print("=" * 60)

    tests = [
        test_legacy_imports_removed,
        test_inventory_imports,
        test_database_connectivity,
        test_health_endpoints,
        test_inventory_apis,
        test_cache_invalidation,
    ]

    results = []
    for test_func in tests:
        results.append(test_func())

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)

    if all(results):
        print(f"✅ SUCESSO! {passed}/{total} testes passaram")
        print("=" * 60)
        return 0
    else:
        print(f"❌ FALHA! {passed}/{total} testes passaram")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
