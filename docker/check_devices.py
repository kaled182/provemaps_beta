from inventory.models import Device

devices = Device.objects.all()
print('ID | Device Name | Uptime Key | CPU Key')
print('-' * 100)
for d in devices:
    uptime = d.uptime_item_key or "EMPTY"
    cpu = d.cpu_usage_item_key or "EMPTY"
    print(f'{d.id} | {d.name[:40]:<40} | {uptime:<20} | {cpu}')
