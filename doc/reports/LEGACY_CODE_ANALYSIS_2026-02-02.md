# 🔍 Análise de Código Legado - MapsProveFiber

**Data**: 2026-02-02  
**Versão**: v2.0.0  
**Status**: 📋 Planejamento  
**Próxima Revisão**: 2026-02-09

---

## ⚠️ Requisito Crítico: Ambiente Docker

**TODOS OS TESTES E OPERAÇÕES DEVEM SER EXECUTADOS NO DOCKER.**

O ecossistema completo (PostgreSQL + PostGIS, Redis, Celery, GDAL, dependências Python) está configurado no Docker. Executar testes fora do Docker resultará em falhas devido a:

- ❌ **GDAL/bibliotecas geoespaciais**: Não instaladas no host
- ❌ **PostgreSQL + PostGIS**: Testes usam SQLite como fallback limitado
- ❌ **Redis e Celery**: Não disponíveis fora do Docker
- ❌ **Extensões Python**: requirements.txt completo só no container

### Como Executar Testes:

```bash
# Testes de auditoria:
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_legacy_code_audit.py -v

# Testes de segurança:
docker compose -f docker/docker-compose.yml exec web pytest backend/tests/test_security_permissions.py -v

# Audit SQL:
docker compose -f docker/docker-compose.yml cp backend/tests/audit_legacy_database.sql db:/tmp/
docker compose -f docker/docker-compose.yml exec db psql -U mapsprovefiber -d mapsprovefiber -f /tmp/audit_legacy_database.sql
```

---

## 📊 Sumário Executivo

| Categoria | Quantidade | Prioridade | Impacto |
|-----------|------------|------------|---------|
| **Arquivos .backup** | 3 arquivos | 🔴 Alta | Baixo |
| **Scripts legados** | 25 arquivos | 🟡 Média | Baixo |
| **Comentários TODO** | 50+ ocorrências | 🟢 Baixa | Médio |
| **Código deprecated** | 15+ ocorrências | 🔴 Alta | Alto |
| **Legacy endpoints** | 5+ endpoints | 🟡 Média | Alto |
| **Tabelas antigas** | 3 tabelas DB | 🔴 Alta | Alto |
| **Imports obsoletos** | 10+ ocorrências | 🟡 Média | Médio |

**Estimativa Total de Limpeza**: 3-4 sprints (6-8 semanas)

---

## 🎯 Categorias de Código Legado

### 1. 🗂️ Arquivos de Backup (.backup)

**Impacto**: Baixo | **Esforço**: Mínimo | **Prioridade**: 🔴 Alta

#### Arquivos Identificados

| Arquivo | Tamanho Aprox. | Última Modificação | Status |
|---------|----------------|-------------------|--------|
| `frontend/src/views/ConfigurationPage.vue.backup` | ~4000 linhas | Desconhecido | ❌ Obsoleto |
| `frontend/src/features/networkDesign/FiberRouteEditor.vue.backup` | ~500 linhas | Desconhecido | ❌ Obsoleto |
| `frontend/src/components/SiteDetailsModal.vue.backup` | ~800 linhas | Desconhecido | ❌ Obsoleto |

#### Ação Recomendada
- ✅ **Mover para**: `doc/archive/backup-files/`
- ✅ **Criar índice**: Documentar motivo do backup
- ✅ **Prazo**: Semana 1 (Imediato)

---

### 2. 📜 Scripts Obsoletos (scripts_old/)

**Impacto**: Baixo | **Esforço**: Mínimo | **Prioridade**: 🟡 Média

#### Diretório Completo

```
scripts/scripts_old/
├── core/
│   ├── monitor-core.sh
│   ├── monitor-utils.sh
│   └── alerts-lib/ (15 arquivos)
├── infra/
│   ├── deploy.sh (duplicado)
│   ├── apply-config.sh
│   └── backup/ (2 arquivos)
├── ops/
│   ├── roadmap.yml
│   └── bootstrap-roadmap.sh
├── setup-server.sh
└── validate-env.sh
```

**Total**: 25 arquivos

#### Análise
- ✅ **Já isolado**: Pasta `scripts_old/` já indica obsolescência
- ✅ **README.md existe**: Documentação parcial disponível
- ⚠️ **Verificar dependências**: Confirmar que nenhum script ativo os referencia

#### Ação Recomendada
- ✅ **Mover para**: `doc/archive/legacy-scripts/`
- ✅ **Documentar**: Criar README com histórico e motivo da remoção
- ✅ **Prazo**: Semana 2

---

### 3. 📌 Comentários TODO/FIXME

**Impacto**: Médio | **Esforço**: Alto | **Prioridade**: 🟢 Baixa

#### Categorização por Tipo

| Tipo | Quantidade | Ação |
|------|------------|------|
| **TODO** | 35+ | Criar issues ou implementar |
| **FIXME** | 5+ | Corrigir ou documentar decisão |
| **XXX/HACK** | 2+ | Refatorar ou justificar |

#### TODOs Críticos Identificados

##### Backend
1. **`backend/inventory/viewsets.py:1064`**
   ```python
   permission_classes = [AllowAny]  # TODO: Restrict to admin in production
   ```
   - 🔴 **Risco de Segurança**: Alta
   - 🎯 **Ação**: Implementar permissões adequadas
   - 📅 **Prazo**: Semana 1 (Crítico)

2. **`backend/inventory/services/cable_segments.py:35-36`**
   ```python
   start_infrastructure=None,  # TODO: mapear Site A
   end_infrastructure=None,    # TODO: mapear Site B
   ```
   - 🟡 **Funcionalidade Incompleta**
   - 🎯 **Ação**: Implementar mapeamento ou remover comentário
   - 📅 **Prazo**: Semana 4

##### Frontend
3. **`frontend/src/components/PortActionsModal.vue:140,157`**
   ```javascript
   // TODO: Implement reset endpoint
   // TODO: Implement logs endpoint
   ```
   - 🟡 **Features Pendentes**
   - 🎯 **Ação**: Criar issues separadas
   - 📅 **Prazo**: Backlog

4. **`frontend/src/views/video/VideoGatewaysView.vue:135,144`**
   ```javascript
   // TODO: Implementar com o código da ConfigurationPage
   // TODO: Implementar exclusão
   ```
   - 🟡 **Features Incompletas**
   - 🎯 **Ação**: Avaliar necessidade ou remover
   - 📅 **Prazo**: Semana 3

#### Ação Recomendada
- ✅ **Fase 1 (Semana 1)**: Resolver TODOs críticos de segurança
- ✅ **Fase 2 (Semanas 2-3)**: Criar issues para TODOs de features
- ✅ **Fase 3 (Semana 4)**: Remover TODOs obsoletos ou documentar decisão

---

### 4. ⚠️ Código Deprecated

**Impacto**: Alto | **Esforço**: Médio-Alto | **Prioridade**: 🔴 Alta

#### Backend - Campos JSONField Legados

##### `inventory/models.py` e `inventory/models_routes.py`

```python
# Linha 584 - models.py
coordinates = JSONField(
    null=True,
    blank=True,
    help_text="Deprecated: use path field."
)

# Linha 161 - models_routes.py
waypoints = JSONField(
    null=True,
    blank=True,
    help_text='Deprecated: use path field with PostGIS.'
)
```

**Análise**:
- ✅ **Substituto existe**: Campo `path` (LineString PostGIS)
- ⚠️ **Dados migrados**: Verificar se 100% dos dados foram migrados
- 🔴 **Remover**: Após confirmação de migração completa

**Ação**:
1. ✅ **Auditoria de dados** (Semana 1)
   ```sql
   SELECT COUNT(*) FROM inventory_fibercable 
   WHERE coordinates IS NOT NULL AND path IS NULL;
   ```
2. ✅ **Migração final** (Semana 2) - Se houver dados remanescentes
3. ✅ **Remover campos** (Semana 3) - Criar migração Django
4. ✅ **Atualizar testes** (Semana 3)

##### API Spatial Legacy

**Arquivo**: `backend/inventory/api/spatial.py:132`

```python
# Legacy JSONField (deprecated)
if cable.coordinates and not cable.path:
    # Código de fallback para JSONField antigo
```

**Ação**:
- ✅ **Remover após**: Campos deprecated serem removidos
- 📅 **Prazo**: Semana 3

#### Frontend - Rotas e Componentes Legacy

##### Router Redirects

**Arquivo**: `frontend/src/router/index.js:149-162`

```javascript
// Legacy redirects
{ path: '/map', redirect: '/Network/NetworkDesign' },

// Legacy fallback (Sprint 1 map-only view)
{ path: '/Network/NetworkDesign', ... }
```

**Análise**:
- ⚠️ **Ainda em uso**: Verificar analytics de acesso
- 🟡 **Migração gradual**: Manter por mais 1-2 meses
- 📅 **Prazo**: Semana 8 (após comunicação interna)

##### Comentários de Legacy

**Arquivo**: `frontend/src/features/networkDesign/fiberRouteBuilder.js`

```javascript
// Linha 394: Legacy functions removed - now using pathState module
// Linha 647: Make initMap available globally for Google Maps callback (legacy support)
// Linha 845: Legacy functions removed - now handled by modalEditor module
```

**Ação**:
- ✅ **Remover comentários** (Semana 1) - Código já removido
- ✅ **Limpar exports** (Semana 1) - Verificar se exports legados são usados

---

### 5. 🗄️ Tabelas e Referências de Banco de Dados

**Impacto**: ~~Alto~~ **NONE - NÃO É LEGACY** | **Esforço**: N/A | **Prioridade**: ❌ **CANCELADO**

#### ⚠️ CORREÇÃO IMPORTANTE - Tabelas `zabbix_api_*` são ATIVAS

**❌ ANÁLISE ANTERIOR INCORRETA:**
Este documento originalmente classificou as tabelas `zabbix_api_*` como legacy e propôs sua remoção. 
**Esta análise estava ERRADA**.

**✅ REALIDADE DESCOBERTA (Sprint 1, Dia 2):**

As tabelas `zabbix_api_*` **NÃO são legacy** - são as **tabelas ATIVAS** usadas pelos modelos Django atuais:

```python
# backend/inventory/models.py - CÓDIGO ATIVO DE PRODUÇÃO

class Site(models.Model):
    class Meta:
        db_table = "zabbix_api_site"  # Preserve original table name

class Device(models.Model):
    class Meta:
        db_table = "zabbix_api_device"  # Preserve original table name

class Port(models.Model):
    class Meta:
        db_table = "zabbix_api_port"  # Preserve original table name

class FiberCable(models.Model):
    class Meta:
        db_table = "zabbix_api_fibercable"  # Preserve original table name
```

**Evidências:**
- ✅ 6 tabelas `zabbix_api_*` com **1.2MB de dados ativos** em produção
- ✅ 20+ referências em código de produção ativo
- ✅ Usadas como `db_table` primária dos models Django
- ✅ Essenciais para funcionamento da aplicação

**Referências Raw SQL Encontradas (TODAS LEGÍTIMAS):**

| Arquivo | Linha | Query | Status |
|---------|-------|-------|--------|
| `inventory/usecases/spatial.py` | 61, 196 | `SELECT * FROM zabbix_api_site` | ✅ Ativo |
| `inventory/api/infrastructure.py` | 133, 200, 331, 450 | `FROM zabbix_api_fibercable` | ✅ Ativo |
| `inventory/management/commands/verify_gist_index.py` | 63 | `FROM zabbix_api_site` | ✅ Ativo |

**Conclusão:**
- ❌ **NÃO remover** estas tabelas - são infraestrutura crítica
- ❌ **NÃO migrar** dados - já são as tabelas de produção
- ℹ️ Nome `zabbix_api_*` é confuso mas não é um problema técnico
- 🔄 Renomear para `inventory_*` seria possível mas **opcional** e de baixa prioridade

#### ~~Ação Recomendada~~ → CANCELADO

**~~Fase 1-4~~**: Todas canceladas - não há tabelas legacy para remover.

**Nova Recomendação (Opcional, Sprint 4+):**
Se desejado por questões de clareza de nomenclatura:
```sql
-- Opcional: Renomear tabelas para refletir propósito atual
ALTER TABLE zabbix_api_site RENAME TO inventory_site;
ALTER TABLE zabbix_api_device RENAME TO inventory_device;
-- etc. (requer migração Django cuidadosa)
```

**Prioridade:** 🟢 Baixa - puramente cosmético, não afeta funcionalidade

---

### 6. 🔗 Legacy Tasks e Aliases do Celery

**Impacto**: Médio | **Esforço**: Médio | **Prioridade**: 🟡 Média

#### Tarefas Identificadas

**Arquivo**: `backend/inventory/routes/tasks.py:205-272`

```python
# Legacy aliases (routes_builder.*) kept for backward compatibility
@shared_task(bind=True, name="routes_builder.build_route")
def build_route_legacy(self: CeleryTask, route_id: int) -> dict[str, Any]:
    logger.debug("Legacy task routes_builder.build_route invoked")
    return build_route(route_id)
```

**Aliases Legacy**:
- `routes_builder.build_route` → `inventory.routes.build_route`
- `routes_builder.build_routes_batch` → `inventory.routes.build_routes_batch`
- `routes_builder.invalidate_route_cache` → `inventory.routes.invalidate_route_cache`
- `routes_builder.import_route_from_payload` → `inventory.routes.import_route_from_payload`
- `routes_builder.health_check` → `inventory.routes.health_check`

#### Análise
- ✅ **Funcionais**: Aliases funcionam como wrappers
- ⚠️ **Monitoramento**: Verificar se ainda são invocados
- 📊 **Métricas**: Adicionar logging para rastrear uso

#### Ação Recomendada

**Fase 1: Instrumentação (Semana 1)**
```python
@shared_task(bind=True, name="routes_builder.build_route")
def build_route_legacy(self: CeleryTask, route_id: int) -> dict[str, Any]:
    logger.warning(
        "DEPRECATED: Legacy task routes_builder.build_route invoked. "
        "Use inventory.routes.build_route instead.",
        extra={"route_id": route_id}
    )
    # Increment Prometheus counter
    legacy_task_calls_total.labels(task="build_route").inc()
    return build_route(route_id)
```

**Fase 2: Comunicação (Semana 2)**
- ✅ Notificar equipe sobre deprecation
- ✅ Atualizar documentação com novas tarefas
- ✅ Criar guia de migração

**Fase 3: Monitoramento (Semanas 3-6)**
- 📊 Monitorar métricas de uso
- ⚠️ Se uso = 0 por 4 semanas → Remover

**Fase 4: Remoção (Semana 7-8)**
- ✅ Remover aliases se uso = 0
- ✅ Atualizar testes

---

### 7. 📡 Legacy Endpoints REST API

**Impacto**: Alto | **Esforço**: Alto | **Prioridade**: 🟡 Média

#### Endpoints Identificados

**Documentado em**: `README.md:133`

```markdown
### Legacy Endpoints (⚠️ Deprecated)

The following endpoints are deprecated and will be removed in future versions:
- `/zabbix_api/*` - Migrated to `/api/v1/inventory/*`
```

#### Status Atual
- ✅ **Documentado**: Marcado como deprecated
- ⚠️ **Ainda existe?**: Verificar se código ainda está presente
- 📊 **Logs de acesso**: Analisar se recebem tráfego

#### Ação Recomendada

**Fase 1: Auditoria (Semana 1)**
```bash
# Verificar se endpoints ainda existem no código
grep -r "zabbix_api" backend/*/urls.py
grep -r "route.*zabbix_api" backend/
```

**Fase 2: Adicionar Warnings (Semana 2)**
```python
# Se endpoints ainda existem, adicionar deprecation warning
class LegacyZabbixAPIView(APIView):
    def dispatch(self, request, *args, **kwargs):
        logger.warning(
            "DEPRECATED: /zabbix_api/* endpoint accessed. "
            "Migrate to /api/v1/inventory/*",
            extra={"path": request.path, "user": request.user}
        )
        # Retornar 410 Gone após período de grace
        return Response(
            {"detail": "This endpoint is deprecated. Use /api/v1/inventory/*"},
            status=410
        )
```

**Fase 3: Remoção (Semana 8)**
- ✅ Remover completamente após período de grace
- ✅ Atualizar changelog

---

## 📅 Cronograma de Execução

### **Sprint 1: Semanas 1-2 (Preparação e Segurança)**

#### Semana 1 (03-09 Fev 2026)
**Foco**: Auditoria e itens críticos de segurança

- [x] **Dia 1-2**: Auditoria completa de dados ✅ **COMPLETO**
  - [x] Verificar migração de campos deprecated (coordinates → path)
  - [x] ~~Verificar tabelas `zabbix_api_*`~~ → **Descoberta: são tabelas ATIVAS, não legacy**
  - [x] Criar testes de auditoria (test_legacy_code_audit.py, 317 linhas)
  - [x] Criar audit SQL (audit_legacy_database.sql, 230 linhas)
  
- [x] **Dia 2**: Correções de Segurança ✅ **COMPLETO**
  - [x] Implementar permissões em `inventory/viewsets.py` (10 endpoints)
  - [x] AllowAny → IsAuthenticated (CRÍTICO)
  - [x] Criar testes de baseline (test_security_permissions.py, 303 linhas)
  
- [x] **Dia 3**: Limpeza Rápida ✅ **COMPLETO**
  - [x] Mover 3 arquivos `.backup` para `doc/archive/backup-files/`
  - [x] Mover 25 arquivos `scripts_old/` para `doc/archive/scripts-deprecated/`
  - [x] Criar READMEs com políticas de retenção (60 dias)
  - [x] Documentar requisito Docker em todos os testes

**Entregáveis**:
- ✅ Relatório de auditoria de dados (DATABASE_AUDIT_2026-02-03.md)
- ✅ Correções de segurança aplicadas (10 endpoints protegidos)
- ✅ Arquivos backup e scripts arquivados (28 arquivos)
- ✅ Relatório de progresso (SPRINT_1_WEEK_1_PROGRESS.md)

**Status**: ✅ **COMPLETO em 3 dias** (2 dias de antecedência)

#### Semana 2 (10-16 Fev 2026)
**Foco**: ~~Scripts e queries SQL~~ → **Métricas e deprecation warnings**

- [ ] **Dia 1**: Atualizar documentação
  - [x] ~~Substituir queries `zabbix_api_*`~~ → **CANCELADO** (são tabelas ativas)
  - [ ] Corrigir documentos que classificavam `zabbix_api_*` como legacy
  - [ ] Atualizar LEGACY_CODE_REMOVAL_SCHEDULE.md com progresso
  
- [ ] **Dia 2-3**: Instrumentação Prometheus
  - [ ] Adicionar counters em ViewSets principais
  - [ ] Adicionar histograms em tasks Celery
  - [ ] Preparar dados para decisões Sprint 4
  
- [ ] **Dia 4**: Deprecation Warnings
  - [ ] Identificar código legacy-style (não tabelas)
  - [ ] Adicionar warnings apropriados
  - [ ] Documentar para Sprint 2
  
- [ ] **Dia 5**: Review e Planejamento
  
- [ ] **Dia 4-5**: Endpoints Deprecated
  - [ ] Adicionar warnings em endpoints legacy (se existirem)
  - [ ] Configurar monitoramento de uso
  - [ ] Documentar plano de migração para clientes

**Entregáveis**:
- ✅ Queries SQL atualizadas
- ✅ Scripts arquivados com documentação
- ✅ Endpoints com deprecation warnings

---

### **Sprint 2: Semanas 3-4 (Remoção de Campos e Tabelas)**

#### Semana 3 (17-23 Fev 2026)
**Foco**: Remoção de campos deprecated

- [ ] **Dia 1**: Migração Final de Dados
  - [ ] Script para migrar dados remanescentes
  - [ ] Validação de integridade de dados
  
- [ ] **Dia 2-3**: Criar Migração Django
  - [ ] Remover campos `coordinates` e `waypoints`
  - [ ] Atualizar serializers e APIs
  - [ ] Testar em ambiente de staging
  
- [ ] **Dia 4-5**: Cleanup e Testes
  - [ ] Remover código de fallback em `api/spatial.py`
  - [ ] Atualizar testes unitários
  - [ ] Executar suite completa de testes

**Entregáveis**:
- ✅ Campos deprecated removidos
- ✅ Testes atualizados e passando
- ✅ Documentação de migração

#### Semana 4 (24 Fev - 02 Mar 2026)
**Foco**: Remoção de tabelas antigas

- [ ] **Dia 1-2**: Preparação
  - [ ] Backup completo do banco de dados
  - [ ] Verificação final de dependências
  
- [ ] **Dia 3**: Remoção de Tabelas
  - [ ] Executar DROP TABLE para tabelas `zabbix_api_*`
  - [ ] Verificar CASCADE e impactos
  - [ ] Monitorar logs de erro
  
- [ ] **Dia 4-5**: Validação
  - [ ] Testes de integração completos
  - [ ] Verificar funcionalidade de features dependentes
  - [ ] Documentar mudanças no CHANGELOG

**Entregáveis**:
- ✅ Tabelas antigas removidas
- ✅ Sistema funcionando sem tabelas legacy
- ✅ Changelog atualizado

---

### **Sprint 3: Semanas 5-6 (TODOs e Refatoração)**

#### Semana 5 (03-09 Mar 2026)
**Foco**: Resolver TODOs críticos

- [ ] **Dia 1-2**: Features Pendentes Backend
  - [ ] Implementar mapeamento Site A/B em cable_segments
  - [ ] Outros TODOs críticos de funcionalidade
  
- [ ] **Dia 3-4**: Features Pendentes Frontend
  - [ ] Avaliar TODOs de VideoGatewaysView
  - [ ] Implementar ou remover features pendentes
  
- [ ] **Dia 5**: Criação de Issues
  - [ ] Criar issues no GitHub para TODOs não críticos
  - [ ] Priorizar backlog

**Entregáveis**:
- ✅ TODOs críticos resolvidos
- ✅ Issues criadas para backlog
- ✅ Código limpo de TODOs obsoletos

#### Semana 6 (10-16 Mar 2026)
**Foco**: Monitoramento e ajustes

- [ ] **Dia 1-3**: Análise de Métricas
  - [ ] Revisar uso de tasks legacy (Celery)
  - [ ] Revisar acesso a endpoints deprecated
  
- [ ] **Dia 4-5**: Ajustes Finais
  - [ ] Remover código não utilizado baseado em métricas
  - [ ] Atualizar documentação
  - [ ] Code review geral

**Entregáveis**:
- ✅ Relatório de uso de código legacy
- ✅ Decisões de remoção baseadas em dados
- ✅ Documentação atualizada

---

### **Sprint 4: Semanas 7-8 (Finalização e Remoção)**

#### Semana 7 (17-23 Mar 2026)
**Foco**: Remoção final de código legacy

- [ ] **Dia 1-2**: Celery Tasks
  - [ ] Remover aliases `routes_builder.*` se uso = 0
  - [ ] Atualizar configuração do Celery
  
- [ ] **Dia 3-4**: Router Redirects
  - [ ] Comunicar mudança de rotas
  - [ ] Atualizar links em documentação externa
  
- [ ] **Dia 5**: Preparação para Remoção de Endpoints
  - [ ] Comunicação final sobre endpoints deprecated
  - [ ] Preparar changelog

**Entregáveis**:
- ✅ Tasks legacy removidas
- ✅ Comunicação enviada
- ✅ Sistema preparado para limpeza final

#### Semana 8 (24-30 Mar 2026)
**Foco**: Limpeza final e documentação

- [ ] **Dia 1-2**: Remoção de Endpoints
  - [ ] Remover endpoints `/zabbix_api/*` completamente
  - [ ] Verificar quebras
  
- [ ] **Dia 3-4**: Documentação Final
  - [ ] Atualizar README.md
  - [ ] Criar guia de migração para v3.0.0
  - [ ] Atualizar CHANGELOG.md
  
- [ ] **Dia 5**: Release
  - [ ] Tag de versão
  - [ ] Anúncio de release
  - [ ] Retrospectiva do processo

**Entregáveis**:
- ✅ Sistema 100% limpo de código legacy crítico
- ✅ Documentação completa
- ✅ Release notes publicadas

---

## 📈 Métricas de Sucesso

### KPIs do Projeto

| Métrica | Baseline | Meta | Prazo |
|---------|----------|------|-------|
| **Arquivos .backup** | 3 | 0 | Semana 1 |
| **Scripts obsoletos** | 25 | 0 | Semana 2 |
| **TODOs críticos** | 10+ | 0 | Semana 5 |
| **Campos deprecated** | 2 | 0 | Semana 3 |
| **Tabelas legacy** | 3+ | 0 | Semana 4 |
| **Tasks legacy** | 5 | 0 | Semana 7 |
| **Endpoints deprecated** | 5+ | 0 | Semana 8 |
| **Linhas de código removidas** | - | 2000+ | Semana 8 |
| **Cobertura de testes** | - | Manter ≥85% | Contínuo |

### Monitoramento Contínuo

**Comandos úteis**:

```bash
# Contar TODOs restantes
grep -r "TODO:" backend/ frontend/ --exclude-dir=node_modules --exclude-dir=dist | wc -l

# Verificar referências a código deprecated
grep -r "deprecated\|DEPRECATED\|@deprecated" backend/ frontend/ --exclude-dir=node_modules

# Buscar tabelas zabbix_api no código
grep -r "zabbix_api_" backend/ --include="*.py"

# Listar arquivos .backup
find . -name "*.backup" -o -name "*.bak" -o -name "*_old.*"
```

---

## 🚨 Riscos e Mitigações

### Riscos Identificados

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Perda de dados durante migração** | Baixa | 🔴 Crítico | Backups automáticos antes de cada migração |
| **Quebra de funcionalidades** | Média | 🔴 Alto | Suite de testes abrangente + staging environment |
| **Endpoints ainda em uso por clientes** | Média | 🟡 Médio | Monitoramento de logs + período de grace de 8 semanas |
| **Tasks Celery legacy ainda agendadas** | Baixa | 🟡 Médio | Instrumentação com métricas + análise de uso |
| **Queries SQL com performance ruim após mudança** | Baixa | 🟡 Médio | Benchmarks antes/depois + índices adequados |

### Plano de Rollback

**Para cada fase crítica**:

1. **Backup Completo**
   ```bash
   # Antes de cada mudança de schema
   python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json
   pg_dump provemaps > db_backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Migração Reversível**
   ```python
   # Todas as migrações Django devem ter método reverse()
   def reverse(apps, schema_editor):
       # Código para desfazer migração
   ```

3. **Feature Flags**
   ```python
   # Para mudanças arriscadas
   if settings.ENABLE_NEW_API:
       use_new_endpoint()
   else:
       use_legacy_endpoint()  # Fallback temporário
   ```

---

## 📋 Checklist de Validação

### Antes de Cada Remoção

- [ ] Verificar que o código não é referenciado em nenhum lugar
- [ ] Executar suite completa de testes
- [ ] Revisar logs de produção para uso recente
- [ ] Criar backup de dados relevantes
- [ ] Documentar mudança no CHANGELOG
- [ ] Comunicar equipe sobre mudança

### Após Cada Remoção

- [ ] Testes passando (≥85% cobertura mantida)
- [ ] Sem erros em logs de desenvolvimento
- [ ] Documentação atualizada
- [ ] Code review aprovado
- [ ] Deploy em staging testado
- [ ] Métricas de performance estáveis

---

## 🎓 Lições Aprendidas e Boas Práticas

### Para Evitar Acúmulo Futuro de Legacy Code

1. **Deprecation Policy**
   ```python
   # Sempre marcar código deprecated com warning
   import warnings
   
   @deprecated(version="3.0.0", reason="Use new_function() instead")
   def old_function():
       warnings.warn("old_function is deprecated", DeprecationWarning)
   ```

2. **TODO Policy**
   - Criar issue no GitHub para cada TODO adicionado
   - Limitar lifetime de TODOs (máx. 2 sprints)
   - Revisar TODOs em code reviews

3. **Database Migration Policy**
   - Nunca fazer migração destrutiva imediatamente
   - Período de transição: 2-3 releases
   - Sempre incluir dados sample em rollback

4. **API Versioning**
   ```
   /api/v1/  -> Estável
   /api/v2/  -> Nova versão
   /api/v1/  -> Deprecated após 6 meses
   /api/v1/  -> Removido após 12 meses
   ```

---

## 📚 Referências

- [Architecture Overview](../architecture/README.md)
- [Breaking Changes Guide](../releases/v2.0.0/BREAKING_CHANGES_v2.0.0.md)
- [Testing Guide](../guides/TESTING.md)
- [Database Migration Guide](../operations/MIGRATION.md)

---

**Próxima Revisão**: 2026-02-09 (Final da Semana 1)  
**Responsável**: Equipe de Desenvolvimento  
**Status**: 📋 Aguardando aprovação para início

