from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0056_remove_path_coordinates_field"),
    ]

    operations = [
        migrations.CreateModel(
            name="CableGroup",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                ("manufacturer", models.CharField(blank=True, max_length=255)),
                (
                    "fiber_count",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        help_text="Number of fibers in the cable",
                    ),
                ),
                (
                    "attenuation_db_per_km",
                    models.DecimalField(
                        blank=True,
                        decimal_places=3,
                        max_digits=5,
                        null=True,
                        help_text=(
                            "Attenuation in dB/km for optical budget"
                            " calculation"
                        ),
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "inventory_cable_group",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="fibercable",
            name="cable_group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cables",
                to="inventory.cablegroup",
                help_text=(
                    "Cable type/group for categorization and optical budget"
                ),
            ),
        ),
    ]
