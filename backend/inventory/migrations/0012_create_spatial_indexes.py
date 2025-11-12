# backend/inventory/migrations/0012_create_spatial_indexes.py
"""
Phase 10.3: Create GiST (Generalized Search Tree) indexes for spatial fields.

GiST indexes enable fast spatial queries:
- BBox filtering (path__bboverlaps)
- Distance calculations (path__distance_lt)
- Intersection queries (path__intersects)

Performance: O(log n) instead of O(n) for spatial queries.
"""
from django.db import connection, migrations


def create_spatial_indexes(apps, schema_editor):
    """Create GiST indexes only when the database supports PostGIS."""

    if schema_editor.connection.vendor != "postgresql":
        print("SKIP: Spatial indexes require PostgreSQL; skipping creation")
        return

    statements = [
        """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS
                inventory_routesegment_path_gist
            ON inventory_routesegment
            USING GIST (path);
        """,
        """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS
                zabbix_api_fibercable_path_gist
            ON zabbix_api_fibercable
            USING GIST (path);
        """,
    ]

    with schema_editor.connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def drop_spatial_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    statements = [
        "DROP INDEX IF EXISTS inventory_routesegment_path_gist;",
        "DROP INDEX IF EXISTS zabbix_api_fibercable_path_gist;",
    ]

    with schema_editor.connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0011_populate_spatial_fields'),
    ]

    # Atomic=False allows CREATE INDEX CONCURRENTLY (no table lock)
    atomic = False

    operations = [
        migrations.RunPython(create_spatial_indexes, drop_spatial_indexes),
    ]
