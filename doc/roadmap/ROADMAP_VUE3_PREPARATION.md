# Roadmap — Preparação para Vue 3

> **Contexto (12/11/2025):** Vue 3 só gera valor quando todas as APIs críticas já respondem em <100 ms e o mapa consome apenas os segmentos visíveis. Este documento consolida o plano único para concluir as entregas backend (Phases 8–10) e liberar a migração frontend (Phase 11).

## Visão Geral e Status

| Fase | Objetivo | Situação | Observações chave |
|------|----------|----------|-------------------|
| 8 | Celery atualiza status de cabos + push Channels | ✅ Concluída | API `/inventory/fibers/oper-status/` caiu de 40 s para <100 ms (commit `5cafda6`). |
| 9 | Rx/Tx óptico assíncrono (persistido) | ✅ Concluída | Endpoint `/fibers/<id>/cached-status/` não chama Zabbix (commit `89d0ac0`). |
| 9.1 | Remover chamadas síncronas restantes | ✅ Concluída | Endpoints `/fibers/<id>/cached-live-status/` implementados; 8 testes passando; zero chamadas síncronas Zabbix. |
| 10 | PostGIS + BBox API | ✅ Backend Concluído | **0.81ms BBox queries (20.3x speedup)**; autenticação habilitada; staging validado; frontend pendente (Phase 11). |
| 11 | Vue 3 + Pinia (dashboard/rotas/setup) | ✅ Sprint 2 Completo / � Sprint 3 Planejado | Dashboard completo com WebSocket, host cards, StatusChart, InfoWindows, MapControls, 25 testes passando. |

## Fundamentos já entregues

### Phase 8 — Celery Background Processing
- Cache Redis 120 s + websocket (`ws/dashboard/status/`)
- `monitoring.tasks.broadcast_dashboard_snapshot` e `refresh_dashboard_cache_task`
- Métricas Prometheus atualizadas (`metrics_celery.py`)

### Phase 9 — Async Optical Levels
- Campos `Port.last_rx_power`, `Port.last_tx_power`, `Port.last_optical_check`
- Tasks que capturam níveis ópticos assíncronos (fila `zabbix`)
- Endpoint cacheado para consumo do frontend

## Phase 9.1 — Encerrando Zabbix síncrono

**Meta:** 0 chamadas Zabbix em requisições web. ✅ **CONCLUÍDA**

Status Final:
- ✅ Migration `0009_fibercable_last_live_check_and_more` com campos de cache aplicada
- ✅ Persistência em `refresh_cables_oper_status` e `refresh_fiber_live_status` implementada
- ✅ Tasks `refresh_fiber_live_status` e `refresh_cables_oper_status` agendadas (Celery beat, 2 min)
- ✅ Endpoints `/api/v1/inventory/fibers/<id>/cached-live-status/` e `/fibers/<id>/cached-status/` validados
- ✅ Testes `inventory/tests/test_fiber_cached_status.py` — 8/8 passando
- ✅ Verificação crítica: zero chamadas Zabbix síncronas confirmada (mock assertions)

**Entregáveis verificados:**
```bash
# Testes executados com sucesso
pytest inventory/tests/test_fiber_cached_status.py -v
# Resultado: 8 passed in 0.57s

# Endpoints disponíveis:
GET /api/v1/inventory/fibers/{cable_id}/cached-status/
    → Retorna optical levels (RX/TX power) cacheados
    
GET /api/v1/inventory/fibers/{cable_id}/cached-live-status/
    → Retorna live status + operational status cacheados
```

**Riscos mitigados:**
- ✅ Fixtures atualizadas para suportar novos campos
- ✅ Endpoints retornam dados mesmo quando cache está vazio (fallback 'unknown')
- ✅ Tasks Celery configuradas no beat schedule (zabbix queue, 120s interval)

## Phase 10 — PostGIS Migration

**Status:** ✅ **BACKEND CONCLUÍDO** (12/11/2025)

**Entregas finalizadas:**
- ✅ Infraestrutura: PostgreSQL 16.4 + PostGIS 3.4 via `docker/docker-compose.postgis.yml`
- ✅ Models e migrations: `0010_add_spatial_fields`, `0011_populate_spatial_fields`, `0012_create_spatial_indexes` aplicadas
- ✅ API BBox: `inventory/api/spatial.py` com autenticação `@api_login_required` habilitada
- ✅ Benchmark: **0.81ms BBox queries vs 16.50ms full scan = 20.3x speedup** (supera meta de 10x)
- ✅ Staging: Infraestrutura validada, containers rodando, migrations aplicadas, API testada
- ✅ Testes: Autenticação validada (HTTP 401 sem credenciais), GiST index confirmado em uso
- ✅ Documentação: `PHASE10_IMPLEMENTATION_SUMMARY.md` atualizado com resultados finais

**Resultados de Performance:**
```
BBox Query:   0.81 ms  (target: <100ms)  ✅ 123x melhor que target
Full Scan:   16.50 ms
Speedup:     20.3x    (target: >10x)    ✅ 2x melhor que target
GiST Index:  CONFIRMED via EXPLAIN ANALYZE
```

**Próximos passos (Phase 11 dependente):**
1. ⏳ **Frontend Integration**
   - Implementar componentes Vue 3 para consumir `/api/v1/inventory/segments/?bbox=...`
   - Atualizar Pinia store `inventory` com merge incremental de segmentos
   - Integrar chamadas BBox no evento `idle` do Google Maps
2. ⏳ **Produção**
   - Aguardar conclusão de frontend integration (Phase 11)
   - Backup MySQL → migrar dados → apontar `DB_ENGINE=postgis`
   - Monitorar métricas Prometheus `inventory_routesegment_path_gist`

**Checklist oficial:**
- [x] Provisionar PostGIS ✅
- [x] Atualizar settings/base com GeoDjango ✅
- [x] Converter JSON → LineString ✅
- [x] GiST indexes ✅
- [x] API BBox ✅
- [x] Testes backend ✅
- [x] Benchmark desempenho ✅
- [x] Staging validado ✅
- [ ] Produção migrada (aguardando Phase 11)
- [ ] Frontend consumindo BBox (Phase 11)

**Próxima ação:** Iniciar Phase 11 (Vue 3 Migration) — backend Phase 10 completo e pronto para integração.

## Phase 11 — Vue 3 Migration Plan

**Pré-requisitos:** Phase 9.1 e 10 concluídas.

### Estrutura proposta (Vite + Pinia)
- `frontend/src/stores/` → `inventory`, `dashboard`, `routes`
- `frontend/src/components/` → `Dashboard/`, `RouteBuilder/`, `Setup/`
- `frontend/src/composables/` → `useWebSocket`, `useCableStatus`, `useGoogleMaps`
- SPA servida por `backend/templates/spa.html` com feature flag `USE_VUE_DASHBOARD`

### Plano por semana
1. **Setup + Dashboard** — bootstrap Vite, migrar mapa/host cards/gráficos, integrar websocket
2. **Route Builder + Setup App** — MapEditor, forms, drag&drop, Pinia routes
3. **APIs + Integração final** — revisar endpoints DRF, testes E2E (Playwright), otimizações

### Checklist
- [x] Feature flag `USE_VUE_DASHBOARD` adicionada
- [x] Template `spa.html` criado
- [x] Vite configurado para `staticfiles/vue-spa/`
- [x] Map store inicial (`map.js`) + `MapView.vue` BBox fetch
- [x] Dependências instaladas (vue3-google-map, vitest, playwright)
- [x] Teste unitário inicial (mapStore.spec.js)
- [x] **Debounce (300ms) implementado em MapView**
- [x] **Cores de status para segmentos (`segmentStatusColors.js`)**
- [x] **Utilities criados: `debounce.js`**
- [x] **Testes unitários: 16/16 passando** (debounce, colors, map, app, websocket, dashboard)
- [x] **Skip duplicate bbox requests**
- [x] **`.env.local` com `VITE_GOOGLE_MAPS_API_KEY` placeholder**
- [x] **WebSocket composable (`useWebSocket`) com auto-reconnect**
- [x] **Dashboard store (`dashboard.js`) para host cards**
- [x] **Segment pruning (remover fora viewport)**
- [x] **Playwright E2E smoke tests (5 tests)**
- [ ] Dashboard components migrados (DashboardView, HostCard, StatusChart)
- [ ] WebSocket integração real com `ws/dashboard/status/`
- [ ] Optical status no mapa (backend integration)
- [ ] InfoWindows para sites e segmentos
- [ ] Map controls (legend, fit bounds)
- [ ] Testes E2E completos (user flows)
- [ ] Deploy canário (10% usuários)
- [ ] Remover legacy `dashboard.js`

## Linha do Tempo consolidada

| Marco | Duração estimada | Situação |
|-------|------------------|----------|
| Phase 8 – Celery status | 3 dias | ✅ Finalizado |
| Phase 9 – Optical levels | 2 dias | ✅ Finalizado |
| Phase 9.1 – Cleanup Zabbix síncrono | 3 dias | ✅ Concluído |
| Phase 10 – PostGIS end-to-end | 7–10 dias | ✅ Backend completo, frontend em integração |
| Phase 11 Sprint 1 – Foundation | 2 dias | ✅ Completo (16 unit + 5 E2E tests) |
| Phase 11 Sprint 2 – Real-time & Features | 1 dia | ✅ Completo (25 tests, build 92 kB) |
| Phase 11 Sprint 3 – Polish & Deploy | 5–7 dias | 📅 Planejado |

**Estimativa total restante:** ~1–2 semanas (Sprint 3 + deploy gradual).

## Critérios de sucesso

**Performance**
- APIs p95 <100 ms
- Zero chamadas REST diretas ao Zabbix
- Mapas carregando <100 segmentos por requisição
- WebSocket <50 ms p95

**Arquitetura / Operação**
- Banco = fonte da verdade (Redis opcional)
- Celery beat saudável (monitoramento via Prometheus)
- SPA Vue 3 ativada com feature flag, fallback seguro

**Qualidade**
- Cobertura >90% nas áreas tocadas
- Testes E2E cobrindo dashboard, route builder, setup
- Guia de deploy atualizado (`operations/DEPLOYMENT.md`)
- Observabilidade revisada (dashboards PostGIS + Vue 3)

## Referências úteis
- `doc/reports/phases/PHASE10_IMPLEMENTATION_SUMMARY.md`
- `doc/operations/POSTGIS_SETUP_GUIDE.md`
- `doc/reports/phases/PHASE9_ASYNC_OPTICAL_LEVELS.md`
- `doc/architecture/ADR/004-refactoring-plan.md`
- [GeoDjango docs](https://docs.djangoproject.com/en/5.0/ref/contrib/gis/)
- [PostGIS docs](https://postgis.net/documentation/)
- [Vue 3 + Pinia](https://pinia.vuejs.org/)

---

**Última atualização:** 12/11/2025  
**Responsável:** Equipe MapsProveFiber  
**Contato rápido:** `#maps-frontend-migration` (Slack)
