"""
Integration tests for inventory models after migration from zabbix_api.

These tests validate that the model separation was successful and that
all relationships, imports, and admin configurations work correctly.
"""
from django.contrib.admin.sites import AdminSite
from django.test import TestCase, SimpleTestCase

from inventory.admin import DeviceAdmin, FiberCableAdmin, PortAdmin, SiteAdmin
from inventory.models import Device, FiberCable, FiberEvent, Port, Site


class InventoryModelsImportTests(SimpleTestCase):
    """Test that inventory models can be imported correctly."""

    def test_can_import_all_models_from_inventory(self):
        """Verify all models can be imported from inventory app."""
        try:
            from inventory.models import (
                Device,
                FiberCable,
                FiberEvent,
                Port,
                Site,
            )
            # If we get here, imports worked
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import inventory models: {e}")

    def test_zabbix_api_models_are_unmanaged(self):
        """Verify old zabbix_api models exist but are managed=False."""
        from zabbix_api.models import (
            Device as OldDevice,
            Site as OldSite,
        )

        # Models should exist but be unmanaged
        self.assertFalse(OldSite._meta.managed)
        self.assertFalse(OldDevice._meta.managed)

    def test_models_use_correct_db_tables(self):
        """Verify models use preserved database table names."""
        self.assertEqual(Site._meta.db_table, "zabbix_api_site")
        self.assertEqual(Device._meta.db_table, "zabbix_api_device")
        self.assertEqual(Port._meta.db_table, "zabbix_api_port")
        self.assertEqual(FiberCable._meta.db_table, "zabbix_api_fibercable")
        self.assertEqual(FiberEvent._meta.db_table, "zabbix_api_fiberevent")


class InventoryModelsRelationshipTests(TestCase):
    """Test that model relationships work correctly after migration."""

    def setUp(self):
        """Create test data."""
        self.site = Site.objects.create(
            name="Test Site",
            city="Test City",
            latitude=-23.5505,
            longitude=-46.6333,
        )

    def test_site_device_relationship(self):
        """Test Site → Device relationship works."""
        device = Device.objects.create(
            site=self.site,
            name="Test Device",
            vendor="Test Vendor",
            model="Test Model",
            zabbix_hostid="12345",
        )

        # Forward relationship
        self.assertEqual(device.site, self.site)

        # Reverse relationship
        self.assertIn(device, self.site.devices.all())
        self.assertEqual(self.site.devices.count(), 1)

    def test_device_port_relationship(self):
        """Test Device → Port relationship works."""
        device = Device.objects.create(
            site=self.site,
            name="Router-01",
            zabbix_hostid="12345",
        )

        port1 = Port.objects.create(
            device=device,
            name="eth0",
            zabbix_interfaceid="100",
        )

        port2 = Port.objects.create(
            device=device,
            name="eth1",
            zabbix_interfaceid="101",
        )

        # Forward relationship
        self.assertEqual(port1.device, device)
        self.assertEqual(port2.device, device)

        # Reverse relationship
        self.assertEqual(device.ports.count(), 2)
        self.assertIn(port1, device.ports.all())
        self.assertIn(port2, device.ports.all())

    def test_fiber_cable_with_ports(self):
        """Test FiberCable creation with origin and destination ports."""
        # Create two devices with ports
        device_a = Device.objects.create(
            site=self.site,
            name="Device A",
            zabbix_hostid="111",
        )
        device_b = Device.objects.create(
            site=self.site,
            name="Device B",
            zabbix_hostid="222",
        )

        port_a = Port.objects.create(
            device=device_a,
            name="Port A",
            zabbix_interfaceid="1000",
        )
        port_b = Port.objects.create(
            device=device_b,
            name="Port B",
            zabbix_interfaceid="2000",
        )

        # Create fiber cable
        fiber = FiberCable.objects.create(
            name="Fiber-01",
            origin_port=port_a,
            destination_port=port_b,
            length_km=10.5,
            status=FiberCable.STATUS_UP,
        )

        # Verify relationships
        self.assertEqual(fiber.origin_port, port_a)
        self.assertEqual(fiber.destination_port, port_b)
        self.assertEqual(fiber.status, "up")
        self.assertEqual(float(fiber.length_km), 10.5)

        # Verify reverse relationships
        self.assertIn(fiber, port_a.fiber_origin.all())
        self.assertIn(fiber, port_b.fiber_destination.all())

    def test_fiber_event_creation(self):
        """Test FiberEvent can be created and linked to FiberCable."""
        device = Device.objects.create(
            site=self.site,
            name="Device",
            zabbix_hostid="333",
        )
        port_a = Port.objects.create(device=device, name="Port A")
        port_b = Port.objects.create(device=device, name="Port B")

        fiber = FiberCable.objects.create(
            name="Fiber-Event-Test",
            origin_port=port_a,
            destination_port=port_b,
            status=FiberCable.STATUS_DOWN,
        )

        # Create event
        event = FiberEvent.objects.create(
            fiber=fiber,
            previous_status=FiberCable.STATUS_UP,
            new_status=FiberCable.STATUS_DOWN,
            detected_reason="Cable cut detected",
        )

        # Verify relationships
        self.assertEqual(event.fiber, fiber)
        self.assertEqual(event.previous_status, "up")
        self.assertEqual(event.new_status, "down")

        # Verify reverse relationship
        self.assertIn(event, fiber.events.all())

    def test_fiber_cable_update_status_method(self):
        """Test FiberCable.update_status() method works."""
        device = Device.objects.create(
            site=self.site,
            name="Device",
            zabbix_hostid="444",
        )
        port_a = Port.objects.create(device=device, name="Port A")
        port_b = Port.objects.create(device=device, name="Port B")

        fiber = FiberCable.objects.create(
            name="Fiber-Status-Test",
            origin_port=port_a,
            destination_port=port_b,
            status=FiberCable.STATUS_UNKNOWN,
        )

        # Update status
        fiber.update_status(FiberCable.STATUS_UP)

        # Verify update
        fiber.refresh_from_db()
        self.assertEqual(fiber.status, "up")
        self.assertIsNotNone(fiber.last_status_update)

    def test_port_backwards_compatibility_properties(self):
        """Test Port model backwards compatibility properties."""
        device = Device.objects.create(
            site=self.site,
            name="Device",
            zabbix_hostid="555",
        )

        port = Port.objects.create(
            device=device,
            name="Test Port",
            zabbix_item_id_trafego_in="item_in_123",
            zabbix_item_id_trafego_out="item_out_456",
        )

        # Test English property names (backwards compatibility)
        self.assertEqual(port.zabbix_item_id_traffic_in, "item_in_123")
        self.assertEqual(port.zabbix_item_id_traffic_out, "item_out_456")

        # Test setters
        port.zabbix_item_id_traffic_in = "new_in_789"
        port.zabbix_item_id_traffic_out = "new_out_012"

        self.assertEqual(port.zabbix_item_id_trafego_in, "new_in_789")
        self.assertEqual(port.zabbix_item_id_trafego_out, "new_out_012")


class InventoryAdminTests(TestCase):
    """Test that admin configurations work correctly."""

    def setUp(self):
        """Set up admin site for testing."""
        self.admin_site = AdminSite()

    def test_site_admin_configuration(self):
        """Test SiteAdmin is properly configured."""
        admin = SiteAdmin(Site, self.admin_site)

        self.assertEqual(
            admin.list_display,
            ("name", "city", "latitude", "longitude")
        )
        self.assertIn("name", admin.search_fields)
        self.assertIn("city", admin.search_fields)

    def test_device_admin_configuration(self):
        """Test DeviceAdmin is properly configured."""
        admin = DeviceAdmin(Device, self.admin_site)

        self.assertEqual(
            admin.list_display,
            ("name", "site", "vendor", "model", "zabbix_hostid")
        )
        self.assertIn("name", admin.search_fields)
        self.assertIn("zabbix_hostid", admin.search_fields)

    def test_port_admin_configuration(self):
        """Test PortAdmin is properly configured."""
        admin = PortAdmin(Port, self.admin_site)

        self.assertEqual(
            admin.list_display,
            ("name", "device", "zabbix_item_key", "notes")
        )
        self.assertIn("name", admin.search_fields)

    def test_fiber_cable_admin_configuration(self):
        """Test FiberCableAdmin is properly configured."""
        admin = FiberCableAdmin(FiberCable, self.admin_site)

        expected_display = (
            "name",
            "origin_port",
            "destination_port",
            "status",
            "length_km",
            "last_status_update",
        )
        self.assertEqual(admin.list_display, expected_display)
        self.assertIn("status", admin.list_filter)

    def test_all_models_registered_in_admin(self):
        """Test that all inventory models are registered in admin."""
        from django.contrib import admin as django_admin

        # Check if models are registered
        self.assertTrue(django_admin.site.is_registered(Site))
        self.assertTrue(django_admin.site.is_registered(Device))
        self.assertTrue(django_admin.site.is_registered(Port))
        self.assertTrue(django_admin.site.is_registered(FiberCable))
        self.assertTrue(django_admin.site.is_registered(FiberEvent))


class InventoryModelsStringRepresentationTests(TestCase):
    """Test string representations of models."""

    def test_site_str(self):
        """Test Site.__str__() returns name."""
        site = Site.objects.create(name="Test Site")
        self.assertEqual(str(site), "Test Site")

    def test_device_str(self):
        """Test Device.__str__() returns site + name."""
        site = Site.objects.create(name="Site A")
        device = Device.objects.create(site=site, name="Device 1")
        self.assertEqual(str(device), "Site A - Device 1")

    def test_port_str(self):
        """Test Port.__str__() returns device::name."""
        site = Site.objects.create(name="Site B")
        device = Device.objects.create(site=site, name="Router")
        port = Port.objects.create(device=device, name="eth0")
        self.assertEqual(str(port), "Site B - Router::eth0")

    def test_fiber_cable_str(self):
        """Test FiberCable.__str__() returns name."""
        site = Site.objects.create(name="Site C")
        device = Device.objects.create(site=site, name="Device")
        port_a = Port.objects.create(device=device, name="Port A")
        port_b = Port.objects.create(device=device, name="Port B")

        fiber = FiberCable.objects.create(
            name="Fiber-Test",
            origin_port=port_a,
            destination_port=port_b,
        )
        self.assertEqual(str(fiber), "Fiber-Test")

    def test_fiber_event_str(self):
        """Test FiberEvent.__str__() returns formatted string."""
        site = Site.objects.create(name="Site D")
        device = Device.objects.create(site=site, name="Device")
        port_a = Port.objects.create(device=device, name="Port A")
        port_b = Port.objects.create(device=device, name="Port B")

        fiber = FiberCable.objects.create(
            name="Fiber-Event",
            origin_port=port_a,
            destination_port=port_b,
        )

        event = FiberEvent.objects.create(
            fiber=fiber,
            previous_status="up",
            new_status="down",
        )

        event_str = str(event)
        self.assertIn("Fiber-Event", event_str)
        self.assertIn("up->down", event_str)
