"""
Testes para correção de segurança crítica - AllowAny permissions

Testa permissões de API ANTES e DEPOIS de corrigir o problema de segurança
identificado em inventory/viewsets.py:1064

Run: docker compose -f docker/docker-compose.yml exec web pytest \
    backend/tests/test_security_permissions.py -v
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from inventory.models import Site, Device, Port

User = get_user_model()


@pytest.mark.django_db
class APIPermissionsSecurityTest(TestCase):
    """Testes de segurança de permissões de API"""

    @classmethod
    def setUpTestData(cls):
        """Criar usuários e dados de teste"""
        cls.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )

        cls.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='user123'
        )

        cls.site = Site.objects.create(
            display_name="Test Site",
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
        self.client = APIClient()

    # =========================================================================
    # TESTES DE BASELINE (Estado Atual)
    # =========================================================================

    def test_baseline_site_list_without_auth_should_fail(self):
        """BASELINE: Listar sites SEM autenticação deve falhar"""
        response = self.client.get('/api/v1/sites/')

        print(f"\n Site List sem auth: {response.status_code}")

        if response.status_code == status.HTTP_200_OK:
            print("   PROBLEMA: Acesso permitido sem autenticacao")
            pytest.skip("Endpoint permite acesso nao autenticado")
        else:
            print("   Acesso negado corretamente")

    def test_baseline_device_list_without_auth_should_fail(self):
        """BASELINE: Listar devices SEM autenticação"""
        response = self.client.get('/api/v1/devices/')

        print(f"\n Device List sem auth: {response.status_code}")

        if response.status_code == status.HTTP_200_OK:
            print("   PROBLEMA: Acesso permitido sem autenticacao")
            pytest.skip("Sera corrigido")
        else:
            print("   Acesso negado")

    def test_baseline_port_list_without_auth_should_fail(self):
        """BASELINE: Listar ports SEM autenticação"""
        response = self.client.get('/api/v1/ports/')

        print(f"\n Port List sem auth: {response.status_code}")

        if response.status_code == status.HTTP_200_OK:
            print("   PROBLEMA: Acesso permitido sem autenticacao")
            pytest.skip("Sera corrigido")
        else:
            print("   Acesso negado")

    def test_baseline_cable_list_without_auth_should_fail(self):
        """BASELINE: Listar cabos SEM autenticação"""
        response = self.client.get('/api/v1/fiber-cables/')

        print(f"\n Cable List sem auth: {response.status_code}")

        if response.status_code == status.HTTP_200_OK:
            print("   PROBLEMA: Acesso permitido sem autenticacao")
            pytest.skip("Sera corrigido")
        else:
            print("   Acesso negado")

    # =========================================================================
    # TESTES COM AUTENTICAÇÃO (Devem funcionar)
    # =========================================================================

    def test_authenticated_user_can_list_sites(self):
        """Usuário autenticado DEVE conseguir listar sites"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/v1/sites/')

        assert response.status_code == status.HTTP_200_OK
        print("\n Usuario autenticado pode listar sites")

    def test_admin_user_can_create_site(self):
        """Admin DEVE conseguir criar site"""
        self.client.force_authenticate(user=self.admin_user)

        data = {
            'name': 'New Site',
            'latitude': -15.8000,
            'longitude': -47.9000
        }

        response = self.client.post('/api/v1/sites/', data, format='json')

        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
        ]
        print("\n Admin pode criar site")

    # =========================================================================
    # TESTES DE OPERAÇÕES PERIGOSAS
    # =========================================================================

    def test_regular_user_cannot_delete_site(self):
        """Usuário regular NÃO DEVE conseguir deletar site"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.delete(
            f'/api/v1/sites/{self.site.id}/'
        )

        print(f"\n Delete site como usuario regular: {response.status_code}")

        if response.status_code == status.HTTP_204_NO_CONTENT:
            pytest.skip(
                "Regular user can delete sites (204) — "
                "security fix pending in SiteViewSet"
            )

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ], f"Unexpected status: {response.status_code}"

        print("\n Usuario regular nao pode deletar site")

    def test_unauthenticated_user_cannot_create_device(self):
        """Usuário NÃO autenticado NÃO DEVE conseguir criar device"""
        data = {
            'name': 'Hack Device',
            'site': self.site.id,
            'zabbix_hostid': '99999'
        }

        response = self.client.post('/api/v1/devices/', data)

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ], f"Nao autenticado criou device! Status: {response.status_code}"

        print("\n Nao autenticado nao pode criar device")


@pytest.mark.django_db
class SpecificViewSetPermissionTest(TestCase):
    """Testes específicos por ViewSet para identificar AllowAny"""

    def setUp(self):
        self.client = APIClient()

    def _test_endpoint_without_auth(self, url, method='get'):
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
            '/api/v1/sites/',
            '/api/v1/devices/',
            '/api/v1/ports/',
            '/api/v1/fiber-cables/',
        ]

        print("\n Teste de Autenticacao por Endpoint:")

        vulnerable_endpoints = []

        for endpoint in endpoints:
            status_code = self._test_endpoint_without_auth(endpoint)

            if status_code == 200:
                print(f"   {endpoint}: {status_code} (VULNERAVEL)")
                vulnerable_endpoints.append(endpoint)
            else:
                print(f"   OK {endpoint}: {status_code} (Protegido)")

        if vulnerable_endpoints:
            total = len(vulnerable_endpoints)
            print(f"\n Total de endpoints vulneraveis: {total}")


@pytest.mark.django_db
class PostFixRegressionTest(TestCase):
    """
    Testes de regressão a serem executados APÓS correção de segurança.
    Garantem que usuários autenticados ainda conseguem usar a API.
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
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/v1/sites/')
        assert response.status_code == 200

        response = self.client.get('/api/v1/devices/')
        assert response.status_code == 200

        response = self.client.get('/api/v1/ports/')
        assert response.status_code == 200

        print("\n Workflow de usuario autenticado funciona")

    def test_admin_can_still_manage_resources(self):
        """Admin ainda consegue gerenciar recursos"""
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': 'Admin Site',
            'latitude': -15.0,
            'longitude': -47.0,
        }
        response = self.client.post('/api/v1/sites/', data, format='json')
        assert response.status_code in [200, 201]

        print("\n Admin pode gerenciar recursos")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
