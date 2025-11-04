# Operations Checklist - Django Maps

Quick reference to manage the production or staging environment.

## Required services
- **Django / ASGI** (`& D:\provemaps_beta\venv\Scripts\python.exe manage.py runserver` for dev, Daphne or Gunicorn+Uvicorn in production).
- **MariaDB/MySQL** (`mapspro_db`) - configure backups via `mysqldump`.
- **Redis** - broker and result backend for Celery and Channels.
- **Channels layer** - set `CHANNEL_LAYER_URL` to the production Redis instance (in-memory fallback only for development).
- **Celery worker and beat** (`& D:\provemaps_beta\venv\Scripts\celery.exe -A core worker -l info` and `& D:\provemaps_beta\venv\Scripts\celery.exe -A core beat -l info`) for async tasks and real-time updates. On Windows add `--pool=solo`.

## Monitoring
- **Prometheus `/metrics/metrics`** - exposes roughly 200 metrics for Django, Celery, Redis, and the database.
- **Health checks** - `/healthz` (full), `/ready` (readiness), `/live` (liveness).
- **HTML dashboard** - `/maps_view/metrics/` for quick searches.
- **Logs** - `logs/application.log` managed by `RotatingFileHandler` (five files of 5 MB each).
- **Slow queries** - `& D:\provemaps_beta\venv\Scripts\python.exe manage.py show_slow_queries --limit 10` using `MYSQL_SLOW_LOG_PATH` or a manual `--path`.

### Health check endpoints

| Endpoint | Purpose | Status code |
|----------|---------|-------------|
| `/healthz` | Full check (DB, cache, storage, system metrics) | 200 (ok), 503 (degraded) |
| `/ready` | Readiness probe (database connectivity) | 200 (ready), 503 (not ready) |
| `/live` | Liveness probe (Django process running) | 200 (alive) |

**Environment variables:**

```powershell
# Strict mode (default): any failure returns 503
$env:HEALTHCHECK_STRICT = 'true'

# Ignore cache failures (useful for dev without Redis)
$env:HEALTHCHECK_IGNORE_CACHE = 'false'

# Database timeout in seconds (Unix/Linux, default 5s)
$env:HEALTHCHECK_DB_TIMEOUT = '5'

# Disk space threshold (default 1 GB)
$env:HEALTHCHECK_DISK_THRESHOLD_GB = '1.0'

# Optional checks
$env:HEALTHCHECK_STORAGE = 'true'
$env:HEALTHCHECK_SYSTEM_METRICS = 'false'  # CPU and memory in the payload
$env:HEALTHCHECK_DEBUG = 'false'           # force logging even when ok
```

**Kubernetes or Docker usage:**

```yaml
livenessProbe:
  httpGet:
    path: /live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

**Development without Redis:**

```powershell
$env:HEALTHCHECK_IGNORE_CACHE = 'true'
& D:\provemaps_beta\venv\Scripts\python.exe manage.py runserver
```

## Main workflows
- **Initial setup**: visit `/setup_app/first_time/` (requires `FERNET_KEY`) then run `Quick Actions -> Configure System` for recurring routines.
- **Import KML**: use the "Import KML" button in the route builder. The modal supports single-port monitoring.
- **Save manual route**: draw on the map, click "Save", and fill device/port data. The dropdown resets after each creation.

## Deployment checklist
1. Copy `.env.example` to `.env`, then generate `FERNET_KEY` with `& D:\provemaps_beta\venv\Scripts\python.exe manage.py generate_fernet_key --write`.
2. Run `& D:\provemaps_beta\venv\Scripts\python.exe manage.py migrate` and `& D:\provemaps_beta\venv\Scripts\python.exe manage.py collectstatic`.
3. Create a superuser (`& D:\provemaps_beta\venv\Scripts\python.exe manage.py createsuperuser`).
4. Configure `DEBUG=False`, `ALLOWED_HOSTS`, and TLS/CSRF settings.
5. Start Celery worker and beat (required for scheduled and real-time tasks).
6. Integrate Prometheus and Grafana with `/metrics/`.
7. Review backup routines (`mysqldump`, copy of `.env`, and the package produced by `scripts/package-release.ps1`).

## Maintenance routines
- Review `/metrics/` or the Grafana dashboard daily.
- Rotate and collect `logs/application.log` (local rotation already configured).
- Run `& D:\provemaps_beta\venv\Scripts\python.exe manage.py show_slow_queries` after database maintenance windows.
- Update dependencies with `& D:\provemaps_beta\venv\Scripts\python.exe -m pip install -r requirements.txt --upgrade` in a controlled environment.

## Quick references
- `README.md` - project overview and onboarding.
- `API_DOCUMENTATION.md` - legacy endpoints.
- `./performance_phase*.md` - performance and observability evolution.
- `./performance_phase6.md` - current observability highlights.

Keep this checklist current to operate Django Maps predictably in real environments. Contributions are welcome.
