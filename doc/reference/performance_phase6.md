# Phase 6 - Observability and Monitoring

## 1. Prometheus metrics
- Installed `django-prometheus` and added it to `INSTALLED_APPS` and `MIDDLEWARE`.
- Exposed a GET `/metrics/` endpoint in `core/urls.py`, publishing Django, Redis, and MariaDB metrics.
- Quick check:
  ```powershell
  curl.exe http://localhost:8000/metrics/ |
    Select-Object -First 20
  ```
  Wire this endpoint into Prometheus/Grafana for latency, cache hit, and Celery task dashboards.

## 2. Structured logging
- `logs/` directory created automatically; a `RotatingFileHandler` writes `application.log` (5 MB, five backups).
- Primary loggers (Django, Celery, `zabbix_api`, etc.) send output to both console and file.
- Tail in real time with `Get-Content logs/application.log -Wait`.

## 3. Slow query inspector
- Management command: `& D:\provemaps_beta\venv\Scripts\python.exe manage.py show_slow_queries --path "C:\Program Files\MariaDB 12.0\data\<host>-slow.log" --limit 10`.
- Omit `--path` if `MYSQL_SLOW_LOG_PATH` is set.
- Output includes `Query_time`, `Lock_time`, examined rows, and the full SQL statement for review or EXPLAIN.

## 4. Suggested next steps
- Connect `/metrics/` to Prometheus/Grafana and configure alerts (high latency, idle workers, log growth).
- Automate slow-log collection (cron + `show_slow_queries`, or ingest via Promtail/Loki).
- Evaluate integrating an APM solution (Sentry, New Relic) to trace Celery and HTTP requests end-to-end.
