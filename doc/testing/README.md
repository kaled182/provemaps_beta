# 🧪 Testing Documentation - MapsProveFiber

**Última Atualização**: 7 de Fevereiro de 2026

Documentação completa sobre testes do projeto MapsProveFiber, incluindo organização, execução e boas práticas.

---

## 📁 Estrutura de Testes

```
backend/
├── tests/                          # Testes principais
│   ├── __init__.py
│   ├── conftest.py                 # Fixtures compartilhadas
│   ├── README.md                   # Este arquivo
│   │
│   ├── inventory/                  # Testes do módulo inventory
│   │   ├── test_models.py
│   │   ├── test_serializers.py
│   │   └── test_viewsets.py
│   │
│   ├── routes/                     # Testes de rotas/otimização
│   │   └── test_route_optimization.py
│   │
│   ├── usecases/                   # Testes de casos de uso
│   │   ├── test_fiber_usecases.py
│   │   └── test_port_usecases.py
│   │
│   ├── scripts/                    # 🆕 Scripts de teste e debug
│   │   ├── check_cables.py
│   │   ├── check_cameras.py
│   │   ├── diagnose_zabbix.py
│   │   ├── fix_cable_50.py
│   │   ├── test_fusion_manual.py
│   │   └── verify_gist_index.py
│   │
│   ├── test_*.py                   # Testes de integração e features
│   │   ├── test_backup_config.py
│   │   ├── test_cable_serializer.py
│   │   ├── test_cache_swr.py
│   │   ├── test_celery_metrics.py
│   │   ├── test_custom_maps_endpoints.py
│   │   ├── test_fiber_modal_data_flow.py
│   │   ├── test_optical_endpoint.py
│   │   ├── test_security_permissions.py
│   │   ├── test_session_persistence.py
│   │   ├── test_user_sync.py
│   │   └── test_zabbix_service.py
│   │
│   └── audit_legacy_database.sql   # Scripts SQL de auditoria

pytest.ini                          # Configuração pytest raiz
backend/pytest.ini                  # Configuração pytest backend
```

---

## 🎯 Categorias de Testes

### 1. **Testes Unitários** (`backend/tests/inventory/`, `backend/tests/usecases/`)
- Testam componentes isolados (modelos, serializers, usecases)
- Execução rápida (<1s por teste)
- Não dependem de serviços externos

**Exemplos**:
- `test_models.py` — Validação de modelos Django
- `test_serializers.py` — Serialização/deserialização
- `test_fiber_usecases.py` — Lógica de negócio de fibras

### 2. **Testes de Integração** (`backend/tests/test_*.py`)
- Testam interação entre componentes
- Podem usar banco de dados de teste
- Incluem endpoints REST API

**Exemplos**:
- `test_fiber_modal_data_flow.py` — Fluxo completo de edição de fibras
- `test_custom_maps_endpoints.py` — Endpoints de custom maps
- `test_user_sync.py` — Sincronização de usuários

### 3. **Testes de Celery** (`test_celery_*.py`, `test_maps_view_tasks.py`)
- Validam tasks assíncronas
- Modo eager ativado em testes (execução síncrona)
- Verificam agendamento e execução

**Exemplos**:
- `test_celery_schedule.py` — Validação de schedules periódicas
- `test_maps_view_tasks.py` — Tasks de atualização de dashboard

### 4. **Testes de Segurança** (`test_security_permissions.py`, `test_zabbix_api_key_flow.py`)
- Validam autenticação e autorização
- Verificam permissions em endpoints
- Testam rotação de credenciais

### 5. **Testes de Cache e Performance** (`test_cache_*.py`, `test_inventory_cache.py`)
- Validam estratégias de cache (SWR, Redis)
- Testam invalidação de cache
- Verificam métricas Prometheus

### 6. **Scripts de Debug** (`backend/tests/scripts/`)
- Scripts ad-hoc para diagnóstico
- Ferramentas de correção de dados
- Validações manuais

---

## ⚙️ Ambiente de Execução

### ⚠️ **IMPORTANTE: TODO TESTE DEVE RODAR NO DOCKER**

Nunca execute testes diretamente no host Windows/Linux. O ambiente Docker garante:
- ✅ PostgreSQL + PostGIS configurados
- ✅ GDAL e bibliotecas geoespaciais
- ✅ Redis e Celery disponíveis
- ✅ Dependências Python completas

### Comandos Básicos

```bash
# Executar todos os testes
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/ -v

# Executar testes rápidos (sem slow/integration)
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/ -v -m "not slow and not integration"

# Executar teste específico
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_custom_maps_endpoints.py -v

# Executar com cobertura
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/ --cov --cov-report=html

# Executar apenas testes de segurança
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_security_permissions.py -v

# Executar testes de Celery
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_celery_schedule.py -v

# Executar scripts de debug
docker compose -f docker/docker-compose.yml exec web python backend/tests/scripts/check_cables.py
docker compose -f docker/docker-compose.yml exec web python backend/tests/scripts/diagnose_zabbix.py
```

---

## 🏷️ Marcadores (Markers)

Os testes utilizam markers pytest para categorização:

```python
@pytest.mark.slow          # Testes lentos (>5s)
@pytest.mark.integration   # Testes de integração
@pytest.mark.zabbix        # Testes que dependem de Zabbix
@pytest.mark.celery        # Testes de Celery tasks
@pytest.mark.api           # Testes de endpoints REST
@pytest.mark.security      # Testes de segurança
```

**Uso**:
```bash
# Executar apenas testes rápidos
docker compose -f docker/docker-compose.yml exec web pytest -m "not slow"

# Executar apenas testes de API
docker compose -f docker/docker-compose.yml exec web pytest -m api

# Executar testes de Celery E integração
docker compose -f docker/docker-compose.yml exec web pytest -m "celery and integration"
```

---

## 🔧 Configuração de Testes

### pytest.ini (raiz do projeto)

```ini
[pytest]
DJANGO_SETTINGS_MODULE = settings.test
pythonpath = . backend
testpaths = backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
    --reuse-db
markers =
    slow: Testes lentos (>5s)
    integration: Testes de integração
    zabbix: Testes que dependem de Zabbix
    celery: Testes de Celery tasks
    api: Testes de endpoints REST
    security: Testes de segurança
```

### settings/test.py

```python
# Configuração de testes
CELERY_TASK_ALWAYS_EAGER = True  # Executa tasks síncronas
CELERY_TASK_EAGER_PROPAGATES = True

# Banco de dados de teste
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',  # SQLite para testes rápidos
        'NAME': ':memory:',
    }
}

# Cache em memória
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
```

---

## 📊 Cobertura de Código

### Executar com Cobertura

```bash
# Gerar relatório HTML
docker compose -f docker/docker-compose.yml exec web pytest --cov --cov-report=html

# Gerar relatório no terminal
docker compose -f docker/docker-compose.yml exec web pytest --cov --cov-report=term-missing

# Salvar relatório em arquivo
docker compose -f docker/docker-compose.yml exec web pytest --cov --cov-report=term > coverage_report.txt
```

### Metas de Cobertura

| Módulo | Meta | Atual |
|--------|------|-------|
| `inventory/` | 85% | ~80% |
| `maps_view/` | 80% | ~75% |
| `monitoring/` | 75% | ~70% |
| `integrations/` | 70% | ~65% |

---

## 🚀 CI/CD Pipeline

### GitHub Actions (em desenvolvimento)

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgis/postgis:13-3.1
      redis:
        image: redis:6-alpine
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: docker compose -f docker/docker-compose.yml exec web pytest backend/tests/ -v
```

---

## 📚 Documentos Relacionados

- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** — Guia completo de testes
- **[backend/tests/README.md](../../backend/tests/README.md)** — Organização de testes
- **[../guides/DEVELOPMENT.md](../guides/DEVELOPMENT.md)** — Guia de desenvolvimento
- **[../operations/DEPLOYMENT.md](../operations/DEPLOYMENT.md)** — Deploy e CI/CD

---

## 📞 Suporte

- **Issues**: Use GitHub Issues para reportar bugs em testes
- **Documentação**: Leia os comentários em `conftest.py` para fixtures disponíveis
- **Referência**: Consulte [pytest docs](https://docs.pytest.org) e [Django testing](https://docs.djangoproject.com/en/5.0/topics/testing/)

---

**Última Revisão**: 7 de Fevereiro de 2026  
**Mantenedor**: Time de Desenvolvimento MapsProveFiber
