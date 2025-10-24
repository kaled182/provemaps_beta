
from django.test import TestCase
from unittest.mock import patch, MagicMock
from decimal import Decimal
from zabbix_api.models import Site, Device, Port
from zabbix_api.usecases.inventory import get_device_ports, add_device_from_zabbix, InventoryNotFound, InventoryValidationError

class GetDevicePortsTests(TestCase):
    def setUp(self):
        """Set up a device with some ports for testing."""
        self.site = Site.objects.create(name="Test Site")
        self.device = Device.objects.create(name="Test Device", site=self.site)
        self.port1 = Port.objects.create(name="Port 1", device=self.device)
        self.port2 = Port.objects.create(name="Port 2", device=self.device, notes="some notes")

    def test_get_ports_for_existing_device(self):
        """Tests that ports are correctly retrieved for a device that exists."""
        result = get_device_ports(self.device.id)

        self.assertIn("ports", result)
        self.assertEqual(len(result["ports"]), 2)

        # Check the content of one of the ports
        port_data = next(p for p in result["ports"] if p["id"] == self.port2.id)
        self.assertEqual(port_data["name"], "Port 2")
        self.assertEqual(port_data["device"], "Test Device")
        self.assertEqual(port_data["notes"], "some notes")

    def test_raises_not_found_for_nonexistent_device(self):
        """Tests that InventoryNotFound is raised for a device ID that does not exist."""
        non_existent_id = 999
        with self.assertRaises(InventoryNotFound):
            get_device_ports(non_existent_id)


class AddDeviceFromZabbixTests(TestCase):
    @patch('zabbix_api.usecases.inventory.ZABBIX_REQUEST')
    def test_add_new_device_happy_path(self, mock_zabbix_request):
        """Tests the successful creation of a new device and its ports from Zabbix."""
        # --- Arrange ---
        # Simulate the Zabbix API responses
        zabbix_hostid = "10101"
        mock_host_response = [{
            'hostid': zabbix_hostid,
            'name': 'Zabbix Host Name',
            'host': 'zabbix.host.name',
            'inventory': {
                'location_lat': '-23.5505',
                'location_lon': '-46.6333',
                'site_address': 'Sao Paulo'
            }
        }]
        mock_items_response = [
            {
                'itemid': '20202',
                'key_': 'ifOperStatus[eth0]',
                'name': 'Interface eth0 status',
                'interfaceid': '30303'
            },
            {
                'itemid': '20203',
                'key_': 'net.if.in[eth0]',
                'name': 'Incoming traffic on eth0'
            }
        ]

        # Set up the mock to return different values based on the API method called
        def zabbix_side_effect(method, params):
            if method == 'host.get':
                # The function makes two host.get calls, we only care about the first one
                if "selectInventory" not in params:
                    return mock_host_response
            elif method == 'item.get':
                return mock_items_response
            return []
        mock_zabbix_request.side_effect = zabbix_side_effect

        payload = {"hostid": zabbix_hostid}

        # --- Act ---
        result = add_device_from_zabbix(payload)

        # --- Assert ---
        # Check Site creation
        self.assertEqual(Site.objects.count(), 1)
        site = Site.objects.first()
        self.assertEqual(site.name, 'Zabbix Host Name')
        self.assertEqual(site.latitude, Decimal('-23.5505'))

        # Check Device creation
        self.assertEqual(Device.objects.count(), 1)
        device = Device.objects.first()
        self.assertEqual(device.name, 'zabbix.host.name')
        self.assertEqual(device.site, site)
        self.assertEqual(device.zabbix_hostid, zabbix_hostid)

        # Check Port creation
        self.assertEqual(Port.objects.count(), 1)
        port = Port.objects.first()
        self.assertEqual(port.name, 'eth0')
        self.assertEqual(port.device, device)
        self.assertEqual(port.zabbix_item_key, 'ifOperStatus[eth0]')

        # Check result payload
        self.assertEqual(result['created']['sites'], 1)
        self.assertEqual(result['created']['devices'], 1)
        self.assertEqual(result['created']['ports'], 1)
