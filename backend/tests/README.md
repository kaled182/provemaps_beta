# 🧪 Testes - MapsProveFiber

**Última Atualização**: 7 de Fevereiro de 2026

## 📚 Documentação Completa

Para documentação detalhada sobre testes, consulte:

- **[doc/testing/INDEX.md](../../doc/testing/INDEX.md)** — Índice completo de documentação
- **[doc/testing/README.md](../../doc/testing/README.md)** — Visão geral e estrutura
- **[doc/testing/TESTING_GUIDE.md](../../doc/testing/TESTING_GUIDE.md)** — Guia completo de testes

---

## ⚠️ IMPORTANTE: Execução Exclusiva no Docker

**TODO O ECOSSISTEMA DO PROJETO FUNCIONA SOB DOCKER.**

Não tente executar testes diretamente no host (Windows/Linux/Mac). Todos os testes devem ser executados dentro dos containers Docker para garantir:

- ✅ PostgreSQL + PostGIS configurados corretamente
- ✅ GDAL e bibliotecas geoespaciais (gdal310+)
- ✅ Dependências Python completas do `requirements.txt`
- ✅ Redis e Celery disponíveis
- ✅ Ambiente idêntico à produção

---

## 📁 Estrutura de Testes (Organizada em 7 Fev 2026)

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
    ├── test_backup_config.py
    ├── test_cable_serializer.py
    ├── test_cache_swr.py
    ├── test_celery_*.py
    ├── test_custom_maps_endpoints.py
    ├── test_fiber_modal_data_flow.py
    ├── test_optical_endpoint.py
    ├── test_security_permissions.py
    ├── test_session_persistence.py
    └── ...
```

---

## 🚀 Comandos Mais Usados

### Testes Python (pytest)

```bash
# Executar TODOS os testes:
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/ -v

# Testes rápidos (sem slow/integration):
docker compose -f docker/docker-compose.yml exec web pytest -m "not slow and not integration"

# Teste específico:
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_custom_maps_endpoints.py -v

# Testes de segurança:
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_security_permissions.py -v

# Testes de um app específico:
docker compose -f docker/docker-compose.yml exec web pytest backend/inventory/tests/ -v

# Com cobertura:
docker compose -f docker/docker-compose.yml exec web pytest --cov --cov-report=html
```

### Scripts de Debug

```bash
# Script de verificação de cabos:
docker compose -f docker/docker-compose.yml exec web python backend/tests/scripts/check_cables.py

# Diagnóstico de Zabbix:
docker compose -f docker/docker-compose.yml exec web python backend/tests/scripts/diagnose_zabbix.py

# Ver todos os scripts disponíveis:
docker compose -f docker/docker-compose.yml exec web ls -la backend/tests/scripts/
```

### Audit SQL (PostgreSQL)

```bash
# Copiar script para o container DB:
docker compose -f docker/docker-compose.yml cp backend/tests/audit_legacy_database.sql db:/tmp/

# Executar audit no PostgreSQL:
docker compose -f docker/docker-compose.yml exec db psql -U mapsprovefiber -d mapsprovefiber -f /tmp/audit_legacy_database.sql

# Ou conectar diretamente ao psql:
docker compose -f docker/docker-compose.yml exec db psql -U mapsprovefiber -d mapsprovefiber
```

### 3️⃣ Shell Django (para testes manuais)

```bash
# Abrir shell Django:
docker compose -f docker/docker-compose.yml exec web python backend/manage.py shell

# Exemplo de teste manual no shell:
>>> from inventory.models import Site, FiberCable
>>> Site.objects.count()
>>> FiberCable.objects.filter(status='ACTIVE').count()
```

---

## 🔍 Suítes de Testes Disponíveis

### Sprint 1 - Auditoria de Código Legado

#### `test_legacy_code_audit.py`
Valida estado atual ANTES de remover código legado:
- **LegacyDatabaseAuditTest**: Tabelas legacy (zabbix_api_*)
- **LegacyFieldMigrationAuditTest**: Migração coordinates → path
- **LegacyCodeUsageAuditTest**: Uso de código deprecated
- **LegacyFileAuditTest**: Arquivos .backup e scripts_old/
- **LegacyDataIntegrityTest**: Integridade de dados migrados
- **LegacyTODOAuditTest**: TODOs e FIXMEs críticos
- **LegacyPerformanceBaselineTest**: Baseline de performance

#### `test_security_permissions.py`
Testa segurança de API (baseline + regression):
- **APIPermissionsSecurityTest**: Estado vulnerável atual (AllowAny)
- **SpecificViewSetPermissionTest**: Auditoria endpoint-a-endpoint
- **PostFixRegressionTest**: Regressão após correção de segurança

#### `audit_legacy_database.sql`
Script SQL para auditoria de banco de dados:
- Verificação de tabelas legacy
- Contagem de dados migrados
- Análise de campos deprecated (coordinates vs path)
- Verificação de índices PostGIS
- Estatísticas de armazenamento

---

## 📁 Estrutura de Testes

```
backend/tests/
├── README.md                          # Este arquivo
├── test_legacy_code_audit.py          # Auditoria de código legado
├── test_security_permissions.py       # Testes de segurança API
├── audit_legacy_database.sql          # Audit SQL para PostgreSQL
└── conftest.py                        # Fixtures compartilhadas

backend/inventory/tests/
├── test_models.py                     # Testes de modelos
├── test_usecases.py                   # Testes de casos de uso
├── test_api.py                        # Testes de API
└── ...

backend/maps_view/tests/
backend/monitoring/tests/
backend/service_accounts/tests/
```

---

## ❌ Por Que NÃO Executar Fora do Docker?

### Problema 1: GDAL Não Disponível
```
django.core.exceptions.ImproperlyConfigured: Could not find the GDAL library 
(tried "gdal310", "gdal309", ...). Is GDAL installed?
```
**Solução**: Executar no Docker (GDAL já instalado no container)

### Problema 2: PostgreSQL vs SQLite
- Testes fora do Docker usam SQLite (fallback do settings.test)
- Comportamento diferente: triggers, índices, PostGIS não disponíveis
- **Solução**: Executar no Docker (PostgreSQL + PostGIS configurados)

### Problema 3: Redis/Celery Indisponíveis
- Cache e tarefas assíncronas não funcionam
- Testes que dependem de Celery falham
- **Solução**: Executar no Docker (Redis + Celery rodando)

### Problema 4: Dependências Python Incompletas
- `requirements.txt` completo só no container
- Instalação manual no host é trabalhosa e sujeita a erros
- **Solução**: Executar no Docker (imagem com tudo instalado)

---

## 🎯 Boas Práticas

### 1. Sempre Execute no Docker
```bash
# ✅ CORRETO:
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_legacy_code_audit.py -v

# ❌ INCORRETO (vai falhar):
pytest backend/tests/test_legacy_code_audit.py -v
```

### 2. Use Markers para Organizar Testes
```python
@pytest.mark.slow          # Testes lentos
@pytest.mark.integration   # Testes de integração
@pytest.mark.unit          # Testes unitários
@pytest.mark.api           # Testes de API
@pytest.mark.security      # Testes de segurança
```

Executar por marker:
```bash
docker compose -f docker/docker-compose.yml exec web pytest -v -m "not slow"
```

### 3. Coverage é Importante
Sempre verifique coverage antes de remover código:
```bash
docker compose -f docker/docker-compose.yml exec web pytest --cov=backend/inventory --cov-report=term-missing
```

### 4. Isole Testes de Integração
Use `@pytest.mark.integration` para testes que dependem de serviços externos (Zabbix, SMTP, etc.)

---

## 📚 Recursos

- **Pytest Docs**: https://docs.pytest.org/
- **Django Testing**: https://docs.djangoproject.com/en/5.0/topics/testing/
- **DRF Testing**: https://www.django-rest-framework.org/api-guide/testing/
- **Cronograma de Remoção**: [../doc/roadmap/LEGACY_CODE_REMOVAL_SCHEDULE.md](../doc/roadmap/LEGACY_CODE_REMOVAL_SCHEDULE.md)
- **Análise Completa**: [../doc/reports/LEGACY_CODE_ANALYSIS_2026-02-02.md](../doc/reports/LEGACY_CODE_ANALYSIS_2026-02-02.md)

---

## 🆘 Troubleshooting

### Container não está rodando?
```bash
# Subir containers:
docker compose -f docker/docker-compose.yml up -d

# Verificar status:
docker compose -f docker/docker-compose.yml ps
```

### Banco de dados não existe?
```bash
# Executar migrações:
docker compose -f docker/docker-compose.yml exec web python backend/manage.py migrate

# Criar superuser:
docker compose -f docker/docker-compose.yml exec web python backend/manage.py createsuperuser
```

### Testes falhando após mudanças no código?
```bash
# Rebuild do container:
docker compose -f docker/docker-compose.yml build web
docker compose -f docker/docker-compose.yml restart web

# Reinstalar dependências:
docker compose -f docker/docker-compose.yml exec web pip install -r backend/requirements.txt
```

---

**Última Atualização**: 2026-02-03  
**Responsável**: Equipe de Desenvolvimento  
**Sprint Atual**: Sprint 1, Semana 1 - Auditoria e Testes
