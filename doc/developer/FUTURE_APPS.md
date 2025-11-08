# Roadmap de Funcionalidades Futuras — MapsProveFiber

> **Status:** Planejamento e especificação técnica  
> **Versão:** Draft 1.0  
> **Data:** 2025-11-08

Este documento detalha os planos de expansão do MapsProveFiber além do core atual (v2.0), incluindo novos módulos, apps Django e funcionalidades avançadas organizadas por edições comerciais.

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

# 🎯 Roadmap de Implementação

| Fase | Funcionalidades | Prioridade | Esforço Estimado |
|------|----------------|-----------|------------------|
| **6** | Catálogos (FiberSpec, CableSpec) + Orçamento Óptico | Alta | 3 semanas |
| **7** | PostGIS Integration + Queries Geoespaciais | Alta | 2 semanas |
| **8** | RCA Engine (MVP com JSONB) | Média | 4 semanas |
| **9** | ZTP - Driver Huawei + Webhook CRM | Média | 5 semanas |
| **10** | GPON Diagnostics + Comparative Analysis | Média | 3 semanas |
| **11** | Asset Management (Racks, Templates) | Baixa | 3 semanas |
| **12** | DWDM Inventory (Models + CRUD) | Baixa | 4 semanas |
| **13** | Predictive Analysis (Optical Signal) | Baixa | 5 semanas |
| **14** | Chaos Engineering Add-on | Baixa | 6 semanas |
| **15** | Financial Impact Analysis Add-on | Baixa | 4 semanas |

---

**Fim do Roadmap de Funcionalidades Futuras**

> **Nota:** Este documento será atualizado conforme cada fase for planejada e priorizada. Para status atual do projeto, consultar `REFATORAR.md`.
