#!/usr/bin/env python
"""Script para recalcular comprimento do cabo 50 manualmente"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.dev")
django.setup()

from inventory.models import FiberCable
from django.db import connection
import json

cable = FiberCable.objects.get(id=50)

# Obter comprimento base da geometria
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT ST_Length(path::geography)
        FROM zabbix_api_fibercable
        WHERE id = 50
    """)
    base_meters = float(cursor.fetchone()[0])

# Obter todas as infraestruturas
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT type, metadata
        FROM inventory_fiber_infrastructure
        WHERE cable_id = 50
    """)
    rows = cursor.fetchall()

# Calcular extensões
total_extension = 0.0
for infra_type, metadata_str in rows:
    if infra_type == "splice_box":
        total_extension += 20.0
        print(f"  CEO: +20.0m")
    elif infra_type == "slack":
        # metadata vem como string JSON no PostgreSQL
        if isinstance(metadata_str, str):
            metadata = json.loads(metadata_str)
        else:
            metadata = metadata_str
        slack_meters = float(metadata.get("slack_length", 0))
        total_extension += slack_meters
        print(f"  Slack: +{slack_meters}m")

new_total_km = (base_meters + total_extension) / 1000.0

print(f"\nBase (path): {base_meters/1000:.3f}km")
print(f"Extensões: {total_extension/1000:.3f}km")
print(f"Total novo: {new_total_km:.3f}km")
print(f"Total antigo: {cable.length_km:.3f}km")

cable.length_km = new_total_km
cable.save()

print(f"\n✅ Cabo 50 atualizado para {new_total_km:.3f}km")
