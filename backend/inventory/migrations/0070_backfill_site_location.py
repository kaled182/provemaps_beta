"""
EV-0024 — preenche ``Site.location`` a partir de latitude/longitude (e vice-versa).

Sites criados antes do sinal `sync_site_spatial_fields` podem ter lat/lng sem
``location`` — ficavam fora de qualquer ST_DWithin (regra dos 100 m, busca por
raio). Idempotente; reverter é no-op (não apaga dados).
"""

from django.db import migrations


def backfill_site_location(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    from django.contrib.gis.geos import Point

    Site = apps.get_model("inventory", "Site")
    for site in (
        Site.objects.filter(location__isnull=True)
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
    ):
        Site.objects.filter(pk=site.pk).update(
            location=Point(float(site.longitude), float(site.latitude), srid=4326)
        )
    for site in Site.objects.filter(latitude__isnull=True, location__isnull=False):
        Site.objects.filter(pk=site.pk).update(
            latitude=round(site.location.y, 6), longitude=round(site.location.x, 6)
        )


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0069_route_json_columns_to_jsonb"),
    ]

    operations = [
        migrations.RunPython(backfill_site_location, migrations.RunPython.noop),
    ]
