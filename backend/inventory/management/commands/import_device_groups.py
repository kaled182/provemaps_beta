"""
Django management command to import device groups from Zabbix.

Usage:
    python manage.py import_device_groups
    python manage.py import_device_groups --sync-devices
"""
from django.core.management.base import BaseCommand

from inventory.services.device_groups import (
    import_device_groups_from_zabbix,
    sync_all_device_groups,
)


class Command(BaseCommand):
    help = "Import device groups from Zabbix host groups"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sync-devices",
            action="store_true",
            help="Also sync device-group relationships from Zabbix",
        )

    def handle(self, *args, **options):
        self.stdout.write("Fetching host groups from Zabbix...")

        try:
            # Import groups
            result = import_device_groups_from_zabbix()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nImported {result['created']} new groups, "
                    f"updated {result['updated']} existing groups"
                )
            )

            # Optionally sync device-group relationships
            if options["sync_devices"]:
                self.stdout.write("\nSyncing device-group relationships...")
                sync_result = sync_all_device_groups()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nSynced groups for {sync_result['synced']} devices, "
                        f"{sync_result['failed']} failed"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error importing groups: {e}")
            )
            raise
