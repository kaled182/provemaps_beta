# Frontend Cache Busting Guide (Fiber Route Builder)

This document summarizes the strategies implemented to ensure the latest JS/CSS assets load reliably during development and production.

## Goals
- Avoid stale `fiber_route_builder.js` after changes.
- Ensure three menu states (idle, creating, selected) always reflect current logic.
- Provide repeatable steps for developers.
- Add traceability via Git commit SHA in asset version.

## Implemented Strategies
1. Version Query Parameter
   - `STATIC_ASSET_VERSION` injected via context processor.
   - Added to critical `<script>` tags as `?v={{ STATIC_ASSET_VERSION }}`.
   - In `dev` now uses pattern `<sha>-<timestamp>` (commit short SHA + start time).

2. Dev No-Cache Middleware
   - Custom middleware sets:
     `Cache-Control: no-cache, no-store, must-revalidate`
     `Pragma: no-cache`
     `Expires: 0`
   - Scoped to Fiber Route Builder and related static requests.

3. Removal of Legacy Assets
   - Eliminated old menu code fragments: `Create New Cable`, `Clear Selection` button.
   - Single authoritative `fiber_route_builder.js` retained.

4. Hash-Based Static Names (Dev & Prod)
   - `ManifestStaticFilesStorage` active in **dev** and **prod** now.
   - Ensures filename changes when content changes (defense in depth with query param).

5. Git SHA Embedding
   - `settings/dev.py` computes `STATIC_ASSET_VERSION = "<sha>-<timestamp>"`.
   - A console print (`🔐 STATIC_ASSET_VERSION=...`) appears on server start for quick validation.

6. Verification Script
   - `scripts/verify_asset_version.py` checks if version starts with current repo SHA.
   - Useful after rebasing or detached HEAD scenarios.

7. Prometheus Metrics
   - `static_asset_version` Info metric exposes current version at `/metrics/`.
   - Labels: `version`, `git_sha`, `timestamp`.
   - Auto-initialized on Django startup via `core.apps.CoreConfig.ready()`.
   - Query example: `static_asset_version_info{version=~".*"}`

## Developer Workflow (Dev)
1. Edit JS/CSS.
2. (Optional) Run `python manage.py collectstatic --noinput` if adding new static files.
3. Hard reload browser (Ctrl+Shift+R) with DevTools Network "Disable cache".
4. Confirm version string in server console matches first segment of query param.

## Quick Verification
```powershell
# Garantir settings.dev
$env:DJANGO_SETTINGS_MODULE = "settings.dev"
python scripts/verify_asset_version.py
```
Output example:
```
STATIC_ASSET_VERSION=abc123-20251026142055
GIT_SHA=abc123
OK: versão contém SHA.
```

### Check Prometheus Metrics
```powershell
# Start server
python manage.py runserver 0.0.0.0:8000

# Query metric (open in browser or curl)
# http://localhost:8000/metrics/
# Look for: static_asset_version_info{git_sha="abc123",timestamp="...",version="..."}
```

## Validation Checklist
- Open DevTools → Network.
- Load `fiber-route-builder/`.
- Confirm `fiber_route_builder.js?v=<sha>-<timestamp>` status 200 (not cached disk).
- Headers show `Cache-Control: no-cache, no-store`.
- Right‑click context menu states:
  - Idle: Import KML + Reload All.
  - Creating: Creating header + Assign + Clear Points.
  - Selected cable: Cable name + Assign + Save Path Changes (if modified) + Delete + Reload This.

## Service Workers
- No service worker registered for `http://localhost:8000`; existing ones are Chrome extensions / Google domains.

## Troubleshooting
| Symptom | Cause | Fix |
|--------|-------|-----|
| Old menu items appear | Browser cached old JS | Hard reload w/ cache disabled / check new version printed |
| JS request shows `(from disk cache)` | Query param unchanged | Restart dev server OR commit new changes (version regen) |
| Version missing SHA | Git command falhou | Verifique git instalado / perms / ambiente CI |
| `404` hashed file | collectstatic não rodou | `python manage.py collectstatic --noinput` |
| Version mismatch after rebase | Detached HEAD / stale server | Reinicie servidor para recapturar novo SHA |

## Future Improvements (Optional)
- Integrate webpack/Vite for bundling + code splitting.
- Add automatic environment badge overlay with version in UI.
- Push version info to Prometheus metric for observability.

## Quick Commands (Windows PowerShell)
```powershell
# Restart server
python manage.py runserver 0.0.0.0:8000

# Collect static (hash generation)
python manage.py collectstatic --noinput

# Verify asset version contains SHA
$env:DJANGO_SETTINGS_MODULE = "settings.dev"
python scripts/verify_asset_version.py
```

## Summary
Com `<sha>-<timestamp>` + ManifestStaticFilesStorage + no-cache headers, eliminamos staleness e ganhamos rastreabilidade. Use o script de verificação e o console print para confirmar versões rapidamente.
