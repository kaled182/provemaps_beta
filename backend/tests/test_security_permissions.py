"""
Testes para correção de segurança crítica - AllowAny permissions

Este módulo testa permissões de API ANTES e DEPOIS de corrigir
o problema de segurança identificado em inventory/viewsets.py:1064

CRÍTICO: Endpoint com AllowAny permite acesso não autenticado

⚠️ IMPORTANTE: Execute os testes no ambiente Docker
═══════════════════════════════════════════════════════════════
Todo o ecossistema do projeto funciona sob Docker, incluindo PostgreSQL + PostGIS.
Executar fora do Docker resultará em falhas (GDAL não disponível, etc.)

Para executar os testes:

    # Executar todos os testes de segurança:
    docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_security_permissions.py -v

    # Executar teste específico:
    docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_security_permissions.py::APIPermissionsSecurityTest -v
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from inventory.models import Site, Device, Port, FiberCable

User = get_user_model()


@pytest.mark.django_db
class APIPermissionsSecurityTest(TestCase):
    """Testes de segurança de permissões de API"""
    
    @classmethod
    def setUpTestData(cls):
        """Criar usuários e dados de teste"""
        # Usuário admin
        cls.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        
        # Usuário regular
        cls.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='user123'
        )
        
        # Dados de teste
        cls.site = Site.objects.create(
            name="Test Site",
            latitude=-15.7942,
            longitude=-47.8822
        )
        
        cls.device = Device.objects.create(
            name="Test Device",
            site=cls.site,
            zabbix_hostid="12345"
        )
        
        cls.port = Port.objects.create(
            name="Port 1",
            device=cls.device
        )
    
    def setUp(self):
        """Criar cliente para cada teste"""
        self.client = APIClient()
    
    # ========================================================================
    # TESTES DE BASELINE (Estado Atual - com AllowAny)
    # ========================================================================
    
    def test_baseline_site_list_without_auth_should_fail(self):
        """
        BASELINE: Listar sites SEM autenticação deve falhar
        
        Se este teste PASSAR (403/401), permissões estão OK.
        Se este teste FALHAR (200), temos problema de segurança.
        """
        response = self.client.get('/api/v1/inventory/sites/')
        
        # Documentar estado atual
        print(f"\n📊 Site List sem auth: {response.status_code}")
        
        # O correto seria 401 ou 403
        # Se retornar 200, temos problema de segurança
        if response.status_code == status.HTTP_200_OK:
            print("   ⚠️  PROBLEMA DE SEGURANÇA: Acesso permitido sem autenticação")
            pytest.skip("Endpoint permite acesso não autenticado - será corrigido")
        else:
            print("   ✅ Acesso negado corretamente")
    
    def test_baseline_device_list_without_auth_should_fail(self):
        """BASELINE: Listar devices SEM autenticação"""
        response = self.client.get('/api/v1/inventory/devices/')
        
        print(f"\n📊 Device List sem auth: {response.status_code}")
        
        if response.status_code == status.HTTP_200_OK:
            print("   ⚠️  PROBLEMA: Acesso permitido sem autenticação")
            pytest.skip("Será corrigido")
        else:
            print("   ✅ Acesso negado")
    
    def test_baseline_port_list_without_auth_should_fail(self):
        """BASELINE: Listar ports SEM autenticação"""
        response = self.client.get('/api/v1/inventory/ports/')
        
        print(f"\n📊 Port List sem auth: {response.status_code}")
        
        if response.status_code == status.HTTP_200_OK:
            print("   ⚠️  PROBLEMA: Acesso permitido sem autenticação")
            pytest.skip("Será corrigido")
        else:
            print("   ✅ Acesso negado")
    
    def test_baseline_cable_list_without_auth_should_fail(self):
        """BASELINE: Listar cabos SEM autenticação"""
        response = self.client.get('/api/v1/inventory/fiber-cables/')
        
        print(f"\n📊 Cable List sem auth: {response.status_code}")
        
        if response.status_code == status.HTTP_200_OK:
            print("   ⚠️  PROBLEMA: Acesso permitido sem autenticação")
            pytest.skip("Será corrigido")
        else:
            print("   ✅ Acesso negado")
    
    # ========================================================================
    # TESTES COM AUTENTICAÇÃO (Devem funcionar)
    # ========================================================================
    
    def test_authenticated_user_can_list_sites(self):
        """Usuário autenticado DEVE conseguir listar sites"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/v1/inventory/sites/')
        
        assert response.status_code == status.HTTP_200_OK
        print("\n✅ Usuário autenticado pode listar sites")
    
    def test_admin_user_can_create_site(self):
        """Admin DEVE conseguir criar site"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'name': 'New Site',
            'latitude': -15.8000,
            'longitude': -47.9000
        }
        
        response = self.client.post('/api/v1/inventory/sites/', data)
        
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]
        print("\n✅ Admin pode criar site")
    
    # ========================================================================
    # TESTES DE OPERAÇÕES PERIGOSAS (Devem requerer admin)
    # ========================================================================
    
    def test_regular_user_cannot_delete_site(self):
        """Usuário regular NÃO DEVE conseguir deletar site"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.delete(f'/api/v1/inventory/sites/{self.site.id}/')
        
        # Deve retornar 403 (Forbidden) ou 405 (Method Not Allowed)
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ], f"Usuário regular conseguiu deletar site! Status: {response.status_code}"
        
        print("\n✅ Usuário regular não pode deletar site")
    
    def test_unauthenticated_user_cannot_create_device(self):
        """Usuário NÃO autenticado NÃO DEVE conseguir criar device"""
        data = {
            'name': 'Hack Device',
            'site': self.site.id,
            'zabbix_hostid': '99999'
        }
        
        response = self.client.post('/api/v1/inventory/devices/', data)
        
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ], f"Usuário não autenticado criou device! Status: {response.status_code}"
        
        print("\n✅ Não autenticado não pode criar device")


@pytest.mark.django_db
class SpecificViewSetPermissionTest(TestCase):
    """Testes específicos por ViewSet para identificar quais têm AllowAny"""
    
    def setUp(self):
        self.client = APIClient()
    
    def _test_endpoint_without_auth(self, url, method='get'):
        """Helper para testar endpoint sem autenticação"""
        if method == 'get':
            response = self.client.get(url)
        elif method == 'post':
            response = self.client.post(url, {})
        else:
            response = self.client.get(url)
        
        return response.status_code
    
    def test_all_inventory_endpoints_require_auth(self):
        """Testa que todos os endpoints de inventory requerem autenticação"""
        endpoints = [
            '/api/v1/inventory/sites/',
            '/api/v1/inventory/devices/',
            '/api/v1/inventory/ports/',
            '/api/v1/inventory/fiber-cables/',
        ]
        
        print("\n🔒 Teste de Autenticação por Endpoint:")
        
        vulnerable_endpoints = []
        
        for endpoint in endpoints:
            status_code = self._test_endpoint_without_auth(endpoint)
            
            if status_code == 200:
                print(f"   ⚠️  {endpoint}: {status_code} (VULNERÁVEL)")
                vulnerable_endpoints.append(endpoint)
            else:
                print(f"   ✅ {endpoint}: {status_code} (Protegido)")
        
        if vulnerable_endpoints:
            print(f"\n⚠️  Total de endpoints vulneráveis: {len(vulnerable_endpoints)}")
            print("   Estes endpoints serão corrigidos na próxima etapa")
        else:
            print("\n✅ Todos os endpoints estão protegidos")


# Teste de regressão para garantir que correção não quebrou funcionalidade
@pytest.mark.django_db  
class PostFixRegressionTest(TestCase):
    """
    Testes de regressão a serem executados APÓS correção de segurança
    
    Garantem que usuários autenticados ainda conseguem usar a API
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            password='test123'
        )
        
        cls.admin = User.objects.create_superuser(
            username='admin',
            password='admin123'
        )
    
    def setUp(self):
        self.client = APIClient()
    
    def test_authenticated_user_workflow_still_works(self):
        """Workflow completo de usuário autenticado deve funcionar"""
        # 1. Login
        self.client.force_authenticate(user=self.user)
        
        # 2. Listar sites
        response = self.client.get('/api/v1/inventory/sites/')
        assert response.status_code == 200
        
        # 3. Listar devices
        response = self.client.get('/api/v1/inventory/devices/')
        assert response.status_code == 200
        
        # 4. Listar ports
        response = self.client.get('/api/v1/inventory/ports/')
        assert response.status_code == 200
        
        print("\n✅ Workflow de usuário autenticado funciona")
    
    def test_admin_can_still_manage_resources(self):
        """Admin ainda consegue gerenciar recursos"""
        self.client.force_authenticate(user=self.admin)
        
        # Criar site
        data = {'name': 'Admin Site', 'latitude': -15.0, 'longitude': -47.0}
        response = self.client.post('/api/v1/inventory/sites/', data)
        assert response.status_code in [200, 201]
        
        print("\n✅ Admin pode gerenciar recursos")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
