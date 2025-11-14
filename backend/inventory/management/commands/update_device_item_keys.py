"""
Django management command to update uptime_item_key and cpu_usage_item_key 
for existing devices by fetching items from Zabbix.
"""
from django.core.management.base import BaseCommand
from inventory.models import Device
from integrations.zabbix.zabbix_service import zabbix_request


class Command(BaseCommand):
    help = "Update uptime_item_key and cpu_usage_item_key for all devices from Zabbix"

    def add_arguments(self, parser):
        parser.add_argument(
            '--device-id',
            type=int,
            help='Update only a specific device by ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without saving',
        )

    def handle(self, *args, **options):
        device_id = options.get('device_id')
        dry_run = options.get('dry_run', False)

        if device_id:
            devices = Device.objects.filter(id=device_id)
            if not devices.exists():
                self.stdout.write(self.style.ERROR(f'Device with ID {device_id} not found'))
                return
        else:
            devices = Device.objects.filter(zabbix_hostid__isnull=False)

        self.stdout.write(f'Processing {devices.count()} device(s)...\n')

        updated_count = 0
        skipped_count = 0

        for device in devices:
            self.stdout.write(f'Device {device.id}: {device.name} (hostid={device.zabbix_hostid})')

            if not device.zabbix_hostid:
                self.stdout.write(self.style.WARNING('  ⚠ No Zabbix hostid, skipping'))
                skipped_count += 1
                continue

            try:
                # Fetch items from Zabbix
                raw_host_items = zabbix_request(
                    "item.get",
                    {
                        "output": ["key_", "name"],
                        "hostids": [device.zabbix_hostid],
                        "filter": {"status": "0"},
                    },
                )

                if not raw_host_items:
                    self.stdout.write(self.style.WARNING('  ⚠ No items found in Zabbix'))
                    skipped_count += 1
                    continue

                # Detect uptime key
                uptime_key = None
                for item in raw_host_items:
                    key = item.get("key_") or ""
                    key_lower = key.lower()
                    name_lower = (item.get("name") or "").lower()

                    if not uptime_key:
                        if "sysuptime" in key_lower:
                            if not any(exclude in key_lower for exclude in ["interface", "lastchange", "lastdown", "iflast"]):
                                uptime_key = key
                        elif "system.uptime" in key_lower:
                            uptime_key = key
                        elif "uptime" in key_lower:
                            if not any(exclude in key_lower for exclude in ["interface", "lastchange", "lastdown", "iflast"]):
                                uptime_key = key
                        elif "uptime" in name_lower and "system" in name_lower:
                            uptime_key = key

                # Detect CPU key
                cpu_key = None
                for item in raw_host_items:
                    key = item.get("key_") or ""
                    key_lower = key.lower()

                    if not cpu_key:
                        if any(pattern in key_lower for pattern in ["hwcpudevduty", "cpu.util", "cpu.usage", "system.cpu"]):
                            cpu_key = key
                        elif "cpu" in key_lower and any(pattern in key_lower for pattern in ["duty", "load", "util", "usage"]):
                            cpu_key = key

                # Update device
                if uptime_key or cpu_key:
                    old_uptime = device.uptime_item_key
                    old_cpu = device.cpu_usage_item_key

                    if dry_run:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Would update:'))
                        if uptime_key:
                            self.stdout.write(f'    Uptime: "{old_uptime or "EMPTY"}" → "{uptime_key}"')
                        if cpu_key:
                            self.stdout.write(f'    CPU: "{old_cpu or "EMPTY"}" → "{cpu_key}"')
                    else:
                        if uptime_key:
                            device.uptime_item_key = uptime_key
                        if cpu_key:
                            device.cpu_usage_item_key = cpu_key
                        device.save()
                        
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Updated:'))
                        if uptime_key:
                            self.stdout.write(f'    Uptime: {uptime_key}')
                        if cpu_key:
                            self.stdout.write(f'    CPU: {cpu_key}')
                        updated_count += 1
                else:
                    self.stdout.write(self.style.WARNING('  ⚠ No uptime or CPU keys detected'))
                    skipped_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {e}'))
                skipped_count += 1

            self.stdout.write('')  # Empty line between devices

        # Summary
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'\nDry run complete:'))
            self.stdout.write(f'  Would update: {updated_count} device(s)')
            self.stdout.write(f'  Skipped: {skipped_count} device(s)')
        else:
            self.stdout.write(self.style.SUCCESS(f'\nUpdate complete:'))
            self.stdout.write(f'  Updated: {updated_count} device(s)')
            self.stdout.write(f'  Skipped: {skipped_count} device(s)')
