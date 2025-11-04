# Phase 4 - Asynchronous Tasks and Cache Warming

## 1. Celery configuration
- Added dependencies (`celery==5.4.0`) and created `core/celery.py` with task autodiscovery.
- `core/__init__.py` exposes `celery_app`, enabling `& D:\provemaps_beta\venv\Scripts\celery.exe -A core worker -l info` on Windows.
- Updated `core/settings.py`:
  - `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` point to Redis (`redis://127.0.0.1:6379/0`).
  - Default queue and serializers configured for JSON (`mapspro_default`).

## 2. Cache warming tasks (`zabbix_api/tasks.py`)
- `warm_port_optical_cache(port_id)`: refreshes and stores the RX/TX snapshot for a port.
- `warm_device_ports(device_id)`: iterates over every port on a device.
- `warm_all_optical_snapshots()`: enqueues `warm_port_optical_cache` for all monitored ports.

## 3. Management command
```powershell
& D:\provemaps_beta\venv\Scripts\python.exe manage.py warm_optical_cache `
  [--device-id <id>] [--async]
```
- Without `--async`, runs inline (useful for manual warming after deployment).
- With `--async`, dispatches work to Celery (`warm_port_optical_cache.delay`).
- Example: `& D:\provemaps_beta\venv\Scripts\python.exe manage.py warm_optical_cache --async` while `& D:\provemaps_beta\venv\Scripts\celery.exe -A core worker -l info` is running.

## 4. Post-warming results (with Redis)
- After running `warm_optical_cache` and keeping Redis active:
  - `port-optical-status`: average ~286 ms / p95 ~1,420 ms (further drop in average compared with the previous phase thanks to the pre-populated cache).
  - Other endpoints remain below 10 ms on average.
- Schedule the warming periodically (Celery beat or cron) to keep the cache ready and avoid cold-start penalties for users.

## 5. Suggested next steps
- Configure a scheduler (Celery beat or cron) to trigger `warm_all_optical_snapshots` at regular intervals.
- Monitor Celery workers and Redis usage (metrics, `docker compose exec redis redis-cli monitor`).
- Consider batching `itemids` for the `port-optical-status` endpoint if latency spikes persist.
