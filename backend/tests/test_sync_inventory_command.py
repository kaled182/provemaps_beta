"""
Tests for sync_zabbix_inventory management command.
"""
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from inventory.models import Device, Port, Site


PATCH_ZABBIX = (
    "inventory.management.commands.sync_zabbix_inventory.zabbix_request"
)


class SyncZabbixInventoryCommandTests(TestCase):
    """Test suite for sync_zabbix_inventory command."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear existing data
        Device.objects.all().delete()
        Site.objects.all().delete()
        Port.objects.all().delete()

    @patch(PATCH_ZABBIX)
    def test_sync_creates_site_and_device(self, mock_zabbix):
        """Test that sync creates site and device from Zabbix data."""
        # Mock Zabbix API response
        mock_zabbix.return_value = [
            {
                "hostid": "12345",
                "host": "test-router",
                "name": "Test Router",
                "status": "0",
                "interfaces": [
                    {
                        "interfaceid": "100",
                        "ip": "192.168.1.1",
                        "dns": "router.example.com",
                        "port": "161",
                        "type": "2",
                        "main": "1",
                    }
                ],
                "inventory": {
                    "location": "DataCenter A",
                    "location_lat": "51.5074",
                    "location_lon": "-0.1278",
                },
                "groups": [{"groupid": "1", "name": "Routers"}],
            }
        ]

        # Run command
        out = StringIO()
        call_command("sync_zabbix_inventory", stdout=out)

        # Verify site created
        site = Site.objects.get(display_name="DataCenter A")
        self.assertIsNotNone(site)
        self.assertAlmostEqual(float(site.latitude), 51.5074, places=4)
        self.assertAlmostEqual(float(site.longitude), -0.1278, places=4)

        # Verify device created
        device = Device.objects.get(zabbix_hostid="12345")
        self.assertEqual(device.name, "Test Router")
        self.assertEqual(device.site, site)

        # Verify port created
        port = Port.objects.get(zabbix_interfaceid="100")
        self.assertEqual(port.device, device)
        self.assertIn("router.example.com", port.name)

        # Check output
        output = out.getvalue()
        self.assertIn("Sync completed successfully", output)

    @patch(PATCH_ZABBIX)
    def test_dry_run_mode(self, mock_zabbix):
        """Test that dry-run mode doesn't create records."""
        mock_zabbix.return_value = [
            {
                "hostid": "99999",
                "host": "test-switch",
                "name": "Test Switch",
                "status": "0",
                "interfaces": [],
                "inventory": {"location": "Test Site"},
                "groups": [],
            }
        ]

        # Run with --dry-run
        out = StringIO()
        call_command("sync_zabbix_inventory", "--dry-run", stdout=out)

        # Verify nothing was created
        self.assertEqual(Site.objects.count(), 0)
        self.assertEqual(Device.objects.count(), 0)

        # Check output mentions dry run
        output = out.getvalue()
        self.assertIn("DRY RUN", output)

    @patch(PATCH_ZABBIX)
    def test_update_existing_device(self, mock_zabbix):
        """Test that sync updates existing device."""
        # Create existing site and device
        site = Site.objects.create(display_name="Existing Site")
        device = Device.objects.create(
            site=site,
            name="Old Name",
            zabbix_hostid="12345",
        )

        # Mock updated data from Zabbix
        mock_zabbix.return_value = [
            {
                "hostid": "12345",
                "host": "updated-device",
                "name": "Updated Name",
                "status": "0",
                "interfaces": [],
                "inventory": {"location": "Existing Site"},
                "groups": [],
            }
        ]

        # Run sync
        call_command("sync_zabbix_inventory")

        # Verify device was updated
        device.refresh_from_db()
        self.assertEqual(device.name, "Updated Name")

    @patch(PATCH_ZABBIX)
    def test_limit_option(self, mock_zabbix):
        """Test that --limit option restricts number of hosts."""
        # Mock returns multiple hosts but limit should restrict
        mock_zabbix.return_value = [
            {
                "hostid": f"{i}",
                "host": f"host{i}",
                "name": f"Host {i}",
                "status": "0",
                "interfaces": [],
                "inventory": {},
                "groups": [{"name": "Test Group"}],
            }
            for i in range(10)
        ]

        # Run with limit=3
        call_command("sync_zabbix_inventory", "--limit", "3")

        # Zabbix request should have been called with limit
        mock_zabbix.assert_called_once()
        call_args = mock_zabbix.call_args[0]
        self.assertIn("limit", call_args[1])
        self.assertEqual(call_args[1]["limit"], 3)

    @patch(PATCH_ZABBIX)
    def test_update_only_mode(self, mock_zabbix):
        """Test that --update-only skips creating new devices."""
        # Create one existing device
        site = Site.objects.create(display_name="Test Site")
        Device.objects.create(
            site=site,
            name="Existing Device",
            zabbix_hostid="1",
        )

        # Mock returns existing + new device
        mock_zabbix.return_value = [
            {
                "hostid": "1",
                "host": "existing",
                "name": "Existing Device Updated",
                "status": "0",
                "interfaces": [],
                "inventory": {},
                "groups": [{"name": "Test Site"}],
            },
            {
                "hostid": "2",
                "host": "new",
                "name": "New Device",
                "status": "0",
                "interfaces": [],
                "inventory": {},
                "groups": [{"name": "Test Site"}],
            },
        ]

        # Run with --update-only
        call_command("sync_zabbix_inventory", "--update-only")

        # Verify only 1 device exists (new one not created)
        self.assertEqual(Device.objects.count(), 1)
        device = Device.objects.get(zabbix_hostid="1")
        self.assertEqual(device.name, "Existing Device Updated")

    @patch(PATCH_ZABBIX)
    def test_handles_missing_inventory_gracefully(self, mock_zabbix):
        """Test that command handles hosts without inventory data."""
        mock_zabbix.return_value = [
            {
                "hostid": "123",
                "host": "minimal-host",
                "name": "Minimal Host",
                "status": "0",
                "interfaces": [],
                # No inventory field
                "groups": [{"name": "Fallback Group"}],
            }
        ]

        # Should not crash
        call_command("sync_zabbix_inventory")

        # Verify device created with fallback site name
        device = Device.objects.get(zabbix_hostid="123")
        self.assertIsNotNone(device)
        self.assertEqual(device.site.name, "Fallback Group")
