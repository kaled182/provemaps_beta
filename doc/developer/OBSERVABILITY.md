# Observability and Health Checks - MapsProveFiber

## Health endpoints
- `/healthz`: overall status (DB, cache, storage, metrics)
- `/ready`: readiness probe (database)
- `/live`: liveness probe (process is alive)
- `/celery/status`: Celery worker status

## Prometheus metrics
- Endpoint: `/metrics/`
- Custom metrics: asset versioning, worker status

## Logs
- Structured logs on the console (`docker compose logs -f web`); optional rotating file via `ENABLE_FILE_LOGGING=true` (non-debug only, path in `LOG_FILE`, default `/var/log/django/app.log`)
- Slow query tracing

## Tips
- Use Prometheus and Grafana for dashboards (see [`../operations/dashboards/README.md`](../operations/dashboards/README.md))
- Review [`../operations/MONITORING.md`](../operations/MONITORING.md) for the custom metrics exported by the app (the older `prometheus_static_version.md` note is archived: [`../archive/2025-historico/prometheus_static_version.md`](../archive/2025-historico/prometheus_static_version.md), histórico)
