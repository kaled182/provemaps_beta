#!/usr/bin/env python
"""Check device groups in database."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from inventory.models import Device, DeviceGroup

# Count groups
total_groups = DeviceGroup.objects.count()
print(f"Total de grupos: {total_groups}")

# List groups
groups = list(DeviceGroup.objects.values_list('name', flat=True))
print(f"\nGrupos ({len(groups)}):")
for group in groups:
    print(f"  - {group}")

# Check devices with groups
print("\n" + "="*70)
print("Dispositivos com grupos:")
print("="*70)

devices_with_groups = Device.objects.filter(
    zabbix_hostid__isnull=False,
    groups__isnull=False
).distinct()

print(f"\nDispositivos com grupos: {devices_with_groups.count()}")

for device in devices_with_groups[:5]:
    group_names = list(device.groups.values_list('name', flat=True))
    print(f"\n{device.name}:")
    for group in group_names:
        print(f"  - {group}")

# Check devices without groups
devices_without_groups = Device.objects.filter(
    zabbix_hostid__isnull=False,
    groups__isnull=True
)

print(f"\nDispositivos SEM grupos: {devices_without_groups.count()}")
if devices_without_groups.count() > 0:
    print("Exemplos:")
    for device in devices_without_groups[:5]:
        print(f"  - {device.name}")
