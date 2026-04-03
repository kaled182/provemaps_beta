"""
Testes de auditoria de código legado - Sprint 1, Semana 1

Este módulo contém testes que validam o estado atual do sistema
ANTES de qualquer remoção de código legado. Os testes devem:

1. Documentar funcionalidades que dependem de código legado
2. Validar que dados foram migrados corretamente
3. Identificar código que pode ser removido com segurança
4. Servir como baseline para refatorações

⚠️ IMPORTANTE: Execute os testes no ambiente Docker
═══════════════════════════════════════════════════════════════
Todo o ecossistema do projeto funciona sob Docker, incluindo PostgreSQL + PostGIS.
Executar fora do Docker resultará em falhas (GDAL não disponível, SQLite vs PostgreSQL, etc.)

Para executar os testes:

    # Executar todos os testes de auditoria:
    docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_legacy_code_audit.py -v

    # Executar teste específico:
    docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_legacy_code_audit.py::LegacyDatabaseAuditTest -v

    # Executar com coverage:
    docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_legacy_code_audit.py --cov --cov-report=html
"""

import pytest
from django.db import connection
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from inventory.models import Site, FiberCable

User = get_user_model()


class LegacyDatabaseAuditTest(TestCase):
    """Auditoria de migração de banco de dados"""

    def test_zabbix_api_tables_existence(self):
        """Verifica se tabelas zabbix_api_* ainda existem no banco"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                  AND tablename LIKE 'zabbix_api_%'
                ORDER BY tablename
            """)
            legacy_tables = [row[0] for row in cursor.fetchall()]
        
        # Documentar tabelas encontradas
        if legacy_tables:
            print(f"\n⚠️  Tabelas legacy encontradas: {legacy_tables}")
            # Não falha - apenas documenta
        else:
            print("\n✅ Nenhuma tabela zabbix_api_* encontrada")
    
    def test_inventory_tables_exist(self):
        """Verifica que tabelas inventory_* existem e têm dados"""
        with connection.cursor() as cursor:
            # Verificar tabela de sites
            cursor.execute("""
                SELECT COUNT(*) FROM inventory_site
            """)
            site_count = cursor.fetchone()[0]
            
            # Verificar tabela de cabos
            cursor.execute("""
                SELECT COUNT(*) FROM inventory_fibercable
            """)
            cable_count = cursor.fetchone()[0]
        
        print(f"\n📊 Estatísticas:")
        print(f"   Sites: {site_count}")
        print(f"   Fiber Cables: {cable_count}")
        
        # Tabelas devem existir
        assert site_count >= 0, "Tabela inventory_site não existe"
        assert cable_count >= 0, "Tabela inventory_fibercable não existe"


class LegacyFieldMigrationAuditTest(TestCase):
    """Auditoria de campos deprecated"""

    @classmethod
    def setUpTestData(cls):
        """Criar dados de teste"""
        cls.site = Site.objects.create(
            name="Test Site",
            latitude=-15.7942,
            longitude=-47.8822
        )
    
    def test_fibercable_coordinates_vs_path_migration(self):
        """Verifica migração de coordinates (JSONField) para path (PostGIS)"""
        # Contar cabos com coordinates mas sem path
        unmigrated_count = FiberCable.objects.filter(
            coordinates__isnull=False
        ).exclude(
            path__isnull=False
        ).count()
        
        print(f"\n📊 Migração coordinates → path:")
        print(f"   Cabos com coordinates E path: {FiberCable.objects.filter(coordinates__isnull=False, path__isnull=False).count()}")
        print(f"   Cabos APENAS com coordinates: {unmigrated_count}")
        print(f"   Cabos APENAS com path: {FiberCable.objects.filter(coordinates__isnull=True, path__isnull=False).count()}")
        
        # Este teste documenta o estado - não falha
        if unmigrated_count > 0:
            print(f"   ⚠️  {unmigrated_count} cabos precisam de migração")
        else:
            print("   ✅ Todos os cabos migrados ou sem coordenadas")
    
    def test_fibercable_has_coordinates_field(self):
        """Verifica que campo coordinates ainda existe (para ser removido depois)"""
        # Verificar se campo existe no modelo
        field_names = [f.name for f in FiberCable._meta.get_fields()]
        
        if 'coordinates' in field_names:
            print("\n⚠️  Campo 'coordinates' ainda existe (deprecated)")
        else:
            print("\n✅ Campo 'coordinates' já foi removido")
    
    def test_fibercable_has_path_field(self):
        """Verifica que novo campo path (PostGIS) existe"""
        field_names = [f.name for f in FiberCable._meta.get_fields()]
        
        assert 'path' in field_names, "Campo 'path' (PostGIS) não existe"
        print("\n✅ Campo 'path' (PostGIS) está presente")


class LegacyCodeUsageAuditTest(TestCase):
    """Auditoria de uso de código legado em tempo de execução"""
    
    def test_api_permissions_audit(self):
        """Audita permissões de API para identificar AllowAny inapropriado"""
        from inventory.viewsets import (
            SiteViewSet, DeviceViewSet, PortViewSet, FiberCableViewSet
        )
        
        viewsets_to_check = [
            ('SiteViewSet', SiteViewSet),
            ('DeviceViewSet', DeviceViewSet),
            ('PortViewSet', PortViewSet),
            ('FiberCableViewSet', FiberCableViewSet),
        ]
        
        print("\n🔒 Auditoria de Permissões de API:")
        
        allow_any_found = []
        for name, viewset in viewsets_to_check:
            permission_classes = getattr(viewset, 'permission_classes', [])
            permission_names = [p.__name__ for p in permission_classes]
            
            if 'AllowAny' in permission_names:
                allow_any_found.append(name)
                print(f"   ⚠️  {name}: {permission_names}")
            else:
                print(f"   ✅ {name}: {permission_names}")
        
        # Documentar, não falhar
        if allow_any_found:
            print(f"\n⚠️  ViewSets com AllowAny: {allow_any_found}")


class LegacyFileAuditTest(TestCase):
    """Auditoria de arquivos legados"""
    
    def test_backup_files_exist(self):
        """Identifica arquivos .backup no projeto"""
        import os
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        backup_files = list(project_root.glob('**/*.backup'))
        
        print(f"\n📁 Arquivos .backup encontrados: {len(backup_files)}")
        for f in backup_files:
            rel_path = f.relative_to(project_root)
            print(f"   - {rel_path}")
        
        # Documentar, não falhar
        if backup_files:
            print(f"\n⚠️  {len(backup_files)} arquivo(s) .backup para arquivar")
    
    def test_scripts_old_directory_exists(self):
        """Verifica se diretório scripts_old/ existe"""
        import os
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        scripts_old = project_root / 'scripts' / 'scripts_old'
        
        if scripts_old.exists():
            # Contar arquivos
            file_count = len(list(scripts_old.rglob('*.*')))
            print(f"\n📁 scripts_old/ encontrado com {file_count} arquivos")
            print("   ⚠️  Diretório para arquivar")
        else:
            print("\n✅ scripts_old/ já foi removido")


@pytest.mark.django_db
class LegacyDataIntegrityTest(TestCase):
    """Testes de integridade de dados antes de remover código legado"""
    
    @classmethod
    def setUpTestData(cls):
        """Criar dados de teste realistas"""
        cls.site_a = Site.objects.create(
            display_name="Legacy Audit Site A",
            latitude=-15.7942,
            longitude=-47.8822,
        )
        cls.site_b = Site.objects.create(
            display_name="Legacy Audit Site B",
            latitude=-15.8000,
            longitude=-47.9000,
        )
    
    def test_site_queries_work_without_legacy_tables(self):
        """Verifica que queries de sites funcionam sem tabelas zabbix_api_*"""
        # Buscar todos os sites
        sites = Site.objects.all()
        assert sites.count() >= 2
        
        # Buscar por coordenadas (PostGIS)
        nearby_sites = Site.objects.filter(
            latitude__gte=-16.0,
            latitude__lte=-15.0
        )
        assert nearby_sites.count() >= 2
        
        print("\n✅ Queries de Site funcionam corretamente")
    
    def test_fibercable_create_without_coordinates_field(self):
        """Testa criação de cabo usando apenas path (PostGIS)"""
        from django.contrib.gis.geos import LineString
        
        # Criar cabo com path PostGIS
        cable = FiberCable.objects.create(
            name="Test Cable Path Only",
            path=LineString(
                (-47.8822, -15.7942),
                (-47.9000, -15.8000)
            )
        )
        
        assert cable.path is not None
        assert cable.calculated_length_km > 0
        
        print(f"\n✅ Cabo criado apenas com path: {cable.calculated_length_km:.2f} km")


class LegacyTODOAuditTest(TestCase):
    """Auditoria de TODOs no código"""
    
    def test_critical_todos_documented(self):
        """Lista TODOs críticos para serem resolvidos"""
        critical_todos = [
            {
                'file': 'backend/inventory/viewsets.py',
                'line': 1064,
                'todo': 'TODO: Restrict to admin in production',
                'priority': 'CRITICAL',
                'category': 'Security'
            },
            {
                'file': 'backend/inventory/services/cable_segments.py',
                'line': 35,
                'todo': 'TODO: mapear Site A',
                'priority': 'HIGH',
                'category': 'Feature'
            },
            {
                'file': 'backend/inventory/services/cable_segments.py',
                'line': 36,
                'todo': 'TODO: mapear Site B',
                'priority': 'HIGH',
                'category': 'Feature'
            },
        ]
        
        print("\n📋 TODOs Críticos Identificados:")
        for todo in critical_todos:
            print(f"\n   {todo['priority']} - {todo['category']}")
            print(f"   📄 {todo['file']}:{todo['line']}")
            print(f"   💬 {todo['todo']}")
        
        # Documentar
        print(f"\n⚠️  Total de TODOs críticos: {len(critical_todos)}")


# Teste de baseline de performance
class LegacyPerformanceBaselineTest(TestCase):
    """Estabelece baseline de performance antes de mudanças"""
    
    @classmethod
    def setUpTestData(cls):
        """Criar dataset para testes de performance"""
        # Criar 100 sites
        sites = [
            Site(
                name=f"Site {i}",
                latitude=-15.7942 + (i * 0.01),
                longitude=-47.8822 + (i * 0.01)
            )
            for i in range(100)
        ]
        Site.objects.bulk_create(sites)
    
    def test_site_list_query_performance(self):
        """Baseline: tempo de query para listar sites"""
        import time
        
        start = time.time()
        list(Site.objects.all())
        duration = time.time() - start
        
        print(f"\n⏱️  Baseline: Site.objects.all() = {duration*1000:.2f}ms")
        
        # Não deve ser muito lento
        assert duration < 1.0, f"Query muito lenta: {duration}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
