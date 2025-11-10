"""Squashed migration removing legacy routes_builder tables."""

from __future__ import annotations

from django.db import migrations

DROP_LEGACY_TABLES_SQL = """
DROP TABLE IF EXISTS routes_builder_routeevent;
DROP TABLE IF EXISTS routes_builder_routesegment;
DROP TABLE IF EXISTS routes_builder_route;
"""


class Migration(migrations.Migration):
    initial = True

    replaces = [
        ("routes_builder", "0001_initial"),
        ("routes_builder", "0002_move_route_models_to_inventory"),
    ]

    dependencies = [
        ("inventory", "0004_rename_route_tables"),
    ]

    operations = [
        migrations.RunSQL(
            sql=DROP_LEGACY_TABLES_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
