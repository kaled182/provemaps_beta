# backend/inventory/migrations/0010_add_spatial_fields.py
"""
Phase 10: Add spatial fields to RouteSegment and FiberCable.

This migration adds LineStringField for PostGIS spatial queries while keeping
path_coordinates JSONField for backward compatibility with MySQL.
"""
from django.core.exceptions import ImproperlyConfigured

try:
    from django.contrib.gis.db import models as gis_gis_models
    HAS_GDAL = True
except (ImproperlyConfigured, ImportError, ModuleNotFoundError):
    from django.db import models as base_models

    HAS_GDAL = False

    class _FallbackLineStringField(base_models.JSONField):
        description = "JSON fallback for LineString when GDAL is unavailable"

        def __init__(self, *args, **kwargs):
            for param in ('srid', 'dim', 'geography', 'spatial_index'):
                kwargs.pop(param, None)
            super().__init__(*args, **kwargs)

    class _FallbackModule:
        LineStringField = _FallbackLineStringField
        JSONField = base_models.JSONField

    gis_gis_models = _FallbackModule()
else:
    gis_gis_models = gis_gis_models

gis_models = gis_gis_models
from django.db import migrations


class Migration(migrations.Migration):

    # Fix dependency name: original referenced non-existent '0009_fibercable_status_cache'
    # Actual migration filename is '0009_fibercable_last_live_check_and_more'
    dependencies = [
        ('inventory', '0009_fibercable_last_live_check_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='fibercable',
            name='path',
            field=gis_models.LineStringField(
                srid=4326,
                blank=True,
                null=True,
                help_text='Spatial path geometry for PostGIS spatial queries (bbox filtering).',
            ),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='routesegment',
                    name='path',
                    field=gis_models.LineStringField(
                        srid=4326,
                        blank=True,
                        null=True,
                        help_text='Spatial path geometry for PostGIS spatial queries (bbox filtering).',
                    ),
                ),
            ],
            database_operations=(
                [
                    migrations.RunSQL(
                        sql=(
                            "ALTER TABLE inventory_routesegment "
                            "ADD COLUMN IF NOT EXISTS path geometry(LineString,4326);"
                        ),
                        reverse_sql=(
                            "ALTER TABLE inventory_routesegment "
                            "DROP COLUMN IF EXISTS path;"
                        ),
                    ),
                ]
                if HAS_GDAL
                else [
                    migrations.AddField(
                        model_name='routesegment',
                        name='path',
                        field=gis_models.LineStringField(
                            srid=4326,
                            blank=True,
                            null=True,
                            help_text='Spatial path geometry for PostGIS spatial queries (bbox filtering).',
                        ),
                    ),
                ]
            ),
        ),
        migrations.AlterField(
            model_name='fibercable',
            name='path_coordinates',
            field=gis_models.JSONField(
                blank=True,
                null=True,
                help_text='Coordinate list e.g. [{\'lat\': -16.6, \'lng\': -49.2}, ...]. Deprecated: use path field.',
            ),
        ),
        migrations.AlterField(
            model_name='routesegment',
            name='path_coordinates',
            field=gis_models.JSONField(
                blank=True,
                null=True,
                help_text='Array of {"lat": float, "lng": float} points. Deprecated: use path field with PostGIS.',
            ),
        ),
    ]
