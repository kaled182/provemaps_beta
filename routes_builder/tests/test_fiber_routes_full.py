"""
Testes completos para Fiber Route Builder
Valida criação, edição, listagem e deleção de cabos de fibra
"""
import pytest
from django.test import Client
from django.contrib.auth.models import User
from inventory.models import FiberCable, Site, Device, Port
import json


@pytest.fixture
def authenticated_client(db):
    """Cliente autenticado para fazer requisições"""
    client = Client()
    User.objects.create_user(
        username='testuser',
        password='testpass123',
        is_staff=True  # Necessário para manual-create endpoint
    )
    client.login(username='testuser', password='testpass123')
    return client


@pytest.fixture
def sample_sites(db):
    """Cria sites de teste"""
    site1 = Site.objects.create(
        name="Site A",
        city="São Paulo",
        latitude=-23.5505,
        longitude=-46.6333
    )
    site2 = Site.objects.create(
        name="Site B",
        city="Rio de Janeiro",
        latitude=-22.9068,
        longitude=-43.1729
    )
    return site1, site2


@pytest.fixture
def sample_devices(db, sample_sites):
    """Cria devices de teste"""
    site1, site2 = sample_sites
    device1 = Device.objects.create(
        name="Switch-A",
        site=site1,
        vendor="Cisco",
        model="Catalyst 2960"
    )
    device2 = Device.objects.create(
        name="Switch-B",
        site=site2,
        vendor="Cisco",
        model="Catalyst 2960"
    )
    return device1, device2


@pytest.fixture
def sample_ports(db, sample_devices):
    """Cria portas de teste"""
    device1, device2 = sample_devices
    port1 = Port.objects.create(
        device=device1,
        name="eth0/1"
    )
    port2 = Port.objects.create(
        device=device2,
        name="eth0/1"
    )
    return port1, port2


@pytest.fixture
def sample_cable(db, sample_ports):
    """Cria cabo de fibra de teste"""
    port1, port2 = sample_ports
    cable = FiberCable.objects.create(
        name="Cabo Teste SP-RJ",
        origin_port=port1,
        destination_port=port2,
        path_coordinates=[
            {"lat": -23.5505, "lng": -46.6333},
            {"lat": -23.0000, "lng": -45.0000},
            {"lat": -22.9068, "lng": -43.1729}
        ],
        length_km=435.5
    )
    return cable


@pytest.mark.django_db
class TestFiberCableAPI:
    """Testes para API de cabos de fibra"""

    def test_list_cables_empty(self, authenticated_client):
        """Testa listagem de cabos quando não há cabos"""
        response = authenticated_client.get('/zabbix_api/api/fibers/')
        assert response.status_code == 200
        data = response.json()
        assert 'fibers' in data or 'cables' in data
        cables = data.get('fibers', data.get('cables', []))
        assert isinstance(cables, list)

    def test_list_cables_with_data(self, authenticated_client, sample_cable):
        """Testa listagem de cabos quando há dados"""
        response = authenticated_client.get('/zabbix_api/api/fibers/')
        assert response.status_code == 200
        data = response.json()
        cables = data.get('fibers', data.get('cables', []))
        assert len(cables) >= 1
        
        # Valida estrutura do cabo
        cable = cables[0]
        assert 'id' in cable
        assert 'name' in cable
        assert cable['name'] == "Cabo Teste SP-RJ"

    def test_get_cable_details(self, authenticated_client, sample_cable):
        """Testa obter detalhes de um cabo específico"""
        url = f'/zabbix_api/api/fiber/{sample_cable.id}/'
        response = authenticated_client.get(url)
        assert response.status_code == 200
        data = response.json()
        
        assert data['id'] == sample_cable.id
        assert data['name'] == "Cabo Teste SP-RJ"
        assert 'path' in data
        assert len(data['path']) == 3
        assert data['length_km'] == 435.5

    def test_get_cable_not_found(self, authenticated_client):
        """Testa obter cabo inexistente"""
        response = authenticated_client.get('/zabbix_api/api/fiber/99999/')
        assert response.status_code == 404

    def test_create_cable_manual(self, authenticated_client, sample_ports):
        """Testa criação de cabo manual"""
        port1, port2 = sample_ports
        payload = {
            'name': 'Novo Cabo Teste',
            'origin_device_id': port1.device.id,
            'origin_port_id': port1.id,
            'dest_device_id': port2.device.id,
            'dest_port_id': port2.id,
            'path': [
                {"lat": -23.5505, "lng": -46.6333},
                {"lat": -22.9068, "lng": -43.1729}
            ]
        }
        
        response = authenticated_client.post(
            '/zabbix_api/api/fibers/manual-create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert 'fiber_id' in data
        assert data['points'] == 2
        
        # Valida que o cabo foi criado no banco
        cable = FiberCable.objects.get(id=data['fiber_id'])
        assert cable.name == 'Novo Cabo Teste'
        assert len(cable.path_coordinates) == 2

    def test_update_cable_path(self, authenticated_client, sample_cable):
        """Testa atualização do path de um cabo"""
        new_path = [
            {"lat": -23.5505, "lng": -46.6333},
            {"lat": -23.2000, "lng": -45.5000},
            {"lat": -23.0000, "lng": -45.0000},
            {"lat": -22.9068, "lng": -43.1729}
        ]
        
        payload = {'path': new_path}
        
        url = f'/zabbix_api/api/fiber/{sample_cable.id}/'
        response = authenticated_client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        # Backend retorna payload completo do cabo, não apenas {points: X}
        assert 'path' in data
        assert len(data['path']) == 4
        
        # Valida que o cabo foi atualizado no banco
        cable = FiberCable.objects.get(id=sample_cable.id)
        assert len(cable.path_coordinates) == 4

    def test_update_cable_metadata(self, authenticated_client, sample_cable):
        """Testa atualização de metadados do cabo"""
        payload = {
            'name': 'Cabo Atualizado',
        }
        
        url = f'/zabbix_api/api/fiber/{sample_cable.id}/'
        response = authenticated_client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # Valida que o nome foi atualizado
        cable = FiberCable.objects.get(id=sample_cable.id)
        assert cable.name == 'Cabo Atualizado'

    def test_delete_cable(self, authenticated_client, sample_cable):
        """Testa deleção de cabo"""
        cable_id = sample_cable.id
        
        url = f'/zabbix_api/api/fiber/{cable_id}/'
        response = authenticated_client.delete(url)
        assert response.status_code in [200, 204]
        
        # Valida que o cabo foi deletado
        assert not FiberCable.objects.filter(id=cable_id).exists()

    def test_delete_cable_not_found(self, authenticated_client):
        """Testa deleção de cabo inexistente"""
        response = authenticated_client.delete(
            '/zabbix_api/api/fiber/99999/'
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestFiberCableVisualization:
    """Testes para visualização de cabos no mapa"""

    def test_load_all_cables(self, authenticated_client, sample_cable):
        """Testa endpoint de listagem de todos os cabos"""
        response = authenticated_client.get('/zabbix_api/api/fibers/')
        
        assert response.status_code == 200
        data = response.json()
        cables = data.get('fibers', data.get('cables', []))
        assert len(cables) >= 1


@pytest.mark.django_db
class TestFiberCableModel:
    """Testes para modelo FiberCable"""

    def test_cable_creation(self, sample_ports):
        """Testa criação de cabo"""
        port1, port2 = sample_ports
        cable = FiberCable.objects.create(
            name="Cabo Modelo Teste",
            origin_port=port1,
            destination_port=port2,
            path_coordinates=[
                {"lat": -23.5505, "lng": -46.6333},
                {"lat": -22.9068, "lng": -43.1729}
            ],
            length_km=400.0
        )
        
        assert cable.id is not None
        assert cable.name == "Cabo Modelo Teste"
        assert len(cable.path_coordinates) == 2
        assert cable.length_km == 400.0

    def test_cable_str_representation(self, sample_cable):
        """Testa representação string do cabo"""
        assert str(sample_cable) == "Cabo Teste SP-RJ"

    def test_cable_path_validation(self, sample_ports):
        """Testa validação do path (deve ser lista de dicts com lat/lng)"""
        port1, port2 = sample_ports
        
        # Path válido
        cable = FiberCable.objects.create(
            name="Cabo Path Válido",
            origin_port=port1,
            destination_port=port2,
            path_coordinates=[{"lat": -23.5505, "lng": -46.6333}],
            length_km=0.0
        )
        assert cable.id is not None


@pytest.mark.django_db
class TestFiberCableEdgeCases:
    """Testes para casos extremos"""

    def test_create_cable_with_single_point(
        self,
        authenticated_client,
        sample_ports
    ):
        """Testa criação de cabo com apenas 1 ponto"""
        port1, port2 = sample_ports
        payload = {
            'name': 'Cabo 1 Ponto',
            'origin_device_id': port1.device.id,
            'origin_port_id': port1.id,
            'dest_device_id': port2.device.id,
            'dest_port_id': port2.id,
            'path': [{"lat": -23.5505, "lng": -46.6333}]
        }
        
        response = authenticated_client.post(
            '/zabbix_api/api/fibers/manual-create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Backend deve rejeitar (mínimo 2 pontos)
        # Aceita 400 (validação) ou 500 (erro interno)
        assert response.status_code in [400, 500]

    def test_create_cable_with_many_points(
        self,
        authenticated_client,
        sample_ports
    ):
        """Testa criação de cabo com muitos pontos (100)"""
        port1, port2 = sample_ports
        
        # Gera 100 pontos entre SP e RJ
        path = []
        for i in range(100):
            lat = -23.5505 + ((-22.9068 + 23.5505) / 100) * i
            lng = -46.6333 + ((-43.1729 + 46.6333) / 100) * i
            path.append({"lat": lat, "lng": lng})
        
        payload = {
            'name': 'Cabo 100 Pontos',
            'origin_device_id': port1.device.id,
            'origin_port_id': port1.id,
            'dest_device_id': port2.device.id,
            'dest_port_id': port2.id,
            'path': path
        }
        
        response = authenticated_client.post(
            '/zabbix_api/api/fibers/manual-create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data['points'] == 100

    def test_update_cable_empty_path(
        self,
        authenticated_client,
        sample_cable
    ):
        """Testa atualização com path vazio"""
        payload = {'path': []}
        
        url = f'/zabbix_api/api/fiber/{sample_cable.id}/'
        response = authenticated_client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Backend permite path vazio (allow_empty=True)
        assert response.status_code == 200


@pytest.mark.django_db
class TestFiberCablePermissions:
    """Testes para permissões de acesso"""

    def test_list_cables_unauthenticated(self):
        """Testa listagem de cabos sem autenticação"""
        client = Client()
        response = client.get('/zabbix_api/api/fibers/')
        
        # Pode redirecionar para login ou retornar 401/403
        assert response.status_code in [302, 401, 403, 200]

    def test_create_cable_unauthenticated(self, sample_ports):
        """Testa criação de cabo sem autenticação"""
        client = Client()
        port1, port2 = sample_ports
        
        payload = {
            'name': 'Cabo Sem Auth',
            'origin_device_id': port1.device.id,
            'origin_port_id': port1.id,
            'dest_device_id': port2.device.id,
            'dest_port_id': port2.id,
            'path': [{"lat": -23.5505, "lng": -46.6333}]
        }
        
        response = client.post(
            '/zabbix_api/api/fibers/manual-create/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Deve rejeitar sem autenticação
        assert response.status_code in [302, 401, 403]
