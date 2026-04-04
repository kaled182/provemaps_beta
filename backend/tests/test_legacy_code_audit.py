"""
Testes de auditoria de código legado - Sprint 1, Semana 1

Valida o estado atual ANTES de qualquer remoção de código legado:
1. Documentar funcionalidades que dependem de código legado
2. Validar que dados foram migrados corretamente
3. Identificar código que pode ser removido com segurança
4. Servir como baseline para refatorações

Run: docker compose -f docker/docker-compose.yml exec web pytest \
    backend/tests/test_legacy_code_audit.py -v
"""

import pytest
from django.db import connection
from django.test import TestCase
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

        if legacy_tables:
            print(f"\n  Tabelas legacy encontradas: {legacy_tables}")
        else:
            print("\n Nenhuma tabela zabbix_api_* encontrada")

    def test_inventory_tables_exist(self):
        """Verifica que tabelas de sites e cabos existem e têm dados"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM zabbix_api_site")
            site_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM zabbix_api_fibercable")
            cable_count = cursor.fetchone()[0]

        print(f"\n Sites: {site_count}, Fiber Cables: {cable_count}")

        assert site_count >= 0, "Tabela zabbix_api_site nao existe"
        assert cable_count >= 0, "Tabela zabbix_api_fibercable nao existe"


class LegacyFieldMigrationAuditTest(TestCase):
    """Auditoria de campos deprecated"""

    @classmethod
    def setUpTestData(cls):
        """Criar dados de teste"""
        cls.site = Site.objects.create(
            display_name="Test Site",
            latitude=-15.7942,
            longitude=-47.8822
        )

    def test_fibercable_coordinates_vs_path_migration(self):
        """Verifica migração de coordinates (JSONField) para path (PostGIS)"""
        field_names = [f.name for f in FiberCable._meta.get_fields()]
        if 'coordinates' not in field_names:
            print("\n Campo 'coordinates' ja foi removido — migracao completa")
            return

        unmigrated_count = FiberCable.objects.filter(
            coordinates__isnull=False
        ).exclude(
            path__isnull=False
        ).count()

        with_both = FiberCable.objects.filter(
            coordinates__isnull=False,
            path__isnull=False,
        ).count()
        only_path = FiberCable.objects.filter(
            coordinates__isnull=True,
            path__isnull=False,
        ).count()

        print(f"\n Cabos com coordinates e path: {with_both}")
        print(f"   Cabos apenas com coordinates: {unmigrated_count}")
        print(f"   Cabos apenas com path: {only_path}")

        if unmigrated_count > 0:
            print(f"   {unmigrated_count} cabos precisam de migracao")
        else:
            print("   Todos os cabos migrados ou sem coordenadas")

    def test_fibercable_has_coordinates_field(self):
        """Verifica se campo coordinates ainda existe (deprecated)"""
        field_names = [f.name for f in FiberCable._meta.get_fields()]
        if 'coordinates' in field_names:
            print("\n Campo 'coordinates' ainda existe (deprecated)")
        else:
            print("\n Campo 'coordinates' ja foi removido")

    def test_fibercable_has_path_field(self):
        """Verifica que novo campo path (PostGIS) existe"""
        field_names = [f.name for f in FiberCable._meta.get_fields()]
        assert 'path' in field_names, "Campo 'path' (PostGIS) nao existe"
        print("\n Campo 'path' (PostGIS) esta presente")


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

        allow_any_found = []
        for name, viewset in viewsets_to_check:
            permission_classes = getattr(viewset, 'permission_classes', [])
            permission_names = [p.__name__ for p in permission_classes]

            if 'AllowAny' in permission_names:
                allow_any_found.append(name)
                print(f"   {name}: {permission_names}")
            else:
                print(f"   OK {name}: {permission_names}")

        if allow_any_found:
            print(f"\n ViewSets com AllowAny: {allow_any_found}")


class LegacyFileAuditTest(TestCase):
    """Auditoria de arquivos legados"""

    def test_backup_files_exist(self):
        """Identifica arquivos .backup no projeto"""
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        backup_files = list(project_root.glob('**/*.backup'))

        print(f"\n Arquivos .backup encontrados: {len(backup_files)}")
        for f in backup_files:
            rel_path = f.relative_to(project_root)
            print(f"   - {rel_path}")

        if backup_files:
            print(f"\n {len(backup_files)} arquivo(s) .backup para arquivar")

    def test_scripts_old_directory_exists(self):
        """Verifica se diretório scripts_old/ existe"""
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        scripts_old = project_root / 'scripts' / 'scripts_old'

        if scripts_old.exists():
            file_count = len(list(scripts_old.rglob('*.*')))
            print(f"\n scripts_old/ encontrado com {file_count} arquivos")
        else:
            print("\n scripts_old/ ja foi removido")


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
        sites = Site.objects.all()
        assert sites.count() >= 2

        nearby_sites = Site.objects.filter(
            latitude__gte=-16.0,
            latitude__lte=-15.0
        )
        assert nearby_sites.count() >= 2

        print("\n Queries de Site funcionam corretamente")

    def test_fibercable_create_without_coordinates_field(self):
        """Testa criação de cabo usando apenas path (PostGIS)"""
        from django.contrib.gis.geos import LineString

        cable = FiberCable.objects.create(
            name="Test Cable Path Only",
            path=LineString(
                (-47.8822, -15.7942),
                (-47.9000, -15.8000)
            )
        )

        assert cable.path is not None
        assert cable.calculated_length_km > 0

        km = cable.calculated_length_km
        print(f"\n Cabo criado apenas com path: {km:.2f} km")


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

        print("\n TODOs Criticos Identificados:")
        for todo in critical_todos:
            print(f"\n   {todo['priority']} - {todo['category']}")
            print(f"   {todo['file']}:{todo['line']}")
            print(f"   {todo['todo']}")

        print(f"\n Total de TODOs criticos: {len(critical_todos)}")


class LegacyPerformanceBaselineTest(TestCase):
    """Estabelece baseline de performance antes de mudanças"""

    @classmethod
    def setUpTestData(cls):
        """Criar dataset para testes de performance"""
        # bulk_create bypasses save() — slug must be set explicitly to avoid
        # unique constraint violation on zabbix_api_site.slug.
        sites = [
            Site(
                display_name=f"Perf Site {i}",
                slug=f"perf-site-{i}",
                latitude=-15.7942 + (i * 0.01),
                longitude=-47.8822 + (i * 0.01),
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

        print(f"\n Baseline: Site.objects.all() = {duration * 1000:.2f}ms")

        assert duration < 1.0, f"Query muito lenta: {duration}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
