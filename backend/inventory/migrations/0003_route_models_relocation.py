from __future__ import annotations

from django.apps.registry import Apps
from django.db import migrations, models, connection
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
import django.db.models.deletion


def forwards_content_types(
    apps: Apps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(
        app_label="routes_builder",
        model__in=["route", "routesegment", "routeevent"],
    ).update(app_label="inventory")


def backwards_content_types(
    apps: Apps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(
        app_label="inventory",
        model__in=["route", "routesegment", "routeevent"],
    ).update(app_label="routes_builder")


state_operations = [
    migrations.CreateModel(
        name="Route",
        fields=[
            (
                "id",
                models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name="ID",
                ),
            ),
            ("name", models.CharField(max_length=150, unique=True)),
            ("description", models.TextField(blank=True)),
            (
                "status",
                models.CharField(
                    choices=[
                        ("planned", "Planned"),
                        ("active", "Active"),
                        ("degraded", "Degraded"),
                        ("archived", "Archived"),
                    ],
                    default="planned",
                    max_length=20,
                ),
            ),
            (
                "length_km",
                models.DecimalField(
                    blank=True,
                    decimal_places=3,
                    help_text="Total cable length in kilometers.",
                    max_digits=7,
                    null=True,
                ),
            ),
            (
                "estimated_loss_db",
                models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    help_text="Expected optical loss in decibels.",
                    max_digits=5,
                    null=True,
                ),
            ),
            (
                "measured_loss_db",
                models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    help_text="Latest measured optical loss in decibels.",
                    max_digits=5,
                    null=True,
                ),
            ),
            ("last_built_at", models.DateTimeField(blank=True, null=True)),
            ("last_built_by", models.CharField(blank=True, max_length=150)),
            (
                "import_source",
                models.CharField(
                    blank=True,
                    help_text=(
                        "Origin of the data import "
                        "(KML file, planner, etc)."
                    ),
                    max_length=150,
                ),
            ),
            ("metadata", models.JSONField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            (
                "destination_port",
                models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="routes_destination",
                    to="inventory.port",
                ),
            ),
            (
                "origin_port",
                models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="routes_origin",
                    to="inventory.port",
                ),
            ),
        ],
        options={"ordering": ["name"], "db_table": "routes_builder_route"},
    ),
    migrations.CreateModel(
        name="RouteEvent",
        fields=[
            (
                "id",
                models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name="ID",
                ),
            ),
            (
                "event_type",
                models.CharField(
                    choices=[
                        ("build", "Build"),
                        ("status", "Status change"),
                        ("import", "Import"),
                        ("measurement", "Measurement"),
                    ],
                    max_length=30,
                ),
            ),
            ("message", models.TextField(blank=True)),
            ("details", models.JSONField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            (
                "created_by",
                models.CharField(
                    blank=True,
                    help_text="Originator of the event (user, task, import).",
                    max_length=150,
                ),
            ),
            (
                "route",
                models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="events",
                    to="inventory.route",
                ),
            ),
        ],
        options={
            "ordering": ["-created_at"],
            "db_table": "routes_builder_routeevent",
        },
    ),
    migrations.CreateModel(
        name="RouteSegment",
        fields=[
            (
                "id",
                models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name="ID",
                ),
            ),
            (
                "order",
                models.PositiveIntegerField(
                    help_text="Segment order within the route.",
                ),
            ),
            (
                "path_coordinates",
                models.JSONField(
                    blank=True,
                    help_text='Array of {"lat": float, "lng": float} points.',
                    null=True,
                ),
            ),
            (
                "length_km",
                models.DecimalField(
                    blank=True,
                    decimal_places=3,
                    max_digits=7,
                    null=True,
                ),
            ),
            (
                "estimated_loss_db",
                models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=5,
                    null=True,
                ),
            ),
            (
                "measured_loss_db",
                models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=5,
                    null=True,
                ),
            ),
            ("metadata", models.JSONField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            (
                "from_port",
                models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="segments_from",
                    to="inventory.port",
                ),
            ),
            (
                "route",
                models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="segments",
                    to="inventory.route",
                ),
            ),
            (
                "to_port",
                models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="segments_to",
                    to="inventory.port",
                ),
            ),
        ],
        options={
            "ordering": ["route", "order"],
            "unique_together": {("route", "order")},
            "db_table": "routes_builder_routesegment",
        },
    ),
]


class Migration(migrations.Migration):
    # routes_builder app removed; dependency trimmed after consolidation
    dependencies = [
        ("inventory", "0002_alter_port_zabbix_item_id_trafego_in_and_more"),
    ]

    def create_legacy_tables_if_missing(apps, schema_editor):
        """Create legacy routes_builder_* tables if missing.

        Fresh installs lack the old app's tables, so later migrations that
        expect them fail. We add minimal structures only when absent; existing
        deployments are untouched.
        """

        vendor = connection.vendor
        existing = set(connection.introspection.table_names())
        required = {
            "routes_builder_route",
            "routes_builder_routesegment",
            "routes_builder_routeevent",
        }
        if required.issubset(existing):
            print("[migration 0003] Legacy route tables already exist; skipping creation.")
            return  # Legacy tables already present; do nothing

        # Only create for PostgreSQL / MySQL; SQLite handled later in 0007.
        if vendor not in {"postgresql", "mysql"}:
            print(f"[migration 0003] Vendor {vendor} not targeted for legacy table creation.")
            return

        with connection.cursor() as cursor:
            if "routes_builder_route" not in existing:
                print("[migration 0003] Creating routes_builder_route")
                cursor.execute(
                    """
                    CREATE TABLE routes_builder_route (
                        id BIGSERIAL PRIMARY KEY,
                        name VARCHAR(150) UNIQUE NOT NULL,
                        description TEXT NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'planned',
                        length_km NUMERIC(7,3),
                        estimated_loss_db NUMERIC(5,2),
                        measured_loss_db NUMERIC(5,2),
                        last_built_at TIMESTAMP,
                        last_built_by VARCHAR(150) NOT NULL DEFAULT '',
                        import_source VARCHAR(150) NOT NULL DEFAULT '',
                        metadata JSON,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        origin_port_id BIGINT NOT NULL,
                        destination_port_id BIGINT NOT NULL
                    )
                    """
                )
            if "routes_builder_routesegment" not in existing:
                print("[migration 0003] Creating routes_builder_routesegment")
                cursor.execute(
                    """
                    CREATE TABLE routes_builder_routesegment (
                        id BIGSERIAL PRIMARY KEY,
                        route_id BIGINT NOT NULL,
                        "order" INTEGER NOT NULL,
                        from_port_id BIGINT,
                        to_port_id BIGINT,
                        path_coordinates JSON,
                        length_km NUMERIC(7,3),
                        estimated_loss_db NUMERIC(5,2),
                        measured_loss_db NUMERIC(5,2),
                        metadata JSON,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        UNIQUE(route_id, "order")
                    )
                    """
                )
            if "routes_builder_routeevent" not in existing:
                print("[migration 0003] Creating routes_builder_routeevent")
                cursor.execute(
                    """
                    CREATE TABLE routes_builder_routeevent (
                        id BIGSERIAL PRIMARY KEY,
                        event_type VARCHAR(30) NOT NULL,
                        message TEXT NOT NULL,
                        details JSON,
                        created_at TIMESTAMP NOT NULL,
                        created_by VARCHAR(150) NOT NULL DEFAULT '',
                        route_id BIGINT NOT NULL
                    )
                    """
                )
            # Basic indexes (Django will add constraints later as state sync)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS routes_builder_routesegment_route_order_idx "
                "ON routes_builder_routesegment(route_id, \"order\")"
            )
        print("[migration 0003] Legacy route table creation completed.")

    operations = [
        migrations.RunPython(
            create_legacy_tables_if_missing,
            migrations.RunPython.noop,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=state_operations,
            database_operations=[],
        ),
        migrations.RunPython(forwards_content_types, backwards_content_types),
    ]
