"""
Teste end-to-end para persistência de edição de cabos de fibra.
"""
import pytest
from django.test import Client
from django.contrib.auth.models import User
from inventory.models import Device, FiberCable, Port, Site


@pytest.mark.django_db
class TestFiberEditPersistence:
    """Testa se edições de cabo persistem corretamente."""

    @pytest.fixture
    def authenticated_client(self):
        """Cliente autenticado."""
        client = Client()
        user = User.objects.create_user(username='testuser', password='testpass')
        client.login(username='testuser', password='testpass')
        return client

    @pytest.fixture
    def test_cable(self):
        """Cria um cabo de teste com portas."""
        # Criar site
        site = Site.objects.create(
            name="Test Site",
            latitude=-16.6869,
            longitude=-49.2648
        )

        # Criar dispositivos
        device1 = Device.objects.create(
            name="Device A",
            site=site,
        )
        device2 = Device.objects.create(
            name="Device B",
            site=site,
        )

        # Criar portas
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

        # Criar cabo
        cable = FiberCable.objects.create(
            name="Test Cable",
            origin_port=port_origin,
            destination_port=port_dest_old,
            path_coordinates=[
                {"lat": -16.6869, "lng": -49.2648},
                {"lat": -16.6900, "lng": -49.2700}
            ]
        )

        return {
            'cable': cable,
            'port_origin': port_origin,
            'port_dest_old': port_dest_old,
            'port_dest_new': port_dest_new,
            'device1': device1,
            'device2': device2,
        }

    def test_fiber_metadata_persistence(self, authenticated_client, test_cable):
        """
        Testa o fluxo completo de edição:
        1. GET cable details
        2. PUT com novos metadados
        3. GET novamente para verificar persistência
        """
        cable = test_cable['cable']
        port_new = test_cable['port_dest_new']

        # 1. GET inicial - verificar dados atuais
        response = authenticated_client.get(f'/zabbix_api/api/fiber/{cable.id}/')
        assert response.status_code == 200
        data = response.json()
        
        assert data['name'] == 'Test Cable'
        assert data['origin']['port_id'] == test_cable['port_origin'].id
        assert data['destination']['port_id'] == test_cable['port_dest_old'].id

        # 2. PUT - atualizar metadados
        update_payload = {
            'name': 'Updated Cable Name',
            'origin_port_id': test_cable['port_origin'].id,
            'dest_port_id': port_new.id,  # Mudando porta de destino
            'path': [
                {"lat": -16.6869, "lng": -49.2648},
                {"lat": -16.6900, "lng": -49.2700},
                {"lat": -16.6950, "lng": -49.2750}
            ]
        }

        response = authenticated_client.put(
            f'/zabbix_api/api/fiber/{cable.id}/',
            data=update_payload,
            content_type='application/json'
        )
        assert response.status_code == 200
        update_data = response.json()

        # Verificar resposta do PUT
        assert update_data['name'] == 'Updated Cable Name'
        assert update_data['destination']['port_id'] == port_new.id

        # 3. GET após update - verificar persistência
        response = authenticated_client.get(f'/zabbix_api/api/fiber/{cable.id}/')
        assert response.status_code == 200
        final_data = response.json()

        # Validações finais
        assert final_data['name'] == 'Updated Cable Name', "Nome não persistiu"
        assert final_data['origin']['port_id'] == test_cable['port_origin'].id, "Porta de origem mudou"
        assert final_data['destination']['port_id'] == port_new.id, "Porta de destino não persistiu"
        assert len(final_data['path']) == 3, "Path não persistiu"

        # 4. Verificar no banco diretamente
        cable.refresh_from_db()
        assert cable.name == 'Updated Cable Name'
        assert cable.destination_port_id == port_new.id

    def test_partial_update_only_destination(self, authenticated_client, test_cable):
        """Testa atualização apenas da porta de destino."""
        cable = test_cable['cable']
        port_new = test_cable['port_dest_new']

        # Atualizar apenas destination_port
        response = authenticated_client.put(
            f'/zabbix_api/api/fiber/{cable.id}/',
            data={'dest_port_id': port_new.id},
            content_type='application/json'
        )
        assert response.status_code == 200

        # Verificar persistência
        cable.refresh_from_db()
        assert cable.destination_port_id == port_new.id
        assert cable.name == 'Test Cable'  # Nome não deve mudar

    def test_update_preserves_other_fields(self, authenticated_client, test_cable):
        """Testa que campos não enviados no PUT são preservados."""
        cable = test_cable['cable']
        original_origin = cable.origin_port_id
        original_path = cable.path_coordinates

        # Atualizar apenas o nome
        response = authenticated_client.put(
            f'/zabbix_api/api/fiber/{cable.id}/',
            data={'name': 'Only Name Changed'},
            content_type='application/json'
        )
        assert response.status_code == 200

        # Verificar que outros campos não mudaram
        cable.refresh_from_db()
        assert cable.name == 'Only Name Changed'
        assert cable.origin_port_id == original_origin
        assert cable.path_coordinates == original_path
