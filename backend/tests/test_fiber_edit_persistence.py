"""End-to-end tests for fiber cable edit persistence."""

from typing import Any, Dict

import json

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from django.contrib.gis.geos import LineString

from inventory.models import Device, FiberCable, Port, Site


@pytest.mark.django_db
class TestFiberEditPersistence:
    """Verify that fiber cable edits persist correctly."""

    @pytest.fixture
    def authenticated_client(self) -> Client:
        """Return an authenticated Django test client."""
        client = Client()
        User.objects.create_user(
            username="testuser",
            password="testpass",
            is_staff=True,
        )
        client.login(username='testuser', password='testpass')
        return client

    @pytest.fixture
    def test_cable(self) -> Dict[str, Any]:
        """Create a test cable and related ports."""
        # Create site
        site = Site.objects.create(
            name="Test Site",
            latitude=-16.6869,
            longitude=-49.2648
        )

        # Create devices
        device1 = Device.objects.create(
            name="Device A",
            site=site,
        )
        device2 = Device.objects.create(
            name="Device B",
            site=site,
        )

        # Create ports
        port_origin = Port.objects.create(
            device=device1,
            name="eth0/1",
        )
        port_dest_old = Port.objects.create(
            device=device2,
            name="eth0/2",
        )
        port_dest_new = Port.objects.create(
            device=device2,
            name="eth0/3",
        )

        # Create cable
        cable = FiberCable.objects.create(
            name="Test Cable",
            origin_port=port_origin,
            destination_port=port_dest_old,
            path=LineString(
                [(-49.2648, -16.6869), (-49.2700, -16.6900)],
                srid=4326,
            ),
        )

        return {
            'cable': cable,
            'port_origin': port_origin,
            'port_dest_old': port_dest_old,
            'port_dest_new': port_dest_new,
            'device1': device1,
            'device2': device2,
        }

    def test_fiber_metadata_persistence(
        self,
        authenticated_client: Client,
        test_cable: Dict[str, Any],
    ) -> None:
        """Run full GET/PUT/GET flow to confirm persistence."""
        cable = test_cable['cable']
        port_new = test_cable['port_dest_new']

        # Step 1: initial GET to inspect current data
        detail_url = reverse("inventory-api:fiber-detail", args=[cable.id])
        response = authenticated_client.get(detail_url)
        assert response.status_code == 200
        data = response.json()

        assert data['name'] == 'Test Cable'
        assert (
            data['origin']['port_id']
            == test_cable['port_origin'].id
        )
        assert (
            data['destination']['port_id']
            == test_cable['port_dest_old'].id
        )

        # Step 2: PUT with new metadata
        update_payload: Dict[str, Any] = {
            'name': 'Updated Cable Name',
            'origin_port_id': test_cable['port_origin'].id,
            'dest_port_id': port_new.id,  # Change destination port
            'path': [
                {"lat": -16.6869, "lng": -49.2648},
                {"lat": -16.6900, "lng": -49.2700},
                {"lat": -16.6950, "lng": -49.2750}
            ]
        }

        response = authenticated_client.put(
            detail_url,
            data=json.dumps(update_payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        update_data = response.json()

        # Validate PUT response
        assert update_data['name'] == 'Updated Cable Name'
        assert update_data['destination']['port_id'] == port_new.id

        # Step 3: GET after update to ensure persistence
        response = authenticated_client.get(detail_url)
        assert response.status_code == 200
        final_data = response.json()

        # Final validations
        assert (
            final_data['name'] == 'Updated Cable Name'
        ), "Name did not persist"
        assert (
            final_data['origin']['port_id'] == test_cable['port_origin'].id
        ), "Origin port changed"
        assert (
            final_data['destination']['port_id'] == port_new.id
        ), "Destination port did not persist"
        assert len(final_data['path']) == 3, "Path did not persist"

        # Step 4: confirm directly in the database
        cable.refresh_from_db()
        assert cable.name == 'Updated Cable Name'
        assert cable.destination_port_id == port_new.id

    def test_partial_update_only_destination(
        self,
        authenticated_client: Client,
        test_cable: Dict[str, Any],
    ) -> None:
        """Ensure updating only the destination port succeeds."""
        cable = test_cable['cable']
        port_new = test_cable['port_dest_new']
        detail_url = reverse("inventory-api:fiber-detail", args=[cable.id])

        # Update only the destination port
        response = authenticated_client.put(
            detail_url,
            data=json.dumps({"dest_port_id": port_new.id}),
            content_type="application/json",
        )
        assert response.status_code == 200

        # Validate persistence
        cable.refresh_from_db()
        assert cable.destination_port_id == port_new.id
        assert cable.name == 'Test Cable'  # Name must stay the same

    def test_update_preserves_other_fields(
        self,
        authenticated_client: Client,
        test_cable: Dict[str, Any],
    ) -> None:
        """Ensure fields omitted from the PUT remain untouched."""
        cable = test_cable['cable']
        original_origin = cable.origin_port_id
        original_path = cable.path_coordinates
        detail_url = reverse("inventory-api:fiber-detail", args=[cable.id])

        # Update only the name
        response = authenticated_client.put(
            detail_url,
            data=json.dumps({"name": "Only Name Changed"}),
            content_type="application/json",
        )
        assert response.status_code == 200

        # Ensure other fields remain unchanged
        cable.refresh_from_db()
        assert cable.name == 'Only Name Changed'
        assert cable.origin_port_id == original_origin
        assert cable.path_coordinates == original_path
