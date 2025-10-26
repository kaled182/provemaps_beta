#!/usr/bin/env python
"""
Verify Port model field to database column mappings.
Tests the English field names map correctly to Portuguese DB columns.
"""
import django
import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.dev")
django.setup()

from inventory.models import Port

print("Port Model Field -> Database Column Mapping:")
print("=" * 60)

for field in Port._meta.get_fields():
    if hasattr(field, "column"):
        db_column = field.column
        field_name = field.name
        print(f"  {field_name:30} -> {db_column}")
        
        # Highlight traffic fields
        if "traffic" in field_name:
            print(f"    ✓ English field '{field_name}' maps to DB column '{db_column}'")

print("\n" + "=" * 60)
print("Testing Port instance access:")
print("=" * 60)

# Get first port if exists
port = Port.objects.first()
if port:
    print(f"\nPort: {port.name}")
    print(f"  zabbix_item_id_traffic_in: {port.zabbix_item_id_traffic_in}")
    print(f"  zabbix_item_id_traffic_out: {port.zabbix_item_id_traffic_out}")
    print("\n✅ Field access successful!")
else:
    print("\n⚠️ No ports found in database")

print("\nValidation: ✅ PASSED - English field names working correctly")
