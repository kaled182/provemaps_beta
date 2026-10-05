# Spatial Stack Enablement Checklist

This guide captures everything needed to run the application with full GIS
functionality (GDAL/GEOS + PostGIS) across local development, Docker, and CI.
Follow the sections in order.

---

## 1. Choose Supported Versions
- GDAL/GEOS come from the **operating system / Docker image**, not from `requirements.txt` (there is no `GDAL` pin in `backend/requirements.txt`). We standardize on the Debian packages shipped with `python:3.12-slim` (same image used by our Dockerfile):
  - `gdal-bin`, `libgdal-dev` (GDAL 3.10.x at the time of writing)
  - `libgeos-dev` (GEOS 3.13.x at the time of writing)
- Keep the native libraries aligned across environments (local, CI, prod) to avoid ABI mismatches.
- Mirror the version info in the main `README.md` once the rollout is complete.

## 2. Update Containers (Docker/Docker Compose)
> ℹ️ PostgreSQL + PostGIS is the only supported database. The default dev stack is `docker/docker-compose.yml` (`postgis/postgis:16-3.4`, web on port 8100; `make up`). `docker/docker-compose.postgis.yml` is an alternative PostGIS-focused variant — avoid mixing the two stacks in the same session.

1. Base image packages:
   - Add to Dockerfile: `apt-get install -y gdal-bin libgdal-dev libgeos-dev postgresql-client` (adjust per distro).
   - Export library paths if the distro places GDAL/GEOS outside default search paths (`LD_LIBRARY_PATH`).
2. Python dependencies:
   - `django.contrib.gis` ships with Django; `backend/requirements.txt` already covers everything the production image needs. Do **not** `pip install GDAL`: Django talks to the system `libgdal`/`libgeos_c` through ctypes.
3. Database service:
   - Use a `postgis/postgis:<postgres-version>-<postgis-version>` image (`docker/docker-compose.yml` uses `postgis/postgis:16-3.4`).
   - `docker/sql/init_postgis.sql` is mounted into the container and runs `CREATE EXTENSION postgis;` (and friends) on first boot.
4. Environment variables in compose:
   ```yaml
   environment:
     DB_ENGINE: postgis
     DB_HOST: postgres
     DB_PORT: "5432"
     DB_NAME: app
     DB_USER: app
     DB_PASSWORD: app
     GDAL_LIBRARY_PATH: /usr/lib/x86_64-linux-gnu/libgdal.so
     GEOS_LIBRARY_PATH: /usr/lib/x86_64-linux-gnu/libgeos_c.so
   ```
5. Expose port 5432 and confirm app containers wait for DB readiness (`depends_on`, healthcheck).

## 3. Configure Django Settings
- `settings/base.py` selects the backend from environment variables (set `DB_ENGINE=postgis`, which switches `ENGINE` to `django.contrib.gis.db.backends.postgis`):
  ```env
  DB_ENGINE=postgis
  DB_NAME=app
  DB_USER=app
  DB_PASSWORD=app
  DB_HOST=postgres      # 127.0.0.1 outside Docker
  DB_PORT=5432
  ```
- `GDAL_LIBRARY_PATH` / `GEOS_LIBRARY_PATH` are exported in the compose files and in CI, but `settings/base.py` does not read them today; Django falls back to `find_library`. If your distro keeps the libraries outside the default search path, set them in the environment **and** add `GDAL_LIBRARY_PATH = os.getenv("GDAL_LIBRARY_PATH")` (same for GEOS) to the settings.
- Keep `django.contrib.gis` in `INSTALLED_APPS` (already present).

## 4. Provision the Database
1. Connect to the PostGIS instance (psql or pgAdmin).
2. Execute:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS postgis_topology;
   ```
3. If migrating data from a legacy database, plan export/import (outside scope here).
4. Run `python manage.py migrate` (from `backend/`) to create spatial columns and GiST indexes.

## 5. Local Development Setup
Match the Docker image as closely as possible (GDAL 3.10.x, GEOS 3.13.x, PROJ provided by the platform). After installing the native libraries, install the standard Python dependency set (`make requirements-dev`, i.e. `pip install -r backend/requirements-dev.txt`); it contains **no** `GDAL` pin — the bindings come from `django.contrib.gis` plus the system libraries.

### Linux (Debian/Ubuntu)
- `sudo apt-get update && sudo apt-get install -y gdal-bin libgdal-dev libgeos-dev`.
- Export the library paths (append to `.bashrc`/`.zshrc`):
  ```bash
  export GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so
  export GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so
  export PROJ_LIB=/usr/share/proj
  ```

### macOS (Homebrew)
- `brew update && brew install gdal` (installs GDAL + GEOS + PROJ).
- Add to your shell profile (adjust if Homebrew lives elsewhere):
  ```bash
  export GDAL_LIBRARY_PATH="$(brew --prefix)/opt/gdal/lib/libgdal.dylib"
  export GEOS_LIBRARY_PATH="$(brew --prefix)/opt/geos/lib/libgeos_c.dylib"
  export PROJ_LIB="$(brew --prefix)/opt/proj/share/proj"
  ```

> ❗️ Windows hosts must run the application exclusively inside Docker. Native GIS tooling for Windows is no longer maintained in this project. Spin up the stack via `make up` (`docker compose -f docker/docker-compose.yml up -d`) and rely on the containerized GDAL/GEOS/PostGIS toolchain.

### Validation Commands
```bash
python -c "from django.contrib.gis import gdal; print(bool(getattr(gdal, 'libgdal', None)), gdal.GDAL_VERSION)"
python manage.py check --tag gis   # run from backend/
```

## 6. Continuous Integration Pipeline
- Use a CI image with GDAL/GEOS preinstalled or add install steps.
- Provide a PostGIS service (GitHub Actions example):
  ```yaml
  services:
    postgres:
      image: postgis/postgis:16-3.4
      env:
        POSTGRES_DB: app
        POSTGRES_USER: app
        POSTGRES_PASSWORD: app
      options: >-
        --health-cmd "pg_isready -U app -d app"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
  ```
- Export env vars before tests:
  ```yaml
  env:
    DJANGO_SETTINGS_MODULE: settings.test
    DB_ENGINE: postgis
    TEST_DB_ENGINE: postgis
    DB_NAME: app
    DB_USER: app
    DB_PASSWORD: app
    DB_HOST: 127.0.0.1
    DB_PORT: "5432"
    GDAL_LIBRARY_PATH: /usr/lib/x86_64-linux-gnu/libgdal.so
    GEOS_LIBRARY_PATH: /usr/lib/x86_64-linux-gnu/libgeos_c.so
  ```
- Install system packages (`gdal-bin libgdal-dev libgeos-dev postgresql-client`) and Python deps (`pip install -r backend/requirements-dev.txt`). See `.github/workflows/tests.yml` for the working reference.
- From `backend/`, run `python manage.py check --tag gis` and `coverage run -m pytest -q` (no spatial skips).

## 7. Regression Tests
- Ensure `backend/tests/test_spatial_api.py` runs (remove skip condition once GDAL present).
- Add fixture coverage for `RouteSegment.path` and `FiberCable.path` using `LineString`.
- Consider adding smoke test hitting `/api/v1/inventory/segments/?bbox=...` and asserting GeoJSON payloads.

## 8. Observability & Health
- Add database healthcheck: `SELECT PostGIS_Version();` in health endpoint or background probe.
- Optionally export Prometheus gauge: `inventory_spatial_mode{enabled="true"}` when GDAL/PostGIS detected.

## 9. Documentation Updates
- Reference this checklist from `doc/developer/README.md`.
- Mention GDAL/GEOS requirements in the root `README.md` prerequisites section.
- Share with the team before merging to ensure ops alignment.

## 10. Final Verification
1. `docker compose -f docker/docker-compose.yml up --build` succeeds; app boots without GIS warnings.
2. `python manage.py migrate` on PostGIS completes.
3. All pytest suites pass, including spatial tests.
4. `/api/v1/inventory/segments/?bbox=...` returns `path_geojson` data.
5. Web dashboards map routes using the spatial column (no fallback JSON).
6. Admin NASA Worldview preview renders the updated geometry after edits (verify via `/admin/inventory/fibercable/<id>/change/`).
7. CI pipeline finishes green.
8. Health checks and metrics reflect GIS readiness.

Once every item is checked, the project runs with full, non-fallback spatial
capabilities.

> ✅ Validation log (2025-11-12): `docker compose -f docker/docker-compose.postgis.yml exec web python manage.py migrate` (applied `inventory.0013_lenient_json_fields`) and `docker compose -f docker/docker-compose.postgis.yml exec web pytest -q` (209 passed, 6 skipped) confirm the PostGIS stack is operational and that NASA Worldview reflects the synchronized path geometry.
