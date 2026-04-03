# Changelog - Modularização MapsProveFiber

## v2.0.0-alpha.1 (2025-01-07) - Phase 4 Cleanup Complete ✅

### 🎯 Objetivo
Remover código legado após consolidação da modularização em `inventory`, `monitoring` e `integrations/zabbix`.

### ✨ Breaking Changes
- **REMOVIDO**: Aplicação `zabbix_api/` completamente deletada
  - Todas as funcionalidades migradas para `inventory/` e `integrations/zabbix/`
  - Endpoints legados `/zabbix/api/*` não existem mais
  - Código legado que importava de `zabbix_api.*` irá falhar

### 📦 Migrações Incluídas
- `inventory.0003_route_models_relocation` - Move modelos Route para inventory
  - **Operação**: Apenas metadados (SeparateDatabaseAndState)
  - **Impacto**: Zero downtime, nenhum dado alterado
  - **Validação**: 14/14 testes de validação passando

### 🔧 Alterações Técnicas

#### Remoções
1. **Diretório `zabbix_api/`** completo (shims, models, views, URLs, tests)
2. **Rotas duplicadas** em `core/urls.py`:
   - ❌ `path('zabbix/api/', include('zabbix_api.urls'))`
3. **Testes de compatibilidade legados**:
   - ❌ `test_zabbix_api_models_reexport_inventory` 
   - ❌ Importações de `zabbix_api.inventory_cache` em testes

#### Atualizações de Configuração
1. **pytest.ini**:
   ```ini
   # ANTES: testpaths = ... zabbix_api/tests
   # DEPOIS: testpaths = ... inventory/tests monitoring/tests
   ```

2. **pyrightconfig.json**:
   ```json
   // ADICIONADO:
   "include": [
     "inventory/api", "inventory/usecases", "inventory/services",
     "monitoring/tests", "integrations/zabbix"
   ],
   // REMOVIDO: "zabbix_api/*"
   ```

3. **CI Workflows** (`.github/workflows/daily-inventory-tests.yml`):
   ```bash
   # ANTES: pytest inventory/tests/test_fibers_api.py zabbix_api/tests.py -q
   # DEPOIS: pytest inventory/tests/ tests/usecases/ tests/test_inventory_endpoints.py -q
   ```

#### Manutenção de Dependências
- **MANTIDO**: `routes_builder` em `INSTALLED_APPS`
  - **Razão**: Migração `inventory.0003` depende de `routes_builder.0001`
  - **Próximo passo**: Remover dependência após aplicação em produção

### 🧪 Validação
- **Testes**: 199/199 passando (tempo: 116.37s)
  - Redução intencional de 200→199 (teste legado removido)
- **System Check**: `python manage.py check` → 0 issues
- **Migrações**: Validação em SQLite → 14/14 checks ✅
- **CI**: Daily inventory tests configurados para nova estrutura

### 📊 Estatísticas
| Métrica | Antes | Depois | Mudança |
|---------|-------|--------|---------|
| Apps Instalados | 13 | 12 | -1 (zabbix_api removido) |
| Testes | 200 | 199 | -1 (compatibilidade removida) |
| Tempo de Testes | ~120s | 116.37s | ↓ 3% |
| Warnings do Django | 1 (urls.W005) | 0 | ✅ Limpo |

### 🚀 Próximos Passos (Fase 5 - Documentação Final)
1. ⏳ Atualizar `README.md` (remover menção a zabbix_api)
2. ⏳ Atualizar `doc/reference-root/API_DOCUMENTATION.md` (marcar endpoints legados)
3. ⏳ Smoke test manual (dashboard, routes, dispositivos)
4. ⏳ Validação de health checks (`/healthz`, `/ready`, `/live`, `/metrics/`)

### 📚 Guias de Migração
- [MIGRATION_PRODUCTION_GUIDE.md](../operations/MIGRATION_PRODUCTION_GUIDE.md) - Procedimento de implantação
- [REFATORAR.md](../developer/REFATORAR.md) - Status completo da refatoração

### ⚠️ Notas de Compatibilidade
- **Frontend**: 100% migrado para `/api/v1/inventory/*` (9 arquivos JS validados)
- **Backend**: Todos os imports agora devem usar:
  ```python
  # ✅ CORRETO
  from inventory.models import Site, Device, Port, Route
  from inventory.cache.fibers import FibersCache
  from integrations.zabbix.zabbix_service import zabbix_request
  
  # ❌ INCORRETO (módulo não existe mais)
  from zabbix_api.models import Site
  from zabbix_api.inventory_cache import FibersCache
  ```

### 🎨 Estrutura Modular Final
```
provemaps_beta/
├── inventory/         # Authoritative data (Site, Device, Port, Route)
│   ├── api/          # REST endpoints /api/v1/inventory/
│   ├── cache/        # FibersCache, device_status.py
│   ├── services/     # SiteService, DeviceService, RouteService
│   └── usecases/     # get_dashboard_data, create_route_from_kml
├── monitoring/        # Health + metrics consolidados
│   ├── usecases.py   # combine_inventory_with_zabbix_status
│   └── tasks.py      # Celery tasks de monitoramento
├── integrations/
│   └── zabbix/       # Cliente isolado (retry, circuit breaker)
│       ├── client.py
│       └── zabbix_service.py
├── routes_builder/    # LEGADO - remover após migração aplicada
└── core/             # Django settings, ASGI, Celery, Prometheus
```

---

**Revisão Técnica**: Don Jonhn  
**Data**: 2025-01-07  
**Versão do Django**: 5.x  
**Python**: 3.13.9
