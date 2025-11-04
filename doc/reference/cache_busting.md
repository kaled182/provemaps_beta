# Frontend Cache Busting Guide (Fiber Route Builder)

This note explains how we keep the latest JS and CSS assets in sync across development and production environments.

## Goals
- Prevent stale copies of `fiber_route_builder.js` after code changes.
- Keep the context menu states (idle, creating, selected) aligned with current logic.
- Provide a repeatable workflow for developers and QA.
- Tag assets with the Git SHA so we can trace which build is running.

## Implemented Strategies
1. Version Query Parameter
   - `STATIC_ASSET_VERSION` is injected via a context processor.
   - Critical `<script>` tags append `?v={{ STATIC_ASSET_VERSION }}`.
   - In `settings.dev` the value follows `<sha>-<timestamp>` (short commit SHA plus server start time).

2. Development No-Cache Middleware
   - Custom middleware applies the headers:
     `Cache-Control: no-cache, no-store, must-revalidate`
     `Pragma: no-cache`
     `Expires: 0`
   - Scope is limited to the Fiber Route Builder paths and the related static assets.

3. Legacy Asset Cleanup
   - Deprecated menu fragments such as the old "Create New Cable" and "Clear Selection" buttons were removed.
   - A single authoritative `fiber_route_builder.js` remains.

4. Hash-Based Static File Names
   - `ManifestStaticFilesStorage` now runs in both development and production.
   - File names change when content changes, providing a second layer beyond the query parameter.

5. Git SHA Embedding
   - `settings/dev.py` computes `STATIC_ASSET_VERSION = "<sha>-<timestamp>"`.
   - Server startup logs include `STATIC_ASSET_VERSION=...` for quick checks.

6. Verification Script
   - `scripts/verify_asset_version.py` asserts that the version prefix matches the current Git SHA.
   - Handy after rebases or when working in a detached HEAD.

7. Prometheus Metrics
   - The `static_asset_version` info metric exposes the current version at `/metrics/`.
   - Labels include `version`, `git_sha`, and `timestamp`.
   - Initialised during Django startup in `core.apps.CoreConfig.ready()`.
   - Example query: `static_asset_version_info{version=~".*"}`.

## Developer Workflow (Development Environment)
1. Modify the JS or CSS files.
2. (Optional) Run `& D:\provemaps_beta\venv\Scripts\python.exe manage.py collectstatic --noinput` when new static files are added.
3. Hard-reload the browser (Ctrl+Shift+R) with the Network tab set to "Disable cache".
4. Confirm that the console log version matches the first segment of the query parameter.

## Quick Verification
```powershell
# Ensure settings.dev is active
$env:DJANGO_SETTINGS_MODULE = "settings.dev"
& D:\provemaps_beta\venv\Scripts\python.exe scripts\verify_asset_version.py
```
Sample output:
```
STATIC_ASSET_VERSION=abc123-20251026142055
GIT_SHA=abc123
OK: version contains SHA.
```

### Check Prometheus Metrics
```powershell
# Start the server
& D:\provemaps_beta\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000

# Open http://localhost:8000/metrics/
# Look for: static_asset_version_info{git_sha="abc123",timestamp="...",version="..."}
```

## Validation Checklist
- Open DevTools > Network.
- Load the Fiber Route Builder screen.
- Confirm `fiber_route_builder.js?v=<sha>-<timestamp>` returns HTTP 200 (not disk cached).
- Response headers include `Cache-Control: no-cache, no-store`.
- Right-click context menu states:
  - Idle: Import KML, Reload All.
  - Creating: Creating header, Assign, Clear Points.
  - Selected cable: Cable name, Assign, Save Path Changes (when modified), Delete, Reload This.

## Service Workers
- No service worker is registered for `http://localhost:8000`; entries you see belong to browser extensions.

## Troubleshooting
| Symptom | Cause | Resolution |
|--------|-------|------------|
| Legacy menu items appear | Browser cached an older bundle | Hard reload with cache disabled and confirm the new version string |
| JS request shows `(from disk cache)` | Query parameter did not change | Restart the dev server or generate a new commit to refresh the version |
| Version string missing SHA | Git command failed | Check that Git is installed and accessible inside the environment or CI job |
| Hashed file returns 404 | `collectstatic` was not executed | Run `& D:\provemaps_beta\venv\Scripts\python.exe manage.py collectstatic --noinput` |
| Version mismatch after rebase | Server still uses old process | Restart the server to pick up the latest SHA |

## Future Improvements (Optional)
- Introduce webpack or Vite for bundling and code splitting.
- Display an environment badge in the UI that shows the asset version.
- Export the asset version to additional Prometheus metrics for richer dashboards.

## Quick Commands (Windows PowerShell)
```powershell
# Restart the development server
& D:\provemaps_beta\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000

# Collect static files and regenerate hashes
& D:\provemaps_beta\venv\Scripts\python.exe manage.py collectstatic --noinput

# Verify that the asset version contains the current SHA
$env:DJANGO_SETTINGS_MODULE = "settings.dev"
& D:\provemaps_beta\venv\Scripts\python.exe scripts\verify_asset_version.py
```

## Summary
Combining `<sha>-<timestamp>` versions, `ManifestStaticFilesStorage`, and strict no-cache headers prevents stale assets while keeping deployments traceable. Use the verification script and startup log message to confirm the active version quickly.
