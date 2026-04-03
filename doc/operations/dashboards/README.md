# Grafana Dashboards - MapsProveFiber

Dashboards Prometheus + Grafana para monitoramento de performance e saúde do sistema.

## 📊 Dashboards Disponíveis

### 1. Inventory API Metrics
**Arquivo**: [inventory-api-metrics.json](inventory-api-metrics.json)  
**UID**: `inventory-api-metrics`

Monitora performance dos ViewSets principais (FiberCable, Port, Device):

**Painéis**:
- Request Rate por endpoint (GET/POST/PUT/DELETE)
- Latency p95/p99 por operação
- Error rate (gauge)
- Cache hit rate
- Inventory object counts (cables, devices, ports, sites)

**Métricas usadas**:
- `inventory_fiber_cable_requests_total`
- `inventory_fiber_cable_latency_seconds`
- `inventory_port_requests_total`
- `inventory_port_latency_seconds`
- `inventory_device_requests_total`
- `inventory_device_latency_seconds`
- `inventory_cache_hits_total`
- `inventory_cache_misses_total`
- `inventory_total_*` (gauges)

**Alertas sugeridos**:
- Latency p95 > 1s
- Error rate > 5%
- Cache hit rate < 70%

---

### 2. Celery Tasks Metrics
**Arquivo**: [celery-tasks-metrics.json](celery-tasks-metrics.json)  
**UID**: `celery-tasks-metrics`

Monitora operações de negócio e tasks assíncronas:

**Painéis**:
- Business operations duration (cable_split, fusion, optical_fetch)
- Operation count por status (success, validation_error, error)
- Optical data fetch rate e error rate
- Database query duration e rate por model/operation
- Error rate gauges

**Métricas usadas**:
- `inventory_cable_split_operations_total`
- `inventory_cable_split_duration_seconds`
- `inventory_fusion_operations_total`
- `inventory_fusion_duration_seconds`
- `inventory_optical_data_fetches_total`
- `inventory_optical_data_latency_seconds`
- `inventory_db_query_count_total`
- `inventory_db_query_duration_seconds`

**Alertas sugeridos**:
- Cable split duration p95 > 30s
- Optical fetch timeout rate > 15%
- DB query duration p95 > 1s

---

## 🚀 Instalação

### Método 1: Via Grafana UI (Manual)

1. Acesse Grafana: `http://localhost:3000` (ou seu servidor)
2. Login: `admin` / `admin` (altere senha no primeiro login)
3. Navegue: **Configuration** → **Dashboards** → **Import**
4. **Upload JSON file**: Selecione `inventory-api-metrics.json` ou `celery-tasks-metrics.json`
5. **Select a Prometheus data source**: Escolha sua datasource Prometheus
6. **Import**

### Método 2: Via API (Automático)

```bash
# Set Grafana API key (ou use user:pass)
export GRAFANA_URL="http://localhost:3000"
export GRAFANA_TOKEN="your-api-key-here"

# Import Inventory API dashboard
curl -X POST "$GRAFANA_URL/api/dashboards/db" \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d @inventory-api-metrics.json

# Import Celery Tasks dashboard
curl -X POST "$GRAFANA_URL/api/dashboards/db" \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d @celery-tasks-metrics.json
```

### Método 3: Provisioning (IaC)

Adicione ao `grafana/provisioning/dashboards/`:

```yaml
# grafana/provisioning/dashboards/mapsprovefiber.yaml
apiVersion: 1

providers:
  - name: 'MapsProveFiber'
    orgId: 1
    folder: 'MapsProveFiber'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards/mapsprovefiber
```

Copie JSONs para: `/etc/grafana/provisioning/dashboards/mapsprovefiber/`

---

## ⚙️ Configuração Prometheus

### Scraping Endpoint

Adicione ao `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'mapsprovefiber'
    static_configs:
      - targets: ['web:8000']  # Django app
    metrics_path: '/metrics/'
    scrape_interval: 15s
    scrape_timeout: 10s
```

### Validação

```bash
# Verificar se métricas estão disponíveis
curl http://localhost:8000/metrics/ | grep inventory_

# Verificar Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="mapsprovefiber")'
```

---

## 📈 Uso dos Dashboards

### Inventory API Dashboard

**Use cases**:
1. **Debugging performance** - Identifique endpoints lentos via latency p95/p99
2. **Capacity planning** - Observe request rate crescente para escalar workers
3. **Cache tuning** - Ajuste TTL baseado em cache hit rate
4. **Error investigation** - Correlacione error spikes com deploys/migrations

**Variáveis disponíveis**: Nenhuma (dashboards fixos por design)

**Timerange recomendado**: Last 6 hours (padrão), ajuste conforme necessidade

---

### Celery Tasks Dashboard

**Use cases**:
1. **Monitor operações críticas** - Cable split, fusion, optical fetch
2. **Detect bottlenecks** - Identifique operações lentas via duration histograms
3. **Database performance** - Monitore query duration por model
4. **Operational health** - Observe error rates de tasks periódicos

**Alertas práticos**:
- Cable split error rate > 10% → Investigar validação de dados
- Optical fetch timeout rate > 20% → Zabbix API lento ou inacessível
- DB query duration > 2s → Índices faltando ou queries N+1

---

## 🔍 Troubleshooting

### Problema: Métricas não aparecem

**Causas possíveis**:
1. Prometheus não está scraping `/metrics/`
   - Solução: Verifique `prometheus.yml` e reinicie Prometheus
2. `PROMETHEUS_METRICS_ENABLED=false` no Django
   - Solução: Set `PROMETHEUS_METRICS_ENABLED=true` em `.env`
3. `prometheus_client` não instalado
   - Solução: `pip install prometheus-client==0.19.0`

**Debug**:
```bash
# Teste endpoint diretamente
curl http://localhost:8000/metrics/ | head -n 50

# Verifique logs Django
docker compose logs web | grep -i prometheus

# Verifique Prometheus targets
http://localhost:9090/targets
```

---

### Problema: Dashboard vazio

**Causas possíveis**:
1. Nenhum dado ainda (sistema novo)
   - Solução: Aguarde 15-30s para primeiro scrape
2. Datasource incorreta
   - Solução: Edit dashboard → Settings → Variables → Select correct Prometheus DS
3. Timerange muito antigo
   - Solução: Ajuste timerange para "Last 6 hours" ou "Last 1 hour"

---

### Problema: Latency muito alta (p95 > 5s)

**Diagnóstico**:
```python
# Django shell
from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as queries:
    # Simule operação lenta
    FiberCable.objects.filter(path__distance_lte=(point, D(km=10)))

# Analise queries
for q in queries:
    if float(q['time']) > 0.1:
        print(f"SLOW: {q['time']}s - {q['sql'][:200]}")
```

**Soluções comuns**:
- N+1 queries → Use `select_related()` / `prefetch_related()`
- Índices faltando → Crie migration com `Meta.indexes`
- Cache disabled → Habilite Redis cache

---

## 📚 Recursos Adicionais

**Documentação**:
- [Prometheus Metrics Reference](../../analysis/SPRINT3_METRICS_ANALYSIS.md)
- [CHANGELOG v2.1.0](../../releases/v2.1.0/CHANGELOG.md)
- [Inventory Metrics Code](../../../backend/inventory/metrics.py)
- [Inventory Decorators](../../../backend/inventory/decorators.py)

**Grafana Docs**:
- [Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- [Prometheus Query](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/best-practices-for-creating-dashboards/)

**Support**:
- Issues: https://github.com/kaled182/provemaps_beta/issues
- Docs: `doc/roadmap/LEGACY_CODE_REMOVAL_SCHEDULE.md`

---

**Criado em**: 04 Fevereiro 2026  
**Última atualização**: 04 Fevereiro 2026  
**Versão**: v2.1.0  
**Autor**: GitHub Copilot (Claude Sonnet 4.5)
