from __future__ import annotations

from django.db import migrations


state_operations = [
    migrations.DeleteModel(name="RouteEvent"),
    migrations.DeleteModel(name="RouteSegment"),
    migrations.DeleteModel(name="Route"),
]


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0003_route_models_relocation"),
        ("routes_builder", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=state_operations,
            database_operations=[],
        )
    ]
