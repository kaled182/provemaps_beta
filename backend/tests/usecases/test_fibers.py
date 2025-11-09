from io import StringIO
from typing import Any, Callable, Dict, cast
from unittest.mock import MagicMock, patch

from django.test import TestCase

from inventory.models import Device, FiberCable, Port, Site
from inventory.usecases.fibers import (
    FiberValidationError,
    create_fiber_from_kml,
    create_manual_fiber,
    delete_fiber,
)

create_manual_fiber = cast(
    Callable[[Dict[str, Any]], Dict[str, Any]],
    create_manual_fiber,
)
create_fiber_from_kml = cast(
    Callable[..., Dict[str, Any]],
    create_fiber_from_kml,
)


class CreateManualFiberTests(TestCase):
    def setUp(self) -> None:
        """Set up a basic environment for tests."""
        self.site_a: Site = Site.objects.create(
            name="Site A",
            latitude=1.0,
            longitude=1.0,
        )
        self.site_b: Site = Site.objects.create(
            name="Site B",
            latitude=2.0,
            longitude=2.0,
        )
        self.device_a: Device = Device.objects.create(
            name="Device A",
            site=self.site_a,
        )
        self.device_b: Device = Device.objects.create(
            name="Device B",
            site=self.site_b,
        )
        self.port_a: Port = Port.objects.create(
            name="Port A",
            device=self.device_a,
        )
        self.port_b: Port = Port.objects.create(
            name="Port B",
            device=self.device_b,
        )
        self.device_a_id: int = cast(int, self.device_a.pk)
        self.device_b_id: int = cast(int, self.device_b.pk)
        self.port_a_id: int = cast(int, self.port_a.pk)
        self.port_b_id: int = cast(int, self.port_b.pk)

    @patch("inventory.usecases.fibers.invalidate_fiber_cache")
    def test_create_fiber_successfully(
        self,
        mock_invalidate_cache: MagicMock,
    ) -> None:
        """Ensure a fiber optic cable is created when the payload is valid."""
        data: Dict[str, Any] = {
            "name": "Fiber-01",
            "origin_device_id": self.device_a_id,
            "origin_port_id": self.port_a_id,
            "dest_device_id": self.device_b_id,
            "dest_port_id": self.port_b_id,
            "path": [
                {"lat": 1.0, "lng": 1.0},
                {"lat": 2.0, "lng": 2.0},
            ],
        }

        result = cast(Dict[str, Any], create_manual_fiber(data))

        self.assertEqual(FiberCable.objects.count(), 1)
        fiber = FiberCable.objects.first()
        assert fiber is not None
        self.assertEqual(fiber.name, "Fiber-01")
        self.assertEqual(fiber.origin_port, self.port_a)
        self.assertEqual(fiber.destination_port, self.port_b)
        self.assertIsNotNone(fiber.length_km)

        self.assertEqual(result["payload"]["name"], "Fiber-01")
        self.assertEqual(
            result["payload"]["origin_port"]["id"],
            self.port_a_id,
        )
        self.assertEqual(
            result["payload"]["destination_port"]["id"],
            self.port_b_id,
        )

        mock_invalidate_cache.assert_called_once()

    def test_validation_error_if_name_is_missing(self) -> None:
        """Ensure a missing name raises FiberValidationError."""
        data: Dict[str, Any] = {
            "name": "",
            "origin_device_id": self.device_a_id,
            "origin_port_id": self.port_a_id,
            "dest_device_id": self.device_b_id,
            "dest_port_id": self.port_b_id,
            "path": [
                {"lat": 1.0, "lng": 1.0},
                {"lat": 2.0, "lng": 2.0},
            ],
        }

        with self.assertRaises(FiberValidationError) as context:
            create_manual_fiber(data)

        self.assertIn("Required fields are missing", str(context.exception))

    @patch("inventory.usecases.fibers.invalidate_fiber_cache")
    def test_create_single_port_fiber_successfully(
        self,
        mock_invalidate_cache: MagicMock,
    ) -> None:
        """Ensure a single-port monitoring fiber is created correctly."""
        data: Dict[str, Any] = {
            "name": "Fiber-Single-Port",
            "origin_device_id": self.device_a_id,
            "origin_port_id": self.port_a_id,
            "dest_port_id": self.port_a_id,
            "single_port": "true",
            "path": [
                {"lat": 1.0, "lng": 1.0},
                {"lat": 1.5, "lng": 1.5},
            ],
        }

        result = cast(Dict[str, Any], create_manual_fiber(data))

        self.assertEqual(FiberCable.objects.count(), 1)
        fiber = FiberCable.objects.first()
        assert fiber is not None
        self.assertEqual(fiber.name, "Fiber-Single-Port")
        self.assertEqual(fiber.origin_port, self.port_a)
        self.assertEqual(fiber.destination_port, self.port_a)
        self.assertEqual(fiber.notes, "single-port-monitoring")

        self.assertEqual(
            result["payload"]["destination_port"]["id"],
            self.port_a_id,
        )
        self.assertTrue(result["payload"]["single_port"])

        mock_invalidate_cache.assert_called_once()


class CreateFiberFromKMLTests(TestCase):
    def setUp(self) -> None:
        self.site_a: Site = Site.objects.create(display_name="Site A")
        self.site_b: Site = Site.objects.create(display_name="Site B")
        self.device_a: Device = Device.objects.create(
            name="Device A",
            site=self.site_a,
        )
        self.device_b: Device = Device.objects.create(
            name="Device B",
            site=self.site_b,
        )
        self.port_a: Port = Port.objects.create(
            name="Port A",
            device=self.device_a,
        )
        self.port_b: Port = Port.objects.create(
            name="Port B",
            device=self.device_b,
        )
        self.device_a_id: int = cast(int, self.device_a.pk)
        self.device_b_id: int = cast(int, self.device_b.pk)
        self.port_a_id: int = cast(int, self.port_a.pk)
        self.port_b_id: int = cast(int, self.port_b.pk)
        self.valid_kml_content = (
            "\n        <kml xmlns=\"http://www.opengis.net/kml/2.2\">\n"
            "          <Placemark>\n"
            "            <LineString>\n"
            "              <coordinates>"
            "-46.633308,-23.550520 -46.633308,-23.650520"
            "</coordinates>\n"
            "            </LineString>\n"
            "          </Placemark>\n"
            "        </kml>\n"
        )

    @patch("inventory.usecases.fibers.invalidate_fiber_cache")
    def test_create_from_valid_kml(
        self,
        mock_invalidate_cache: MagicMock,
    ) -> None:
        kml_file = StringIO(self.valid_kml_content)
        kml_file.name = "test.kml"

        result = cast(
            Dict[str, Any],
            create_fiber_from_kml(
                name="KML-Fiber",
                origin_device_id=str(self.device_a_id),
                dest_device_id=str(self.device_b_id),
                origin_port_id=str(self.port_a_id),
                dest_port_id=str(self.port_b_id),
                kml_file=kml_file,
            ),
        )

        self.assertEqual(FiberCable.objects.count(), 1)
        fiber = FiberCable.objects.first()
        assert fiber is not None
        assert fiber.path_coordinates is not None
        self.assertEqual(fiber.name, "KML-Fiber")
        self.assertEqual(len(fiber.path_coordinates), 2)
        self.assertEqual(fiber.path_coordinates[0]["lng"], -46.633308)
        self.assertEqual(result["name"], "KML-Fiber")
        mock_invalidate_cache.assert_called_once()

    def test_raises_validation_error_for_invalid_kml(self) -> None:
        invalid_kml_file = StringIO("<kml><invalid></kml>")
        invalid_kml_file.name = "invalid.kml"

        with self.assertRaises(FiberValidationError) as context:
            create_fiber_from_kml(
                name="Invalid-KML-Fiber",
                origin_device_id=str(self.device_a_id),
                dest_device_id=str(self.device_b_id),
                origin_port_id=str(self.port_a_id),
                dest_port_id=str(self.port_b_id),
                kml_file=invalid_kml_file,
            )

        self.assertIn("Failed to process KML", str(context.exception))

    def test_raises_validation_error_for_kml_with_no_coordinates(self) -> None:
        """Raise a validation error when the KML lacks coordinate data."""
        kml_without_coords = (
            "\n        <kml xmlns=\"http://www.opengis.net/kml/2.2\">\n"
            "          <Placemark>\n"
            "            <LineString>\n"
            "              <!-- no coordinates tag -->\n"
            "            </LineString>\n"
            "          </Placemark>\n"
            "        </kml>\n"
        )
        kml_file = StringIO(kml_without_coords)
        kml_file.name = "no_coords.kml"

        with self.assertRaises(FiberValidationError) as context:
            create_fiber_from_kml(
                name="No-Coords-Fiber",
                origin_device_id=str(self.device_a_id),
                dest_device_id=str(self.device_b_id),
                origin_port_id=str(self.port_a_id),
                dest_port_id=str(self.port_b_id),
                kml_file=kml_file,
            )

        self.assertIn(
            "No coordinates found in the KML payload",
            str(context.exception),
        )


class DeleteFiberTests(TestCase):
    def setUp(self) -> None:
        site: Site = Site.objects.create(display_name="Test Site")
        device: Device = Device.objects.create(name="Test Device", site=site)
        port1: Port = Port.objects.create(name="Port 1", device=device)
        port2: Port = Port.objects.create(name="Port 2", device=device)
        self.fiber: FiberCable = FiberCable.objects.create(
            name="Fiber-to-delete",
            origin_port=port1,
            destination_port=port2,
        )

    @patch("inventory.usecases.fibers.invalidate_fiber_cache")
    def test_delete_fiber_successfully(
        self,
        mock_invalidate_cache: MagicMock,
    ) -> None:
        self.assertEqual(FiberCable.objects.count(), 1)

        delete_fiber(self.fiber)

        self.assertEqual(FiberCable.objects.count(), 0)
        mock_invalidate_cache.assert_called_once()
