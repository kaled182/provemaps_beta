# 📋 Índice de Documentação de Testes

Navegação rápida para toda a documentação de testes do projeto MapsProveFiber.

---

## 🎯 Início Rápido

- **[README.md](README.md)** — Visão geral e estrutura de testes
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** — Guia completo de execução e desenvolvimento

---

## 📚 Documentação por Categoria

### Para Desenvolvedores

1. **[TESTING_GUIDE.md](TESTING_GUIDE.md)** — Guia definitivo de testes
   - Como executar testes no Docker
   - Tipos de testes (unitários, integração, API, etc.)
   - Escrevendo novos testes
   - Fixtures e helpers
   - Debugging e troubleshooting

2. **[README.md](README.md)** — Organização de testes
   - Estrutura de diretórios
   - Categorias de testes
   - Markers pytest
   - Comandos básicos

### Para QA/Testing

- **Testes de Integração**: [backend/tests/test_*.py](../../backend/tests/)
- **Testes de API**: Buscar arquivos com `@pytest.mark.api`
- **Testes de Segurança**: [backend/tests/test_security_permissions.py](../../backend/tests/test_security_permissions.py)

### Para DevOps

- **Configuração Docker**: Ver seção "Ambiente de Testes" em [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **CI/CD**: Ver seção "CI/CD Pipeline" em [README.md](README.md)
- **Cobertura**: Comandos em [TESTING_GUIDE.md](TESTING_GUIDE.md#-executando-testes)

---

## 🗂️ Estrutura de Arquivos de Teste

```
backend/tests/
├── README.md                       # Este arquivo
├── conftest.py                     # Fixtures globais
│
├── inventory/                      # Testes unitários de inventory
│   ├── test_models.py
│   ├── test_serializers.py
│   └── test_viewsets.py
│
├── usecases/                       # Testes de casos de uso
│   ├── test_fiber_usecases.py
│   └── test_port_usecases.py
│
├── routes/                         # Testes de otimização de rotas
│   └── test_route_optimization.py
│
├── scripts/                        # 🆕 Scripts de debug e verificação
│   ├── README.md                   # Documentação de scripts
│   ├── check_*.py                  # Scripts de verificação
│   ├── diagnose_*.py               # Scripts de diagnóstico
│   ├── fix_*.py                    # Scripts de correção
│   └── test_*.py                   # Testes manuais
│
└── test_*.py                       # Testes de integração e features
    ├── test_cache_swr.py
    ├── test_celery_*.py
    ├── test_custom_maps_endpoints.py
    ├── test_fiber_modal_data_flow.py
    ├── test_optical_endpoint.py
    ├── test_security_permissions.py
    └── ...
```

---

## 🚀 Comandos Mais Usados

```bash
# Executar todos os testes
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/ -v

# Testes rápidos (sem slow/integration)
docker compose -f docker/docker-compose.yml exec web pytest -m "not slow and not integration"

# Teste específico
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_custom_maps_endpoints.py -v

# Com cobertura
docker compose -f docker/docker-compose.yml exec web pytest --cov --cov-report=html

# Scripts de debug
docker compose -f docker/docker-compose.yml exec web python backend/tests/scripts/check_cables.py
```

---

## 🏷️ Markers Disponíveis

| Marker | Descrição | Exemplo de Uso |
|--------|-----------|----------------|
| `slow` | Testes lentos (>5s) | `pytest -m "not slow"` |
| `integration` | Testes de integração | `pytest -m integration` |
| `api` | Testes de endpoints REST | `pytest -m api` |
| `celery` | Testes de tasks Celery | `pytest -m celery` |
| `security` | Testes de segurança | `pytest -m security` |
| `zabbix` | Testes que dependem de Zabbix | `pytest -m "not zabbix"` |

---

## 📊 Métricas de Qualidade

| Métrica | Meta | Comando |
|---------|------|---------|
| Cobertura de código | >85% | `pytest --cov --cov-report=term` |
| Testes passing | 100% | `pytest backend/tests/ -v` |
| Tempo de execução | <60s | `pytest --durations=10` |

---

## 🔍 Busca Rápida

### Por Funcionalidade

- **Fibras**: `backend/tests/test_fiber_*.py`
- **Portas**: `backend/tests/test_port*.py`
- **Custom Maps**: `backend/tests/test_custom_maps_*.py`
- **Cache**: `backend/tests/test_cache_*.py`
- **Celery**: `backend/tests/test_celery_*.py`
- **Zabbix**: `backend/tests/test_zabbix_*.py`
- **Segurança**: `backend/tests/test_security_*.py`

### Por Tipo

- **Unitários**: `backend/tests/inventory/`, `backend/tests/usecases/`
- **Integração**: `backend/tests/test_*_integration.py`
- **API/Endpoints**: `backend/tests/test_*_endpoint.py`
- **Scripts Debug**: `backend/tests/scripts/`

---

## 📞 Suporte

- **Issues**: GitHub Issues para reportar bugs em testes
- **Documentação**: Leia os comentários em arquivos de teste
- **Referências**: 
  - [Pytest Docs](https://docs.pytest.org)
  - [Django Testing](https://docs.djangoproject.com/en/5.0/topics/testing/)
  - [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)

---

## 🔗 Links Relacionados

### Documentação do Projeto

- **[doc/README.md](../README.md)** — Índice geral de documentação
- **[doc/guides/DEVELOPMENT.md](../guides/DEVELOPMENT.md)** — Guia de desenvolvimento
- **[doc/operations/DEPLOYMENT.md](../operations/DEPLOYMENT.md)** — Deploy e CI/CD

### Roadmap e Planejamento

- **[doc/roadmap/LEGACY_CODE_REMOVAL_SCHEDULE.md](../roadmap/LEGACY_CODE_REMOVAL_SCHEDULE.md)** — Cronograma de remoção de código legado
- **[doc/roadmap/SPRINT1_SUMMARY.md](../roadmap/SPRINT1_SUMMARY.md)** — Sumário Sprint 1

### Relatórios e Análises

- **[doc/reports/](../reports/)** — Relatórios de progresso e análises
- **[doc/analysis/](../analysis/)** — Análises técnicas

---

**Última Atualização**: 7 de Fevereiro de 2026  
**Versão**: 1.0.0
