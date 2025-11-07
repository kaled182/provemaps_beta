# 📚 Plano de Reorganização da Documentação v2.0.0

## 🎯 Objetivo
Transformar a pasta `doc/` em uma wiki limpa, coesa e fácil de navegar, removendo documentação obsoleta e consolidando guias duplicados.

---

## 🗂️ Estrutura Proposta (v2.0.0)

```
doc/
├── README.md                           # 📖 Índice mestre (navegação principal)
│
├── getting-started/                    # 🚀 Primeiros passos
│   ├── README.md                       # Índice de quickstart
│   ├── QUICKSTART.md                   # Guia consolidado (local + Docker)
│   └── TROUBLESHOOTING.md              # Problemas comuns
│
├── guides/                             # 📘 Guias de desenvolvimento
│   ├── README.md                       # Índice de guias
│   ├── DEVELOPMENT.md                  # Setup local, comandos diários
│   ├── DOCKER.md                       # Docker Compose, containers
│   ├── TESTING.md                      # Testes, coverage, CI/CD
│   └── OBSERVABILITY.md                # Metrics, health checks, logging
│
├── architecture/                       # 🏗️ Arquitetura e design
│   ├── README.md                       # Visão geral da arquitetura
│   ├── OVERVIEW.md                     # Arquitetura v2.0.0
│   ├── MODULES.md                      # Descrição de cada app Django
│   ├── DATA_FLOW.md                    # Fluxos de dados (diagramas)
│   └── ADR/                            # Architecture Decision Records
│       ├── 001-modular-architecture.md
│       ├── 002-zabbix-isolation.md
│       └── 003-inventory-as-source-of-truth.md
│
├── api/                                # 🔌 Documentação de APIs
│   ├── README.md                       # Visão geral das APIs
│   ├── ENDPOINTS.md                    # Lista completa de endpoints
│   ├── AUTHENTICATION.md               # Auth, permissions, RBAC
│   └── EXAMPLES.md                     # Exemplos de uso (cURL, Python)
│
├── operations/                         # ⚙️ Operações e deployment
│   ├── README.md                       # Índice de operações
│   ├── DEPLOYMENT.md                   # Guia de deployment
│   ├── MIGRATION.md                    # Database migrations
│   ├── MONITORING.md                   # Prometheus, Grafana, alerts
│   └── TROUBLESHOOTING.md              # Diagnóstico e resolução
│
├── releases/                           # 📦 Changelogs e breaking changes
│   ├── README.md                       # Índice de releases
│   ├── CHANGELOG.md                    # Changelog consolidado
│   ├── BREAKING_CHANGES.md             # Breaking changes (todas versões)
│   └── v2.0.0/                         # Documentos específicos v2.0.0
│       ├── COMPLETION_REPORT.md
│       └── MIGRATION_GUIDE.md
│
└── contributing/                       # 🤝 Contribuição e processos
    ├── README.md                       # Como contribuir
    ├── CODE_STYLE.md                   # Padrões de código
    ├── PR_GUIDELINES.md                # Pull request guidelines
    └── TESTING_STANDARDS.md            # Standards de testes
```

---

## 🗑️ Arquivos a Deletar (Obsoletos)

### `doc/reference/` - Histórico e Reports Antigos

**Deletar**:
- ❌ `performance_phase1.md` até `performance_phase6.md` (histórico, não relevante)
- ❌ `FASE4_SUCCESS_REPORT.md`, `FASE4_TEST_REPORT.md` (substituído por `PHASE4_COMPLETION_REPORT.md`)
- ❌ `FINAL_CONSOLIDATED_REPORT.md` (histórico, pré-v2.0.0)
- ❌ `PROJECT_STATUS_REPORT.md` (substituído por `PHASE5_COMPLETION_REPORT.md`)
- ❌ `DATABASE_TEST_ERRORS_ANALYSIS.md` (debugging temporário)
- ❌ `TEST_ERRORS_DETAILED_REPORT.md` (debugging temporário)
- ❌ `FRONTEND_MODULARIZATION_PHASE2.md` (concluído, integrado em ARCHITECTURE)
- ❌ `OBSERVABILITY_PHASE3.md` (concluído, integrado em OBSERVABILITY.md)
- ❌ `MARIADB_IMPLEMENTATION_COMPLETE.md` (histórico)
- ❌ `MARIADB_SUCCESS_REPORT.md` (histórico)
- ❌ `FIBER_ROUTE_BUILDER_BUG_FIX.md` (bug fix específico, não relevante)
- ❌ `ANALISE_EDICAO_CABOS.md` (análise temporária)
- ❌ `CONFIGURACAO_PERSISTENTE.md` (obsoleto)
- ❌ `refactor_fibers.md` (concluído na refatoração)
- ❌ `inventory_migration_guide.md` (substituído por `BREAKING_CHANGES_v2.0.0.md`)
- ❌ `modules/` (documentação legada de JS modules)
- ❌ `maps_view/` (documentação legada específica de app)

**Manter**:
- ✅ `ARCHITECTURE_v2.0.0.md` → mover para `architecture/OVERVIEW.md`
- ✅ `REDIS_HIGH_AVAILABILITY.md` → mover para `operations/REDIS.md`
- ✅ `REDIS_GRACEFUL_DEGRADATION.md` → mover para `architecture/MODULES.md` (seção cache)
- ✅ `TESTING_QUICK_REFERENCE.md` → mover para `guides/TESTING.md`
- ✅ `operations_checklist.md` → consolidar em `operations/DEPLOYMENT.md`
- ✅ `prometheus_static_version.md` → mover para `operations/MONITORING.md`
- ✅ `PROMETHEUS_ALERTS.md` → mover para `operations/MONITORING.md`
- ✅ `CELERY_MONITORING_CHECKLIST.md` → mover para `operations/MONITORING.md`
- ✅ `cache_busting.md` → mover para `guides/DEVELOPMENT.md` (frontend section)
- ✅ `i18n_and_pr_guidelines.md` → mover para `contributing/PR_GUIDELINES.md`
- ✅ `adr_fiber_route_builder.md` → mover para `architecture/ADR/001-fiber-route-builder.md`
- ✅ `TECHNICAL_REVIEW.md` → mover para `architecture/ADR/000-technical-review.md`

### `doc/releases/` - Changelogs Antigos

**Deletar**:
- ❌ `CHANGELOG_20251025_REDIS.md` (integrar em CHANGELOG consolidado)
- ❌ `CHANGELOG_20251105_ZABBIX_SHIMS.md` (integrar em CHANGELOG consolidado)

**Manter**:
- ✅ `CHANGELOG_MODULARIZATION.md` → renomear para `v2.0.0/CHANGELOG.md`
- ✅ `PHASE4_COMPLETION_REPORT.md` → mover para `v2.0.0/PHASE4_REPORT.md`
- ✅ `PHASE5_COMPLETION_REPORT.md` → renomear para `v2.0.0/COMPLETION_REPORT.md`
- ✅ `BREAKING_CHANGES_v2.0.0.md` → mover para `v2.0.0/BREAKING_CHANGES.md`

### `doc/developer/` - Guias Duplicados

**Consolidar**:
- 🔀 `QUICKSTART_LOCAL.md` + `DOCKER_SETUP.md` → `getting-started/QUICKSTART.md`
- 🔀 `COMANDOS_RAPIDOS.md` → integrar em `guides/DEVELOPMENT.md`
- 🔀 `OBSERVABILITY.md` → mover para `guides/OBSERVABILITY.md`
- ❌ `refactor-log.md` (histórico, deletar)

**Manter**:
- ✅ `REFATORAR.md` → mover para `architecture/ADR/004-refactoring-plan.md` (histórico)

### `doc/operations/` - Duplicações

**Consolidar**:
- 🔀 `COMANDOS_RAPIDOS.md` (duplicado de developer/) → deletar
- 🔀 `DEPLOYMENT.md` + `DEPLOYMENT_CHECKLIST_v2.0.0.md` → consolidar em `DEPLOYMENT.md`
- 🔀 `STATUS_SERVICOS.md` → integrar em `TROUBLESHOOTING.md`

**Manter**:
- ✅ `MIGRATION_PRODUCTION_GUIDE.md` → renomear para `MIGRATION.md`

### `doc/reference-root/`

**Manter**:
- ✅ `API_DOCUMENTATION.md` → mover para `api/ENDPOINTS.md`

### `doc/getting-started/`

**Consolidar**:
- 🔀 `QUICKSTART_LOCAL.md` + `TUTORIAL_DOCKER.md` → `QUICKSTART.md` único

### Raiz `doc/`

**Deletar**:
- ❌ `temporary_zabbix_optical_plan.md` (temporário, concluído)

---

## 📋 Ações de Migração

### Fase 1: Criar Nova Estrutura
1. ✅ Criar pastas: `guides/`, `architecture/`, `api/`, `contributing/`
2. ✅ Criar subpastas: `architecture/ADR/`, `releases/v2.0.0/`

### Fase 2: Mover Documentos Relevantes
1. ✅ Mover arquivos de `reference/` para nova estrutura
2. ✅ Mover arquivos de `developer/` para `guides/`
3. ✅ Reorganizar `releases/` com versionamento
4. ✅ Mover `API_DOCUMENTATION.md` para `api/`

### Fase 3: Consolidar Guias Duplicados
1. ✅ Criar `getting-started/QUICKSTART.md` (unificado)
2. ✅ Criar `guides/DEVELOPMENT.md` (consolidado)
3. ✅ Criar `operations/DEPLOYMENT.md` (consolidado)
4. ✅ Criar `releases/CHANGELOG.md` (consolidado)

### Fase 4: Deletar Obsoletos
1. ✅ Deletar performance phases (1-6)
2. ✅ Deletar reports históricos
3. ✅ Deletar debugging temporários
4. ✅ Deletar pasta `modules/` e `maps_view/`

### Fase 5: Criar Índices (READMEs)
1. ✅ `doc/README.md` (índice mestre)
2. ✅ `getting-started/README.md`
3. ✅ `guides/README.md`
4. ✅ `architecture/README.md`
5. ✅ `api/README.md`
6. ✅ `operations/README.md`
7. ✅ `releases/README.md`
8. ✅ `contributing/README.md`

### Fase 6: Validação
1. ✅ Atualizar todos os links internos
2. ✅ Validar referências em README.md raiz do projeto
3. ✅ Testar navegação completa

---

## 📊 Métricas de Limpeza

| Métrica | Antes | Depois | Redução |
|---------|-------|--------|---------|
| **Arquivos em doc/** | ~60 | ~25 | ↓ 58% |
| **Pastas** | 7 | 7 | = |
| **Documentos obsoletos** | 25+ | 0 | ↓ 100% |
| **Duplicações** | 8 | 0 | ↓ 100% |
| **READMEs de navegação** | 2 | 8 | ↑ 300% |

---

## ✅ Checklist de Execução

- [ ] Criar nova estrutura de pastas
- [ ] Mover documentos relevantes
- [ ] Consolidar guias duplicados
- [ ] Deletar documentação obsoleta
- [ ] Criar READMEs de navegação
- [ ] Atualizar links internos
- [ ] Validar navegação completa
- [ ] Atualizar README.md raiz do projeto

---

**Status**: 📝 Planejamento  
**Owner**: Don Jonhn  
**Data**: 2025-01-07
