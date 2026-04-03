# Roadmap de Funcionalidades Futuras — MapsProveFiber

> **Status:** Planejamento e especificação técnica  
> **Versão:** Draft 2.0  
> **Data:** 2025-11-19 (Atualizado)  
> **Plano Piloto:** `doc/process/PLANO_PILOTO_PADRAO.md`

Este documento detalha os planos de expansão do MapsProveFiber além do core atual (v2.0), incluindo novos módulos, apps Django e funcionalidades avançadas organizadas por edições comerciais.

**⚠️ IMPORTANTE:** Todas as novas implementações devem seguir o **Plano Piloto Padrão** (8 dias) documentado em `doc/process/PLANO_PILOTO_PADRAO.md`.

---

## ✅ Implementações Concluídas

### **Phase 7: Spatial Radius Search** (Nov 2025)
**Status:** ✅ COMPLETO - Em produção (100% rollout)

**Implementado:**
- ✅ **Day 1:** Planning & Architecture
  - Especificação técnica: `PHASE7_SPEC.md` (500+ lines)
  - Diagrama de fluxo: API → Service → PostGIS → Cache
  - Endpoints definidos: `GET /api/v1/inventory/sites/radius`
  - Riscos identificados: Performance, cache invalidation

- ✅ **Day 2:** Data Layer & PostGIS
  - Validação de modelos: `Site` com `lat`/`lng` (SRID 4326)
  - Índices otimizados: `idx_site_location` (B-tree composto)
  - Queries espaciais: Haversine distance calculation
  - Testes: `test_spatial_queries.py` (10 test cases)

- ✅ **Day 3:** Business Logic & Services
  - Serviço: `inventory/services/radius_search.py`
  - Função: `search_sites_by_radius(lat, lng, radius_km)`
  - Validação: radius_km entre 0.1 e 100
  - DTO tipado: `RadiusSearchResult` dataclass
  - Testes: 15 unit tests, 94% coverage

- ✅ **Day 4:** API Endpoints
  - Endpoint: `GET /api/v1/inventory/sites/radius?lat={lat}&lng={lng}&radius_km={radius}`
  - Serializer: `SiteRadiusSerializer` com validação completa
  - Paginação: LimitOffsetPagination (max 1000)
  - Swagger: `@extend_schema` documentation
  - Status codes: 200/400/404/500

- ✅ **Day 5:** SWR Cache Implementation
  - Cache pattern: Stale-While-Revalidate
  - TTLs: fresh_ttl=30s, stale_ttl=60s
  - Cache key: `radius:{md5(lat,lng,radius)}`
  - Invalidação: signals em `Site.save()/delete()`
  - Celery task: `refresh_radius_cache.delay()`
  - Benchmarks: p95 <200ms (10k sites)

- ✅ **Day 6:** Testing & Quality
  - Testes: 14/15 passing (93% success rate)
  - Coverage: 94% (backend/inventory/)
  - Performance: 100 concurrent users, p95 <200ms
  - E2E: Playwright tests (search + map interaction)

- ✅ **Day 7:** Monitoring & Observability
  - Prometheus alerts: `radius_search.yml` (16 alerts)
    - 5 critical: High error rate, high latency, cache down, task failures, Redis exhaustion
    - 6 warning: Low hit rate, elevated latency, high stale rate, cache slowness, backlog, DB slowness
    - 2 info: Cache warming, low adoption
  - Grafana dashboard: `phase7_radius_search.json` (8 panels)
    - Cache hit rate gauge, API latency graph, request rate area chart
    - Celery tasks graph, Redis memory graph, cache operations donut
    - Cache latency graph, result count bar chart
  - Deployment plan: `PHASE7_DEPLOYMENT_PLAN.md` (2500+ lines)
  - Monitoring setup: `MONITORING_SETUP.md` (800+ lines)
  - Docker integration: Prometheus + Grafana via docker-compose.yml

- ✅ **Day 8:** Production Rollout
  - Phase 1-4: 10% → 25% → 50% → 100% (COMPLETO)
  - Monitoring stack: Prometheus + Grafana operational
  - Success criteria: hit rate >70%, p95 <200ms, error <0.1%
  - Verification: `PHASE7_DAY7_VERIFICATION.md` (370+ lines)
  - Status: ✅ 100% rollout deployed
  - Production: Stable, all metrics within targets

**Métricas de Sucesso:**
- ✅ Coverage: 94% (target: >90%)
- ✅ Performance: p95 <200ms (target: <200ms)
- ✅ Deployment: 8 dias (target: 8 dias)
- ✅ Documentation: 1670+ lines (comprehensive)
- ⏳ Uptime: Monitoring 24h (target: >99.9%)

**Lessons Learned:**
1. Planejamento detalhado evita surpresas
2. SWR cache equilibra freshness e performance
3. Monitoring first dá visibilidade total
4. Rollout gradual permite detectar issues cedo
5. Automated deployment reduz erros manuais

**Arquivos Criados:**
- `doc/operations/PHASE7_DEPLOYMENT_PLAN.md`
- `doc/operations/MONITORING_SETUP.md`
- `doc/operations/PHASE7_DAY7_VERIFICATION.md`
- `docker/prometheus/prometheus.yml`
- `docker/prometheus/alerts/radius_search.yml`
- `docker/prometheus/README.md`
- `docker/grafana/datasources/prometheus.yml`
- `docker/grafana/dashboards/dashboard.yml`
- `docker/grafana/dashboards/phase7_radius_search.json`
- `scripts/deploy_monitoring.ps1`

---

## 📦 Edições Planejadas

### 1) **MONITORAMENTO** (Core - v2.0 Atual)
Núcleo de observabilidade e operação (health/readiness/liveness, métricas, alertas, dashboards).

**Status atual:** ✅ Implementado em v2.0

### 2) **+ Mapeamento de Rede**
Gestão completa de ativos físicos, inventário detalhado e rastreabilidade ponta-a-ponta.

**Status:** 🔄 Parcialmente implementado (inventário básico existe)

### 3) **+ GPON**
Operação e diagnóstico de redes GPON com integração CRM/OSS.

**Status:** ⏳ Planejado (app `gpon/` scaffolded)

### 4) **+ DWDM**
Camada óptica L0, grid de canais, monitoramento de performance óptica.

**Status:** ⏳ Planejado (app `dwdm/` scaffolded)

---

## 🗺️ Matriz de Recursos (Planejamento)

| Recurso / Edição                                  | MONITORAMENTO | + Mapeamento | + GPON  | **+ DWDM** |
|---                                                |:---:          |    :---:     |  :---:  |    :---:   |
| Health/Readiness/Liveness                         |✅            |      ✅      |   ✅    |     ✅    |
| Métricas e Dashboards                             |✅            |      ✅      |   ✅    |     ✅    |
| Alertas (RED/USE)                                 |✅            |      ✅      |   ✅    |     ✅    |
| Inventário básico (sites/devices)                 |✅            |      ✅      |   ✅    |     ✅    |
| Desenho de cabos/rotas                            |➖            |      ✅      |   ✅    |     ✅    |
| Caixas de emenda (bandejas/emendas)               |➖            |      ✅      |   ✅    |     ✅    |
| DIO/patch panel e patch cords                     |➖            |      ✅      |   ✅    |     ✅    |
| Reservas/dutos                                    |➖            |      ✅      |   ✅    |     ✅    |
| Circuito ponta-a-ponta                            |➖            |      ✅      |   ✅    |     ✅    |
| Árvore GPON (OLT→PON→Splitters→CTO→ONU)           |➖            |      ➖      |   ✅    |     ✅    |
| Integração CRM/OSS (cliente/geo/finance/serviço)  |➖            |      ➖      |   ✅    |     ✅    |
| Diagnóstico GPON (potência/keep-alive)            |➖            |      ➖      |   ✅    |     ✅    |
| **Inventário L0 (Mux/Amp/Transponder)**           |➖            |      ➖      |   ➖    |     ✅    |
| **Grid de Canais (Lambdas)**                      |➖            |      ➖      |   ➖    |     ✅    |
| **Monitoramento Óptico (OSNR/Potência)**          |➖            |      ➖      |   ➖    |     ✅    |
| **Planejador de Canal/Dispersão**                 |➖            |      ➖      |   ➖    |     ✅    |
| **Simulação de Falhas (Chaos)**                   | **Add-on**   | ➖           | ➖      | ➖          |
| **Análise de Impacto Financeiro**                 | ➖           | ➖           | **Add-on** | ➖      |

**Legenda:** ✅ incluído · ➖ não incluído · **Add-on** = módulo opcional

---

# 1) Edição MONITORAMENTO — Núcleo Inteligente (Futuro)

## 1.1 Motor de Correlação de Eventos (RCA — Root Cause Analysis)

**Objetivo:** Reduzir ruído correlacionando alertas por **topologia e dependências**.

**Exemplo de uso:** Se um **Switch/OLT** principal em um **POP** cai, o sistema **agrega** centenas de alertas "cliente offline" relacionados, gerando **1 incidente raiz**.

### Conceito Técnico
- **Modelo de dependência**: Grafo (POP → devices → interfaces → circuitos → clientes)
- **Regras de causalidade**: 
  - _Hard_: físico/energia
  - _Soft_: degradação, flapping
- **Agrupamento temporal**: Janelas (5–10 min) para consolidar eventos filhos
- **Sinais de apoio**: Índice de impacto (entidades afetadas), severidade, criticidade

### Arquitetura Mínima
**Serviço `rca-engine` (Celery worker):**
1. Consome eventos (Prometheus/Zabbix/Webhooks)
2. Consulta **grafo** de dependências
3. Classifica/agrupa eventos
4. Publica _incidents_ via API

**Persistência do grafo:**
- MVP: Tabela/JSONB (Django models)
- Fase 2: Grafo dedicado (Neo4j/ArangoDB)

**Endpoints:**
- `POST /api/v1/incidents` — Criar incidente
- `GET /api/v1/incidents/{id}` — Detalhes do incidente
- `GET /api/v1/incidents?root_only=true` — Listar apenas incidentes raiz

### SLO Sugerido
- Agrupar eventos em **< 20s p95** após alerta raiz

---

## 1.2 Análise Preditiva de Falhas

**Objetivo:** Prever impactos por séries temporais (potência óptica, banda, CPU, CRC).

**Exemplo:** "ONU X com **−0,5 dB/dia**; atual **−24,5 dB**; **falha provável em 4 dias**".

### Técnica (MVP)
- Features simples: derivada/gradiente, EWMA, _z-score_
- _Thresholds_ por baseline diurno/noturno
- **Fase 2:** ARIMA/Prophet ou regressão robusta por ONU/porta

### APIs
- `POST /api/v1/predict/optical`
  - **Entrada:** Série ONU/porta
  - **Saída:** Tendência/risco/data estimada
- `GET /api/v1/predictions?entity_type=ONU&state=ACTIVE`

### SLO
- Previsão por entidade **< 1s p95** (com cache)

---

## 1.3 Observabilidade Integrada (Métricas + Logs + Traces)

### Boas Práticas
- **Correlação** por labels/campos: `trace_id`, `span_id`, `device_id`, `client_id`
- **Exporters:** OpenTelemetry (OTLP) → Prometheus/Loki/Tempo/Jaeger
- **Grafana:** Links de métrica → _Explore logs_ / _traces_

### SLO
- _Jump_ métrica→logs/traces **< 3s**

---

## 1.4 Health Checks Hierárquicos

**API:** `GET /api/v1/health`

**Exemplo de resposta:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-02T10:30:00Z",
  "checks": {
    "database": {"status": "healthy", "response_time_ms": 12},
    "redis": {"status": "healthy", "response_time_ms": 5},
    "prometheus": {"status": "degraded", "response_time_ms": 1500},
    "crm_integration": {"status": "unhealthy", "error": "Connection timeout"}
  }
}
```

---

## 1.5 Add-on: Simulação de Falhas (Chaos Engineering)

**Objetivo:** Validar resiliência do **RCA**, grafo e runbooks com cenários controlados.

### Cenários de Teste
- Queda de OLT
- Rompimento de fibra
- Flapping de link
- Overload de banda

### API
- `POST /api/v1/simulation/failure`

### Métricas
- Tempo de detecção
- Eficácia de supressão
- _MTTD_/_MTTR_ simulado

---

# 2) Edição + Mapeamento de Rede — Gestão de Ativos Completa

## 2.1 Gestão de Ativos (Asset Management) Detalhada

### Modelo (MVP)
**Django Models:**
- `Site` / `Room` / `Rack (id, face, u_min, u_max)`
- `RackUnit (rack_id, u, front/back, occupied_by)`
- `Asset (device/dio/closure, purchase_date, warranty_end, eol/eos)`

**Auditoria:**
- `created_at`, `updated_at`, `created_by`, `updated_by`

**Relações:**
- Porta-a-porta e fibra-a-fibra
- Cores: **TIA-598-C**
- Conectores: **IEC-61754**

### Relatórios
- Capacidade por rack/U
- Ativos por status
- Ocupação por POP

---

## 2.2 Templates de Equipamentos

### Exemplos
- **"OLT Huawei MA5800-X15"** → Cria 15 slots de serviço + 2 de gerência
- **"Switch Cisco 48p"** → Portas 1..48 + uplinks SFP/QSFP

### Técnico
**Django Models:**
- `DeviceTemplate` (modelo, vendor, _port/slot profiles_)

**API:**
- `POST /api/v1/devices` com `template_id` aplica **naming policy** (ITU/TMF)

---

## 2.3 Projetos de Expansão (Sandbox)

### Fluxo de Estados
- `PLANNED` → `UNDER_CONSTRUCTION` → `COMMISSIONED`

**Regras:**
- Comissionar move ativos para `IN_PRODUCTION` com **versionamento** (diffs)
- Apenas `PLANNED/UNDER_CONSTRUCTION` são mutáveis

---

# 3) Edição + GPON — Operação e Cliente no Centro

## 3.1 Diagnóstico Comparativo de Vizinhança

### Técnico
**API:**
- `GET /api/v1/gpon/tree/{pon_id}` → Retorna splitters/CTOs/ONUs com **estado**
  - Potência atual
  - Último keep-alive

**Heurística:**
- Comparar ONU alvo vs. ONUs irmãs no mesmo ramo

---

## 3.2 Auto-Provisionamento (ZTP — Zero-Touch Provisioning)

### Fluxo
1. Webhook do CRM (cliente ativo) → Celery `provision_client`
2. Validar **porta livre** na CTO e **perfil de serviço**
3. Calcular **orçamento óptico** esperado (distância + split)
4. Autorizar ONU (serial/MAC) na OLT + aplicar perfil (VLAN/PPP/IPoE)
5. Confirmar sessão; atualizar inventário e CRM

### Controles
- RBAC
- *Dry-run* mode
- Auditoria **who/when/what**
- **Idempotency-Key** em requests

---

## 3.3 Histórico e Linha de Base de Sinal

### UI Features
- Gráficos 48h/7d/30d com bandas de tolerância
- Marcações de _flapping_
- Export CSV/JSON

---

## 3.4 Add-on: Análise de Impacto Financeiro

**Objetivo:** Estimar **custo de indisponibilidade** por incidente/cliente/segmento.

### Relatórios
- "Falha na OLT-X impactou R$Y em SLA"
- Custo acumulado por POP/tecnologia

**Requisito:** Integração CRM/OSS (`finance_status` agregado)

---

# 4) Edição + DWDM (Camada Óptica L0)

## 4.1 Inventário e Modelagem DWDM

### Django Models (apps/dwdm/)
- `DwdmEquipment` (Mux/Demux, Transponder/Muxponder, EDFA/Raman, OADM, DCM)
- `ChannelGrid` (grid ITU-T 100 GHz C-Band; λ/frequência)
- `OpticalChannel (Lambda)` (circuito L0)
- `OpticalLink` (rota física com fibras do `apps/inventory`)

### Funções
- CRUD DWDM (alocados em `Sites/Racks` do inventário)
- **Grid view** de canais: `Disponível | Em Uso | Reservado`
- Rastreabilidade L0: `Transponder-A ↔ Transponder-B` via `OpticalLink`

---

## 4.2 Monitoramento de Performance Óptica (OPM)

### Métricas Chave
- **OSNR** (Optical Signal-to-Noise Ratio)
- **Potência Tx/Rx**
- **CD/PMD** (Chromatic Dispersion / Polarization Mode Dispersion)
- **FEC (Pre/Post)** (Forward Error Correction)

### RCA Integration
- `rca-engine` entende dependência: _N_ `OpticalChannels` → 1 `EDFA`

---

## 4.3 Planejador de Canais & Dispersão

### Fluxo
1. Selecionar `Rota` (LineString) e `Canal (λ)`
2. API: `POST /api/v1/optical/budget/estimate`
3. Calcular:
   - Perda Total
   - Penalidade de Dispersão
4. Resultado: "Viável/Não-viável" + justificativas

---

# 🧱 Decisões de Arquitetura (Futuras)

## Catálogos (apps/catalog)
**Django Models:**
- `FiberSpec` — Especificações de fibra óptica
- `CableSpec` — Especificações de cabos
- `Catalog` — Catálogo genérico
- `CatalogItem` — Itens de catálogo
- `ActiveCatalog` — Catálogo ativo por categoria

## PostGIS
- **SRID 4326** desde o início
- Índices **GiST** para performance
- Funções: `ST_Length`, `ST_DWithin`, `ST_Intersects`

## ZTP (Adapter Pattern)
**Components:**
- `GponProvisioner` (interface base)
- Drivers por vendor: `Huawei`, `Zte`, `Fiberhome`
- **NETCONF/YANG** preferencial; fallback SSH/Telnet

## Integração CRM/OSS Resiliente
**Padrões:**
- Celery `autoretry` + _backoff_ com _jitter_
- **Circuit Breaker** pattern
- **DLQ** (Dead Letter Queue)
- **Idempotency-Key** em requests

## RCA Pragmático
**Janelas por domínio:**
- Backbone: 5–10 min
- Acesso: 2–5 min

## Auditoria por Eventos
**Stack:**
- PostgreSQL como fonte
- Eventos imutáveis (signals/django-simple-history)
- ES (Elasticsearch) fora do MVP

## Feature Flags
**Planejadas:**
- `rca_engine`
- `postgis_enabled`
- `ztp_driver_huawei`
- `chaos_enabled`

---

# 📚 Catálogos de Fibra & Cabos + Orçamento Óptico

## 1) Catálogo de Fibra Óptica (`FiberSpec`)

### Campos
- `itu_class` (ex.: G.652.D, G.657.A2, OM4)
- `mode` (`SM`|`MM`)
- `attenuation_db_per_km` por λ:
  ```json
  {"1310": 0.35, "1490": 0.28, "1550": 0.22}
  ```
- `macro_bend_sensitivity`
- `min_bend_radius_mm`
- `splice_loss_db_default` (ex.: 0.05 dB)
- `connector_loss_db_default` (ex.: 0.25 dB)
- `temp_coeff_db_per_km_per_c` (opcional)
- `aging_margin_db` (ex.: 0.3 dB)

---

## 2) Catálogo de Cabos (`CableSpec`)

### Campos
- `construction` (ADSS, OPGW, LooseTube, Microduct, DropFlat, Armored, Dielectric)
- `fiber_count`
- `sheath`, `armoring`, `water_blocking`
- `weight_kg_per_km`, `max_tension_N`, `max_span_m`
- `outer_diameter_mm`, `min_install_bend_radius_mm`
- `default_fiber_spec` → FK para `FiberSpec`
- `uv_rating`, `fire_rating` (LSZH/CPR)

---

## 3) Inventário x Catálogo

**Relações:**
- `Cable` referencia `CableSpec` (e opcionalmente um `FiberSpec`)
- Rotas (LineString) associam `segmento → cable_id`
- Comprimento calculado via `ST_Length(geog)`

---

## 4) Orçamento Óptico (por λ)

### Fórmula
```
Perda_total_dB =
   Σ( length_km(segmento) * attenuation_db_per_km[λ] )
 + (N_splices * splice_loss_db_default)
 + (N_connectors * connector_loss_db_default)
 + (Σ splitters * insertion_loss_db(split_ratio))
 + engineering_margin_db 
 + aging_margin_db 
 + (ajustes de temperatura)
```

### Observações
- `attenuation_db_per_km` do `FiberSpec`
- Perdas de splitters em catálogo:
  - 1:2 ≈ 3.5 dB
  - 1:8 ≈ 10.5 dB
  - 1:16 ≈ 13.5 dB
  - 1:32 ≈ 17.0 dB
- OTDR pode sobrescrever perdas → auditar (quem/quando/por quê)

---

## 5) APIs Planejadas

### Endpoints
- `GET /api/v1/catalog/fibers` — Listar especificações de fibra
- `GET /api/v1/catalog/cables` — Listar especificações de cabo
- `GET /api/v1/catalog/splitters` — Listar especificações de splitters
- `POST /api/v1/inventory/cables` — Criar cabo
- `POST /api/v1/optical/budget/estimate` — Calcular orçamento óptico

### Exemplo de Request (Budget Estimate)
```json
{
  "route_id": 123,
  "wavelength_nm": 1550,
  "splices": 6,
  "connectors": 4,
  "splitters": [
    {"ratio": "1:16"},
    {"ratio": "1:2"}
  ],
  "margins": {
    "engineering": 1.0,
    "aging": "auto"
  }
}
```

### Exemplo de Response
```json
{
  "length_km": 12.43,
  "loss_db": 9.87,
  "details": {
    "segments": [...],
    "components": [...]
  }
}
```

---

## 6) UI/UX Planejado

### Features
- Formulário de **cabo** baseado em `CableSpec`
- Sugestão automática de perdas
- No mapa: orçamento estimado por λ (abas 1310/1490/1550) ao salvar rota
- GPON: validar orçamento vs. perfil de porta/ONU antes do provisionamento

---

## 7) Boas Práticas

- **Versionar catálogos** e manter histórico
- **Unidades consistentes** (dB, km, mm, N)
- **Testes:** unidade, integração (rotas), e2e (cabo→rota→orçamento)

---

# 🧪 Workflow de Manutenção Programada

### Funcionalidades
- Agendamento de janelas de manutenção
- Notificação de entidades afetadas
- Supressão de alertas durante janela

### API
- `POST /api/v1/maintenance/windows`

---

# 📋 Catálogo de Runbooks

### Exemplo
**"Falha em OLT":**
1. Verificar energia/alimentação
2. Contatar fornecedor
3. Escalar para NOC

### ChatOps Integration
- Slack/Teams
- Templates de comunicação pré-definidos

---

# ❓ Questões em Aberto (Para Amadurecer)

## 1) Nomenclatura Oficial
**Questão:** Conectores, portas, bandejas, cores — qual catálogo adotar como referência primária?

**Opções:**
- (A) Catálogo fixo
- (B) **Catálogos configuráveis** (**recomendado**)

**Recomendação:**
- `ActiveCatalog` por categoria: `fiber_color`, `connector`, `port_name_policy`, `tray_schema`

**MVP:**
- `Catalog`, `CatalogItem`, `ActiveCatalog` + _presets_ TIA/IEC/BR

**Métricas:**
- % conformidade
- _Switch_ de catálogo < 5 min

---

## 2) Persistência Geoespacial (PostGIS)
**Questão:** Ativar PostGIS desde o início ou quando densidade aumentar?

**Recomendação:**
- Ativar agora (SRID 4326, GiST, `ST_Length/DWithin/Intersects`)

**Métricas:**
- p95 "cabo mais próximo" ≤ 120 ms
- p95 rota ≤ 200 ms

---

## 3) ZTP — Vendors e Canais
**Questão:** Quais OLTs/vendors serão alvo? Canais preferenciais (NETCONF/SSH/OMCI)?

**Iniciais:**
- Huawei, ZTE, Fiberhome

**Canais:**
- NETCONF/YANG (preferencial)
- Fallback SSH/Telnet
- OMCI via OLT

**MVP:**
- Driver Huawei + webhook CRM → `provision_client`

**Métricas:**
- Sucesso p95 ≥ 98%
- p95 ≤ 90 s
- Rollback ≤ 30 s

---

## 4) CRM/OSS Integration
**Questão:** Endpoints e limites de rate/latência? Escopo de dados financeiros?

**Contratos:**
- `/clients`, `/addresses`, `/services`, `/devices`, `/events`
- Webhooks bidirecionais

**Resiliência:**
- Retries com backoff+jitter
- Circuit Breaker
- DLQ
- Idempotency-Key

**Métricas:**
- Falhas/1k ≤ 0,5%
- Webhook ≤ 3 s

---

## 5) RCA — Thresholds & Janelas
**Questão:** Valores iniciais e tuning automático por tecnologia (backbone x GPON)?

**Valores Iniciais:**
- Backbone: 5–10 min
- Acesso: 2–5 min
- Borda: 2–3 min
- Rearm: 3–10 min

**Métricas:**
- p95 correlação ≤ 20 s
- Redução de ruído ≥ 70%

---

# 📊 Métricas de Sucesso (KPIs Planejados)

| Módulo | Métrica | Meta |
|---|---|---|
| RCA | Tempo p/ causa raiz | < 30s p95 |
| ZTP | Sucesso de provisionamento | ≥ 98% |
| Inventário | Atualização após comissionamento | < 5s |
| DWDM | Cálculo de orçamento óptico | < 2s |
| API | Latência p95 | < 200ms |
| Health Check | Disponibilidade | ≥ 99.9% |
| CRM Integration | Falhas por 1k eventos | ≤ 0.5% |
| Catálogo | Switch de padrão | < 5 min |
| PostGIS | Query "cabo mais próximo" | ≤ 120ms p95 |

---

# 🔧 Configuração Operacional (Exemplo YAML)

```yaml
# Configuração futura (feature flags e thresholds)
rca:
  backbone:
    window_s: 600
    rearm_s: 600
  access:
    window_s: 180
    rearm_s: 300
  border:
    window_s: 150
    rearm_s: 180

ztp:
  drivers_enabled:
    - huawei
    - zte
  dry_run: true
  timeout_s: 90

catalogs:
  active:
    fiber_color: TIA-598-C
    connector: IEC-61754
    port_naming: ITU-T
    tray_schema: ANSI-TIA-568

features:
  rca_engine: true
  predictive_analysis: true
  ztp_auto_provisioning: true
  chaos_engineering: false
  postgis_enabled: true
  dwdm_module: false

limits:
  crm_rate_per_min: 60
  timeout_ms: 4000
  max_concurrent_provisions: 10

monitoring:
  prometheus:
    scrape_interval_s: 15
  health_check_interval_s: 30
```

---

## 🎯 Roadmap de Implementação

**⚠️ Todas as fases devem seguir `doc/process/PLANO_PILOTO_PADRAO.md` (8 dias)**

| Fase | Funcionalidades | Prioridade | Status | Esforço |
|------|----------------|-----------|--------|---------|
| **7** | ✅ Spatial Radius Search + PostGIS | Alta | **COMPLETO** | 8 dias |
| **8** | OpenAPI Documentation (Swagger/Redoc) | Alta | ⏳ NEXT | 8 dias |
| **9** | PostGIS Full Integration (spatial queries otimizadas) | Alta | 📋 PLANNED | 8 dias |
| **10** | Catálogos (FiberSpec, CableSpec) + Orçamento Óptico | Alta | 📋 PLANNED | 8 dias |
| **11** | Asset Management Detalhado (Racks, Templates) | Média | 📋 PLANNED | 8 dias |
| **12** | RCA Engine (MVP com JSONB) | Média | 📋 PLANNED | 8 dias |
| **13** | ZTP - Driver Huawei + Webhook CRM | Média | 📋 PLANNED | 8 dias |
| **14** | GPON Diagnostics + Comparative Analysis | Média | 📋 PLANNED | 8 dias |
| **15** | DWDM Inventory (Models + CRUD) | Baixa | 📋 PLANNED | 8 dias |
| **16** | Predictive Analysis (Optical Signal) | Baixa | 📋 PLANNED | 8 dias |
| **17** | Chaos Engineering Add-on | Baixa | 📋 PLANNED | 8 dias |
| **18** | Financial Impact Analysis Add-on | Baixa | 📋 PLANNED | 8 dias |

**Legenda:**
- ✅ **COMPLETO** - Em produção (ou em rollout gradual)
- ⏳ **NEXT** - Próxima implementação
- 📋 **PLANNED** - No backlog

**Progresso Geral:**
- Concluídas: 1/12 fases (8%)
- Em andamento: 1/12 (Phase 7 - monitoring 24h)
- Planejadas: 10/12 (83%)

**Estimativa Total:** 96 dias (12 fases × 8 dias) = ~4.8 meses (assumindo 1 fase por semana)

---

## 🤖 AI Agent Instructions (Copilot)

**CRITICAL:** Ao implementar qualquer feature deste roadmap:

1. ✅ **SEMPRE seguir** `doc/process/PLANO_PILOTO_PADRAO.md` (8 dias)
2. ✅ **SEMPRE criar** especificação técnica antes do código (Day 1)
3. ✅ **SEMPRE implementar** monitoring (Prometheus + Grafana) desde Day 1
4. ✅ **SEMPRE fazer** rollout gradual (10% → 25% → 50% → 100%)
5. ✅ **SEMPRE documentar** lessons learned ao finalizar fase
6. ✅ **SEMPRE atualizar** este arquivo (`FUTURE_APPS.md`) com status
7. ✅ **SEMPRE marcar** cada etapa como completa no plano piloto

**Workflow Padrão:**
```
User: "Implementar [Feature do Roadmap]"

Agent:
1. Verificar se feature está no roadmap (este arquivo)
2. Criar branch: feature/phase-X-<name>
3. Seguir doc/process/PLANO_PILOTO_PADRAO.md (Days 1-8)
4. Atualizar FUTURE_APPS.md com status ✅/⏳/📋
5. Atualizar PLANO_PILOTO_PADRAO.md com lessons learned
6. Commit tudo junto
```

**Template de Resposta:**
```markdown
Vou implementar [Feature X] do roadmap seguindo o Plano Piloto Padrão.

**Fase:** Phase X
**Duração:** 8 dias
**Referência:** doc/process/PLANO_PILOTO_PADRAO.md

## Day 1: Planning & Architecture
Criando especificação técnica...
[Create doc/architecture/PHASE_X_SPEC.md]

Especificação criada. Revisar antes de prosseguir para Day 2?
```

---

**Fim do Roadmap de Funcionalidades Futuras**

> **Notas Importantes:**
> 1. Este documento é atualizado após cada fase completada
> 2. Para implementar nova feature, siga `doc/process/PLANO_PILOTO_PADRAO.md`
> 3. Para status detalhado de Phase 7, ver `doc/operations/PHASE7_DAY7_VERIFICATION.md`
> 4. Para arquitetura geral do projeto, consultar `doc/architecture/MODULES.md`

---

*Última Atualização: 2025-11-19*  
*Versão: 2.0*  
*Fases Completadas: 1/12 (8%)*  
*Próxima Fase: Phase 8 - OpenAPI Documentation*
