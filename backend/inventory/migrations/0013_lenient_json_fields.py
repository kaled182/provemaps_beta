# Generated manually to adopt the lenient JSONField wrapper.
from __future__ import annotations

from django.db import migrations

import inventory.fields


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0012_create_spatial_indexes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fibercable",
            name="path_coordinates",
            field=inventory.fields.LenientJSONField(
                blank=True,
                help_text=(
                    "Coordinate list e.g. [{'lat': -16.6, 'lng': -49.2}, "
                    "...]. Deprecated: use path field."
                ),
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="routesegment",
            name="path_coordinates",
            field=inventory.fields.LenientJSONField(
                blank=True,
                help_text=(
                    'Array of {"lat": float, "lng": float} points. '
                    'Deprecated: use path field with PostGIS.'
                ),
                null=True,
            ),
        ),
    ]
