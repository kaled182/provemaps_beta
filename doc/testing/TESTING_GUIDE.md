# 🧪 Guia Completo de Testes - MapsProveFiber

**Data**: 7 de Fevereiro de 2026  
**Versão**: 2.1.0

---

## 📋 Índice

1. [Ambiente de Testes](#ambiente-de-testes)
2. [Tipos de Testes](#tipos-de-testes)
3. [Executando Testes](#executando-testes)
4. [Escrevendo Testes](#escrevendo-testes)
5. [Fixtures e Helpers](#fixtures-e-helpers)
6. [Debugging](#debugging)
7. [Boas Práticas](#boas-práticas)
8. [Troubleshooting](#troubleshooting)

---

## 🐳 Ambiente de Testes

### ⚠️ Regra de Ouro: SEMPRE USE DOCKER

**NUNCA execute testes diretamente no host Windows/Linux.** O ambiente Docker é obrigatório porque:

✅ **PostgreSQL + PostGIS**: Banco de dados geoespacial configurado  
✅ **GDAL**: Bibliotecas geoespaciais instaladas  
✅ **Redis**: Cache e broker Celery disponíveis  
✅ **Celery**: Worker configurado corretamente  
✅ **Dependências Python**: Todas instaladas via requirements.txt  
✅ **Ambiente idêntico à produção**: Evita "funciona na minha máquina"

### Iniciar Ambiente de Testes

```bash
# Subir todos os serviços
cd docker
docker compose up -d

# Verificar status
docker compose ps

# Acessar shell do container web
docker compose exec web bash

# Executar testes (de fora do container)
docker compose exec web pytest backend/tests/ -v
```

---

## 🎯 Tipos de Testes

### 1. Testes Unitários

**Objetivo**: Testar componentes isolados (models, serializers, utils)

**Localização**: `backend/tests/inventory/`, `backend/tests/usecases/`

**Características**:
- Execução rápida (<1s por teste)
- Sem dependências externas (Zabbix, Redis, etc.)
- Usam factories para criar dados de teste

**Exemplo**:

```python
# backend/tests/inventory/test_models.py
import pytest
from inventory.models import FiberCable, Site

@pytest.mark.django_db
def test_fiber_cable_creation():
    """Testa criação de cabo de fibra"""
    site_a = Site.objects.create(name="Site A", code="STA")
    site_b = Site.objects.create(name="Site B", code="STB")
    
    cable = FiberCable.objects.create(
        name="Cable Test",
        site_a=site_a,
        site_b=site_b,
        fiber_count=24
    )
    
    assert cable.name == "Cable Test"
    assert cable.fiber_count == 24
    assert cable.site_a == site_a
```

### 2. Testes de Integração

**Objetivo**: Testar interação entre componentes

**Localização**: `backend/tests/test_*.py`

**Características**:
- Testa fluxos completos (request → viewset → usecase → model)
- Usa banco de dados de teste
- Pode incluir chamadas HTTP

**Exemplo**:

```python
# backend/tests/test_custom_maps_endpoints.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

@pytest.mark.api
@pytest.mark.django_db
def test_create_custom_map(api_client, authenticated_user):
    """Testa criação de custom map via API"""
    response = api_client.post('/api/v1/maps/custom/', {
        'name': 'Mapa Teste',
        'description': 'Teste de criação'
    })
    
    assert response.status_code == 201
    assert response.data['name'] == 'Mapa Teste'
```

### 3. Testes de Celery

**Objetivo**: Validar tasks assíncronas

**Localização**: `backend/tests/test_celery_*.py`

**Características**:
- Modo eager ativado (execução síncrona)
- Testa agendamento e execução
- Valida resultados de tasks

**Exemplo**:

```python
# backend/tests/test_celery_schedule.py
import pytest
from maps_view.tasks import refresh_dashboard_cache

@pytest.mark.celery
@pytest.mark.django_db
def test_refresh_dashboard_task():
    """Testa task de refresh do dashboard"""
    result = refresh_dashboard_cache.delay()
    
    assert result.successful()
    # Verificar que cache foi atualizado
    from django.core.cache import cache
    cached_data = cache.get('dashboard_data')
    assert cached_data is not None
```

### 4. Testes de API/Endpoints

**Objetivo**: Validar endpoints REST

**Localização**: `backend/tests/test_*_endpoint.py`

**Características**:
- Usa DRF APIClient
- Testa autenticação e permissions
- Valida serialização de responses

**Exemplo**:

```python
# backend/tests/test_fiber_cable_endpoint.py
import pytest
from rest_framework import status

@pytest.mark.api
@pytest.mark.django_db
def test_list_fiber_cables(api_client, authenticated_user):
    """Testa listagem de cabos de fibra"""
    response = api_client.get('/api/v1/fiber-cables/')
    
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.data, list)
```

### 5. Testes de Segurança

**Objetivo**: Validar autenticação e autorização

**Localização**: `backend/tests/test_security_permissions.py`

**Características**:
- Verifica permissions em endpoints
- Testa rotação de credenciais
- Valida políticas de acesso

**Exemplo**:

```python
# backend/tests/test_security_permissions.py
import pytest
from rest_framework import status

@pytest.mark.security
@pytest.mark.django_db
def test_unauthorized_access_denied(api_client):
    """Verifica que acesso não autenticado é negado"""
    response = api_client.get('/api/v1/fiber-cables/')
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

---

## 🚀 Executando Testes

### Comandos Básicos

```bash
# Todos os testes
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/ -v

# Testes rápidos (sem slow/integration)
docker compose -f docker/docker-compose.yml exec web pytest -m "not slow and not integration"

# Teste específico
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_custom_maps_endpoints.py -v

# Teste específico (função)
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_custom_maps_endpoints.py::test_create_custom_map -v

# Apenas testes de API
docker compose -f docker/docker-compose.yml exec web pytest -m api -v

# Apenas testes de segurança
docker compose -f docker/docker-compose.yml exec web pytest -m security -v

# Apenas testes de Celery
docker compose -f docker/docker-compose.yml exec web pytest -m celery -v
```

### Cobertura de Código

```bash
# Cobertura completa
docker compose -f docker/docker-compose.yml exec web pytest --cov --cov-report=html

# Cobertura com relatório no terminal
docker compose -f docker/docker-compose.yml exec web pytest --cov --cov-report=term-missing

# Cobertura de módulo específico
docker compose -f docker/docker-compose.yml exec web pytest --cov=inventory --cov-report=term

# Abrir relatório HTML (após gerar)
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

### Executar com Verbosidade

```bash
# Verbosidade mínima
docker compose -f docker/docker-compose.yml exec web pytest -q

# Verbosidade padrão
docker compose -f docker/docker-compose.yml exec web pytest -v

# Verbosidade máxima
docker compose -f docker/docker-compose.yml exec web pytest -vv

# Mostrar prints
docker compose -f docker/docker-compose.yml exec web pytest -s

# Mostrar warnings
docker compose -f docker/docker-compose.yml exec web pytest -v --tb=short -W default
```

### Executar com Filtros

```bash
# Por nome de teste
docker compose -f docker/docker-compose.yml exec web pytest -k "cable"

# Por marker
docker compose -f docker/docker-compose.yml exec web pytest -m api

# Combinar markers
docker compose -f docker/docker-compose.yml exec web pytest -m "api and not slow"

# Excluir markers
docker compose -f docker/docker-compose.yml exec web pytest -m "not zabbix"
```

### Executar Scripts de Debug

```bash
# Script de verificação de cabos
docker compose -f docker/docker-compose.yml exec web python backend/tests/scripts/check_cables.py

# Diagnóstico de Zabbix
docker compose -f docker/docker-compose.yml exec web python backend/tests/scripts/diagnose_zabbix.py

# Verificar índice GIST
docker compose -f docker/docker-compose.yml exec web python backend/tests/scripts/verify_gist_index.py
```

---

## ✍️ Escrevendo Testes

### Template Básico

```python
"""
Tests for [module/feature name]

Description: [What this test module covers]
"""
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

# Markers
pytestmark = [pytest.mark.django_db]

# Fixtures locais (se necessário)
@pytest.fixture
def sample_data():
    """Create sample data for tests"""
    # Setup
    data = {"key": "value"}
    yield data
    # Teardown (opcional)

# Testes
def test_something(sample_data):
    """Test description"""
    # Arrange
    expected = "value"
    
    # Act
    result = sample_data["key"]
    
    # Assert
    assert result == expected
```

### Estrutura AAA (Arrange-Act-Assert)

```python
def test_fiber_cable_serialization():
    """Testa serialização de cabo de fibra"""
    # Arrange - Preparar dados
    cable = FiberCable.objects.create(
        name="Test Cable",
        fiber_count=24
    )
    serializer = FiberCableSerializer(cable)
    
    # Act - Executar ação
    data = serializer.data
    
    # Assert - Verificar resultado
    assert data['name'] == "Test Cable"
    assert data['fiber_count'] == 24
```

### Usando Markers

```python
import pytest

# Aplicar marker a teste individual
@pytest.mark.slow
@pytest.mark.integration
def test_complex_operation():
    """Teste lento de integração"""
    pass

# Aplicar marker a módulo inteiro
pytestmark = [pytest.mark.api, pytest.mark.django_db]

def test_api_endpoint():
    """Todos os testes neste módulo terão markers api e django_db"""
    pass
```

### Testando Endpoints

```python
@pytest.mark.api
@pytest.mark.django_db
def test_create_fiber_cable(api_client, authenticated_user):
    """Testa criação de cabo via API"""
    # Arrange
    payload = {
        'name': 'New Cable',
        'fiber_count': 48,
        'site_a': 1,
        'site_b': 2
    }
    
    # Act
    response = api_client.post('/api/v1/fiber-cables/', payload)
    
    # Assert
    assert response.status_code == 201
    assert response.data['name'] == 'New Cable'
    
    # Verificar banco de dados
    cable = FiberCable.objects.get(name='New Cable')
    assert cable.fiber_count == 48
```

### Testando Exceptions

```python
def test_invalid_cable_raises_error():
    """Testa que cabo inválido levanta erro"""
    with pytest.raises(ValidationError) as exc_info:
        FiberCable.objects.create(
            name="",  # Nome vazio deve falhar
            fiber_count=-1  # Quantidade negativa deve falhar
        )
    
    assert 'name' in str(exc_info.value)
```

### Testando Tasks Celery

```python
@pytest.mark.celery
@pytest.mark.django_db
def test_celery_task():
    """Testa task Celery"""
    # Modo eager ativado em settings.test
    result = my_task.delay(arg1, arg2)
    
    assert result.successful()
    assert result.result == expected_value
```

---

## 🔧 Fixtures e Helpers

### Fixtures Globais (conftest.py)

```python
# backend/tests/conftest.py

@pytest.fixture
def api_client():
    """DRF API Client"""
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def authenticated_user(api_client):
    """Usuário autenticado"""
    User = get_user_model()
    user = User.objects.create_user(
        username='testuser',
        password='testpass'
    )
    api_client.force_authenticate(user=user)
    return user

@pytest.fixture
def sample_fiber_cable():
    """Cabo de fibra de exemplo"""
    site_a = Site.objects.create(name="Site A", code="STA")
    site_b = Site.objects.create(name="Site B", code="STB")
    
    return FiberCable.objects.create(
        name="Test Cable",
        site_a=site_a,
        site_b=site_b,
        fiber_count=24
    )
```

### Usando Fixtures

```python
def test_with_fixtures(api_client, authenticated_user, sample_fiber_cable):
    """Usa múltiplas fixtures"""
    response = api_client.get(f'/api/v1/fiber-cables/{sample_fiber_cable.id}/')
    
    assert response.status_code == 200
    assert response.data['name'] == "Test Cable"
```

### Factories (Factory Boy)

```python
# backend/tests/factories.py
import factory
from inventory.models import Site, FiberCable

class SiteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Site
    
    name = factory.Sequence(lambda n: f"Site {n}")
    code = factory.Sequence(lambda n: f"ST{n}")

class FiberCableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FiberCable
    
    name = factory.Sequence(lambda n: f"Cable {n}")
    site_a = factory.SubFactory(SiteFactory)
    site_b = factory.SubFactory(SiteFactory)
    fiber_count = 24

# Uso
def test_with_factory():
    cable = FiberCableFactory.create()
    assert cable.fiber_count == 24
```

---

## 🐛 Debugging

### Usando pytest.set_trace()

```python
def test_debugging():
    """Teste com breakpoint"""
    cable = FiberCable.objects.create(name="Debug Cable")
    
    pytest.set_trace()  # Breakpoint aqui
    
    assert cable.name == "Debug Cable"
```

**Executar**:
```bash
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_file.py::test_debugging -s
```

### Usando --pdb

```bash
# Para no primeiro erro
docker compose -f docker/docker-compose.yml exec web pytest --pdb

# Para em exceções
docker compose -f docker/docker-compose.yml exec web pytest --pdb-trace
```

### Print Debugging

```python
def test_with_prints():
    """Teste com prints"""
    cable = FiberCable.objects.create(name="Test")
    
    print(f"\n[DEBUG] Cable ID: {cable.id}")
    print(f"[DEBUG] Cable Name: {cable.name}")
    
    assert cable.id is not None
```

**Executar com -s para ver prints**:
```bash
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_file.py -s
```

### Logging em Testes

```python
import logging

logger = logging.getLogger(__name__)

def test_with_logging(caplog):
    """Teste com logging"""
    with caplog.at_level(logging.INFO):
        logger.info("Starting test")
        # ... código do teste
        logger.info("Test complete")
    
    assert "Starting test" in caplog.text
```

---

## ✅ Boas Práticas

### 1. Nomes Descritivos

```python
# ❌ Ruim
def test_1():
    pass

# ✅ Bom
def test_fiber_cable_creation_with_valid_data():
    """Testa criação de cabo com dados válidos"""
    pass
```

### 2. Um Conceito por Teste

```python
# ❌ Ruim - Testa múltiplas coisas
def test_everything():
    # Testa criação
    cable = FiberCable.objects.create(name="Test")
    # Testa atualização
    cable.name = "Updated"
    cable.save()
    # Testa deleção
    cable.delete()

# ✅ Bom - Um teste por conceito
def test_cable_creation():
    cable = FiberCable.objects.create(name="Test")
    assert cable.name == "Test"

def test_cable_update():
    cable = FiberCable.objects.create(name="Test")
    cable.name = "Updated"
    cable.save()
    assert cable.name == "Updated"
```

### 3. Independência de Testes

```python
# ❌ Ruim - Depende de ordem
def test_create():
    global cable
    cable = FiberCable.objects.create(name="Test")

def test_update():
    cable.name = "Updated"  # Depende de test_create

# ✅ Bom - Independente
@pytest.fixture
def cable():
    return FiberCable.objects.create(name="Test")

def test_create(cable):
    assert cable.name == "Test"

def test_update(cable):
    cable.name = "Updated"
    cable.save()
    assert cable.name == "Updated"
```

### 4. Usar Fixtures em Vez de Setup Global

```python
# ❌ Ruim
class TestFiberCable:
    def setup_method(self):
        self.cable = FiberCable.objects.create(name="Test")
    
    def test_name(self):
        assert self.cable.name == "Test"

# ✅ Bom
@pytest.fixture
def cable():
    return FiberCable.objects.create(name="Test")

def test_cable_name(cable):
    assert cable.name == "Test"
```

### 5. Markers para Categorização

```python
# ✅ Bom - Usar markers
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.zabbix
def test_zabbix_integration():
    """Teste de integração com Zabbix (lento)"""
    pass

# Executar apenas testes rápidos
# pytest -m "not slow"
```

---

## 🔍 Troubleshooting

### Problema: ModuleNotFoundError

**Sintoma**:
```
ModuleNotFoundError: No module named 'inventory'
```

**Solução**:
```bash
# Verificar que pytest.ini tem pythonpath correto
[pytest]
pythonpath = . backend

# Executar do diretório correto
cd /path/to/provemaps_beta
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/ -v
```

### Problema: GDAL não encontrado

**Sintoma**:
```
OSError: Could not find the GDAL library
```

**Solução**:
```bash
# SEMPRE use Docker - GDAL está instalado no container
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/ -v

# Não execute no host Windows/Linux
```

### Problema: Database já existe

**Sintoma**:
```
django.db.utils.DatabaseError: database "test_..." already exists
```

**Solução**:
```bash
# Usar --reuse-db para reutilizar banco
docker compose -f docker/docker-compose.yml exec web pytest --reuse-db

# Ou resetar banco de teste
docker compose -f docker/docker-compose.yml exec web python backend/manage.py flush --database=test --no-input
```

### Problema: Redis não disponível

**Sintoma**:
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solução**:
```bash
# Verificar que Redis está rodando
docker compose ps redis

# Reiniciar Redis se necessário
docker compose restart redis

# Em testes, usar cache em memória (configurado em settings.test)
```

### Problema: Celery tasks não executam

**Sintoma**:
```
Task não retorna resultado
```

**Solução**:
```python
# Verificar settings.test tem:
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Em testes, usar marker @pytest.mark.celery
@pytest.mark.celery
def test_task():
    result = my_task.delay()
    assert result.successful()
```

### Problema: Testes lentos

**Sintoma**:
```
Testes demorando muito (>30s)
```

**Solução**:
```bash
# Executar apenas testes rápidos
docker compose -f docker/docker-compose.yml exec web pytest -m "not slow"

# Usar --durations para identificar testes lentos
docker compose -f docker/docker-compose.yml exec web pytest --durations=10

# Considerar paralelização (pytest-xdist)
docker compose -f docker/docker-compose.yml exec web pytest -n auto
```

---

## 📊 Métricas e Relatórios

### Relatório de Cobertura

```bash
# Gerar relatório HTML
docker compose -f docker/docker-compose.yml exec web pytest --cov --cov-report=html

# Copiar relatório para host
docker compose cp web:/app/htmlcov ./htmlcov

# Abrir no navegador
start htmlcov/index.html  # Windows
```

### Relatório de Duração

```bash
# 10 testes mais lentos
docker compose -f docker/docker-compose.yml exec web pytest --durations=10

# Todos os testes com duração
docker compose -f docker/docker-compose.yml exec web pytest --durations=0
```

### Relatório JUnit (para CI/CD)

```bash
# Gerar relatório JUnit XML
docker compose -f docker/docker-compose.yml exec web pytest --junitxml=junit.xml

# Usado por Jenkins, GitLab CI, etc.
```

---

## 📚 Recursos Adicionais

### Documentação Oficial

- **Pytest**: https://docs.pytest.org
- **Django Testing**: https://docs.djangoproject.com/en/5.0/topics/testing/
- **DRF Testing**: https://www.django-rest-framework.org/api-guide/testing/
- **Factory Boy**: https://factoryboy.readthedocs.io

### Documentos do Projeto

- **[README.md](README.md)** — Visão geral de testes
- **[backend/tests/README.md](../../backend/tests/README.md)** — Organização de testes
- **[../guides/DEVELOPMENT.md](../guides/DEVELOPMENT.md)** — Guia de desenvolvimento

---

**Última Atualização**: 7 de Fevereiro de 2026  
**Mantenedor**: Time de Desenvolvimento MapsProveFiber
