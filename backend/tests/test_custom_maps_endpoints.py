"""
Teste dos endpoints de Custom Maps
Valida se as rotas estão corretamente registradas no Django
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestCustomMapsEndpoints:
    """Testa os endpoints de custom maps"""
    
    def test_custom_maps_list_endpoint_exists(self):
        """Verifica se o endpoint de listagem de mapas está acessível"""
        # Criar usuário de teste
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        client = Client()
        client.force_login(user)
        
        # Teste GET - listar mapas
        response = client.get('/api/v1/maps/custom/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert 'maps' in data, "Response should contain 'maps' key"
        assert 'total' in data, "Response should contain 'total' key"
        assert isinstance(data['maps'], list), "maps should be a list"
    
    def test_custom_maps_create_endpoint(self):
        """Verifica se o endpoint de criação de mapas está funcionando"""
        user = User.objects.create_user(
            username='testuser2',
            password='testpass123',
            email='test2@example.com'
        )
        
        client = Client()
        client.force_login(user)
        
        # Teste POST - criar novo mapa
        map_data = {
            'name': 'Mapa de Teste',
            'description': 'Descrição do mapa de teste',
            'category': 'backbone',
            'is_public': True
        }
        
        response = client.post(
            '/api/v1/maps/custom/',
            data=map_data,
            content_type='application/json'
        )
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        
        data = response.json()
        assert 'map' in data, "Response should contain 'map' key"
        assert data['map']['name'] == 'Mapa de Teste'
        assert 'id' in data['map'], "Map should have an ID"
    
    def test_custom_map_detail_endpoint(self):
        """Verifica se o endpoint de detalhes do mapa está funcionando"""
        from inventory.models import CustomMap
        
        user = User.objects.create_user(
            username='testuser3',
            password='testpass123',
            email='test3@example.com'
        )
        
        # Criar um mapa de teste
        custom_map = CustomMap.objects.create(
            name='Mapa Teste Detail',
            description='Descrição',
            category='backbone',
            is_public=True,
            created_by=user
        )
        
        client = Client()
        client.force_login(user)
        
        # Teste GET - buscar detalhes
        response = client.get(f'/api/v1/maps/custom/{custom_map.id}/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert 'map' in data
        assert data['map']['id'] == custom_map.id
        assert data['map']['name'] == 'Mapa Teste Detail'
    
    def test_custom_map_update_endpoint(self):
        """Verifica se o endpoint de atualização do mapa está funcionando"""
        from inventory.models import CustomMap
        
        user = User.objects.create_user(
            username='testuser4',
            password='testpass123',
            email='test4@example.com'
        )
        
        # Criar um mapa de teste
        custom_map = CustomMap.objects.create(
            name='Mapa Original',
            description='Descrição original',
            category='backbone',
            is_public=True,
            created_by=user
        )
        
        client = Client()
        client.force_login(user)
        
        # Teste PUT - atualizar mapa
        update_data = {
            'name': 'Mapa Atualizado',
            'description': 'Nova descrição',
            'category': 'backbone',
            'is_public': False
        }
        
        response = client.put(
            f'/api/v1/maps/custom/{custom_map.id}/',
            data=update_data,
            content_type='application/json'
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verificar se foi atualizado
        custom_map.refresh_from_db()
        assert custom_map.name == 'Mapa Atualizado'
        assert custom_map.description == 'Nova descrição'
        assert custom_map.is_public == False
    
    def test_custom_map_delete_endpoint(self):
        """Verifica se o endpoint de exclusão do mapa está funcionando"""
        from inventory.models import CustomMap
        
        user = User.objects.create_user(
            username='testuser5',
            password='testpass123',
            email='test5@example.com'
        )
        
        # Criar um mapa de teste
        custom_map = CustomMap.objects.create(
            name='Mapa para Deletar',
            description='Será deletado',
            category='backbone',
            is_public=True,
            created_by=user
        )
        
        map_id = custom_map.id
        
        client = Client()
        client.force_login(user)
        
        # Teste DELETE — implementação retorna 204 No Content
        response = client.delete(f'/api/v1/maps/custom/{map_id}/')
        assert response.status_code == 204, f"Expected 204, got {response.status_code}"
        
        # Verificar se foi deletado
        assert not CustomMap.objects.filter(id=map_id).exists()
    
    def test_save_map_items_endpoint(self):
        """Verifica se o endpoint de salvamento de itens está funcionando"""
        from inventory.models import CustomMap
        
        user = User.objects.create_user(
            username='testuser6',
            password='testpass123',
            email='test6@example.com'
        )
        
        # Criar um mapa de teste
        custom_map = CustomMap.objects.create(
            name='Mapa com Itens',
            description='Teste de itens',
            category='backbone',
            is_public=True,
            created_by=user
        )
        
        client = Client()
        client.force_login(user)
        
        # Teste POST - salvar itens
        items_data = {
            'selected_items': {
                'devices': [1, 2, 3],
                'cables': [10, 20],
                'cameras': [],
                'racks': []
            }
        }
        
        response = client.post(
            f'/api/v1/maps/custom/{custom_map.id}/items/',
            data=items_data,
            content_type='application/json'
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verificar se os itens foram salvos
        custom_map.refresh_from_db()
        assert custom_map.selected_devices == [1, 2, 3]
        assert custom_map.selected_cables == [10, 20]
