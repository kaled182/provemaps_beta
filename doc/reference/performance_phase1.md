# Phase 1 – Performance Preparation and Diagnostics

This first stage collects a trustworthy baseline before we apply invasive changes. All of the steps below can be executed in the current environment (SQLite) and repeated after migration to validate the gains.

## 1. Endpoint baseline

1. Make sure there is a user with access to the endpoints (for example, `staff`).
2. Run the newly created profiling command:

   ```bash
   python manage.py profile_endpoints --username=<USER> --password=<PASS> --runs=5
   ```

   The command exercises the critical routes (`/zabbix_api/api/fibers/`, `/zabbix_api/api/sites/`, `/zabbix_api/api/device-ports/<id>/`, etc.) and prints the average, p95, and max time in milliseconds. Use this result as the reference for comparisons after migration or caching.

3. If you need additional detail, temporarily enable Django request timing logs by adding the following to `settings.py`:

   ```python
   LOGGING["loggers"]["django.request"] = {
       "handlers": ["console"],
       "level": "INFO",
   }
   ```

   Alternatively, use load-testing tools (Locust, k6) against the REST endpoints to record throughput and latency.

## 2. Instrument Zabbix calls

All `zabbix_request` calls are now logged with duration and status (`DEBUG`). To capture the real volume:

1. In Django `LOGGING`, enable the `zabbix_api.services.zabbix_service` namespace at the `DEBUG` level during the measurement window:

   ```python
   LOGGING["loggers"]["zabbix_api.services.zabbix_service"] = {
       "handlers": ["console"],
       "level": "DEBUG",
   }
   ```

2. Run the system normally (or execute the profiling command above) and watch the console for the number of calls, average duration, presence of retries, and similar data. This log will validate whether future optimizations (batch requests, cache) reduce the volume and duration of those calls.

## 3. Current database CPU/IO consumption

Even with SQLite you can monitor the impact of queries:

- Enable Django slow query logging by adding:

  ```python
  LOGGING["loggers"]["django.db.backends"] = {
      "handlers": ["console"],
      "level": "DEBUG",
  }
  ```

  This prints every executed SQL statement alongside its estimated duration (helpful to spot N+1 patterns or expensive queries).

- Use operating system tools (Task Manager, `Get-Process`, `perfmon`) to inspect CPU and IO usage while the tests run.

- On Linux, `iotop` and `htop` make bottlenecks easy to visualize.

These observations highlight both SQLite’s limitations and the tables we query most frequently.

## 4. Map current infrastructure and plan the migration

- Confirm that the project uses SQLite (`django.db.backends.sqlite3`) and that the `db.sqlite3` file resides at `C:\Users\Paulo Adriano\Downloads\django-maps-prove-master-fixed\db.sqlite3`. This engine does not handle multiple processes or concurrent loads well.

- Determine where else the project runs (staging/production). If those environments also rely on SQLite, schedule downtime for migration.

- Choose the target database: MySQL 8.x or MariaDB 10.x are recommended by the Zabbix ecosystem, but PostgreSQL is also fully supported by Django. Coordinate with infrastructure to understand hosting and backup capabilities.

- Validate the required Django drivers/libraries:
  * MySQL/MariaDB: `mysqlclient` (better performance) or `PyMySQL`.
  * PostgreSQL: `psycopg2`.
  * Make sure the dependencies are listed in `requirements.txt`.

- Draft the migration plan:
  1. Create an empty database on the target platform (use `utf8mb4` for MySQL/MariaDB).
  2. Update `settings.DATABASES` (keep the default `CONN_MAX_AGE` for now).
  3. Run `python manage.py migrate`.
  4. Load data via `dumpdata/loaddata` or native tooling (for example, `sqlite3 db.sqlite3 .dump | mysql ...`).
  5. Execute the command suite (`profile_endpoints`, automated tests).

## 5. Next steps after Phase 1

With the baseline metrics collected:

- Document the results (retain profiling output and the Zabbix logger captures).
- Use these metrics as the baseline for Phase 2 (database migration and indexing).
- Once MySQL is operational, rerun `profile_endpoints` and compare the results.

This checklist provides visibility into the current state before any structural change, helping measure the real gains achieved in later phases.
