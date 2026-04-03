# Consolidated migration (Phase 4 cleanup)
# Convert Route / RouteSegment / RouteEvent db_table names from
# routes_builder_* to inventory_* using state-aware operations.
# This replaces prior raw SQL rename logic and removes need for
# follow-up state alignment migration.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0003_route_models_relocation"),
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
