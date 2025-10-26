"""
Django management command to synchronize Zabbix inventory with local database.

This command fetches hosts, interfaces, and groups from Zabbix API and updates
the local inventory (Site, Device, Port) models accordingly.

Usage:
    python manage.py sync_zabbix_inventory [options]

Options:
    --dry-run: Show what would be synced without making changes
    --limit N: Limit sync to first N hosts
    --host-filter TEXT: Filter hosts by name pattern
    --update-only: Only update existing records, don't create new ones
    --verbose: Show detailed progress

Examples:
    # Full sync (creates/updates all hosts)
    python manage.py sync_zabbix_inventory

    # Dry run to preview changes
    python manage.py sync_zabbix_inventory --dry-run

    # Sync only first 10 hosts
    python manage.py sync_zabbix_inventory --limit 10

    # Sync hosts matching pattern
    python manage.py sync_zabbix_inventory --host-filter "router*"

    # Update existing devices only
    python manage.py sync_zabbix_inventory --update-only
"""
from __future__ import annotations

import logging
import time
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.utils import timezone

from inventory.models import Device, Port, Site
from zabbix_api.services.zabbix_service import zabbix_request

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize Zabbix inventory (hosts, interfaces) with local database"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without committing to database",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of hosts to sync (useful for testing)",
        )
        parser.add_argument(
            "--host-filter",
            type=str,
            default=None,
            help="Filter hosts by name pattern (e.g., 'router*')",
        )
        parser.add_argument(
            "--update-only",
            action="store_true",
            help="Only update existing devices, don't create new ones",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed progress information",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Main command execution."""
        dry_run = options["dry_run"]
        limit = options["limit"]
        host_filter = options["host_filter"]
        update_only = options["update_only"]
        verbose = options["verbose"]

        start_time = time.time()

        self.stdout.write(
            self.style.SUCCESS("=" * 70)
        )
        self.stdout.write(
            self.style.SUCCESS("🔄 Zabbix Inventory Sync")
        )
        self.stdout.write(
            self.style.SUCCESS("=" * 70)
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("⚠️  DRY RUN MODE - No changes will be saved")
            )

        # Fetch hosts from Zabbix
        self.stdout.write("📡 Fetching hosts from Zabbix API...")
        hosts = self._fetch_zabbix_hosts(host_filter, limit)

        if not hosts:
            self.stdout.write(
                self.style.WARNING("No hosts found in Zabbix")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"✓ Found {len(hosts)} host(s) in Zabbix")
        )

        # Sync hosts
        stats = {
            "sites_created": 0,
            "sites_updated": 0,
            "devices_created": 0,
            "devices_updated": 0,
            "ports_created": 0,
            "ports_updated": 0,
            "errors": 0,
        }

        for idx, host in enumerate(hosts, 1):
            if verbose:
                self.stdout.write(
                    f"\n[{idx}/{len(hosts)}] Processing: {host.get('name', 'Unknown')}"
                )

            try:
                result = self._sync_host(host, dry_run, update_only, verbose)
                for key, value in result.items():
                    stats[key] += value
            except Exception as e:
                stats["errors"] += 1
                logger.exception(f"Error syncing host {host.get('hostid')}: {e}")
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error: {str(e)}")
                )

        # Summary
        elapsed = time.time() - start_time
        self._print_summary(stats, elapsed, dry_run)

    def _fetch_zabbix_hosts(
        self,
        host_filter: str | None,
        limit: int | None
    ) -> list[dict[str, Any]]:
        """Fetch hosts from Zabbix API."""
        params: dict[str, Any] = {
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type", "main"],
            "selectInventory": ["location", "location_lat", "location_lon"],
            "selectGroups": ["groupid", "name"],
        }

        if host_filter:
            params["filter"] = {"name": host_filter}

        if limit:
            params["limit"] = limit

        try:
            result = zabbix_request("host.get", params)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.exception(f"Failed to fetch hosts from Zabbix: {e}")
            self.stdout.write(
                self.style.ERROR(f"API Error: {str(e)}")
            )
            return []

    def _sync_host(
        self,
        host: dict[str, Any],
        dry_run: bool,
        update_only: bool,
        verbose: bool
    ) -> dict[str, int]:
        """Sync a single host with local database."""
        stats = {
            "sites_created": 0,
            "sites_updated": 0,
            "devices_created": 0,
            "devices_updated": 0,
            "ports_created": 0,
            "ports_updated": 0,
            "errors": 0,
        }

        host_name = host.get("name", host.get("host", "Unknown"))
        hostid = host.get("hostid")

        if not hostid:
            if verbose:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠️  Skipping host without hostid: {host_name}")
                )
            return stats

        # Get or create site
        site_name = self._extract_site_name(host)
        site = None

        if not dry_run:
            site, site_created = self._get_or_create_site(host, site_name)
            if site_created:
                stats["sites_created"] += 1
                if verbose:
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Created site: {site_name}")
                    )
        else:
            # Dry run - check if site exists
            site = Site.objects.filter(name=site_name).first()
            if not site:
                stats["sites_created"] += 1
                if verbose:
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Would create site: {site_name}")
                    )

        # Get or create device
        device = Device.objects.filter(zabbix_hostid=hostid).first()

        if device:
            # Update existing device
            if not dry_run:
                device.name = host_name
                if site:
                    device.site = site
                device.save()
            stats["devices_updated"] += 1
            if verbose:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Updated device: {host_name}")
                )
        elif not update_only:
            # Create new device
            if not dry_run and site:
                device = Device.objects.create(
                    site=site,
                    name=host_name,
                    zabbix_hostid=hostid,
                )
            stats["devices_created"] += 1
            if verbose:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Created device: {host_name}")
                )
        else:
            if verbose:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠️  Skipping new device (update-only mode): {host_name}"
                    )
                )

        # Sync interfaces (ports)
        interfaces = host.get("interfaces", [])
        if interfaces and device:
            port_stats = self._sync_interfaces(
                device, interfaces, dry_run, verbose
            )
            stats["ports_created"] += port_stats["created"]
            stats["ports_updated"] += port_stats["updated"]

        return stats

    def _extract_site_name(self, host: dict[str, Any]) -> str:
        """Extract site name from host data."""
        # Try inventory location first
        inventory = host.get("inventory") or {}
        location = inventory.get("location")
        if location:
            return location.strip()

        # Try host groups
        groups = host.get("groups", [])
        if groups:
            # Use first group as site name
            return groups[0].get("name", "Unknown Site")

        # Fallback to host name
        return host.get("name", "Unknown Site")

    def _get_or_create_site(
        self,
        host: dict[str, Any],
        site_name: str
    ) -> tuple[Site, bool]:
        """Get or create a Site record."""
        inventory = host.get("inventory") or {}
        lat = inventory.get("location_lat")
        lon = inventory.get("location_lon")

        # Try to parse lat/lon
        try:
            latitude = float(lat) if lat else None
            longitude = float(lon) if lon else None
        except (ValueError, TypeError):
            latitude = None
            longitude = None

        site, created = Site.objects.get_or_create(
            name=site_name,
            defaults={
                "latitude": latitude,
                "longitude": longitude,
            }
        )

        if not created and (latitude or longitude):
            # Update coordinates if provided
            updated = False
            if latitude and site.latitude != latitude:
                site.latitude = latitude
                updated = True
            if longitude and site.longitude != longitude:
                site.longitude = longitude
                updated = True
            if updated:
                site.save()

        return site, created

    def _sync_interfaces(
        self,
        device: Device,
        interfaces: list[dict[str, Any]],
        dry_run: bool,
        verbose: bool
    ) -> dict[str, int]:
        """Sync host interfaces as ports."""
        stats = {"created": 0, "updated": 0}

        for iface in interfaces:
            interfaceid = iface.get("interfaceid")
            if not interfaceid:
                continue

            # Create port name from interface details
            iface_type = iface.get("type", "1")  # 1=agent, 2=SNMP
            ip = iface.get("ip", "")
            dns = iface.get("dns", "")
            port_name = dns or ip or f"interface-{interfaceid}"

            if dry_run:
                # Check if port exists
                port_exists = Port.objects.filter(
                    device=device,
                    zabbix_interfaceid=interfaceid
                ).exists()
                if port_exists:
                    stats["updated"] += 1
                else:
                    stats["created"] += 1
                    if verbose:
                        self.stdout.write(
                            f"    → Would create port: {port_name}"
                        )
            else:
                port, created = Port.objects.update_or_create(
                    device=device,
                    zabbix_interfaceid=interfaceid,
                    defaults={
                        "name": port_name,
                    }
                )
                if created:
                    stats["created"] += 1
                    if verbose:
                        self.stdout.write(
                            f"    → Created port: {port_name}"
                        )
                else:
                    stats["updated"] += 1

        return stats

    def _print_summary(
        self,
        stats: dict[str, int],
        elapsed: float,
        dry_run: bool
    ) -> None:
        """Print sync summary."""
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(
            self.style.SUCCESS("📊 Sync Summary")
        )
        self.stdout.write("=" * 70)

        mode = "DRY RUN" if dry_run else "COMMITTED"
        self.stdout.write(f"Mode: {mode}")
        self.stdout.write(f"Duration: {elapsed:.2f}s\n")

        self.stdout.write(
            self.style.SUCCESS(f"Sites created: {stats['sites_created']}")
        )
        self.stdout.write(
            f"Sites updated: {stats['sites_updated']}"
        )
        self.stdout.write(
            self.style.SUCCESS(f"Devices created: {stats['devices_created']}")
        )
        self.stdout.write(
            f"Devices updated: {stats['devices_updated']}"
        )
        self.stdout.write(
            self.style.SUCCESS(f"Ports created: {stats['ports_created']}")
        )
        self.stdout.write(
            f"Ports updated: {stats['ports_updated']}"
        )

        if stats["errors"] > 0:
            self.stdout.write(
                self.style.ERROR(f"\n⚠️  Errors: {stats['errors']}")
            )

        total_changes = (
            stats["sites_created"] +
            stats["devices_created"] +
            stats["ports_created"]
        )

        if dry_run and total_changes > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n💡 Run without --dry-run to apply {total_changes} change(s)"
                )
            )
        elif not dry_run:
            self.stdout.write(
                self.style.SUCCESS("\n✅ Sync completed successfully!")
            )
