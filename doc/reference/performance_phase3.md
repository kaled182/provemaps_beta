# Phase 3 – Caching and Zabbix Call Reduction

## 1. Django cache configuration
- `core/settings.py`: added a `CACHES` entry using `LocMemCache` (default timeout 60 seconds); `CONN_MAX_AGE` remains set to 60.
- Local in-memory cache is sufficient for validating gains. Replace with Redis or Memcached in production.

## 2. Cached endpoints and helpers
- `api_fiber_cables` now reads and writes from the cache with a 30 second TTL.
- `api_device_ports` follows the same pattern.
- `_fetch_port_optical_snapshot` stores RX/TX snapshots per port for 30 seconds when no custom discovery is required, cutting repeated `item.get` and `history.get` calls.
- `refreshCableStatusValueMapped` still refreshes InfoWindow details; after expiry, the cache repopulates automatically.

## 3. Profiling results (MariaDB + cache)
```powershell
& D:\provemaps_beta\venv\Scripts\python.exe manage.py profile_endpoints `
	--username=perf_tester --password='Perf#2025' --runs=5
```
- `fibers`: average 1.6 ms / p95 4.8 ms
- `sites`: average 1.7 ms / p95 2.3 ms
- `device-ports`: average 7.7 ms / p95 34.3 ms (previously 33.4 / 35.5 ms)
- `port-optical-status`: average 252.1 ms / p95 1,253.5 ms (previously 351.4 / 1,749.6 ms)
- `fiber-detail`: average 2.3 ms / p95 3.1 ms

Notes:
- `port-optical-status` mean latency improved markedly. Residual spikes occur when the cache expires and a new `item.get` is triggered. A shared cache or batched requests should lower p95 further.
- DEBUG logs in `zabbix_api.services.zabbix_service` continue to expose individual call durations for continuous monitoring.

## 4. Next steps
- Evaluate Redis or Memcached for shared caching and an invalidation strategy (for example, when cables or ports change).
- Implement batched Zabbix queries (group item IDs) to mitigate latency spikes.
- Consider asynchronous workers (Celery or RQ) to prefetch traffic and history data.
