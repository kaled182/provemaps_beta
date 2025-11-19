# Plano Piloto Padrão — MapsProveFiber

> **Objetivo:** Metodologia padronizada para implementação de novas funcionalidades  
> **Status:** Template Ativo  
> **Versão:** 1.0  
> **Data:** 2025-11-19  
> **Baseado em:** Phase 7 - Spatial Radius Search (Caso de Sucesso)

---

## 🎯 Visão Geral

Este documento define o processo padrão para implementação de novas funcionalidades no MapsProveFiber, desde o planejamento inicial até o rollout em produção. Todas as novas implementações devem seguir este plano piloto.

### Princípios Fundamentais

1. **Desenvolvimento Incremental:** Funcionalidades entregues em fases de 1-2 semanas
2. **Qualidade First:** Testes automatizados antes de merge
3. **Observabilidade Obrigatória:** Métricas + logs + alertas desde Day 1
4. **Rollout Gradual:** Canary deployment (10% → 25% → 50% → 100%)
5. **Documentação Contínua:** Docs atualizados junto com código

---

## 📋 Estrutura do Plano Piloto (8 Dias)

### **Day 1: Planning & Architecture**
**Duração:** 1 dia  
**Deliverables:**
- [ ] Documento de especificação técnica (`PHASE_X_SPEC.md`)
- [ ] Diagrama de arquitetura (componentes, fluxo de dados)
- [ ] Definição de APIs (endpoints, payloads, status codes)
- [ ] Identificação de riscos e mitigações
- [ ] Estimativa de esforço por dia

**Exemplo (Phase 7):**
```
✅ PHASE7_SPEC.md criado (500+ linhas)
✅ Endpoints definidos: GET /api/v1/inventory/sites/radius
✅ Riscos identificados: Performance em 10k+ sites, cache invalidation
```

---

### **Day 2: Data Layer & Models**
**Duração:** 1 dia  
**Deliverables:**
- [ ] Modelos Django criados/atualizados
- [ ] Migrações aplicadas (com rollback testado)
- [ ] Índices de banco de dados otimizados
- [ ] Campos espaciais configurados (se aplicável)
- [ ] Testes unitários de modelos (>90% coverage)

**Exemplo (Phase 7):**
```
✅ Modelos existentes validados (Site com lat/lng)
✅ Índices criados: idx_site_location (lat, lng)
✅ PostGIS configurado: LineString para rotas
✅ Testes: test_site_coordinates_validation.py
```

**Checklist Técnico:**
- [ ] Migrations reversíveis (`reverse_code` definido)
- [ ] Índices B-tree/GiST apropriados
- [ ] Constraints de integridade (FKs, unique, not null)
- [ ] Default values para novos campos
- [ ] Documentação de schema no modelo

---

### **Day 3: Business Logic & Services**
**Duração:** 1 dia  
**Deliverables:**
- [ ] Camada de serviços implementada (`<app>/services/` ou `<app>/usecases/`)
- [ ] Lógica de negócio isolada de views/serializers
- [ ] DTOs/dataclasses tipados (Python 3.10+)
- [ ] Validações de entrada robustas
- [ ] Testes de integração (mock de dependências externas)

**Exemplo (Phase 7):**
```
✅ inventory/services/radius_search.py
✅ Função: calculate_distance_km(lat1, lng1, lat2, lng2)
✅ Validação: radius_km entre 0.1 e 100
✅ DTO: RadiusSearchResult (sites, total_count, query_info)
✅ Testes: test_radius_search_logic.py (15 test cases)
```

**Padrões de Código:**
```python
# ✅ BOM: Serviço tipado e testável
from dataclasses import dataclass
from typing import List

@dataclass
class RadiusSearchResult:
    sites: List[Site]
    total_count: int
    center_lat: float
    center_lng: float
    radius_km: float

def search_sites_by_radius(lat: float, lng: float, radius_km: float) -> RadiusSearchResult:
    # Validação
    if not (0.1 <= radius_km <= 100):
        raise ValueError("radius_km must be between 0.1 and 100")
    
    # Lógica
    sites = Site.objects.filter(...)
    
    return RadiusSearchResult(...)

# ❌ RUIM: Lógica misturada na view
def api_view(request):
    lat = float(request.GET['lat'])  # Sem validação!
    sites = Site.objects.all()  # Sem filtro espacial!
    return JsonResponse({'sites': list(sites)})  # Sem tipagem!
```

---

### **Day 4: API Endpoints & Serialization**
**Duração:** 1 dia  
**Deliverables:**
- [ ] Endpoints REST implementados (DRF ViewSets/APIViews)
- [ ] Serializers com validação completa
- [ ] Paginação configurada (LimitOffsetPagination)
- [ ] Rate limiting definido (se necessário)
- [ ] Documentação OpenAPI/Swagger inline

**Exemplo (Phase 7):**
```
✅ GET /api/v1/inventory/sites/radius
✅ Query params: lat, lng, radius_km (validados)
✅ Paginação: limit/offset (default 100, max 1000)
✅ Response: {sites: [...], total_count: N, query: {...}}
✅ Swagger: @extend_schema decorators
```

**Checklist de API:**
- [ ] Versionamento explícito (`/api/v1/`)
- [ ] Status codes corretos (200/400/404/500)
- [ ] Error responses padronizados (`{"error": "...", "code": "..."}`)
- [ ] CORS configurado (se necessário)
- [ ] Autenticação/autorização (RBAC)
- [ ] Request/response examples na doc

---

### **Day 5: Caching & Performance**
**Duração:** 1 dia  
**Deliverables:**
- [ ] Estratégia de cache definida (SWR, TTL, invalidation)
- [ ] Cache implementado (Redis/locmem)
- [ ] Invalidação automática em mutations
- [ ] Testes de performance (load testing)
- [ ] Benchmarks documentados (p50/p95/p99)

**Exemplo (Phase 7):**
```
✅ SWR Cache: fresh_ttl=30s, stale_ttl=60s
✅ Cache key: radius_search:{md5(lat,lng,radius)}
✅ Invalidação: signals em Site.save()/delete()
✅ Celery task: refresh_radius_cache.delay()
✅ Benchmarks: p95 <200ms (10k sites)
```

**Padrões de Cache:**
```python
# ✅ BOM: SWR pattern com invalidação
from maps_view.cache_swr import SWRCache

def get_sites_cached(lat, lng, radius_km):
    cache_key = f"radius:{lat}:{lng}:{radius_km}"
    cache = SWRCache(key=cache_key, fresh_ttl=30, stale_ttl=60)
    
    data = cache.get()
    if data is not None:
        return data
    
    # Compute fresh data
    result = search_sites_by_radius(lat, lng, radius_km)
    cache.set(result)
    
    # Trigger async refresh if stale
    if cache.is_stale():
        refresh_radius_cache.delay(lat, lng, radius_km)
    
    return result

# Invalidação
@receiver(post_save, sender=Site)
def invalidate_radius_cache(sender, instance, **kwargs):
    cache.delete_pattern("radius:*")
```

---

### **Day 6: Testing & Quality Assurance**
**Duração:** 1 dia  
**Deliverables:**
- [ ] Testes unitários (>90% coverage)
- [ ] Testes de integração (API + DB + Cache)
- [ ] Testes end-to-end (cenários reais)
- [ ] Testes de performance (load/stress)
- [ ] Relatório de cobertura (`htmlcov/`)

**Exemplo (Phase 7):**
```
✅ 14/15 testes passing (93%)
✅ Coverage: 94% (backend/inventory/)
✅ Performance: 100 concurrent users, p95 <200ms
✅ E2E: Playwright tests (search + map interaction)
```

**Categorias de Testes:**

**1. Testes Unitários** (`tests/unit/`)
```python
# test_radius_calculation.py
def test_haversine_distance():
    # Porto Alegre → São Paulo: ~858 km
    distance = calculate_distance_km(-30.03, -51.23, -23.55, -46.63)
    assert 850 < distance < 870

def test_invalid_radius_raises():
    with pytest.raises(ValueError):
        search_sites_by_radius(0, 0, radius_km=200)  # > 100km
```

**2. Testes de Integração** (`tests/integration/`)
```python
# test_radius_api.py
@pytest.mark.django_db
def test_radius_search_with_cache(client):
    # Create test data
    Site.objects.create(name="Site A", lat=-29.68, lng=-51.13)
    
    # First request (cache miss)
    response = client.get('/api/v1/inventory/sites/radius?lat=-29.68&lng=-51.13&radius_km=10')
    assert response.status_code == 200
    assert response.json()['total_count'] == 1
    
    # Second request (cache hit)
    response = client.get('/api/v1/inventory/sites/radius?lat=-29.68&lng=-51.13&radius_km=10')
    assert response.status_code == 200  # Served from cache
```

**3. Testes E2E** (`tests/e2e/`)
```javascript
// test_radius_search_flow.spec.js
test('search sites by radius on map', async ({ page }) => {
  await page.goto('/dashboard');
  await page.fill('#search-lat', '-29.68');
  await page.fill('#search-lng', '-51.13');
  await page.fill('#search-radius', '10');
  await page.click('#search-button');
  
  await expect(page.locator('.site-marker')).toHaveCount(5);
});
```

**4. Testes de Performance** (`tests/performance/`)
```python
# test_radius_performance.py
@pytest.mark.slow
def test_radius_search_performance():
    # Setup: 10k sites
    Site.objects.bulk_create([...] * 10000)
    
    # Benchmark
    start = time.time()
    result = search_sites_by_radius(-29.68, -51.13, 10)
    duration_ms = (time.time() - start) * 1000
    
    assert duration_ms < 200  # p95 target
    assert result.total_count > 0
```

---

### **Day 7: Monitoring & Observability**
**Duração:** 1 dia  
**Deliverables:**
- [ ] Prometheus metrics exportadas
- [ ] Grafana dashboard criado (6-8 painéis)
- [ ] Alert rules configurados (critical/warning/info)
- [ ] Logs estruturados (JSON format)
- [ ] Deployment plan documentado

**Exemplo (Phase 7):**
```
✅ Prometheus alerts: radius_search.yml (16 alerts)
✅ Grafana dashboard: phase7_radius_search.json (8 panels)
✅ Métricas: request rate, latency, cache hit rate, errors
✅ Deployment plan: PHASE7_DEPLOYMENT_PLAN.md (2500 lines)
```

**Métricas Obrigatórias:**

**1. RED Metrics** (Rate, Errors, Duration)
```python
# Django view with metrics
from prometheus_client import Counter, Histogram

radius_search_requests = Counter(
    'radius_search_requests_total',
    'Total radius search requests',
    ['status']
)

radius_search_latency = Histogram(
    'radius_search_latency_seconds',
    'Radius search latency',
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
)

@radius_search_latency.time()
def search_sites_by_radius(...):
    try:
        result = ...
        radius_search_requests.labels(status='success').inc()
        return result
    except Exception as e:
        radius_search_requests.labels(status='error').inc()
        raise
```

**2. Cache Metrics**
```python
cache_operations = Counter(
    'radius_cache_operations_total',
    'Cache operations',
    ['operation', 'result']  # operation: get/set/delete, result: hit/miss/stale
)

cache_latency = Histogram(
    'radius_cache_latency_seconds',
    'Cache operation latency',
    ['operation']
)
```

**3. Business Metrics**
```python
sites_found = Histogram(
    'radius_search_sites_found',
    'Number of sites found per search',
    buckets=[0, 1, 5, 10, 50, 100, 500]
)
```

**Alert Rules (Prometheus):**

**Critical (P1)** - Página imediata
```yaml
- alert: RadiusSearchHighErrorRate
  expr: rate(radius_search_requests_total{status="error"}[5m]) > 0.01
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Radius search error rate > 1%"
```

**Warning (P2)** - Investigar em 1h
```yaml
- alert: RadiusSearchHighLatency
  expr: histogram_quantile(0.95, radius_search_latency_seconds) > 0.5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "p95 latency > 500ms"
```

**Info (P3)** - Monitorar tendência
```yaml
- alert: RadiusSearchLowCacheHitRate
  expr: rate(radius_cache_operations_total{result="hit"}[30m]) / rate(radius_cache_operations_total{operation="get"}[30m]) < 0.5
  for: 30m
  labels:
    severity: info
  annotations:
    summary: "Cache hit rate < 50%"
```

**Grafana Dashboard (8 Painéis Padrão):**

1. **Request Rate** (area chart) - Requests/sec por status
2. **API Latency** (graph) - p50/p95/p99 percentiles
3. **Error Rate** (gauge) - % de erros (threshold: <1%)
4. **Cache Hit Rate** (gauge) - % de hits (target: >70%)
5. **Cache Operations** (donut) - MISS/HIT/STALE distribution
6. **Celery Tasks** (graph) - Success/failure por task
7. **Response Size** (histogram) - Sites found per query
8. **Top Errors** (table) - Error types e counts

---

### **Day 8: Production Rollout**
**Duração:** 1 dia + monitoramento contínuo  
**Deliverables:**
- [ ] Phase 1: 10% rollout (24h monitoring)
- [ ] Phase 2: 25% rollout (48h monitoring)
- [ ] Phase 3: 50% rollout (48h monitoring)
- [ ] Phase 4: 100% rollout (1 week monitoring)
- [ ] Runbook de troubleshooting
- [ ] Post-mortem report (se houver incidentes)

**Exemplo (Phase 7):**
```
✅ Phase 1: VUE_DASHBOARD_ROLLOUT_PERCENTAGE=10 (deployed)
✅ Monitoring stack: Prometheus + Grafana (operational)
✅ Success criteria defined: hit rate >70%, p95 <200ms, error <0.1%
⏳ 24h monitoring period (in progress)
⏳ Phases 2-4 pending
```

**Rollout Checklist (Por Fase):**

**Pre-Deployment:**
- [ ] Feature flag configurado (`.env` + `database/runtime.env`)
- [ ] Monitoring stack validado (Prometheus targets UP)
- [ ] Rollback plan documentado
- [ ] On-call schedule definido

**Deployment:**
```powershell
# Phase 1: 10%
# 1. Update environment
Set-Content -Path .env -Value "VUE_DASHBOARD_ROLLOUT_PERCENTAGE=10"
Set-Content -Path database/runtime.env -Value "VUE_DASHBOARD_ROLLOUT_PERCENTAGE=10"

# 2. Restart (NOT docker compose restart - use down/up to reload env_file)
cd docker
docker compose down
docker compose up -d

# 3. Verify
docker compose exec web env | findstr VUE
Invoke-WebRequest -Uri "http://localhost:8000/ready" -UseBasicParsing
```

**Post-Deployment (Monitoramento):**

**Intervalo de Verificação:**
- Phase 1 (10%): A cada 6h por 24h
- Phase 2-3 (25%/50%): A cada 12h por 48h
- Phase 4 (100%): Diário por 1 semana

**Checklist de Verificação (6h/12h/24h):**
1. **Grafana Dashboard** (http://localhost:3000)
   - [ ] Cache hit rate >70% (ou >30% durante warmup)
   - [ ] API p95 latency <200ms
   - [ ] Error rate <0.1%
   - [ ] Request rate estável (sem spikes anormais)
   - [ ] Redis memory <1GB

2. **Prometheus Alerts** (http://localhost:9090/alerts)
   - [ ] 0 alertas critical ativos
   - [ ] ≤2 alertas warning (aceitável)

3. **Application Logs**
   ```powershell
   docker compose logs --tail=100 web | Select-String -Pattern "ERROR|CRITICAL"
   docker compose logs --tail=100 celery | Select-String -Pattern "FAILED"
   ```
   - [ ] 0 ERRORs relacionados à nova feature
   - [ ] 0 stack traces de exceptions

4. **User Feedback**
   - [ ] 0 tickets de suporte relacionados
   - [ ] NPS/CSAT mantido ou melhorado

**Critérios de Go/No-Go (Próxima Fase):**

**GO** (Avançar para próxima fase):
- ✅ Todos os checkpoints passando
- ✅ 0 critical alerts
- ✅ Métricas dentro dos SLOs
- ✅ 0 rollbacks necessários

**NO-GO** (Pausar rollout):
- ❌ Qualquer critical alert ativo
- ❌ Error rate >1%
- ❌ P95 latency >500ms
- ❌ Cache down por >15min
- ❌ User complaints >5/dia

**Rollback Procedure:**
```powershell
# 1. Revert feature flag
Set-Content -Path .env -Value "VUE_DASHBOARD_ROLLOUT_PERCENTAGE=0"
Set-Content -Path database/runtime.env -Value "VUE_DASHBOARD_ROLLOUT_PERCENTAGE=0"

# 2. Restart containers
cd docker
docker compose down
docker compose up -d

# 3. Verify rollback
docker compose exec web env | findstr VUE  # Should show 0

# 4. Monitor for 30min
# Check Grafana: errors should drop to 0
# Check Prometheus: alerts should clear

# 5. Post-mortem
# Document: What happened? Why? How to prevent?
```

---

## 🎯 Success Criteria Template

### Métricas de Qualidade

| Métrica | Target | Método de Medição |
|---------|--------|-------------------|
| Test Coverage | >90% | `pytest --cov` |
| API p95 Latency | <200ms | Prometheus histogram |
| Error Rate | <0.1% | `rate(requests{status="error"}[5m])` |
| Cache Hit Rate | >70% | `cache_hits / cache_gets` |
| Uptime | >99.9% | `/ready` endpoint |

### Métricas de Negócio

| Métrica | Target | Método de Medição |
|---------|--------|-------------------|
| Adoption Rate | >50% após 30d | Feature flag analytics |
| User Satisfaction | NPS >8 | Surveys |
| Support Tickets | <5/semana | Ticket system |
| Revenue Impact | 0% churn | CRM data |

---

## 📂 Estrutura de Arquivos Padrão

```
doc/
├── operations/
│   ├── PHASE_X_DEPLOYMENT_PLAN.md       # Plano completo (2000+ lines)
│   ├── PHASE_X_DAYX_VERIFICATION.md     # Checklist de verificação
│   └── MONITORING_SETUP.md              # Setup de observabilidade
├── architecture/
│   ├── PHASE_X_SPEC.md                  # Especificação técnica
│   └── DIAGRAMS.md                      # Diagramas (Mermaid/PlantUML)
└── troubleshooting/
    └── PHASE_X_RUNBOOK.md               # Runbook operacional

backend/
├── <app>/
│   ├── models.py                        # Django models
│   ├── services/                        # Business logic
│   │   └── <feature>_service.py
│   ├── api/                             # REST endpoints
│   │   ├── serializers.py
│   │   └── viewsets.py
│   ├── cache/                           # Caching layer
│   │   └── <feature>_cache.py
│   ├── tasks.py                         # Celery tasks
│   └── tests/
│       ├── test_models.py
│       ├── test_services.py
│       ├── test_api.py
│       └── test_cache.py
└── tests/
    ├── integration/
    ├── e2e/
    └── performance/

docker/
├── prometheus/
│   ├── prometheus.yml
│   └── alerts/
│       └── <feature>.yml                # 10-20 alert rules
└── grafana/
    └── dashboards/
        └── <feature>.json               # 6-8 panels

scripts/
└── deploy_<feature>.ps1                 # Deployment automation
```

---

## 🔄 Workflow de Desenvolvimento

### 1. Branch Strategy (Git Flow)

```bash
# Criar branch de feature
git checkout -b feature/phase-X-<feature-name>

# Commits frequentes (1-3x por dia)
git commit -m "feat(phase-X): implement <component>"

# Merge para develop após Day 8
git checkout develop
git merge feature/phase-X-<feature-name>

# Tag de release
git tag -a v2.X.0 -m "Phase X: <Feature Name>"
```

**Commit Message Convention:**
```
<type>(phase-X): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Documentação
- `test`: Testes
- `perf`: Performance
- `refactor`: Refatoração
- `chore`: Manutenção

**Exemplos:**
```
feat(phase-7): add spatial radius search endpoint
fix(phase-7): correct Haversine distance calculation
docs(phase-7): add deployment plan and monitoring setup
test(phase-7): add integration tests for radius API
perf(phase-7): implement SWR cache for radius searches
```

### 2. Pull Request Template

```markdown
## Phase X - <Feature Name> (Day Y)

### Summary
Brief description of changes (1-2 sentences).

### Changes
- [ ] Models updated/created
- [ ] Services implemented
- [ ] API endpoints added
- [ ] Tests passing (X/Y)
- [ ] Documentation updated

### Testing
- Unit tests: XX% coverage
- Integration tests: Y passing
- Performance: p95 <Xms

### Rollout Plan
- Phase 1: 10% (24h)
- Phase 2: 25% (48h)
- Phase 3: 50% (48h)
- Phase 4: 100% (1w)

### Rollback Plan
Revert feature flag to 0%, restart containers.

### Reviewers
@team-lead @backend-engineer @devops-engineer
```

### 3. Code Review Checklist

**Revisor deve verificar:**
- [ ] Código segue padrões do projeto (Black, Ruff, isort)
- [ ] Testes cobrem casos principais e edge cases
- [ ] Documentação atualizada (docstrings, README, specs)
- [ ] Migrações reversíveis e testadas
- [ ] Sem secrets hardcoded (usar env vars)
- [ ] Logs estruturados (JSON format)
- [ ] Métricas Prometheus implementadas
- [ ] Alert rules configurados
- [ ] Performance aceitável (benchmarks documentados)
- [ ] Segurança: SQL injection, XSS, CSRF prevenidos

---

## 🚨 Red Flags - Quando NÃO Avançar

### Bloqueadores Técnicos
- ❌ Coverage de testes <80%
- ❌ Migrations sem rollback testado
- ❌ Performance p95 >1s (sem justificativa)
- ❌ Memory leaks detectados
- ❌ N+1 queries não resolvidos
- ❌ Secrets hardcoded no código

### Bloqueadores de Qualidade
- ❌ Linting errors não resolvidos
- ❌ Type hints faltando em funções públicas
- ❌ Documentação incompleta (API sem examples)
- ❌ Logs sem context (user_id, request_id, etc.)

### Bloqueadores de Observabilidade
- ❌ Métricas Prometheus não implementadas
- ❌ Alert rules não configurados
- ❌ Grafana dashboard não criado
- ❌ Runbook de troubleshooting faltando

### Bloqueadores de Processo
- ❌ Deployment plan não revisado pelo time
- ❌ Rollback procedure não testado
- ❌ On-call não definido para rollout
- ❌ Stakeholders não notificados

---

## 📊 Métricas de Sucesso do Processo

### Eficiência de Desenvolvimento
- **Velocidade:** 8 dias por fase (planning → production)
- **Qualidade:** <5% de rollbacks por bugs
- **Previsibilidade:** ±20% de estimativa de esforço

### Qualidade de Código
- **Coverage:** >90% em novas features
- **Debt Ratio:** <5% (Technical Debt / Total Code)
- **Bug Escape Rate:** <2 bugs críticos por release

### Operacional
- **MTTR (Mean Time To Recover):** <30min
- **MTTD (Mean Time To Detect):** <5min
- **Change Failure Rate:** <5%
- **Deployment Frequency:** ≥1x por semana

---

## 🎓 Lessons Learned (Phase 7)

### O Que Funcionou Bem ✅
1. **Planejamento detalhado:** PHASE7_DEPLOYMENT_PLAN.md (2500 lines) evitou surpresas
2. **Rollout gradual:** 10% → 25% → 50% → 100% permitiu detectar issues cedo
3. **SWR Cache:** fresh_ttl=30s, stale_ttl=60s equilibrou freshness e performance
4. **Monitoring first:** Prometheus + Grafana desde Day 1 deu visibilidade total
5. **Automated deployment:** deploy_monitoring.ps1 reduziu erros manuais
6. **Comprehensive docs:** 1670+ lines de documentação facilitaram handoff

### Desafios e Soluções 🔧
1. **Problema:** Prometheus não conseguia scrape Django (Content-Type HTML)
   - **Causa:** Rota `/metrics/` capturada por view errada
   - **Solução:** Usar `/metrics/metrics` (django-prometheus default)
   - **Prevenção:** Testar endpoints de métricas em ambiente local antes de deploy

2. **Problema:** Deploy script com emojis causava parse error no PowerShell
   - **Causa:** PowerShell não interpreta unicode emoji characters corretamente
   - **Solução:** Substituir emojis por labels ASCII (`[OK]`, `[ERROR]`, etc.)
   - **Prevenção:** Evitar emojis em scripts de automação

3. **Problema:** `docker compose restart` não recarregava environment variables
   - **Causa:** `env_file` só é lido no `up`, não no `restart`
   - **Solução:** Usar `docker compose down && docker compose up -d`
   - **Prevenção:** Documentar comportamento de env vars no runbook

### Não Repetir ❌
1. **Assumir que `/metrics/` é endpoint padrão** → Sempre verificar django-prometheus docs
2. **Usar emojis em scripts PowerShell** → ASCII-only para compatibilidade
3. **Esquecer de testar rollback** → Sempre fazer dry-run de rollback antes de deploy
4. **Ignoror path navigation em scripts** → Sempre usar absolute paths ou validar $PSScriptRoot

---

## 🔮 Próximas Implementações (Backlog)

### Prioridade Alta (Q1 2026)
- [ ] **Phase 8:** OpenAPI Documentation (Day 8 do Phase 7)
- [ ] **Phase 9:** PostGIS Full Integration (spatial queries otimizadas)
- [ ] **Phase 10:** Fiber Cable Management (catálogo de fibras + orçamento óptico)

### Prioridade Média (Q2 2026)
- [ ] **Phase 11:** Asset Management Detalhado (racks, templates, auditoria)
- [ ] **Phase 12:** RCA Engine (Root Cause Analysis com grafo de dependências)
- [ ] **Phase 13:** GPON Diagnostics (potência óptica, keep-alive)

### Prioridade Baixa (Q3-Q4 2026)
- [ ] **Phase 14:** ZTP Auto-Provisioning (Huawei/ZTE drivers)
- [ ] **Phase 15:** DWDM Inventory (L0 layer, channel grid)
- [ ] **Phase 16:** Predictive Analysis (ML para previsão de falhas)

**Nota:** Todas as fases seguirão este plano piloto padrão.

---

## 📝 Template de Documentação (Por Fase)

### 1. Specification Document (`PHASE_X_SPEC.md`)
```markdown
# Phase X - <Feature Name> Specification

## Overview
- **Objetivo:** <1-2 sentences>
- **Stakeholders:** <quem usa>
- **Prioridade:** High/Medium/Low
- **Esforço:** X dias

## Requirements
### Functional
- RF1: <requirement>
- RF2: <requirement>

### Non-Functional
- RNF1: Performance p95 <Xms
- RNF2: Availability >99.9%

## Architecture
### Components
- Component A: <description>
- Component B: <description>

### Data Flow
[Mermaid diagram]

## API Design
### Endpoints
- `GET /api/v1/...`

## Database Schema
### Models
- ModelName (fields, indexes)

## Caching Strategy
- Cache key pattern
- TTL values
- Invalidation logic

## Risks & Mitigations
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
```

### 2. Deployment Plan (`PHASE_X_DEPLOYMENT_PLAN.md`)
```markdown
# Phase X - <Feature Name> Deployment Plan

## Rollout Strategy
### Phase 1: 10% (24h)
- Feature flag: 10%
- Success criteria: ...
- Rollback trigger: ...

### Phase 2-4: 25% → 50% → 100%
[Same structure]

## Monitoring
### Metrics
- Metric 1: <PromQL query>
- Metric 2: <PromQL query>

### Alerts
- Critical: <conditions>
- Warning: <conditions>

### Dashboards
- Panel 1: <description>
- Panel 2: <description>

## Rollback Plan
1. Revert feature flag
2. Restart containers
3. Verify metrics return to baseline

## Smoke Tests
- [ ] Test 1
- [ ] Test 2
```

### 3. Verification Checklist (`PHASE_X_DAYX_VERIFICATION.md`)
```markdown
# Phase X Day Y - Verification Checklist

## Deployment Summary
- Date: YYYY-MM-DD
- Status: DEPLOYED/FAILED
- Rollout: Phase N (X%)

## Automated Checks
- [ ] Docker containers healthy
- [ ] Prometheus targets UP
- [ ] Tests passing (X/Y)
- [ ] Coverage >90%

## Manual Verification
- [ ] Access URL 1
- [ ] Access URL 2
- [ ] Generate test traffic

## Success Criteria
- [ ] Metric 1 within target
- [ ] Metric 2 within target

## Next Steps
- [ ] Step 1
- [ ] Step 2
```

---

## 🤖 AI Agent Instructions (Copilot)

### Regras para IA ao Implementar Novas Features

**SEMPRE:**
1. ✅ Seguir este plano piloto (8 dias)
2. ✅ Criar documentação ANTES do código (Day 1)
3. ✅ Escrever testes JUNTO com o código (não depois)
4. ✅ Implementar métricas Prometheus desde Day 1
5. ✅ Configurar alerts críticos antes de deploy
6. ✅ Testar rollback antes de Phase 1
7. ✅ Atualizar `PLANO_PILOTO_PADRAO.md` com lessons learned
8. ✅ Marcar cada etapa como completa no plano

**NUNCA:**
1. ❌ Pular etapas (ex: ir direto para código sem spec)
2. ❌ Deploy sem monitoring configurado
3. ❌ Merge sem testes passing
4. ❌ Rollout 100% sem fases graduais
5. ❌ Ignorar code review feedback
6. ❌ Hardcodar valores (usar env vars)
7. ❌ Esquecer de documentar decisões arquiteturais

**Quando Usuário Pedir Nova Feature:**

```
User: "Implementar [Feature X]"

Agent:
1. Criar branch: feature/phase-X-<name>
2. Criar doc/architecture/PHASE_X_SPEC.md
3. Pedir aprovação do spec antes de codificar
4. Seguir Days 2-7 do plano piloto
5. Criar PR com template padrão
6. Aguardar code review
7. Deploy Phase 1 (10%)
8. Monitorar 24h
9. Reportar status
10. Atualizar PLANO_PILOTO_PADRAO.md com lessons learned
```

**Template de Resposta da IA:**
```markdown
Vou implementar [Feature X] seguindo o Plano Piloto Padrão (8 dias).

## Day 1: Planning & Architecture
Criando especificação técnica...
[Create PHASE_X_SPEC.md]

Especificação criada. Revisar antes de prosseguir?
- Endpoints: [list]
- Models: [list]
- Risks: [list]

**Aguardando aprovação para Day 2.**
```

---

## 🎯 KPIs do Processo (Acompanhamento Mensal)

| KPI | Target | Medição |
|-----|--------|---------|
| **Velocity** | 2 fases/mês | Features completadas em 8 dias |
| **Quality** | <5% rollbacks | Rollbacks / Deploys |
| **Test Coverage** | >90% | pytest --cov |
| **Documentation** | 100% specs | Specs criados / Features |
| **Monitoring** | 100% dashboards | Dashboards / Features |
| **Uptime** | >99.9% | Prometheus uptime |
| **MTTR** | <30min | Incident resolution time |
| **Code Review Time** | <24h | PR approval time |

**Revisão Trimestral:**
- Revisar KPIs
- Atualizar plano piloto com lessons learned
- Ajustar targets se necessário
- Identificar bottlenecks

---

## 📚 Referências e Templates

### Documentação Padrão
- **Architecture Decision Records (ADR):** `doc/architecture/ADR-XXX.md`
- **Runbooks:** `doc/operations/RUNBOOK_<feature>.md`
- **Troubleshooting:** `doc/troubleshooting/<feature>_ISSUES.md`

### Ferramentas Recomendadas
- **Planejamento:** GitHub Projects, Linear, Jira
- **Diagramas:** Mermaid (inline em Markdown), PlantUML, Excalidraw
- **Testes:** pytest, Playwright, Locust
- **Observabilidade:** Prometheus, Grafana, Sentry
- **CI/CD:** GitHub Actions, GitLab CI

### Links Úteis
- [Django Best Practices](https://docs.djangoproject.com/en/stable/topics/best-practices/)
- [Prometheus Alerting Best Practices](https://prometheus.io/docs/practices/alerting/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [SRE Book - Google](https://sre.google/books/)

---

## ✅ Checklist de Atualização Deste Documento

**Quando Atualizar:**
- ✅ Após cada fase completada (adicionar lessons learned)
- ✅ Quando processo for ajustado (novo step, novo template)
- ✅ Quando KPIs mudarem (targets, métricas)
- ✅ Trimestral (revisão completa)

**Como Atualizar:**
1. Adicionar nova seção em "Lessons Learned"
2. Atualizar métricas de sucesso
3. Revisar templates se necessário
4. Commit: `docs: update plano piloto with phase-X learnings`
5. Notificar time sobre mudanças

---

**Fim do Plano Piloto Padrão**

> **Nota:** Este documento é vivo e deve ser atualizado continuamente. Toda implementação deve referenciar e seguir este plano.

---

*Última Atualização: 2025-11-19*  
*Versão: 1.0*  
*Autor: GitHub Copilot (AI Agent) + Time de Desenvolvimento*
