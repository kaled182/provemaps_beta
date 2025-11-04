# Phase 2 – Migration to MariaDB and Database Tuning

## 1. MariaDB configuration
- Local server: `C:\Program Files\MariaDB 12.0` with the `MariaDB` service running.
- Databases provisioned: `mapspro_db` (charset `utf8mb4`) and test database `test_mapspro_db` for the Django suite.
- Application user: `mapspro_user` with password `Maps@Prove#2025` (apply stricter credentials before production).

## 2. Project updates
- `core/settings.py` now treats MariaDB as the default database and keeps SQLite configured as `legacy` for read-only queries or dumps.
- Added the `PyMySQL` dependency (see `requirements.txt`) and invoked `pymysql.install_as_MySQLdb()` inside `core/__init__.py` to maintain Django compatibility.

## 3. Data migration process
1. Generate a dump from SQLite through the `legacy` alias:
  ```powershell
  & D:\provemaps_beta\venv\Scripts\python.exe manage.py dumpdata --database=legacy `
     --natural-foreign --natural-primary `
     --exclude=contenttypes --exclude=auth.permission `
     --exclude=sessions.session --exclude=admin.logentry `
     --indent 2 --output data/sqlite_dump.json
   ```
2. Re-create the MariaDB database (drop, migrate) and load the data:
  ```powershell
  & "C:\Program Files\MariaDB 12.0\bin\mysql.exe" -u root -p `
    -e "DROP DATABASE IF EXISTS mapspro_db; DROP DATABASE IF EXISTS test_mapspro_db; CREATE DATABASE mapspro_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
  & D:\provemaps_beta\venv\Scripts\python.exe manage.py migrate
  & D:\provemaps_beta\venv\Scripts\python.exe manage.py loaddata data\sqlite_dump.json
  ```
3. Create or reset the test user `perf_tester` (password `Perf#2025`) after loading the fixtures so credentials remain available for profiling.

## 4. Indexes and logging
- Additional indexes on frequently queried columns:
  ```sql
  CREATE INDEX idx_port_device ON zabbix_api_port (device_id);
  CREATE INDEX idx_fiber_origin_port ON zabbix_api_fibercable (origin_port_id);
  CREATE INDEX idx_fiber_destination_port ON zabbix_api_fibercable (destination_port_id);
  CREATE INDEX idx_fiberevent_fiber ON zabbix_api_fiberevent (fiber_id);
  ```
- Slow query log enabled in MariaDB:
  ```sql
  SET GLOBAL slow_query_log = 'ON';
  SET GLOBAL long_query_time = 0.5;
  ```
  (Default file `hostname-slow.log` under `C:/Program Files/MariaDB 12.0/data/`.)

## 5. Validation
- Profiling command:
  ```powershell
  & D:\provemaps_beta\venv\Scripts\python.exe manage.py profile_endpoints --username=perf_tester --password=Perf#2025 --runs=5
  ```
  Sample results (milliseconds): `fibers` avg 2.5 / p95 5.3, `device-ports` avg 33.4 / p95 35.5, `port-optical-status` avg 1794 / p95 1871, `fiber-detail` avg 3.0 / p95 4.2.
  Debug logs show `item.get` calls around 600 ms each, which will be targeted in Phase 3.
- Automated tests:
  ```powershell
  & D:\provemaps_beta\venv\Scripts\python.exe manage.py test tests
  ```
  Current outcome: 23 tests passing against MariaDB.

## 6. Next steps
- Implement caching or batching for Zabbix requests, focusing on `port-optical-status`.
- Evaluate Redis or Memcached for `/api/fibers/` and `/api/device-ports/` endpoints.
- Tune `CONN_MAX_AGE` once the production workload is known and monitor the slow query log for new bottlenecks.
