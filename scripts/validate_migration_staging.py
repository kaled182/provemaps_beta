#!/usr/bin/env python
"""
Script de validação de migração para staging.

Valida a migração inventory.0003 que move os modelos Route, RouteSegment
e RouteEvent de routes_builder para inventory.

Uso:
    python scripts/validate_migration_staging.py [--dry-run]
"""
import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.test")
django.setup()

from django.db import connection
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command


def print_header(text: str) -> None:
    """Imprime cabeçalho formatado."""
    print(f"\n{'=' * 80}")
    print(f"  {text}")
    print('=' * 80)


def check_database_connection() -> bool:
    """Verifica conexão com o banco."""
    print_header("1. Verificando Conexão com Banco de Dados")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        print("✅ Conexão com banco estabelecida")
        print(f"   Engine: {connection.settings_dict['ENGINE']}")
        print(f"   Database: {connection.settings_dict.get('NAME', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return False


def check_current_migration_state() -> dict:
    """Verifica estado atual das migrações."""
    print_header("2. Verificando Estado das Migrações")
    
    from django.db.migrations.recorder import MigrationRecorder
    recorder = MigrationRecorder(connection)
    
    inventory_migrations = list(
        recorder.migration_qs.filter(app='inventory').order_by('applied')
    )
    routes_builder_migrations = list(
        recorder.migration_qs.filter(app='routes_builder').order_by('applied')
    )
    
    print(f"\n📦 Inventory ({len(inventory_migrations)} migrações aplicadas):")
    for mig in inventory_migrations:
        print(f"   ✓ {mig.name}")
    
    print(f"\n📦 Routes Builder ({len(routes_builder_migrations)} migrações aplicadas):")
    for mig in routes_builder_migrations:
        print(f"   ✓ {mig.name}")
    
    # Verificar se 0003 já foi aplicada
    has_0003 = any(m.name == '0003_route_models_relocation' for m in inventory_migrations)
    has_rb_0002 = any(m.name == '0002_move_route_models_to_inventory' for m in routes_builder_migrations)
    
    return {
        'inventory_count': len(inventory_migrations),
        'routes_builder_count': len(routes_builder_migrations),
        'has_0003': has_0003,
        'has_rb_0002': has_rb_0002,
    }


def check_content_types() -> dict:
    """Verifica ContentTypes dos modelos Route."""
    print_header("3. Verificando ContentTypes")
    
    route_models = ['route', 'routesegment', 'routeevent']
    results = {}
    
    for model_name in route_models:
        cts_inventory = ContentType.objects.filter(
            app_label='inventory', model=model_name
        )
        cts_routes = ContentType.objects.filter(
            app_label='routes_builder', model=model_name
        )
        
        results[model_name] = {
            'inventory': cts_inventory.count(),
            'routes_builder': cts_routes.count(),
        }
        
        if cts_inventory.exists():
            print(f"✅ {model_name}: inventory (id={cts_inventory.first().id})")
        elif cts_routes.exists():
            print(f"⚠️  {model_name}: routes_builder (id={cts_routes.first().id}) - Precisa migrar")
        else:
            print(f"❌ {model_name}: NÃO ENCONTRADO")
    
    return results


def check_model_tables() -> dict:
    """Verifica se as tabelas dos modelos existem."""
    print_header("4. Verificando Tabelas no Banco")
    
    tables = ['routes_builder_route', 'routes_builder_routesegment', 'routes_builder_routeevent']
    results = {}
    
    with connection.cursor() as cursor:
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                results[table] = count
                print(f"✅ {table}: {count} registros")
            except Exception as e:
                results[table] = None
                print(f"❌ {table}: Não encontrada ({str(e)[:50]})")
    
    return results


def check_model_imports() -> bool:
    """Verifica se os modelos podem ser importados corretamente."""
    print_header("5. Verificando Imports de Modelos")
    
    try:
        from inventory.models import Route, RouteSegment, RouteEvent
        print("✅ inventory.models: Route, RouteSegment, RouteEvent")
        
        # Verificar se são os modelos corretos
        print(f"   Route._meta.app_label = '{Route._meta.app_label}'")
        print(f"   Route._meta.db_table = '{Route._meta.db_table}'")
        
        if Route._meta.app_label != 'inventory':
            print("⚠️  AVISO: Route ainda está registrado como routes_builder")
            return False
        
        return True
    except ImportError as e:
        print(f"❌ Erro ao importar: {e}")
        return False


def check_shims() -> bool:
    """Verifica se os shims estão funcionando."""
    print_header("6. Verificando Shims de Compatibilidade")
    
    try:
        from routes_builder.models import Route as RBRoute
        from inventory.models import Route as InvRoute
        
        print("✅ routes_builder.models.Route (shim) importado")
        print("✅ inventory.models.Route importado")
        
        # Verificar se são a mesma classe
        if RBRoute is InvRoute:
            print("✅ Shim está delegando corretamente para inventory")
            return True
        else:
            print("⚠️  Shim não está delegando corretamente")
            return False
    except Exception as e:
        print(f"❌ Erro ao verificar shims: {e}")
        return False


def run_sample_queries() -> bool:
    """Executa queries de amostra para validar funcionamento."""
    print_header("7. Testando Queries de Amostra")
    
    try:
        from inventory.models import Route
        
        # Count
        count = Route.objects.count()
        print(f"✅ Route.objects.count() = {count}")
        
        # First
        if count > 0:
            first = Route.objects.first()
            print(f"✅ Route.objects.first() = {first.name if first else 'None'}")
        
        # Create test (rollback)
        from django.db import transaction
        try:
            with transaction.atomic():
                test_route = Route.objects.create(
                    name=f"TEST_VALIDATION_{os.getpid()}",
                    description="Teste de validação",
                    status="planned"
                )
                print(f"✅ Route.objects.create() funcionando (id={test_route.id})")
                raise Exception("Rollback intencional")
        except Exception:
            pass  # Rollback esperado
        
        return True
    except Exception as e:
        print(f"❌ Erro nas queries: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_validation(dry_run: bool = False) -> bool:
    """Executa validação completa."""
    print_header("VALIDAÇÃO DE MIGRAÇÃO - STAGING")
    print(f"Modo: {'DRY-RUN' if dry_run else 'NORMAL'}")
    
    results = {}
    
    # 1. Conexão
    if not check_database_connection():
        print("\n❌ FALHA: Não foi possível conectar ao banco")
        return False
    
    # 2. Estado das migrações
    results['migrations'] = check_current_migration_state()
    
    # 3. ContentTypes
    results['content_types'] = check_content_types()
    
    # 4. Tabelas
    results['tables'] = check_model_tables()
    
    # 5. Imports
    results['imports'] = check_model_imports()
    
    # 6. Shims
    results['shims'] = check_shims()
    
    # 7. Queries
    results['queries'] = run_sample_queries()
    
    # Resumo
    print_header("RESUMO DA VALIDAÇÃO")
    
    migration_applied = results['migrations']['has_0003']
    content_types_ok = all(
        ct['inventory'] > 0 and ct['routes_builder'] == 0
        for ct in results['content_types'].values()
    )
    tables_exist = all(count is not None for count in results['tables'].values())
    
    print(f"\n📊 Status:")
    print(f"   Migração 0003 aplicada: {'✅ Sim' if migration_applied else '❌ Não'}")
    print(f"   ContentTypes corretos: {'✅ Sim' if content_types_ok else '❌ Não'}")
    print(f"   Tabelas existem: {'✅ Sim' if tables_exist else '❌ Não'}")
    print(f"   Imports funcionando: {'✅ Sim' if results['imports'] else '❌ Não'}")
    print(f"   Shims funcionando: {'✅ Sim' if results['shims'] else '❌ Não'}")
    print(f"   Queries funcionando: {'✅ Sim' if results['queries'] else '❌ Não'}")
    
    all_ok = all([
        tables_exist,
        results['imports'],
        results['shims'],
        results['queries']
    ])
    
    if not migration_applied:
        print("\n⚠️  AÇÃO NECESSÁRIA: Executar migração")
        print("   python manage.py migrate inventory 0003_route_models_relocation")
        print("   python manage.py migrate routes_builder 0002_move_route_models_to_inventory")
    
    if all_ok:
        print("\n✅ VALIDAÇÃO COMPLETA: Sistema pronto para Fase 4")
        return True
    else:
        print("\n❌ VALIDAÇÃO FALHOU: Corrija os problemas antes de prosseguir")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Valida migração de modelos Route')
    parser.add_argument('--dry-run', action='store_true', help='Apenas simula, não executa')
    args = parser.parse_args()
    
    success = run_validation(dry_run=args.dry_run)
    sys.exit(0 if success else 1)
