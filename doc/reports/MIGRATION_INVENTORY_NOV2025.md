# 📊 Inventário de Migração Django → Vue 3
**Data**: 18 de Novembro de 2025  
**Objetivo**: Planejar migração completa para Vue.js SPA  
**Status**: 🔄 Sprint de 4 semanas iniciada

---

## 🎯 Executive Summary

### Estado Atual:
- **Frontend "Split Brain"**: 2 codebases coexistindo
  - ✅ **Vue 3 SPA** (`frontend/src/`) — Moderno, componentizado, testável
  - ⚠️ **Django Templates** (`backend/*/templates/`) — Legado, monolítico, JavaScript inline

- **Impacto**:
  - 🔴 **2x desenvolvimento**: Bugs precisam ser corrigidos em 2 lugares
  - 🔴 **Confusão UX**: Interfaces inconsistentes (Vue moderna vs Django antiga)
  - 🔴 **Testes frágeis**: 40% pass rate no Playwright devido a timeouts fixos

### Objetivo da Sprint:
- ✅ **Semanas 1-3**: Migrar templates Django → Vue 3
- ✅ **Semanas 1-2**: Corrigir testes Playwright (40% → 95%)
- ✅ **Semana 4**: Deletar código legado, validar

---

## 📋 Inventário Completo

### 1️⃣ Templates Django (28 arquivos encontrados)

#### 🟢 JÁ MIGRADOS PARA VUE (8 arquivos — pode deletar após validação):
| Arquivo Django | Equivalente Vue | Status API | Ação |
|----------------|----------------|------------|------|
| `backend/setup_app/templates/setup_dashboard.html` | `frontend/src/views/ConfigurationPage.vue` | ✅ `/api/config/` | ⏸️ **Manter por feature flag** |
| `backend/setup_app/templates/docs/view.html` | `frontend/src/views/DocsView.vue` | ✅ `/api/docs/<path>` | ⏸️ **Manter por feature flag** |
| `backend/templates/spa.html` | `frontend/dist/index.html` (build output) | N/A | ✅ **Não deletar** (entry point) |
| `backend/templates/base_spa.html` | `frontend/src/App.vue` | N/A | ✅ **Não deletar** (layout base) |
| - | `frontend/src/views/UsersManagement.vue` | ✅ `/api/users/` | ✅ **100% Vue** (sem Django) |
| - | `frontend/src/views/SystemHealthView.vue` | ✅ `/api/metrics/health/` | ✅ **100% Vue** (sem Django) |

#### 🔴 LEGADO ATIVO (requer migração ou validação):
| Arquivo | Rota Django | Complexidade | Prioridade | Estimativa |
|---------|-------------|--------------|------------|------------|
| `backend/maps_view/templates/dashboard.html` | `/maps_view/` | 🔴 **ALTA** (538 linhas, Leaflet, WebSocket) | P0 | 3 dias |
| `backend/maps_view/templates/metrics_dashboard.html` | `/metrics/` | 🟡 **MÉDIA** (Prometheus, gráficos) | P1 | 2 dias |
| `backend/inventory/templates/inventory/fiber_route_builder.html` | `/inventory/route-builder/` | 🔴 **ALTA** (mapa interativo) | P0 | 3 dias |
| `backend/templates/zabbix/lookup.html` | `/zabbix/lookup/` | 🟢 **BAIXA** (formulário simples) | P2 | 1 dia |
| `backend/templates/registration/login.html` | `/accounts/login/` | 🟢 **BAIXA** (Django auth padrão) | P3 | 1 dia |

#### 📦 PARTIALS/COMPONENTS (podem ser deletados após migração das páginas principais):
| Arquivo | Usado Por | Ação |
|---------|-----------|------|
| `backend/templates/partials/header.html` | `dashboard.html`, `base_dashboard.html` | ⏸️ **Deletar após migrar dashboard** |
| `backend/templates/partials/user_menu.html` | `header.html` | ⏸️ **Deletar após migrar dashboard** |
| `backend/templates/partials/add_device.html` | `dashboard.html` (modal) | ⏸️ **Deletar após migrar dashboard** |
| `backend/templates/partials/import_kml.html` | `dashboard.html` (modal) | ⏸️ **Deletar após migrar dashboard** |

#### 🔧 BASES/LAYOUTS (manter até final da migração):
| Arquivo | Propósito | Ação |
|---------|-----------|------|
| `backend/templates/base.html` | Layout Django padrão | ✅ **Manter** (usado por admin) |
| `backend/templates/base_with_sidebar.html` | Layout com menu lateral | ⏸️ **Deletar após migrar todas as páginas** |
| `backend/maps_view/templates/base_dashboard.html` | Layout específico do dashboard | ⏸️ **Deletar após migrar dashboard** |
| `backend/setup_app/templates/base_setup_dashboard.html` | Layout do setup | ⏸️ **Deletar após validar Vue** |
| `backend/setup_app/templates/base_first_time_setup.html` | Layout do setup inicial | ⏸️ **Deletar após validar Vue** |

---

### 2️⃣ JavaScript Legado (backend/*/static/js/)

#### 🔴 DUPLICAÇÃO CRÍTICA (1.430 linhas de JS legado):
| Arquivo | LOC | Funcionalidade | Equivalente Vue | Ação |
|---------|-----|----------------|----------------|------|
| `backend/maps_view/static/js/dashboard.js` | **1.430** | Leaflet map, WebSocket real-time, modal traffic | `frontend/src/components/Dashboard/DashboardView.vue` | ⚠️ **DELETAR após validar Vue** |
| `backend/maps_view/static/js/traffic_chart.js` | ~200 | Chart.js traffic graphs | `frontend/src/components/Dashboard/TrafficChart.vue` | ⚠️ **DELETAR após validar Vue** |

**Impacto da duplicação**:
- Bug fix em Vue não propaga para Django JS
- Usuários veem comportamentos diferentes dependendo da feature flag
- Dificulta manutenção (2 implementações do mesmo código)

---

### 3️⃣ Rotas Django vs Vue Router

#### 🔄 ROTAS DUPLICADAS (servindo Django template + Vue component):
| URL | Django View | Vue Component | Status |
|-----|-------------|---------------|--------|
| `/maps_view/` | `maps_view.views.dashboard_view()` | `DashboardView.vue` | ⚠️ **Feature flag** (`USE_VUE_DASHBOARD`) |
| `/metrics/` | `maps_view.views.metrics_dashboard()` | ⏸️ **Não existe ainda** | 🔴 **Precisa migrar** |
| `/setup_app/config` | `setup_app.views.setup_dashboard()` | `ConfigurationPage.vue` | ⚠️ **Feature flag** |
| `/docs` | `setup_app.views_docs.docs_index()` | `DocsView.vue` | ⚠️ **Feature flag** |

#### ✅ ROTAS 100% VUE (sem Django template):
| URL | API | Vue Component | Status |
|-----|-----|---------------|--------|
| `/system/users` | `/api/users/` | `UsersManagement.vue` | ✅ **Completo** |
| `/metrics/health` | `/api/metrics/health/` | `SystemHealthView.vue` | ✅ **Completo** |
| `/monitoring/monitoring-all` | `/api/v1/inventory/*` | `MonitoringOverview.vue` | ✅ **Completo** |
| `/Network/NetworkDesign/` | `/api/v1/*` | `NetworkDesignView.vue` | ✅ **Completo** |

#### 🔴 ROTAS APENAS DJANGO (precisa criar Vue + API):
| URL | Django View | Complexidade | Prioridade |
|-----|-------------|--------------|------------|
| `/inventory/route-builder/` | `render(request, "fiber_route_builder.html")` | 🔴 **ALTA** | P0 |
| `/zabbix/lookup/` | `core.views.zabbix_lookup_page()` | 🟢 **BAIXA** | P2 |
| `/accounts/login/` | Django `auth.views.LoginView` | 🟢 **BAIXA** | P3 |

---

## 🧪 Testes Playwright - Análise de Flakiness

### Estado Atual: 40% Pass Rate ❌

#### 🔴 Problema Principal: Fixed Timeouts
**12 ocorrências de `waitForTimeout()` encontradas**:
| Arquivo | Linha | Código | Problema |
|---------|-------|--------|----------|
| `dashboard.spec.js` | 86, 121, 145, etc. | `await page.waitForTimeout(2000)` | Assume que 2s é suficiente (falha em CI lento) |
| `map-loading.spec.js` | 190 | `await page.waitForTimeout(5000)` | 5s desperdiçados mesmo quando mapa carrega em 1s |
| `mapView.spec.js` | 72 | `await page.waitForTimeout(2000)` | Não espera evento real (Leaflet tiles loaded) |

#### ✅ Solução: Event-Based Waiting
```javascript
// ❌ ANTES (frágil):
await page.waitForTimeout(5000);
const mapTiles = page.locator('.leaflet-tile');
await expect(mapTiles).toBeVisible();

// ✅ DEPOIS (robusto):
await page.waitForFunction(() => {
  const tiles = document.querySelectorAll('.leaflet-tile');
  return tiles.length > 0 && Array.from(tiles).some(t => t.complete);
}, { timeout: 10000 });
```

#### 📊 Testes com Maior Impacto (priorizar):
| Teste | Timeouts | Taxa de Falha | Impacto |
|-------|----------|---------------|---------|
| `dashboard.spec.js` - "should load Leaflet map" | 8x | 60% | 🔴 **Crítico** |
| `map-loading.spec.js` - "should load Google Maps tiles" | 1x | 30% | 🟡 **Médio** |
| `mapView.spec.js` - "map should respond to interactions" | 1x | 20% | 🟢 **Baixo** |

---

## 🎯 Plano de Migração - 4 Semanas

### 📅 SEMANA 1: Baseline + Top Priority Routes

#### Dia 1-2: **Corrigir Testes Playwright** (Quick Win)
- ✅ **Ação**: Substituir todos os `waitForTimeout()` por event-based waiting
- ✅ **Arquivos**: `dashboard.spec.js`, `map-loading.spec.js`, `mapView.spec.js`
- ✅ **Padrões**:
  - Maps (Leaflet): `waitForFunction(() => document.querySelectorAll('.leaflet-tile-loaded').length > 0)`
  - Maps (Google): `waitForSelector('img[src*="maps.googleapis.com"]', { state: 'visible' })`
  - API responses: `waitForResponse(url => url.includes('/api/v1/'))`
- 🎯 **Meta**: 40% → 75% pass rate (Day 2)

#### Dia 3-5: **Migrar Dashboard Legacy** (P0 — maior impacto)
- 📂 **Django**: `backend/maps_view/templates/dashboard.html` (538 linhas)
- 📂 **JS Legado**: `backend/maps_view/static/js/dashboard.js` (1.430 linhas)
- 🎯 **Vue Target**: Refatorar `frontend/src/components/Dashboard/DashboardView.vue`
- ✅ **Tarefas**:
  1. ✅ Validar que feature flag `USE_VUE_DASHBOARD=1` funciona 100%
  2. ✅ Comparar comportamento Django vs Vue (WebSocket, Leaflet markers, modals)
  3. ✅ Migrar funcionalidades faltantes (se houver)
  4. ✅ Testar em produção com rollout gradual (10% → 50% → 100%)
  5. ⚠️ **Deletar** `dashboard.html` e `dashboard.js` após validação
- 🎯 **Success Criteria**: 100% dos usuários em Vue, 0 bugs reportados

---

### 📅 SEMANA 2: Medium Priority Routes + Consolidação

#### Dia 6-7: **Migrar Metrics Dashboard** (P1)
- 📂 **Django**: `backend/maps_view/templates/metrics_dashboard.html`
- 🎯 **Vue Target**: Criar `frontend/src/views/MetricsDashboard.vue`
- ✅ **API**: Já existe `/api/metrics/health/` (usado por `SystemHealthView.vue`)
- ✅ **Tarefas**:
  1. Criar componente Vue com gráficos (Chart.js ou similar)
  2. Adicionar rota em `frontend/src/router/index.js`
  3. Atualizar `core/urls.py` para servir Vue SPA
  4. Testar Prometheus metrics rendering
  5. Deletar template Django

#### Dia 8-10: **Migrar Fiber Route Builder** (P0 — complexo)
- 📂 **Django**: `backend/inventory/templates/inventory/fiber_route_builder.html`
- 🎯 **Vue Target**: `frontend/src/views/FiberRouteBuilder.vue` (novo)
- ✅ **API**: Já existe `/api/v1/inventory/routes/` (usado por `NetworkDesignView.vue`)
- ✅ **Tarefas**:
  1. Criar componente com mapa interativo (Leaflet ou Google Maps)
  2. Implementar lógica de desenho de rotas (polylines, markers)
  3. Integrar com API de rotas (`POST /api/v1/inventory/routes/build/`)
  4. Adicionar validação de segmentos
  5. Testar criação, edição e exclusão de rotas
  6. Deletar template Django

---

### 📅 SEMANA 3: Low Priority Routes + Polimento

#### Dia 11-12: **Migrar Zabbix Lookup** (P2 — simples)
- 📂 **Django**: `backend/templates/zabbix/lookup.html`
- 🎯 **Vue Target**: `frontend/src/views/ZabbixLookup.vue` (novo)
- ✅ **API**: Criar endpoint `/api/zabbix/lookup/` (se não existir)
- ✅ **Tarefas**:
  1. Criar formulário Vue (search input + results table)
  2. Integrar com API Zabbix
  3. Adicionar rota em Vue Router
  4. Deletar template Django

#### Dia 13-14: **Migrar Login Page** (P3 — autenticação)
- 📂 **Django**: `backend/templates/registration/login.html`
- 🎯 **Vue Target**: `frontend/src/views/LoginPage.vue` (novo)
- ✅ **API**: Usar Django REST Framework authentication
- ⚠️ **Decisão**: Manter Django login ou migrar para Vue + JWT?
  - **Opção A**: Vue SPA com JWT tokens (mais moderno)
  - **Opção B**: Manter Django session auth (menos mudança)
- ✅ **Tarefas**:
  1. Decidir estratégia de autenticação
  2. Implementar componente de login
  3. Testar fluxo completo (login → redirect → logout)
  4. Atualizar middleware de autenticação

#### Dia 15: **Corrigir Testes Restantes** (Meta: 95% pass rate)
- ✅ Rodar suite completa Playwright: `npm run test:e2e`
- ✅ Identificar testes ainda com falhas
- ✅ Aplicar padrões event-based waiting
- ✅ Adicionar testes para novas rotas migradas
- 🎯 **Meta**: 95%+ pass rate consistente

---

### 📅 SEMANA 4: Cleanup + Validação

#### Dia 16-17: **Deletar Código Legado**
- ✅ **Templates Django** (após validação):
  ```bash
  # ⚠️ CUIDADO: Fazer backup antes!
  git mv backend/maps_view/templates/dashboard.html backend/maps_view/templates/.archived/
  git mv backend/maps_view/static/js/dashboard.js backend/maps_view/static/js/.archived/
  git rm backend/templates/partials/*.html
  ```
- ✅ **JavaScript Legado**:
  ```bash
  git rm backend/maps_view/static/js/dashboard.js
  git rm backend/maps_view/static/js/traffic_chart.js
  ```
- ✅ **Views Django** (manter apenas APIs):
  ```python
  # backend/maps_view/views.py
  # DELETAR funções que servem templates:
  # - dashboard_view() → substituído por Vue
  # - metrics_dashboard() → substituído por Vue
  ```

#### Dia 18-19: **Validação Final**
- ✅ **Testes E2E**: 95%+ pass rate
- ✅ **Testes Unitários**: Todos passando
- ✅ **Performance**: Lighthouse score > 90
- ✅ **Acessibilidade**: WCAG 2.1 AA compliance
- ✅ **Navegadores**: Chrome, Firefox, Safari, Edge
- ✅ **Mobile**: Responsive em iOS/Android

#### Dia 20: **Deploy + Documentação**
- ✅ Deploy para produção (rollout gradual)
- ✅ Atualizar documentação:
  - `README.md` — remover referências a templates Django
  - `doc/architecture/FRONTEND.md` — documentar arquitetura 100% Vue
  - `CHANGELOG.md` — registrar migração completa
- ✅ Criar release tag: `v2.1.0 - 100% Vue.js SPA`

---

## 📊 Success Metrics

### Antes da Migração:
| Métrica | Valor | Status |
|---------|-------|--------|
| Frontend stack | Django + Vue (split brain) | 🔴 **Duplicado** |
| LOC JavaScript legado | 1.630+ linhas | 🔴 **Alto** |
| Playwright pass rate | 40% | 🔴 **Crítico** |
| Tempo para corrigir bug | 2x (Django + Vue) | 🔴 **Alto** |
| Bundle size | 500 KB (duplicação) | 🟡 **Médio** |

### Após a Migração (Meta — Semana 4):
| Métrica | Valor | Status |
|---------|-------|--------|
| Frontend stack | 100% Vue 3 SPA | ✅ **Unificado** |
| LOC JavaScript legado | 0 linhas | ✅ **Limpo** |
| Playwright pass rate | 95%+ | ✅ **Confiável** |
| Tempo para corrigir bug | 1x (apenas Vue) | ✅ **Otimizado** |
| Bundle size | 400 KB (-100 KB) | ✅ **Reduzido** |

---

## 🚧 Riscos e Mitigações

### 🔴 RISCO ALTO: Feature Flag não 100% equivalente
- **Problema**: Vue dashboard pode ter bugs que Django não tem
- **Mitigação**:
  1. ✅ Rollout gradual (10% → 50% → 100%)
  2. ✅ Monitorar logs de erro (Sentry/Similar)
  3. ✅ Manter feature flag por 2 semanas após 100% rollout
  4. ✅ Ter rollback plan (reverter flag)

### 🟡 RISCO MÉDIO: Testes Playwright ainda frágeis após correção
- **Problema**: Pode haver outros fatores além de timeouts (race conditions, etc.)
- **Mitigação**:
  1. ✅ Rodar testes 10x consecutivas para validar estabilidade
  2. ✅ Adicionar retry lógica no Playwright config
  3. ✅ Usar visual regression tests (screenshots)

### 🟢 RISCO BAIXO: Usuários reportam UX diferente
- **Problema**: Mudança visual pode confundir usuários
- **Mitigação**:
  1. ✅ Comunicar mudanças antes do deploy
  2. ✅ Criar guia de "O que mudou?"
  3. ✅ Coletar feedback via formulário in-app

---

## 🎉 Conclusão

Esta migração eliminará o "split brain" frontend e reduzirá **drasticamente** o tempo de desenvolvimento.

**Benefícios esperados**:
- ⚡ **50% faster bug fixes** (apenas 1 codebase)
- 📦 **100 KB menor bundle** (sem duplicação)
- 🧪 **95%+ test reliability** (event-based waiting)
- 🎨 **UI consistente** (100% Vue components)

**Próximos Passos**:
1. ✅ **HOJE**: Corrigir testes Playwright (Dia 1)
2. ✅ **Esta semana**: Validar Vue dashboard com 100% usuários
3. ✅ **Próximas 3 semanas**: Migrar rotas restantes
4. ✅ **Semana 4**: Deletar código legado

**Responsável**: Time de Engenharia MapsProveFiber  
**Deadline**: 16 de Dezembro de 2025 (4 semanas)  
**Tracking**: Este documento será atualizado diariamente
