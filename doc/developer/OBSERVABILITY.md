# Observabilidade e Health Checks — MapsProveFiber

## Endpoints de Saúde
- `/healthz`: status geral (DB, cache, storage, métricas)
- `/ready`: readiness probe (DB)
- `/live`: liveness probe (processo ativo)
- `/celery/status`: status dos workers Celery

## Métricas Prometheus
- Endpoint: `/metrics/`
- Métricas customizadas: versionamento de assets, status de workers

## Logs
- Logs estruturados em `logs/application.log`
- Rastreamento de queries lentas

## Dicas
- Use Prometheus e Grafana para dashboards
- Consulte [`../reference/prometheus_static_version.md`](../reference/prometheus_static_version.md) para detalhes de métricas customizadas
