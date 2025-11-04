# Phase 5 – Scheduler and Continuous Operation

## 1. Celery beat configuration
- `core/settings.py` defines `CELERY_BEAT_SCHEDULE` to run `zabbix_api.tasks.warm_all_optical_snapshots` every 10 minutes.
- The schedule uses the same `mapspro_default` queue. Start beat and worker in separate terminals (or supervise them with systemd, Supervisor, or Docker):

```powershell
& D:\provemaps_beta\venv\Scripts\celery.exe -A core worker -l info
& D:\provemaps_beta\venv\Scripts\celery.exe -A core beat -l info
```

## 2. Cache warming task
- `warm_all_optical_snapshots` triggers `warm_port_optical_cache` for every monitored port so RX/TX snapshots stay in Redis before user requests arrive.
- Adjust the 10 minute cadence as needed. Shorter intervals reduce the chance of cold cache misses.

## 3. Operational guidance
- Keep an eye on worker and beat logs (`& D:\provemaps_beta\venv\Scripts\celery.exe -A core worker -l info`, `& D:\provemaps_beta\venv\Scripts\celery.exe -A core beat -l info`).
- Monitor Redis metrics (memory usage, latency) with `docker compose exec redis redis-cli info` or your observability stack.
- In production, run the worker and beat under a process supervisor (systemd, Supervisor, Docker Compose, Kubernetes, etc.).
- For dynamic scheduling without code changes, consider adding `django-celery-beat` later.

With the beat service active, optical power caches remain warm automatically, which keeps the `port-optical-status` endpoint responsive even under repeated load.
