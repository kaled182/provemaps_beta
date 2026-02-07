from inventory.models import Device
import json

# Pega os primeiros 2 devices do site Furacão
devices = Device.objects.filter(site__display_name__icontains='Furacão')[:2]

print(f"\n=== Dispositivos no site Furacão ===\n")
for dev in devices:
    print(f"Device ID: {dev.id}")
    print(f"  Nome: {dev.name}")
    print(f"  Zabbix Host ID: {dev.zabbix_hostid}")
    print(f"  CPU Item Key: {dev.cpu_usage_item_key or '(não configurado)'}")
    print(f"  Memory Item Key: {dev.memory_usage_item_key or '(não configurado)'}")
    print(f"  Uptime Item Key: {dev.uptime_item_key or '(não configurado)'}")
    print(f"  CPU Manual: {dev.cpu_usage_manual_percent}")
    print(f"  Memory Manual: {dev.memory_usage_manual_percent}")
    print()

print("Para configurar os item keys, acesse:")
print("http://localhost:8000/admin/inventory/device/")
