# Reference Library - MapsProveFiber

> Platform focus: all instructions in this directory assume a Linux shell (bash). Do not convert examples to PowerShell or Windows-specific tooling. The project is developed and validated inside Linux containers (Docker). On Windows we rely only on VS Code and Docker Desktop for editing and orchestration, while staging and production environments run the same Linux containers end to end.

This directory gathers deep-dive documentation covering architecture, advanced operations, and historical context. Use it as a reference after reading the introductory guides in [`doc/getting-started/`](../getting-started/) and [`doc/developer/`](../developer/).

## Quick navigation
- **Architecture and ADRs**: [`adr_fiber_route_builder.md`](./adr_fiber_route_builder.md), [`TECHNICAL_REVIEW.md`](./TECHNICAL_REVIEW.md)
- **Infrastructure and observability**: [`REDIS_HIGH_AVAILABILITY.md`](./REDIS_HIGH_AVAILABILITY.md), [`prometheus_static_version.md`](./prometheus_static_version.md), [`operations_checklist.md`](./operations_checklist.md)
- **Performance and scalability**: series from [`performance_phase1.md`](./performance_phase1.md) to [`performance_phase6.md`](./performance_phase6.md)
- **Testing and quality**: [`TESTING_QUICK_REFERENCE.md`](./TESTING_QUICK_REFERENCE.md), [`TEST_ERRORS_DETAILED_REPORT.md`](./TEST_ERRORS_DETAILED_REPORT.md), [`TESTING_WITH_MARIADB.md`](./TESTING_WITH_MARIADB.md)
- **Historical reports**: [`PROJECT_STATUS_REPORT.md`](./PROJECT_STATUS_REPORT.md), [`FINAL_CONSOLIDATED_REPORT.md`](./FINAL_CONSOLIDATED_REPORT.md), [`FASE4_SUCCESS_REPORT.md`](./FASE4_SUCCESS_REPORT.md)
- **App-specific guides**:
  - [`maps_view/`](./maps_view/) - dashboard and map integration guides
  - [`modules/`](./modules/) - legacy documentation for fiber builder JS modules

## How to use
1. **Planning and architecture**: start with the ADRs and technical reviews to understand historical decisions.
2. **Production operations**: review the Redis HA guide, operational checklist, and Prometheus alert catalog before shipping new releases.
3. **Performance and troubleshooting**: rely on the performance phase reports and error analysis documents for diagnostics.
4. **Testing**: follow the test plans and checklists to secure QA coverage for critical releases.

## Conventions
- File names and headings use snake_case.
- Links stay relative to this folder for easy reading in GitHub or VS Code.
- Historical content remains intact for traceability, with older documents marked at the top when needed.

> Tip: use `Ctrl+P` in VS Code and search for the file name to jump directly to any reference.
