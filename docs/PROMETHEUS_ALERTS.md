# Alertas Prometheus para Celery

Este documento fornece exemplos de regras de alerta (Prometheus Alert Manager) e queries PromQL úteis para monitorar a saúde dos workers Celery via métricas exportadas pelo endpoint `/celery/status`.

## Métricas Disponíveis

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| `celery_worker_available` | Gauge | 1 se worker respondeu ao ping, 0 caso contrário |
| `celery_status_latency_ms` | Gauge | Latência da última verificação em ms |
| `celery_worker_count` | Gauge | Número de workers ativos |
| `celery_active_tasks` | Gauge | Total de tarefas em execução |
| `celery_scheduled_tasks` | Gauge | Total de tarefas agendadas (ETA) |
| `celery_reserved_tasks` | Gauge | Total de tarefas reservadas |

## Regras de Alerta Recomendadas

### 1. Worker Indisponível

Alerta quando nenhum worker está respondendo por mais de 3 minutos.

```yaml
# prometheus/alerts/celery.yml
groups:
  - name: celery_alerts
    interval: 30s
    rules:
      - alert: CeleryWorkerDown
        expr: celery_worker_available == 0
        for: 3m
        labels:
          severity: critical
          component: celery
        annotations:
          summary: "Celery worker indisponível"
          description: "Nenhum worker Celery respondeu ao ping nos últimos 3 minutos. Verificar logs e status dos containers."
```

**Ações recomendadas:**
- Verificar logs: `docker compose logs celery --tail=100`
- Reiniciar workers: `docker compose restart celery beat`
- Validar conectividade com Redis: `docker compose logs redis`

---

### 2. Latência Alta

Alerta quando a latência de verificação excede 5 segundos consistentemente.

```yaml
      - alert: CeleryHighLatency
        expr: celery_status_latency_ms > 5000
        for: 5m
        labels:
          severity: warning
          component: celery
        annotations:
          summary: "Latência elevada no Celery"
          description: "Latência de verificação do Celery está acima de 5s por mais de 5 minutos. Possível sobrecarga ou lentidão no broker."
```

**Ações recomendadas:**
- Verificar uso de CPU/memória dos workers: `docker stats celery`
- Avaliar backlog de tarefas: acessar `/celery/status` e verificar `active_tasks`
- Considerar aumentar concorrência: ajustar `-c` no `docker-compose.yml`

---

### 3. Nenhum Worker Ativo

Alerta se contagem de workers cai para zero.

```yaml
      - alert: CeleryNoWorkersActive
        expr: celery_worker_count == 0
        for: 2m
        labels:
          severity: critical
          component: celery
        annotations:
          summary: "Nenhum worker Celery ativo"
          description: "Contagem de workers Celery está em zero. Sistema não processará tarefas assíncronas."
```

**Ações recomendadas:**
- Verificar se containers estão rodando: `docker compose ps`
- Reiniciar serviços Celery: `docker compose up -d celery beat`
- Verificar erros de inicialização: `docker compose logs celery`

---

### 4. Acúmulo de Tarefas Ativas

Alerta quando muitas tarefas estão em execução simultaneamente (possível indicador de travamento).

```yaml
      - alert: CeleryHighActiveTasks
        expr: celery_active_tasks > 50
        for: 10m
        labels:
          severity: warning
          component: celery
        annotations:
          summary: "Alto número de tarefas ativas no Celery"
          description: "{{ $value }} tarefas ativas há mais de 10 minutos. Possível gargalo ou travamento."
```

**Ações recomendadas:**
- Verificar tarefas lentas via `/celery/status`
- Inspecionar logs para tarefas travadas: `docker compose logs celery | grep ERROR`
- Considerar aumentar timeout de tarefas (`CELERY_TASK_TIME_LIMIT`)

---

### 5. Crescimento de Tarefas Agendadas

Alerta se backlog de tarefas agendadas cresce rapidamente (indica workers não dando conta).

```yaml
      - alert: CeleryScheduledTasksGrowing
        expr: rate(celery_scheduled_tasks[5m]) > 5
        for: 5m
        labels:
          severity: warning
          component: celery
        annotations:
          summary: "Backlog de tarefas agendadas crescendo"
          description: "Tarefas agendadas crescendo a uma taxa de {{ $value }}/min. Workers podem estar sobrecarregados."
```

**Ações recomendadas:**
- Escalar workers horizontalmente: `docker compose up -d --scale celery=3`
- Revisar taxa de chegada de tarefas
- Ajustar prefetch multiplier (`CELERY_WORKER_PREFETCH_MULTIPLIER`)

---

## Queries PromQL Úteis

### Taxa de Disponibilidade (últimas 24h)

```promql
avg_over_time(celery_worker_available[24h]) * 100
```

### Latência Média (última hora)

```promql
avg_over_time(celery_status_latency_ms[1h])
```

### Pico de Tarefas Ativas (últimas 6h)

```promql
max_over_time(celery_active_tasks[6h])
```

### Taxa de Crescimento de Tarefas Reservadas

```promql
rate(celery_reserved_tasks[5m])
```

### Contagem de Workers Ativos ao Longo do Tempo

```promql
celery_worker_count
```

---

## Dashboards Grafana

### Painel Básico de Monitoramento

```json
{
  "dashboard": {
    "title": "Celery Monitoring",
    "panels": [
      {
        "title": "Worker Availability",
        "targets": [{"expr": "celery_worker_available"}],
        "type": "stat"
      },
      {
        "title": "Active Tasks",
        "targets": [{"expr": "celery_active_tasks"}],
        "type": "graph"
      },
      {
        "title": "Latency (ms)",
        "targets": [{"expr": "celery_status_latency_ms"}],
        "type": "graph"
      },
      {
        "title": "Worker Count",
        "targets": [{"expr": "celery_worker_count"}],
        "type": "stat"
      }
    ]
  }
}
```

### Importação Rápida

1. Acesse Grafana → Dashboards → Import
2. Cole o JSON acima ou crie manualmente
3. Selecione datasource Prometheus
4. Ajuste intervalos conforme necessário

---

## Configuração do Alert Manager

### Roteamento de Alertas

```yaml
# alertmanager.yml
route:
  group_by: ['component']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'celery-team'
  routes:
    - match:
        severity: critical
        component: celery
      receiver: 'celery-oncall'
      continue: true

receivers:
  - name: 'celery-team'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK'
        channel: '#celery-alerts'
        title: 'Celery Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'celery-oncall'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

---

## Integração com CI/CD

### Validação Pré-Deploy

Antes de fazer deploy, valide se métricas estão operacionais:

```bash
#!/bin/bash
# scripts/validate_metrics.sh

METRICS_URL="http://localhost:8000/metrics"
REQUIRED_METRICS=(
  "celery_worker_available"
  "celery_status_latency_ms"
  "celery_worker_count"
)

for metric in "${REQUIRED_METRICS[@]}"; do
  if ! curl -s "$METRICS_URL" | grep -q "$metric"; then
    echo "❌ Métrica ausente: $metric"
    exit 1
  fi
done

echo "✅ Todas as métricas Celery presentes"
```

### Health Check Kubernetes

```yaml
# k8s/deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mapsprovefiber
spec:
  template:
    spec:
      containers:
      - name: web
        livenessProbe:
          httpGet:
            path: /live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /celery/status
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
```

---

## Troubleshooting

### Métricas Não Atualizando

**Sintoma:** Valores congelados ou ausentes.

**Verificação:**
```bash
# Validar se task periódica está rodando
docker compose exec celery celery -A core inspect scheduled

# Verificar logs do beat
docker compose logs beat --tail=50 | grep update_celery_metrics_task
```

**Solução:**
```bash
# Reiniciar beat
docker compose restart beat

# Validar variável de ambiente
docker compose exec web python -c "import os; print(os.getenv('CELERY_METRICS_ENABLED', 'true'))"
```

---

### Alertas Falsos Positivos

**Sintoma:** Alertas disparando frequentemente sem causa real.

**Ajustes:**
- Aumentar `for` duration nas regras (de 3m para 5m)
- Ajustar thresholds (ex.: latência de 5s para 8s)
- Revisar timeouts no endpoint (`CELERY_STATUS_TIMEOUT`)

---

## Boas Práticas

1. **Ambientes separados**: Use labels Prometheus para diferenciar `environment=prod` vs `environment=staging`
2. **Retention**: Configure retenção de métricas (mínimo 30 dias para análise de tendências)
3. **Agregação**: Use `sum()`, `avg()`, `max()` em queries para múltiplos workers
4. **Runbooks**: Documente procedimentos de resposta para cada alerta
5. **Testes**: Simule falhas (parar workers) para validar alertas antes de produção

---

## Referências

- [Prometheus Alerting](https://prometheus.io/docs/alerting/latest/overview/)
- [Alert Manager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [Celery Monitoring Guide](https://docs.celeryproject.org/en/stable/userguide/monitoring.html)

---

**Última atualização:** 26 de outubro de 2025  
**Autor:** Sistema de desenvolvimento automatizado
