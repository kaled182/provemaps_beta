# Endpoint de Status do Celery

## Visão Geral

O endpoint `/celery/status` fornece informações em tempo real sobre o estado dos workers Celery e estatísticas das filas de tarefas.

## Informações Técnicas

- **URL**: `/celery/status`
- **Método**: `GET`
- **Autenticação**: Não requerida (pode ser adicionada posteriormente)
- **View**: `core.views_health.celery_status`
- **Timeout padrão**: 3 segundos (configurável via `CELERY_STATUS_TIMEOUT`)

## Configuração

```bash
# Opcional: ajustar timeout no .env
CELERY_STATUS_TIMEOUT=5  # segundos
```

## Comportamento

O endpoint dispara a task `get_queue_stats` definida em `core/celery.py` e aguarda o resultado. Se nenhum worker estiver disponível ou o timeout for atingido, retorna status `degraded` (HTTP 503).

### Mecanismo de Resiliência (Fallback)

Após ajustes recentes, o endpoint implementa uma estratégia em duas fases para reduzir falsos negativos:

1. `ping.delay()` (task leve) é executado primeiro com um timeout curto (`CELERY_PING_TIMEOUT`, padrão 2s). Se responder `"pong"`, o worker é considerado **available**.
2. Só então tenta coletar estatísticas detalhadas via `get_queue_stats.delay()` usando `CELERY_STATUS_TIMEOUT` (padrão 3s, recomendável 5–8s em produção). Se esta segunda etapa falhar por timeout/erro, o status global é `degraded` porém `worker.available` permanece `true`.

Benefícios:
- Evita marcar todo o cluster como indisponível quando apenas a inspeção de filas está lenta.
- Gera sinal mais útil para escalonadores: `503` indica degradação (talvez sobrecarga), mas diferencia cenário sem workers vs. atraso em métricas.

Variáveis suportadas:
```bash
CELERY_STATUS_TIMEOUT=6      # Timeout da coleta de estatísticas
CELERY_PING_TIMEOUT=2        # Timeout do ping leve
```

Exemplo de resposta degradada com ping OK e estatísticas com timeout:
```json
{
  "timestamp": 1730000000.123,
  "latency_ms": 3044.52,
  "status": "degraded",
  "worker": {
    "available": true,
    "error": "The operation timed out.",
    "stats": null
  }
}
```

Exemplo de resposta saudável:
```json
{
  "timestamp": 1730000101.456,
  "latency_ms": 4021.11,
  "status": "ok",
  "worker": {
    "available": true,
    "error": null,
    "stats": {
      "workers": ["celery@hostname"],
      "active_tasks": {"celery@hostname": []},
      "scheduled_tasks": {"celery@hostname": []},
      "reserved_tasks": {"celery@hostname": []},
      "timestamp": 1730000101.0
    }
  }
}
```

### Fluxo de Execução

1. Cliente acessa `/celery/status`
2. View dispara task `get_queue_stats.delay()`
3. Aguarda resultado com timeout configurado
4. Retorna JSON com status e estatísticas

## Respostas

### Cenário 1: Worker Ativo e Operacional

**HTTP Status**: `200 OK`

```json
{
  "timestamp": 1730000000.123,
  "latency_ms": 45.67,
  "status": "ok",
  "worker": {
    "available": true,
    "error": null,
    "stats": {
      "workers": ["celery@hostname"],
      "active_tasks": {
        "celery@hostname": []
      },
      "scheduled_tasks": {
        "celery@hostname": []
      },
      "reserved_tasks": {
        "celery@hostname": []
      },
      "timestamp": 1730000000.0
    }
  }
}
```

### Cenário 2: Worker Indisponível

**HTTP Status**: `503 Service Unavailable`

```json
{
  "timestamp": 1730000000.123,
  "latency_ms": 3005.45,
  "status": "degraded",
  "worker": {
    "available": false,
    "error": "Timeout: task did not complete within 3.0 seconds",
    "stats": null
  }
}
```

### Cenário 3: Erro de Importação

**HTTP Status**: `503 Service Unavailable`

```json
{
  "timestamp": 1730000000.123,
  "latency_ms": 1.23,
  "status": "degraded",
  "worker": {
    "available": false,
    "error": "ImportError: No module named 'celery'",
    "stats": null
  }
}
```

## Campos da Resposta

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `timestamp` | float | Unix timestamp da requisição |
| `latency_ms` | float | Tempo de resposta em milissegundos |
| `status` | string | `"ok"` ou `"degraded"` |
| `worker.available` | boolean | Worker respondeu dentro do timeout |
| `worker.error` | string\|null | Mensagem de erro (se houver) |
| `worker.stats` | object\|null | Estatísticas detalhadas das filas |

### Estrutura de `worker.stats`

Quando disponível, contém:

- **workers**: Lista de workers ativos
- **active_tasks**: Tarefas em execução por worker
- **scheduled_tasks**: Tarefas agendadas (ETA)
- **reserved_tasks**: Tarefas reservadas mas não iniciadas
- **timestamp**: Timestamp da coleta

## Uso em Monitoramento

### Prometheus/Grafana

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'celery-status'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['app:8000']
```

#### Métricas Exportadas

O endpoint `/celery/status` atualiza métricas Prometheus (Gauges) definidas em `core/metrics_celery.py`. A coleta das métricas é exposta normalmente pelo endpoint global `/metrics` (via `prometheus_client` / `django-prometheus`). A atualização ocorre a cada requisição ao `/celery/status`. Para scraping direto das métricas use somente `/metrics`.

Variável de controle:

```bash
CELERY_METRICS_ENABLED=true  # desabilite com 'false' para não atualizar gauges
```

Gauges disponíveis:

| Nome | Descrição |
|------|-----------|
| `celery_worker_available` | 1 se o ping ao worker respondeu, 0 caso contrário |
| `celery_status_latency_ms` | Latência da última chamada a `/celery/status` em ms |
| `celery_worker_count` | Quantidade de workers respondendo à inspeção |
| `celery_active_tasks` | Soma de tarefas ativas em todos os workers |
| `celery_scheduled_tasks` | Soma de tarefas agendadas (ETA) |
| `celery_reserved_tasks` | Soma de tarefas reservadas |

Exemplo de scrape parcial (`/metrics`):

```
celery_worker_available 1
celery_status_latency_ms 87.12
celery_worker_count 1
celery_active_tasks 0
celery_scheduled_tasks 0
celery_reserved_tasks 0
```

Boas práticas:
- Combine com dashboard Grafana: painel de disponibilidade + latência.
- Adicione alertas: `celery_worker_available == 0` por 3m ou `increase(celery_status_latency_ms[5m]) > 5000`.
- Para reduzir sobrecarga, cachear resposta do endpoint ou usar uma task periódica futura para atualizar métricas sem chamadas externas.

### Healthcheck Docker

```yaml
# docker-compose.yml
healthcheck:
  test: ["CMD-SHELL", "python -c \"import urllib.request; exit(0 if urllib.request.urlopen('http://localhost:8000/celery/status').getcode() == 200 else 1)\""]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Script de Monitoramento

```bash
#!/bin/bash
# check_celery.sh

RESPONSE=$(curl -s -w "%{http_code}" http://localhost:8000/celery/status)
HTTP_CODE="${RESPONSE: -3}"
BODY="${RESPONSE:0:-3}"

if [ "$HTTP_CODE" -eq 200 ]; then
  echo "✓ Celery OK"
  exit 0
else
  echo "✗ Celery Degraded: $BODY"
  exit 1
fi
```

### Script de Monitoramento (PowerShell)

Para ambientes Windows / execução via Agendador:
```powershell
# check_celery.ps1
$Url = "http://localhost:8000/celery/status"
$Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 8
$Json = $Response.Content | ConvertFrom-Json
if ($Response.StatusCode -eq 200 -and $Json.status -eq 'ok') {
  Write-Host "✓ Celery OK (latency=$($Json.latency_ms)ms workers=$($Json.worker.stats.workers.Count))"
  exit 0
} elseif ($Json.worker.available -eq $true) {
  Write-Host "⚠ Celery Degradado (worker ativo, stats indisponíveis)"; exit 1
} else {
  Write-Host "✗ Celery Indisponível (sem worker)"; exit 2
}
```

## Testes

Teste unitário localizado em `tests/test_celery_status.py`.

```bash
# Executar teste
pytest tests/test_celery_status.py -v

# Com cobertura
pytest tests/test_celery_status.py --cov=core.views_health --cov-report=term
```

## Management Command

Complementarmente, existe o comando `celery_health` para verificações manuais:

```bash
# Teste básico
python manage.py celery_health

# Com saída JSON formatada
python manage.py celery_health --pretty

# Timeout customizado
python manage.py celery_health --timeout 10
```

## Troubleshooting

### Problema: Sempre retorna 503

**Causa**: Workers não estão rodando ou não conseguem se conectar ao broker.

**Solução**:
```bash
# Verificar Redis
docker compose logs redis

# Verificar worker Celery
docker compose logs celery

# Testar conectividade manual
docker compose exec celery celery -A core.celery_app inspect ping
```

### Problema: Timeout muito curto

**Causa**: Workers lentos ou sobrecarregados.

**Solução**:
```bash
# Aumentar timeout (em .env ou environment)
CELERY_STATUS_TIMEOUT=10

# Reiniciar serviços
docker compose restart web
```

### Problema: ImportError em produção

**Causa**: Dependências não instaladas no container.

**Solução**:
```bash
# Rebuild com dependências
docker compose build --no-cache web celery beat
docker compose up -d
```

## Segurança

Por padrão, o endpoint não requer autenticação. Para ambientes de produção, considere:

1. **Adicionar decorador de autenticação**:
```python
from django.contrib.auth.decorators import login_required

@login_required
def celery_status(request: HttpRequest):
    # ...
```

2. **Rate limiting**:
```python
from django.views.decorators.cache import cache_page

@cache_page(10)  # cache por 10 segundos
def celery_status(request: HttpRequest):
    # ...
```

3. **IP whitelist** (via middleware ou nginx/proxy reverso)

## Integração com Outros Endpoints

Este endpoint complementa os health checks existentes:

- `/healthz` - Comprehensive health (DB, cache, storage)
- `/ready` - Readiness probe (DB connectivity)
- `/live` - Liveness probe (processo vivo)
- `/celery/status` - Status específico dos workers Celery

## Changelog

### 2025-10-26
- ✨ Endpoint inicial implementado
- ✅ Testes unitários adicionados
- 📝 Documentação criada
- 📊 Métricas Prometheus integradas ao endpoint (`update_metrics`)
- ⚡ Cache de 5s adicionado ao endpoint para reduzir latência
- 🔄 Task periódica do beat (`update_celery_metrics_task`) para atualizar métricas a cada 30s
- 🚨 Guia de alertas Prometheus criado (`docs/PROMETHEUS_ALERTS.md`)

---

**Autor**: Sistema de desenvolvimento automatizado  
**Última atualização**: 26 de outubro de 2025