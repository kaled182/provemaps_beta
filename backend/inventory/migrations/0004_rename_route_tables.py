# Generated migration - Phase 4 cleanup (2025-11-07)
# Renames route tables from routes_builder_* to inventory_*
# This resolves pytest serialization issues and aligns table names with
# model ownership

from django.db import connection, migrations


def rename_tables_if_needed(apps, schema_editor):
    """Rename tables only if they exist with the old name."""
    with connection.cursor() as cursor:
        # Check database type
        db_vendor = connection.vendor
        
        if db_vendor == 'sqlite':
            # SQLite: Check if old table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='routes_builder_route'"
            )
            if cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE routes_builder_route "
                    "RENAME TO inventory_route"
                )
                cursor.execute(
                    "ALTER TABLE routes_builder_routesegment "
                    "RENAME TO inventory_routesegment"
                )
                cursor.execute(
                    "ALTER TABLE routes_builder_routeevent "
                    "RENAME TO inventory_routeevent"
                )
        elif db_vendor in ('mysql', 'postgresql'):
            # MySQL/PostgreSQL: Use information_schema
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name='routes_builder_route'"
            )
            if cursor.fetchone():
                if db_vendor == 'mysql':
                    cursor.execute(
                        "RENAME TABLE routes_builder_route "
                        "TO inventory_route"
                    )
                    cursor.execute(
                        "RENAME TABLE routes_builder_routesegment "
                        "TO inventory_routesegment"
                    )
                    cursor.execute(
                        "RENAME TABLE routes_builder_routeevent "
                        "TO inventory_routeevent"
                    )
                else:  # postgresql
                    cursor.execute(
                        "ALTER TABLE routes_builder_route "
                        "RENAME TO inventory_route"
                    )
                    cursor.execute(
                        "ALTER TABLE routes_builder_routesegment "
                        "RENAME TO inventory_routesegment"
                    )
                    cursor.execute(
                        "ALTER TABLE routes_builder_routeevent "
                        "RENAME TO inventory_routeevent"
                    )


def reverse_rename_tables(apps, schema_editor):
    """Reverse the table renames."""
    with connection.cursor() as cursor:
        db_vendor = connection.vendor
        
        if db_vendor == 'sqlite':
            cursor.execute(
                "ALTER TABLE inventory_route "
                "RENAME TO routes_builder_route"
            )
            cursor.execute(
                "ALTER TABLE inventory_routesegment "
                "RENAME TO routes_builder_routesegment"
            )
            cursor.execute(
                "ALTER TABLE inventory_routeevent "
                "RENAME TO routes_builder_routeevent"
            )
        elif db_vendor in ('mysql', 'postgresql'):
            if db_vendor == 'mysql':
                cursor.execute(
                    "RENAME TABLE inventory_route "
                    "TO routes_builder_route"
                )
                cursor.execute(
                    "RENAME TABLE inventory_routesegment "
                    "TO routes_builder_routesegment"
                )
                cursor.execute(
                    "RENAME TABLE inventory_routeevent "
                    "TO routes_builder_routeevent"
                )
            else:  # postgresql
                cursor.execute(
                    "ALTER TABLE inventory_route "
                    "RENAME TO routes_builder_route"
                )
                cursor.execute(
                    "ALTER TABLE inventory_routesegment "
                    "RENAME TO routes_builder_routesegment"
                )
                cursor.execute(
                    "ALTER TABLE inventory_routeevent "
                    "RENAME TO routes_builder_routeevent"
                )


class Migration(migrations.Migration):
    """
    Rename route-related tables to align with inventory app ownership.
    
    Context:
    - Models were relocated from routes_builder to inventory in migration 0003
    - ContentType.app_label updated to 'inventory'
    - But db_table still used 'routes_builder_*' prefix (legacy compatibility)
    - This caused pytest-django serialization failures when routes_builder
      removed from INSTALLED_APPS
    
    Solution:
    - Rename tables to match new app ownership: inventory_route, etc.
    - Update models.py to use new table names
    - After this, routes_builder app can be safely removed from
      INSTALLED_APPS
    - Uses RunPython with conditional logic to handle both fresh and
      existing databases
    """

    dependencies = [
        ("inventory", "0003_route_models_relocation"),
    ]

    operations = [
        migrations.RunPython(
            rename_tables_if_needed,
            reverse_rename_tables,
        ),
    ]
