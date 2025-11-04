# Phase 4 - Test Report and Improvement Analysis

**Date:** 27 October 2025  
**Phase:** Phase 4 - Testing (Observability)  
**Overall Status:** Partially complete - pending decisions

---

## Executive Summary

### Successfully Delivered Items

1. **Phase 3 - Observability (100 percent complete)**
   - Fifteen custom Prometheus metrics implemented.
   - Structured logging in place with structlog.
   - Request ID middleware available for distributed tracing.
   - Supporting documentation exceeds four hundred lines.

2. **Phase 4 - Testing (approximately 60 percent complete)**
   - Eighteen tests cover the custom metrics module (`tests/test_metrics.py`).
   - Seventeen tests cover the request ID middleware (`tests/test_middleware.py`).
   - Metrics package reaches 99 percent coverage when the suite executes correctly.
   - Fifteen tests currently fail because of assertion mismatches.
   - Test suite depends on SQLite when run locally.

---

## Critical Issues Observed

### Issue 1: Test Database Strategy

Current configuration (`settings/test.py`):
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
```

Impact:
- Unit tests should avoid external dependencies. SQLite in memory satisfies that goal.
- When `DJANGO_SETTINGS_MODULE` is not set to `settings.test`, pytest attempts to use the default MariaDB configuration and fails with authentication errors.
- Temporary workaround: export `DJANGO_SETTINGS_MODULE=settings.test` before running pytest.

Execution examples:
```powershell
# Fails - attempts to reach MariaDB
D:/provemaps_beta/venv/Scripts/python.exe -m pytest tests/

# Succeeds - forces SQLite
$env:DJANGO_SETTINGS_MODULE='settings.test'; D:/provemaps_beta/venv/Scripts/python.exe -m pytest tests/
```

### Issue 2: Outdated Assertions

Fifteen tests assert older interfaces:

- **Zabbix metrics (five failures)**: tests expect the label `success=True`; implementation publishes `status='success'` or `status='error'`.
- **Cache metrics (four failures)**: tests expect the label `hit`; implementation uses `result` with values `hit`, `miss`, or `success`.
- **Celery queue metrics (two failures)**: tests call `update_celery_queue_metrics` with a mapping; implementation accepts a queue name and depth as separate arguments.
- **Request ID middleware (four failures)**: tests inspect individual keyword arguments, but the implementation passes the entire set directly into `structlog.contextvars.bind_contextvars`.

---

## Coverage Snapshot

Run performed with SQLite in memory:
```
---------- coverage: platform win32, python 3.13.9-final-0 -----------
Name                             Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------------
core/metrics_custom.py              31      1      4      0    97%   145
core/middleware/request_id.py       30      0      8      0   100%
----------------------------------------------------------------------------
TOTAL                                61      1     12      0    99%

Outcome: 20 passed, 15 failed. Duration: 0.83 seconds
```

Highlights:
- `metrics_custom.py` lacks coverage for a single branch on line 145.
- `request_id.py` achieves full statement and branch coverage.
- The failing tests do not reduce coverage because they reach the relevant code paths. The failures stem from assertion logic only.

---

## Decisions Required

### Decision 1: Test Database Baseline

- **Recommended**: continue using SQLite in memory for unit tests.
  - Pros: fast (35 tests in under one second), isolated, no external services, easy to run on CI.
  - Cons: does not capture MariaDB specific SQL behaviour, though those differences are minimal for the covered modules.
  - Implementation: keep `settings/test.py` as-is and ensure the `DJANGO_SETTINGS_MODULE` environment variable is set.

- **Alternative (not recommended)**: depend on MariaDB for unit tests.
  - Pros: exercises the production SQL dialect.
  - Cons: requires Docker Compose or a dedicated server, slows the suite by an order of magnitude, complicates CI configuration, and introduces flakiness due to credentials and permissions.

### Decision 2: Fix the Test Failures

- **Recommended**: update affected tests to match the current interfaces.
  - Estimated effort: roughly thirty minutes.
  - Scope: adjust label expectations in `tests/test_metrics.py`; update the queue metric helper calls; allow middleware assertions to inspect the aggregated keyword dictionary or use helper functions for extraction.

- **Alternative (not recommended)**: revert the implementation to satisfy outdated tests.
  - This would undo the label normalisation performed in Phase 3 and require documentation updates.

### Decision 3: Execution Workflow

- **Recommended**: add a dedicated PowerShell script (`scripts/run_tests.ps1`) that sets the environment variable and runs pytest with coverage. This removes manual steps and prevents accidental MariaDB usage.
- Optionally, mirror the script in the `makefile` for consistency with Unix environments.

---

## Recommended Remediation Plan

### High Priority Tasks

1. **Fix the environment variable**
   - Add `Set-Item -Path Env:DJANGO_SETTINGS_MODULE -Value 'settings.test'` to the engineer profile or call it in scripts prior to pytest.

2. **Update failing assertions**
   - `tests/test_metrics.py`: align the expected label names (`status`, `result`) and update the Celery queue metric helper usage.
   - `tests/test_middleware.py`: adapt the mocks so they provide `__setitem__`, remove hard coded expectations for individual kwargs, and use the context dictionary instead.

3. **Create `scripts/run_tests.ps1`**
   ```powershell
   Write-Host "Running unit tests with SQLite in-memory..." -ForegroundColor Cyan
   $env:DJANGO_SETTINGS_MODULE = 'settings.test'
   & D:/provemaps_beta/venv/Scripts/python.exe -m pytest tests/ `
       --cov=core.metrics_custom `
       --cov=core.middleware.request_id `
       --cov-report=term-missing `
       --cov-report=html `
       --tb=short `
       -v
   if ($LASTEXITCODE -eq 0) {
       Write-Host "All tests passed." -ForegroundColor Green
       Write-Host "Coverage report: htmlcov/index.html" -ForegroundColor Cyan
   } else {
       Write-Host "Test failures detected." -ForegroundColor Red
       exit 1
   }
   ```

### Medium Priority Tasks

4. **Document the workflow**
   - Add a testing section to `OBSERVABILITY_PHASE3.md` describing the PowerShell script, direct pytest command, and coverage locations.

5. **Ignore build artefacts**
   - Ensure `.gitignore` contains `htmlcov/`, `.coverage`, `.coverage.*`, and `.pytest_cache/` entries.

### Low Priority (Optional)

6. **Integrate with CI/CD**
   - Example GitHub Actions job:
   ```yaml
   name: Tests

   on: [push, pull_request]

   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: '3.13'
         - run: pip install -r requirements.txt pytest pytest-cov pytest-django
         - env:
             DJANGO_SETTINGS_MODULE: settings.test
           run: pytest tests/ --cov=core --cov-report=xml
         - uses: codecov/codecov-action@v4
   ```

---

## Implementation Checklist

### Phase 1 (critical)
- [ ] Persist the environment variable configuration.
- [ ] Update ten assertions in `tests/test_metrics.py`.
- [ ] Update five assertions in `tests/test_middleware.py`.
- [ ] Add `scripts/run_tests.ps1` to the repository.
- [ ] Rerun the suite and confirm 35 of 35 tests pass.

### Phase 2 (documentation and hygiene)
- [ ] Update observability documentation with testing guidance.
- [ ] Add coverage artefacts to `.gitignore`.
- [ ] Optionally create `TESTING_STRATEGY.md` for quick reference.

### Phase 3 (quality automation)
- [ ] Wire the test script into GitHub Actions or another CI pipeline.
- [ ] Upload coverage reports if needed.

---

## Key Takeaways

- The implementation is stable; failing tests stem from outdated expectations.
- SQLite in memory keeps the feedback loop fast and reliable.
- Automating the setup prevents regressions caused by missing environment variables.
- Once the fifteen assertions are updated, Phase 4 can be marked complete.

---

**Next steps:** approve the recommended plan, adjust the tests, and re-run the suite to close Phase 4.
