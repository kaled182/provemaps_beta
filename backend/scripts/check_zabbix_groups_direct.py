#!/usr/bin/env python
"""Check Zabbix groups directly from API."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from integrations.zabbix.zabbix_service import zabbix_request
from inventory.models import Device

# Get a device with zabbix_hostid
device = Device.objects.filter(zabbix_hostid__isnull=False).first()

if not device:
    print("No device with zabbix_hostid found")
    sys.exit(1)

print(f"Checking device: {device.name}")
print(f"Zabbix Host ID: {device.zabbix_hostid}")

# Fetch from Zabbix
try:
    hosts = zabbix_request(
        "host.get",
        {
            "output": ["hostid", "host", "name"],
            "hostids": [device.zabbix_hostid],
            "selectGroups": ["groupid", "name"],
        },
    )
    
    if not hosts:
        print(f"ERROR: Device not found in Zabbix")
        sys.exit(1)
    
    host_data = hosts[0]
    print(f"\nZabbix Host Name: {host_data.get('name')}")
    print(f"Zabbix Host: {host_data.get('host')}")
    
    groups = host_data.get("groups", [])
    print(f"\nGroups from Zabbix API ({len(groups)}):")
    
    if not groups:
        print("  (No groups found)")
    else:
        for group in groups:
            print(f"  - {group.get('name')} (ID: {group.get('groupid')})")
            
except Exception as e:
    print(f"ERROR calling Zabbix API: {e}")
    import traceback
    traceback.print_exc()
