#!/usr/bin/env python
"""Test device groups extraction."""
import os
import sys
import django

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from monitoring.usecases import combine_device_and_zabbix_data
from inventory.models import Device

# Get a device with groups
device = Device.objects.filter(name__icontains='Santana').first()

if device:
    print(f"\nDevice: {device.name}")
    print(f"Groups: {[g.name for g in device.groups.all()]}")
    
    # Get status using combine_device_and_zabbix_data
    status = combine_device_and_zabbix_data([device])
    
    if status:
        print(f"Extracted device_type: {status[0].get('device_type', 'N/A')}")
        print(f"\nFull status:")
        print(status[0])
else:
    print("No device found")
