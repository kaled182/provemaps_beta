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
| Backend Runtime & Config | 2 | Core services, commands, and settings with user-facing strings |
| Frontend & Static Assets | 9 | Legacy JS backups and markdown checklists surfaced to users |
| Tests & QA Assets | 11 | Test descriptions/assertions in Portuguese |
| Tooling & Scripts | 11 | Shell/Python/PowerShell scripts shown to operators |
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

## Detailed Status (Pending)

### Documentation & Guides
- _None pending_

### Backend Runtime & Config
- `zabbix_api/usecases/__init__.py`
- `zabbix_api/usecases/inventory.py`

### Frontend & Static Assets
- `routes_builder/static/js/fiber_route_builder.js.backup`
- `staticfiles/js/fiber_route_builder.js.backup`
- `staticfiles/js/modules/BROWSER_TESTING_CHECKLIST.md`
- `staticfiles/js/modules/INTEGRATION_COMPLETE.md`
- `staticfiles/js/modules/README.md`
- `maps_view/static/img/logo.png` (embedded text)
- `staticfiles/img/logo.png` (embedded text)
- `staticfiles/admin/css/changelists.css` (Portuguese comments)
- `staticfiles/admin/js/urlify.js` (Portuguese reference strings)

### Tests & QA Assets
- `tests/test_cache_swr.py`
- `tests/test_celery_metrics.py`
- `tests/test_celery_status.py`
- `tests/test_celery_status_fallback.py`
- `tests/test_check_translations.py`
- `tests/test_fiber_edit_persistence.py`
- `tests/test_resilient_zabbix_client.py`
- `tests/test_setup_docs_views.py`
- `tests/test_smoke.py`
- `tests/test_zabbix_service.py`
- `service_accounts/tests/*` (if any Portuguese strings)

### Tooling & Scripts
- `.dockerignore`
- `.pre-commit-config.yaml`
- `scripts/check_celery.ps1`
- `scripts/check_celery.sh`
- `scripts/check_port_columns.py`
- `scripts/deploy.sh`
- `scripts/diagnose_google_maps.py`
- `scripts/package-release.ps1`
- `scripts/setup_test_db_permissions.sql`
- `scripts/update_imports.ps1`
- `scripts/verify_asset_version.py`

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

1. Finish translating remaining `zabbix_api/usecases` modules and verify tests.
2. Address pending frontend markdowns/JS backups surfaced to users.
3. Continue auditing tests and operator scripts for Portuguese strings.
4. Refresh this report after each translation pass, moving files to a **Completed** list as work finishes.
