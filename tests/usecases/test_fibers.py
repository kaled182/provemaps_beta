
from unittest.mock import patch
from django.test import TestCase
from zabbix_api.models import Site, Device, Port, FiberCable
from zabbix_api.usecases.fibers import (
    create_manual_fiber, 
    create_fiber_from_kml, 
    delete_fiber, 
    FiberValidationError
)

class CreateManualFiberTests(TestCase):
    def setUp(self):
        """Set up a basic environment for tests."""
        self.site_a = Site.objects.create(name="Site A", latitude=1.0, longitude=1.0)
        self.site_b = Site.objects.create(name="Site B", latitude=2.0, longitude=2.0)
        self.device_a = Device.objects.create(name="Device A", site=self.site_a)
        self.device_b = Device.objects.create(name="Device B", site=self.site_b)
        self.port_a = Port.objects.create(name="Port A", device=self.device_a)
        self.port_b = Port.objects.create(name="Port B", device=self.device_b)

    @patch("zabbix_api.usecases.fibers.invalidate_fiber_cache")
    def test_create_fiber_successfully(self, mock_invalidate_cache):
        """
        Tests that a fiber optic cable is created successfully with valid data.
        """
        data = {
            "name": "Fiber-01",
            "origin_device_id": self.device_a.id,
            "origin_port_id": self.port_a.id,
            "dest_device_id": self.device_b.id,
            "dest_port_id": self.port_b.id,
            "path": [{"lat": 1.0, "lng": 1.0}, {"lat": 2.0, "lng": 2.0}]
        }

        result = create_manual_fiber(data)

        # Check if the fiber was created in the database
        self.assertEqual(FiberCable.objects.count(), 1)
        fiber = FiberCable.objects.first()
        self.assertEqual(fiber.name, "Fiber-01")
        self.assertEqual(fiber.origin_port, self.port_a)
        self.assertEqual(fiber.destination_port, self.port_b)
        self.assertIsNotNone(fiber.length_km)

        # Check the returned payload
        self.assertEqual(result["payload"]["name"], "Fiber-01")
        self.assertEqual(result["payload"]["origin_port"]["id"], self.port_a.id)
        self.assertEqual(result["payload"]["destination_port"]["id"], self.port_b.id)

        # Check if cache invalidation was called
        mock_invalidate_cache.assert_called_once()

    def test_validation_error_if_name_is_missing(self):
        """
        Tests that a FiberValidationError is raised if the name is missing.
        """
        data = {
            "name": "",  # Missing name
            "origin_device_id": self.device_a.id,
            "origin_port_id": self.port_a.id,
            "dest_device_id": self.device_b.id,
            "dest_port_id": self.port_b.id,
            "path": [{"lat": 1.0, "lng": 1.0}, {"lat": 2.0, "lng": 2.0}]
        }

        with self.assertRaises(FiberValidationError) as context:
            create_manual_fiber(data)
        
        self.assertIn("Required fields are missing", str(context.exception))

    @patch("zabbix_api.usecases.fibers.invalidate_fiber_cache")
    def test_create_single_port_fiber_successfully(self, mock_invalidate_cache):
        """
        Tests creating a single-port monitoring fiber.
        """
        data = {
            "name": "Fiber-Single-Port",
            "origin_device_id": self.device_a.id,
            "origin_port_id": self.port_a.id,
            "dest_port_id": self.port_a.id, # Same as origin
            "single_port": "true",
            "path": [{"lat": 1.0, "lng": 1.0}, {"lat": 1.5, "lng": 1.5}]
        }

        result = create_manual_fiber(data)

        self.assertEqual(FiberCable.objects.count(), 1)
        fiber = FiberCable.objects.first()
        self.assertEqual(fiber.name, "Fiber-Single-Port")
        self.assertEqual(fiber.origin_port, self.port_a)
        self.assertEqual(fiber.destination_port, self.port_a) # Destination is same as origin
        self.assertEqual(fiber.notes, "single-port-monitoring")

        mock_invalidate_cache.assert_called_once()


from io import StringIO

class CreateFiberFromKMLTests(TestCase):
    def setUp(self):
        self.site_a = Site.objects.create(name="Site A")
        self.site_b = Site.objects.create(name="Site B")
        self.device_a = Device.objects.create(name="Device A", site=self.site_a)
        self.device_b = Device.objects.create(name="Device B", site=self.site_b)
        self.port_a = Port.objects.create(name="Port A", device=self.device_a)
        self.port_b = Port.objects.create(name="Port B", device=self.device_b)
        self.valid_kml_content = '''
        <kml xmlns="http://www.opengis.net/kml/2.2">
          <Placemark>
            <LineString>
              <coordinates>-46.633308,-23.550520 -46.633308,-23.650520</coordinates>
            </LineString>
          </Placemark>
        </kml>
        '''

    @patch("zabbix_api.usecases.fibers.invalidate_fiber_cache")
    def test_create_from_valid_kml(self, mock_invalidate_cache):
        kml_file = StringIO(self.valid_kml_content)
        kml_file.name = "test.kml"

        result = create_fiber_from_kml(
            name="KML-Fiber",
            origin_device_id=self.device_a.id,
            dest_device_id=self.device_b.id,
            origin_port_id=self.port_a.id,
            dest_port_id=self.port_b.id,
            kml_file=kml_file
        )

        self.assertEqual(FiberCable.objects.count(), 1)
        fiber = FiberCable.objects.first()
        self.assertEqual(fiber.name, "KML-Fiber")
        self.assertEqual(len(fiber.path_coordinates), 2)
        self.assertEqual(fiber.path_coordinates[0]['lng'], -46.633308)
        mock_invalidate_cache.assert_called_once()

    def test_raises_validation_error_for_invalid_kml(self):
        invalid_kml_file = StringIO("<kml><invalid></kml>")
        invalid_kml_file.name = "invalid.kml"

        with self.assertRaises(FiberValidationError) as context:
            create_fiber_from_kml(
                name="Invalid-KML-Fiber",
                origin_device_id=self.device_a.id,
                dest_device_id=self.device_b.id,
                origin_port_id=self.port_a.id,
                dest_port_id=self.port_b.id,
                kml_file=invalid_kml_file
            )
        self.assertIn("Erro ao processar KML", str(context.exception))

    def test_raises_validation_error_for_kml_with_no_coordinates(self):
        """Tests that a validation error is raised for a KML file with no coordinate data."""
        kml_without_coords = '''
        <kml xmlns="http://www.opengis.net/kml/2.2">
          <Placemark>
            <LineString>
              <!-- no coordinates tag -->
            </LineString>
          </Placemark>
        </kml>
        '''
        kml_file = StringIO(kml_without_coords)
        kml_file.name = "no_coords.kml"

        with self.assertRaises(FiberValidationError) as context:
            create_fiber_from_kml(
                name="No-Coords-Fiber",
                origin_device_id=self.device_a.id,
                dest_device_id=self.device_b.id,
                origin_port_id=self.port_a.id,
                dest_port_id=self.port_b.id,
                kml_file=kml_file
            )
        self.assertIn("Nenhum ponto encontrado no KML", str(context.exception))


class DeleteFiberTests(TestCase):
    def setUp(self):
        site = Site.objects.create(name="Test Site")
        device = Device.objects.create(name="Test Device", site=site)
        port1 = Port.objects.create(name="Port 1", device=device)
        port2 = Port.objects.create(name="Port 2", device=device)
        self.fiber = FiberCable.objects.create(
            name="Fiber-to-delete",
            origin_port=port1,
            destination_port=port2
        )

    @patch("zabbix_api.usecases.fibers.invalidate_fiber_cache")
    def test_delete_fiber_successfully(self, mock_invalidate_cache):
        self.assertEqual(FiberCable.objects.count(), 1)
        
        delete_fiber(self.fiber)

        self.assertEqual(FiberCable.objects.count(), 0)
        mock_invalidate_cache.assert_called_once()
