# Reports Overview

This area centralizes historical markdown artifacts that used to live in the repository root. Documents are grouped by theme so you can quickly find delivery reports, compliance audits, and PR-ready material.

## Phase Reports (`phases/`)

| Document | Focus | Highlights |
|----------|-------|------------|
| [PHASE6_COMPLETION_REPORT.md](phases/PHASE6_COMPLETION_REPORT.md) | Structure reorganization recap | End-to-end summary of the backend/frontend/database split, metrics, and lessons learned. |
| [PHASE6_READY.md](phases/PHASE6_READY.md) | Execution checklist | Pre-flight checklist covering scripts, commits, tagging, and validation tasks before running the reorganization. |
| [PHASE7_DASHBOARD_PERFORMANCE.md](phases/PHASE7_DASHBOARD_PERFORMANCE.md) | Dashboard loading fixes | Root-cause analysis and redesign plan to remove 30s page loads via async data fetch and cache policy. |
| [PHASE8_CABLE_STATUS_CELERY.md](phases/PHASE8_CABLE_STATUS_CELERY.md) | Cable status background task | Architecture diagram, Celery schedule, and WebSocket integration for precomputed cable status. |
| [PHASE9_ASYNC_OPTICAL_LEVELS.md](phases/PHASE9_ASYNC_OPTICAL_LEVELS.md) | Optical telemetry decoupling | Strategy to eliminate synchronous Zabbix reads by using cached optical snapshots and Celery refresh. |
| [PHASE10_POSTGIS_MIGRATION_PLAN.md](phases/PHASE10_POSTGIS_MIGRATION_PLAN.md) | Database migration plan | Step-by-step roadmap for moving from MariaDB to PostGIS with rollback guidance and risk assessment. |
| [PHASE10_IMPLEMENTATION_SUMMARY.md](phases/PHASE10_IMPLEMENTATION_SUMMARY.md) | Execution log | Timeline of the PostGIS migration work, blockers, and resolutions. |
| [PHASE10_DEV_NOTES.md](phases/PHASE10_DEV_NOTES.md) | Developer notebook | Scratchpad of in-progress findings, manual commands, and follow-up items captured during Phase 10. |
| [PHASE10_COMMIT_MESSAGE.md](phases/PHASE10_COMMIT_MESSAGE.md) | Release messaging | Canonical commit body used for the Phase 10 merge, ready for reuse in PR descriptions. |
| [PHASE10_TESTING.md](phases/PHASE10_TESTING.md) | Validation evidence | Test plan, datasets, and validation checklist for the PostGIS rollout. |

## Compliance Reports (`compliance/`)

| Document | Focus | Highlights |
|----------|-------|------------|
| [CACHE_COMPLIANCE_VERIFIED.md](compliance/CACHE_COMPLIANCE_VERIFIED.md) | Cache policy verification | Evidence that cable status caching follows the 120s SLA with CLI output and screenshots. |
| [CACHE_TIMEOUT_COMPLIANCE.md](compliance/CACHE_TIMEOUT_COMPLIANCE.md) | Timeout inventory | Code excerpts consolidating all cache timeout values confirming they remain under two minutes. |

## PR & Status Updates

| Document | Focus | Highlights |
|----------|-------|------------|
| [PR_STATUS.md](status/PR_STATUS.md) | Phase 5 readiness log | Step-by-step checklist for preparing and submitting the Phase 5 modularization PR. |
| [PR_PHASE5_COMPLETE.md](pr/PR_PHASE5_COMPLETE.md) | Pull request body | Final PR description, including scope, validation, breaking changes, and deployment notes. |

## Related Process References

- [doc/process/ANALYSIS_FOLDER_RESTRUCTURE.md](../process/ANALYSIS_FOLDER_RESTRUCTURE.md) — Impact study backing the folder restructuring.
- [doc/roadmap/ROADMAP_NEXT_STEPS.md](../roadmap/ROADMAP_NEXT_STEPS.md) — Multi-phase execution plan with success metrics.
- [doc/roadmap/ROADMAP_VUE3_PREPARATION.md](../roadmap/ROADMAP_VUE3_PREPARATION.md) — Vue 3 migration readiness plan tied to the async backend work.

> Need something else? Check the top-level [Documentation README](../README.md) for the full knowledge base map.
