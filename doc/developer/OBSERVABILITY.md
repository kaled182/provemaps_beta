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
- Structured logs at `logs/application.log`
- Slow query tracing

## Tips
- Use Prometheus and Grafana for dashboards (see `doc/reference/grafana/README.md`)
- Review [`../reference/prometheus_static_version.md`](../reference/prometheus_static_version.md) for the custom metrics exported by the app
