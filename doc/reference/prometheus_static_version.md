# Cache Busting and Prometheus Integration Summary

The following capabilities are now live and verified:

## 1. ManifestStaticFilesStorage in Development
- File: `settings/dev.py`
- Storage: `ManifestStaticFilesStorage` to append hash digests to asset filenames automatically
- Requirement: run `& D:\provemaps_beta\venv\Scripts\python.exe manage.py collectstatic --noinput` after any change to static files

## 2. Version Tag with Git SHA
- File: `settings/dev.py`
- Function: `_git_sha()` captures the short commit SHA
- Format: `<sha>-<timestamp>` (example: `e90e25c-20251026200851`)
- Console output: `[STATIC_VERSION] STATIC_ASSET_VERSION=...`

## 3. Prometheus Metric
- Files created:
  - `core/metrics_static_version.py` (defines an Info metric)
  - `core/apps.py` (CoreConfig with `ready()` that registers the metric)
- Metric: `static_asset_version_info{version="...",git_sha="...",timestamp="..."}`
- Endpoint: `/metrics/metrics` provided by `django-prometheus`

## 4. Verification Script
- File: `scripts/verify_asset_version.py`
- Purpose: validates that the configured version string includes the current Git SHA
- Usage:
  ```powershell
  $env:DJANGO_SETTINGS_MODULE = "settings.dev"
  & D:\provemaps_beta\venv\Scripts\python.exe scripts\verify_asset_version.py
  ```

## 5. Documentation
- File: `cache_busting.md`
- Sections:
  - Strategies (query parameter, no cache headers, hashing, SHA)
  - Development workflow
  - Verification steps (script plus Prometheus)
  - Troubleshooting

## Points to Watch

### Encoding on Windows
- Issue: emojis such as lock or control icons trigger `UnicodeDecodeError` under Windows code page 1252
- Fix: replace those symbols with ASCII tags like `[STATIC_VERSION]` and `[DEBUG_TOOLBAR]`

### Database Dependency (optional)
- The Django app needs a working database connection to complete startup
- The Prometheus metric is registered inside `CoreConfig.ready()`
- If the database connection fails the `ready()` hook does not execute and the metric does not appear
- Workaround:
  - Use SQLite in development: `$env:DB_ENGINE="sqlite"`, or
  - Provide valid MySQL or MariaDB credentials in `.env`

### Prometheus Endpoint
- Correct URL: `/metrics/metrics` (note the nested `metrics` path)
- `django-prometheus` mounts the Prometheus view at `/metrics/`
- Every exported metric is therefore available at `/metrics/metrics`

## Manual Validation

### 1. Confirm the SHA in the console
```powershell
$env:DEBUG = "True"
$env:DJANGO_SETTINGS_MODULE = "settings.dev"
& D:\provemaps_beta\venv\Scripts\python.exe manage.py check
# Expected output:
# [STATIC_VERSION] STATIC_ASSET_VERSION=abc123-YYYYMMDDHHMMSS
# System check identified no issues (0 silenced).
```

### 2. Inspect the metric via Prometheus
```powershell
# Start the development server (with a valid database connection)
& D:\provemaps_beta\venv\Scripts\python.exe manage.py runserver 8000

# Query by browser or curl
# http://localhost:8000/metrics/metrics
# Look for: static_asset_version_info{...}
```

### 3. Run the verification script
```powershell
$env:DJANGO_SETTINGS_MODULE = "settings.dev"
& D:\provemaps_beta\venv\Scripts\python.exe scripts\verify_asset_version.py
# Expected output:
# STATIC_ASSET_VERSION=abc123-20251026200851
# GIT_SHA=abc123
# OK: version string includes the SHA.
```

## Next Steps (optional)

1. **User interface badge**: add a visual badge with the current version in the footer or header.
2. **Grafana dashboard**: chart historic deployments using the Prometheus metric.
3. **CI or CD integration**: attach the same version string to build artifacts.
4. **Alerting**: raise an alert if the version remains unchanged for several hours, which can reveal stalled deployments.

## Files Touched

- `settings/base.py`: added `core.apps.CoreConfig` to `INSTALLED_APPS`
- `settings/dev.py`: enabled `ManifestStaticFilesStorage`, introduced `_git_sha()`, removed emojis
- `core/apps.py`: created `CoreConfig.ready()` to initialize the Prometheus metric
- `core/metrics_static_version.py`: new module that defines the metric
- `cache_busting.md`: updated with SHA strategy, Prometheus usage, and verification steps
- `scripts/verify_asset_version.py`: new validation script

---

**Status**: implementation complete. Validated with `manage.py check`. Metric is exposed at `/metrics/metrics` when the server starts with a working database connection.
