# Translation Status Report

_Last updated: 2025-11-04 (post-test sweep)_

This report tracks the cleanup of Portuguese-language strings across the project. Priorities follow the agreed order: user-facing documentation, visible UI strings, runtime error messages, then internal comments/logs.

## Legend

- **Pending** – File still contains Portuguese content that must be translated or rewritten.
- **Vendor/3rd-party** – File originates from an external dependency and is typically left unchanged.

## Summary

| Category | Files Pending | Notes |
| --- | --- | --- |
| Documentation & Guides | 0 | Monitoring for new or regenerated docs |
| Backend Runtime & Config | 0 | Core services, commands, and settings with user-facing strings |
| Frontend & Static Assets | 2 | Logo assets with embedded Portuguese text |
| Tests & QA Assets | 0 | Test descriptions/assertions in Portuguese |
| Tooling & Scripts | 0 | Shell/Python/PowerShell scripts shown to operators |
| Vendor Bundles | 43 | Select2/XRegExp i18n, admin assets (kept as-is) |

Completed files are tracked below; pending items remain highlighted per category.

## Completed (this branch)

- `README.md` — translated to English on 2025-11-03
- `doc/developer/README.md` — translated to English on 2025-11-03
- `doc/getting-started/QUICKSTART_LOCAL.md` — translated to English on 2025-11-03
- `doc/operations/STATUS_SERVICOS.md` — translated to English on 2025-11-03
- `doc/process/CONTRIBUTING.md` — translated to English on 2025-11-03
- `doc/reference/MARIADB_SUCCESS_REPORT.md` — translated to English on 2025-11-03
- `doc/reference/TESTING_WITH_MARIADB.md` — translated to English on 2025-11-03
- `doc/reference/PROJECT_STATUS_REPORT.md` — translated to English on 2025-11-03
- `doc/reference/REDIS_GRACEFUL_DEGRADATION.md` — translated to English on 2025-11-03
- `doc/reference/SETUP_REDIS_WINDOWS.md` — translated to English on 2025-11-03
- `doc/reference/TESTING_QUICK_REFERENCE.md` — translated to English on 2025-11-03
- `doc/reference/performance_phase1.md` — translated to English on 2025-11-03
- `doc/releases/CHANGELOG_20251025_REDIS.md` — translated to English on 2025-11-03
- `doc/reference/MARIADB_IMPLEMENTATION_COMPLETE.md` — language audit completed on 2025-11-03
- `.env.example` — comments translated to English on 2025-11-03
- `conftest.py` — docstrings and skip messages translated to English on 2025-11-03
- `core/celery.py` — comments and docstrings translated to English on 2025-11-03
- `core/management/commands/celery_health.py` — help text and messages translated to English on 2025-11-03
- `core/metrics_celery.py` — inline comments translated to English on 2025-11-03
- `core/management/commands/ensure_superuser.py` — docstrings and outputs translated to English on 2025-11-03
- `core/middleware/no_cache_dev.py` — middleware docstring and headers localized on 2025-11-03
- `core/middleware/request_id.py` — request ID handling strings translated to English on 2025-11-03
- `core/views_health.py` — health check endpoints translated to English on 2025-11-03
- `docker-compose.test.yml` — test stack comments translated to English on 2025-11-03
- `docker-entrypoint.sh` — entrypoint helper logs translated to English on 2025-11-03
- `dockerfile` — image build documentation translated to English on 2025-11-03
- `makefile` — development shortcuts translated to English on 2025-11-03
- `pyproject.toml` — unified project settings translated to English on 2025-11-03
- `pytest.ini` — pytest configuration and markers translated to English on 2025-11-03
- `settings/__init__.py` — environment helpers translated to English on 2025-11-03
- `settings/base.py` — core settings defaults translated to English on 2025-11-03
- `settings/dev.py` — development overrides translated to English on 2025-11-03
- `settings/prod.py` — production overrides translated to English on 2025-11-03
- `settings/test.py` — test overrides translated to English on 2025-11-03
- `zabbix_api/client.py` — resilient API client translated to English on 2025-11-03
- `zabbix_api/decorators.py` — API decorators translated to English on 2025-11-03
- `zabbix_api/domain/geometry.py` — geometry utilities translated to English on 2025-11-03
- `zabbix_api/domain/optical.py` — optical power helpers translated to English on 2025-11-03
- `zabbix_api/inventory.py` — inventory endpoints translated to English on 2025-11-03
- `zabbix_api/management/commands/show_slow_queries.py` — translated to English on 2025-11-04
- `zabbix_api/management/commands/warm_optical_cache.py` — translated to English on 2025-11-04
- `zabbix_api/services/zabbix_client.py` — translated to English on 2025-11-04
- `zabbix_api/services/zabbix_service.py` — phase-one translation & cleanup completed on 2025-11-04
- `zabbix_api/usecases/fibers.py` — runtime validations and comments translated on 2025-11-04
- `zabbix_api/usecases/__init__.py` — module docstring translated to English on 2025-11-04
- `tests/usecases/test_fibers.py` — assertions and fixtures translated to English on 2025-11-04
- `tests/test_celery_status.py` — status endpoint smoke test translated to English on 2025-11-04
- `tests/test_cache_swr.py` — SWR cache tests translated to English on 2025-11-04
- `tests/test_celery_metrics.py` — Celery metrics tests translated to English on 2025-11-04
- `tests/test_celery_status_fallback.py` — fallback status test translated to English on 2025-11-04
- `tests/test_fiber_edit_persistence.py` — fiber edit persistence flow translated to English on 2025-11-04
- `tests/test_resilient_zabbix_client.py` — resilient client scenarios translated to English on 2025-11-04
- `tests/test_setup_docs_views.py` — documentation views smoke tests translated to English on 2025-11-04
- `tests/test_smoke.py` — smoke assertions translated to English on 2025-11-04
- `tests/test_zabbix_service.py` — service helper tests translated to English on 2025-11-04
- `service_accounts/tests.py` — service account management tests translated to English on 2025-11-04
- `tests/test_check_translations.py` — translation scanner tests confirmed in English on 2025-11-04
- `zabbix_api/usecases/inventory.py` — inventory ingestion and port matching translated to English on 2025-11-04
- `staticfiles/js/modules/BROWSER_TESTING_CHECKLIST.md` — browser QA checklist translated to English on 2025-11-04
- `staticfiles/js/modules/INTEGRATION_COMPLETE.md` — integration summary verified in English on 2025-11-04
- `staticfiles/js/modules/README.md` — module architecture notes translated to English on 2025-11-04
- `routes_builder/static/js/fiber_route_builder.js.backup` — legacy bundle comments translated to English on 2025-11-04
- `staticfiles/js/fiber_route_builder.js.backup` — static bundle comments translated to English on 2025-11-04
- `.pre-commit-config.yaml` — developer tooling comments translated to English on 2025-11-04
- `scripts/check_celery.ps1` — operator script output translated to English on 2025-11-04
- `scripts/check_celery.sh` — operator health check translated to English on 2025-11-04
- `scripts/check_port_columns.py` — diagnostics output translated to English on 2025-11-04
- `scripts/deploy.sh` — deployment helper logs translated to English on 2025-11-04
- `.dockerignore` — Docker build context comments translated to English on 2025-11-04
- `scripts/diagnose_google_maps.py` — multi-layer diagnostic output translated to English on 2025-11-04
- `scripts/package-release.ps1` — release packaging script translated to English on 2025-11-04
- `scripts/setup_test_db_permissions.sql` — test DB permissions script translated to English on 2025-11-04
- `scripts/update_imports.ps1` — import migration helper translated to English on 2025-11-04
- `scripts/verify_asset_version.py` — asset version verifier translated to English on 2025-11-04
- `staticfiles/admin/css/changelists.css` — replaced non-ASCII arrows with ASCII equivalents on 2025-11-04
- `staticfiles/admin/js/urlify.js` — verified transliteration map (no Portuguese text) on 2025-11-04

## Detailed Status (Pending)

### Documentation & Guides
- _None pending_

### Backend Runtime & Config
- _None pending_

### Tests & QA Assets

### Tooling & Scripts
- _None pending_

### Vendor / Third-Party (Informational)
- `staticfiles/admin/js/vendor/select2/i18n/*.js`
- `staticfiles/admin/js/vendor/select2/select2.full.min.js`
- `staticfiles/admin/js/vendor/xregexp/xregexp.js`
- `staticfiles/admin/js/vendor/xregexp/xregexp.min.js`
- `staticfiles/admin/css/changelists.css` (portion auto-generated)
- `staticfiles/js/modules/core-js*` (previously excluded)
- `staticfiles/js/modules/vendor*` (previously excluded)
- Binary assets: `maps_view/static/img/logo.png`, `staticfiles/img/logo.png`, `test_db.sqlite3`, `test_errors.txt`

> **Note:** Vendor files should remain untouched unless there is a specific compliance requirement.

## Next Steps

1. Decide on remediation strategy for the remaining logo assets with embedded Portuguese text.
2. Keep this report updated if new Portuguese content appears.
