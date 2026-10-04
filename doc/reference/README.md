# Reference Library - MapsProveFiber

> Platform focus: all instructions in this directory assume a Linux shell (bash). Do not convert examples to PowerShell or Windows-specific tooling. The project is developed and validated inside Linux containers (Docker). On Windows we rely only on VS Code and Docker Desktop for editing and orchestration, while staging and production environments run the same Linux containers end to end.

This directory gathers deep-dive documentation covering architecture, advanced operations, and historical context. Use it as a reference after reading the introductory guides in [`doc/getting-started/`](../getting-started/) and [`doc/developer/`](../developer/).

## Quick navigation
- **Architecture and ADRs**: [`adr_fiber_route_builder.md`](./adr_fiber_route_builder.md), [`API_FIBER_ROUTES_SPEC.md`](./API_FIBER_ROUTES_SPEC.md); current architectural decisions live in [`doc/adr/`](../adr/README.md)
- **Infrastructure and observability**: [`../operations/REDIS_HA.md`](./../operations/REDIS_HA.md), [`REDIS_GRACEFUL_DEGRADATION.md`](./REDIS_GRACEFUL_DEGRADATION.md), [`SETUP_REDIS_WINDOWS.md`](./SETUP_REDIS_WINDOWS.md), [`PROMETHEUS_ALERTS.md`](./PROMETHEUS_ALERTS.md), [`CELERY_STATUS_ENDPOINT.md`](./CELERY_STATUS_ENDPOINT.md), [`CELERY_MONITORING_CHECKLIST.md`](./CELERY_MONITORING_CHECKLIST.md)
- **Frontend and integrations**: [`GOOGLE_MAPS_API_SETUP.md`](./GOOGLE_MAPS_API_SETUP.md), [`cache_busting.md`](./cache_busting.md), [`i18n_and_pr_guidelines.md`](./i18n_and_pr_guidelines.md)
- **App-specific guides**: [`monitoring_dashboard_flow.md`](./monitoring_dashboard_flow.md) - SWR sequence and API ownership
- **Testing and quality**: [`doc/guides/TESTING.md`](../guides/TESTING.md), [`doc/testing/`](../testing/README.md) and [`CLAUDE.md`](../../CLAUDE.md) section 9
- **Production deployment**: [`DEPLOY.md`](../../DEPLOY.md) (root) and [`doc/operations/`](../operations/README.md)
- **Historical reports** (archived, do not describe the current system): [`TECHNICAL_REVIEW.md`](../archive/2025-historico/TECHNICAL_REVIEW.md), [`TESTING_QUICK_REFERENCE.md`](../archive/2025-historico/TESTING_QUICK_REFERENCE.md), [`TESTING_WITH_MARIADB.md`](../archive/2025-historico/TESTING_WITH_MARIADB.md), [`operations_checklist.md`](../archive/2025-historico/operations_checklist.md), [`prometheus_static_version.md`](../archive/2025-historico/prometheus_static_version.md), [`translation_report.md`](../archive/2025-historico/translation_report.md), [`FRONTEND_TESTING_MANUAL_PLAN.md`](../archive/2025-historico/FRONTEND_TESTING_MANUAL_PLAN.md) (histórico; index in [`doc/archive/README.md`](../archive/README.md))

## How to use
1. **Planning and architecture**: start with the ADRs in [`doc/adr/`](../adr/README.md) and the notes above to understand historical decisions.
2. **Production operations**: review [`DEPLOY.md`](../../DEPLOY.md), the Redis HA guide, and the Prometheus alert catalog before shipping new releases.
3. **Troubleshooting**: consult the case notes in [`doc/troubleshooting/`](../troubleshooting/) and the Celery/Prometheus references above for diagnostics.
4. **Testing**: follow [`doc/guides/TESTING.md`](../guides/TESTING.md) and the checklists in [`doc/guides/testing/`](../guides/testing/) to secure QA coverage for critical releases.

## Conventions
- File names and headings use snake_case.
- Links stay relative to this folder for easy reading in GitHub or VS Code.
- Historical content remains intact for traceability, with older documents marked at the top when needed.

> Tip: use `Ctrl+P` in VS Code and search for the file name to jump directly to any reference.
