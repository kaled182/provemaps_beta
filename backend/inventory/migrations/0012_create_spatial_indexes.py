# backend/inventory/migrations/0012_create_spatial_indexes.py
"""
Phase 10.3: Create GiST (Generalized Search Tree) indexes for spatial fields.

GiST indexes enable fast spatial queries:
- BBox filtering (path__bboverlaps)
- Distance calculations (path__distance_lt)
- Intersection queries (path__intersects)

Performance: O(log n) instead of O(n) for spatial queries.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0011_populate_spatial_fields'),
    ]

    # Atomic=False allows CREATE INDEX CONCURRENTLY (no table lock)
    atomic = False

    operations = [
        # RouteSegment spatial index
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    inventory_routesegment_path_gist
                ON inventory_routesegment
                USING GIST (path);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS inventory_routesegment_path_gist;
            """,
        ),
        
        # FiberCable spatial index
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    zabbix_api_fibercable_path_gist
                ON zabbix_api_fibercable
                USING GIST (path);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS zabbix_api_fibercable_path_gist;
            """,
        ),
    ]
