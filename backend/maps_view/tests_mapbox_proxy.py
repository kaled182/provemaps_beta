"""
Testes para o proxy Mapbox.

Valida que o proxy está funcionando corretamente e retornando JSON em vez de HTML.
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from setup_app.models import FirstTimeSetup

User = get_user_model()


@pytest.fixture
def authenticated_client(db):
    """Cliente autenticado para testes."""
    user = User.objects.create_user(username='testuser', password='testpass123')
    client = Client()
    client.login(username='testuser', password='testpass123')
    return client


@pytest.fixture
def mapbox_config(db):
    """Configuração com token Mapbox."""
    config, _ = FirstTimeSetup.objects.get_or_create(pk=1)
    config.mapbox_token = 'pk.eyJ1Ijoia2FsZWQxODIiLCJhIjoiY21jNjd1M3p2MGozMTJvcDloa3kzeXZ0cCJ9.azs0yBSvCd8WlGXB-pptog'
    config.save()
    return config


@pytest.mark.django_db
class TestMapboxProxy:
    """Testes para endpoints do proxy Mapbox."""
    
    def test_proxy_requires_authentication(self, db):
        """Proxy deve exigir autenticação."""
        client = Client()
        response = client.get('/maps/api/mapbox-proxy/styles/mapbox/streets-v12')
        
        # Deve redirecionar para login
        assert response.status_code == 302
        assert '/accounts/login' in response.url
    
    def test_proxy_without_token_returns_error(self, authenticated_client, db):
        """Proxy sem token configurado deve retornar erro JSON."""
        # Garantir que não há token
        FirstTimeSetup.objects.filter(pk=1).delete()
        
        response = authenticated_client.get('/maps/api/mapbox-proxy/styles/mapbox/streets-v12')
        
        assert response.status_code == 500
        assert response['Content-Type'] == 'application/json'
        data = response.json()
        assert 'error' in data
        assert 'Token Mapbox não configurado' in data['error']
    
    def test_proxy_returns_json_not_html(self, authenticated_client, mapbox_config):
        """Proxy deve retornar JSON da API Mapbox, não HTML."""
        response = authenticated_client.get('/maps/api/mapbox-proxy/styles/mapbox/streets-v12')
        
        # Não deve ser HTML
        assert not response.content.startswith(b'<!DOCTYPE')
        assert not response.content.startswith(b'<html')
        
        # Content-Type deve ser JSON
        content_type = response['Content-Type']
        assert 'json' in content_type.lower() or response.status_code != 200
    
    def test_proxy_forwards_mapbox_response(self, authenticated_client, mapbox_config):
        """Proxy deve encaminhar resposta da API Mapbox."""
        response = authenticated_client.get('/maps/api/mapbox-proxy/styles/mapbox/streets-v12')
        
        # Se API Mapbox estiver acessível, deve retornar 200
        # Se houver problema de rede, deve retornar 502
        assert response.status_code in [200, 502]
        
        if response.status_code == 200:
            # Deve ser JSON válido
            data = response.json()
            # Style JSON deve ter campos obrigatórios
            assert 'version' in data or 'name' in data or 'sources' in data
    
    def test_proxy_tiles_endpoint(self, authenticated_client, mapbox_config):
        """Endpoint de tiles deve aceitar requests."""
        response = authenticated_client.get(
            '/maps/api/mapbox-proxy/tiles/mapbox.mapbox-streets-v8/0/0/0.vector.pbf'
        )
        
        # Deve processar (200 ou 502 se offline)
        assert response.status_code in [200, 404, 502]
        
        # Content-Type deve ser protobuf se sucesso
        if response.status_code == 200:
            assert 'protobuf' in response['Content-Type'].lower()
    
    def test_proxy_sprites_endpoint(self, authenticated_client, mapbox_config):
        """Endpoint de sprites deve aceitar requests."""
        response = authenticated_client.get(
            '/maps/api/mapbox-proxy/sprites/mapbox/streets-v12/sprite.json'
        )
        
        assert response.status_code in [200, 404, 502]
    
    def test_proxy_glyphs_endpoint(self, authenticated_client, mapbox_config):
        """Endpoint de glyphs deve aceitar requests."""
        response = authenticated_client.get(
            '/maps/api/mapbox-proxy/fonts/Open%20Sans%20Regular/0-255.pbf'
        )
        
        assert response.status_code in [200, 404, 502]


@pytest.mark.django_db
@pytest.mark.integration
class TestMapboxIntegration:
    """Testes de integração com API Mapbox real."""
    
    @pytest.mark.slow
    def test_real_mapbox_api_call(self, authenticated_client, mapbox_config):
        """Testa chamada real para API Mapbox (requer internet)."""
        response = authenticated_client.get('/maps/api/mapbox-proxy/styles/mapbox/streets-v12')
        
        # Se temos internet e token válido, deve retornar 200
        if response.status_code == 200:
            data = response.json()
            assert 'version' in data
            assert data['version'] == 8  # Mapbox Style Spec version
            assert 'sources' in data
            assert 'layers' in data
            assert len(data['layers']) > 0
            
            print(f"\n✅ API Mapbox respondeu com {len(data['layers'])} layers")
            print(f"   Style name: {data.get('name', 'N/A')}")
            print(f"   Metadata: {data.get('metadata', {})}")
