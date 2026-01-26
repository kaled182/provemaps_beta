"""
Testes para endpoint de status óptico de cabos
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from inventory.models import FiberCable, Port, Device, Site

User = get_user_model()


@pytest.mark.django_db
class TestFiberOpticalEndpoint:
    """Testes para o endpoint /api/v1/inventory/fibers/{id}/cached-status/"""

    @pytest.fixture
    def authenticated_client(self):
        """Cliente autenticado para testes"""
        client = Client()
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        client.force_login(user)
        return client

    def test_endpoint_structure_validation(self, authenticated_client):
        """Testa estrutura do endpoint usando primeiro cabo disponível no banco"""
        # Buscar primeiro cabo no banco
        cable = FiberCable.objects.first()
        
        if not cable:
            pytest.skip("Nenhum cabo disponível no banco de teste")
        
        response = authenticated_client.get(f'/api/v1/inventory/fibers/{cable.id}/cached-status/')
        
        # Validar status code
        assert response.status_code == 200
        
        # Validar estrutura da resposta
        data = response.json()
        assert isinstance(data, dict)
        
        # Validar campos obrigatórios
        assert 'cable_id' in data, "Campo 'cable_id' ausente"
        assert 'status' in data, "Campo 'status' ausente"
        assert 'origin_optical' in data, "Campo 'origin_optical' ausente"
        assert 'destination_optical' in data, "Campo 'destination_optical' ausente"
        
        # Validar cable_id corresponde
        assert data['cable_id'] == cable.id
        
        # Se cabo tem portas, validar estrutura dos dados ópticos
        if cable.origin_port:
            origin = data['origin_optical']
            if origin is not None:  # Pode ser None se não houver dados ópticos
                assert 'rx_dbm' in origin, "Campo 'rx_dbm' ausente em origin_optical"
                assert 'tx_dbm' in origin, "Campo 'tx_dbm' ausente em origin_optical"
                assert 'last_check' in origin, "Campo 'last_check' ausente em origin_optical"
        
        if cable.destination_port:
            dest = data['destination_optical']
            if dest is not None:  # Pode ser None se não houver dados ópticos
                assert 'rx_dbm' in dest, "Campo 'rx_dbm' ausente em destination_optical"
                assert 'tx_dbm' in dest, "Campo 'tx_dbm' ausente em destination_optical"
                assert 'last_check' in dest, "Campo 'last_check' ausente em destination_optical"
        
        print(f"\n✅ Estrutura do endpoint validada com sucesso:")
        print(f"   Cable ID: {data['cable_id']}")
        print(f"   Status: {data['status']}")
        print(f"   Origin Optical: {data['origin_optical']}")
        print(f"   Destination Optical: {data['destination_optical']}")
    
    def test_endpoint_requires_authentication(self):
        """Testa se endpoint requer autenticação"""
        client = Client()  # Cliente não autenticado
        cable = FiberCable.objects.first()
        
        if not cable:
            pytest.skip("Nenhum cabo disponível no banco de teste")
        
        response = client.get(f'/api/v1/inventory/fibers/{cable.id}/cached-status/')
        
        # Deve retornar 403 (Forbidden) ou 401 (Unauthorized)
        assert response.status_code in [401, 403]
    
    def test_endpoint_handles_not_found(self, authenticated_client):
        """Testa se endpoint retorna 404 para cabo inexistente"""
        response = authenticated_client.get('/api/v1/inventory/fibers/99999999/cached-status/')
        
        assert response.status_code == 404

    def test_endpoint_requires_authentication(self):
        """Testa se endpoint requer autenticação"""
        cable = FiberCable.objects.create(name='Test', status='up')
        
        client = Client()
        response = client.get(f'/api/v1/inventory/fibers/{cable.id}/cached-status/')
        
        # Deve retornar erro de autenticação
        assert response.status_code in [401, 403]

    def test_endpoint_returns_404_for_nonexistent_cable(self, authenticated_client):
        """Testa se endpoint retorna 404 para cabo inexistente"""
        response = authenticated_client.get('/api/v1/inventory/fibers/99999/cached-status/')
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
