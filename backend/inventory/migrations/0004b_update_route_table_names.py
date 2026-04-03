from django.db import migrations


class Migration(migrations.Migration):
    """Update model state to reflect renamed route tables (inventory_*).

    Previous migration 0004 performed raw SQL renames without updating the
    Django migration state, causing subsequent migrations to still target
    legacy routes_builder_* table names. This migration aligns the state by
    altering the db_table for Route, RouteSegment, and RouteEvent models.
    """

    dependencies = [
        ("inventory", "0004_rename_route_tables"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="Route",
            table="inventory_route",
        ),
        migrations.AlterModelTable(
            name="RouteSegment",
            table="inventory_routesegment",
        ),
        migrations.AlterModelTable(
            name="RouteEvent",
            table="inventory_routeevent",
        ),
    ]
