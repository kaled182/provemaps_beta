from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("inventory", "0001_initial_from_existing_tables"),
    ]

    operations = [
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
                        max_length=20,
                        choices=[
                            ("planned", "Planned"),
                            ("active", "Active"),
                            ("degraded", "Degraded"),
                            ("archived", "Archived"),
                        ],
                        default="planned",
                    ),
                ),
                (
                    "length_km",
                    models.DecimalField(
                        max_digits=7,
                        decimal_places=3,
                        null=True,
                        blank=True,
                        help_text="Total cable length in kilometers.",
                    ),
                ),
                (
                    "estimated_loss_db",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Expected optical loss in decibels.",
                    ),
                ),
                (
                    "measured_loss_db",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Latest measured optical loss in decibels.",
                    ),
                ),
                ("last_built_at", models.DateTimeField(null=True, blank=True)),
                ("last_built_by", models.CharField(blank=True, max_length=150)),
                (
                    "import_source",
                    models.CharField(
                        max_length=150,
                        blank=True,
                        help_text="Origin of the data import (KML file, planner, etc).",
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
            options={"ordering": ["name"]},
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
                        max_length=30,
                        choices=[
                            ("build", "Build"),
                            ("status", "Status change"),
                            ("import", "Import"),
                            ("measurement", "Measurement"),
                        ],
                    ),
                ),
                ("message", models.TextField(blank=True)),
                ("details", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.CharField(
                        max_length=150,
                        blank=True,
                        help_text="Originator of the event (user, task, import).",
                    ),
                ),
                (
                    "route",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="routes_builder.route",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
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
                        null=True,
                        help_text='Array of {"lat": float, "lng": float} points.',
                    ),
                ),
                (
                    "length_km",
                    models.DecimalField(
                        max_digits=7,
                        decimal_places=3,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "estimated_loss_db",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "measured_loss_db",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
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
                        to="routes_builder.route",
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
            },
        ),
    ]
