#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from integrations.zabbix.zabbix_service import zabbix_request as ZABBIX_REQUEST

items = ZABBIX_REQUEST('item.get', {
    'output': ['key_', 'name'],
    'hostids': '10658',
    'filter': {'status': '0'},
    'limit': 2000
})

print("=" * 80)
print("ITEMS COM 'UPTIME' NO KEY OU NAME:")
print("=" * 80)
uptime_items = [i for i in items if 'uptime' in i.get('key_', '').lower() or 'uptime' in i.get('name', '').lower()]
for item in uptime_items[:15]:
    print(f"Key: {item.get('key_'):60s} | Name: {item.get('name')}")

print("\n" + "=" * 80)
print("ITEMS COM 'CPU' NO KEY OU NAME:")
print("=" * 80)
cpu_items = [i for i in items if 'cpu' in i.get('key_', '').lower() or 'cpu' in i.get('name', '').lower()]
for item in cpu_items[:15]:
    print(f"Key: {item.get('key_'):60s} | Name: {item.get('name')}")
