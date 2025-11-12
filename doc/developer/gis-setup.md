# Spatial Stack Enablement Checklist

This guide captures everything needed to run the application with full GIS
functionality (GDAL/GEOS + PostGIS) across local development, Docker, and CI.
Follow the sections in order.

---

## 1. Choose Supported Versions
- We standardize on the Debian **trixie** packages shipped with `python:3.12-slim` (same image used by our Dockerfile):
  - `gdal-bin` **3.10.3+dfsg-1**
  - `libgdal-dev` **3.10.3+dfsg-1**
  - `libgeos-dev` **3.13.1-1**
- Stick to these versions in every environment (local, CI, prod) to avoid ABI mismatches.
- Mirror the version info in the main `README.md` once the rollout is complete.

## 2. Update Containers (Docker/Docker Compose)
> ℹ️ Use `docker/docker-compose.postgis.yml` as the default stack for GIS work. It now launches the web, Celery, and Redis services against PostGIS. The legacy `docker/docker-compose.yml` remains only for MariaDB compatibility or fallback testing—avoid mixing the two runtimes in the same session.

1. Base image packages:
   - Add to Dockerfile: `apt-get install -y gdal-bin libgdal-dev libgeos-dev postgresql-client` (adjust per distro).
   - Export library paths if the distro places GDAL/GEOS outside default search paths (`LD_LIBRARY_PATH`).
2. Python dependencies:
   - `pip install "django[gis]"` and `pip install "GDAL==<chosen version>"` (match exact GDAL version).
3. Database service:
   - Swap PostgreSQL image for `postgis/postgis:<postgres-version>-<postgis-version>` in `docker-compose.yml`.
   - Ensure volume mounts run `CREATE EXTENSION postgis;` on first boot if not done manually.
4. Environment variables in compose:
   ```yaml
   environment:
     GDAL_LIBRARY_PATH: /usr/lib/libgdal.so
     GEOS_LIBRARY_PATH: /usr/lib/libgeos_c.so
     DATABASE_URL: postgis://user:pass@postgres:5432/db
   ```
5. Expose port 5432 and confirm app containers wait for DB readiness (`depends_on`, healthcheck).

## 3. Configure Django Settings
- In `settings/base.py` (and derived settings):
  ```python
  DATABASES = {
      "default": {
          "ENGINE": "django.contrib.gis.db.backends.postgis",
          "NAME": os.getenv("POSTGRES_DB", "maps"),
          "USER": os.getenv("POSTGRES_USER", "maps"),
          "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
          "HOST": os.getenv("POSTGRES_HOST", "postgres"),
          "PORT": os.getenv("POSTGRES_PORT", "5432"),
      }
  }
  ```
- Load GDAL/GEOS variables via `.env` or container env:
  ```python
  GDAL_LIBRARY_PATH = os.getenv("GDAL_LIBRARY_PATH")
  GEOS_LIBRARY_PATH = os.getenv("GEOS_LIBRARY_PATH")
  ```
- Keep `django.contrib.gis` in `INSTALLED_APPS` (already present).

## 4. Provision the Database
1. Connect to the PostGIS instance (psql or pgAdmin).
2. Execute:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS postgis_topology;
   ```
3. If migrating data from SQLite/MySQL, plan export/import (outside scope here).
4. Run `python manage.py migrate` to create spatial columns and GiST indexes.

## 5. Local Development Setup
Match the Docker image everywhere: GDAL **3.10.3**, GEOS **3.13.1**, PROJ provided by the platform. After installing the native libraries, reuse the standard Python dependency set (`pip install -r backend/requirements.txt`) which already pins `GDAL==3.10.3`.

### Linux (Debian/Ubuntu)
- `sudo apt-get update && sudo apt-get install -y gdal-bin libgdal-dev libgeos-dev python3-gdal`.
- In your virtualenv: `python -m pip install --upgrade pip` then `python -m pip install GDAL==3.10.3`.
- Export the library paths (append to `.bashrc`/`.zshrc`):
  ```bash
  export GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so
  export GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so
  export PROJ_LIB=/usr/share/proj
  ```

### macOS (Homebrew)
- `brew update && brew install gdal` (installs GDAL + GEOS + PROJ).
- Install the Python binding inside the virtualenv: `python -m pip install GDAL==3.10.3`.
- Add to your shell profile (adjust if Homebrew lives elsewhere):
  ```bash
  export GDAL_LIBRARY_PATH="$(brew --prefix)/opt/gdal/lib/libgdal.dylib"
  export GEOS_LIBRARY_PATH="$(brew --prefix)/opt/geos/lib/libgeos_c.dylib"
  export PROJ_LIB="$(brew --prefix)/opt/proj/share/proj"
  ```

> ❗️ Windows hosts must run the application exclusively inside Docker. Native GIS tooling for Windows is no longer maintained in this project. Spin up the stack via `docker compose up` and rely on the containerized GDAL/GEOS/PostGIS toolchain.

### Validation Commands
```bash
python -c "from django.contrib.gis import gdal; print(bool(getattr(gdal, 'libgdal', None)), gdal.GDAL_VERSION)"
python manage.py check --tag gis
```

## 6. Continuous Integration Pipeline
- Use a CI image with GDAL/GEOS preinstalled or add install steps.
- Provide a PostGIS service (GitHub Actions example):
  ```yaml
  services:
    postgres:
      image: postgis/postgis:15-3.4
      env:
        POSTGRES_DB: maps
        POSTGRES_USER: maps
        POSTGRES_PASSWORD: maps
      options: >-
        --health-cmd "pg_isready -U maps"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
  ```
- Export env vars before tests:
  ```yaml
  env:
    GDAL_LIBRARY_PATH: /usr/lib/libgdal.so
    GEOS_LIBRARY_PATH: /usr/lib/libgeos_c.so
    DATABASE_URL: postgis://maps:maps@localhost:5432/maps
  ```
- Install Python deps (`pip install GDAL==... django[gis]`).
- Run `pytest` (no spatial skips) and `python manage.py check --tag gis`.

## 7. Regression Tests
- Ensure `tests/test_spatial_api.py` runs (remove skip condition once GDAL present).
- Add fixture coverage for `RouteSegment.path` and `FiberCable.path` using `LineString`.
- Consider adding smoke test hitting `/api/v1/inventory/segments/?bbox=...` and asserting GeoJSON payloads.

## 8. Observability & Health
- Add database healthcheck: `SELECT PostGIS_Version();` in health endpoint or background probe.
- Optionally export Prometheus gauge: `inventory_spatial_mode{enabled="true"}` when GDAL/PostGIS detected.

## 9. Documentation Updates
- Reference this checklist from `doc/developer/getting-started/README.md`.
- Mention GDAL/GEOS requirements in the root `README.md` prerequisites section.
- Share with the team before merging to ensure ops alignment.

## 10. Final Verification
1. `docker compose up --build` succeeds; app boots without GIS warnings.
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
