# doc/archive — documentos históricos

> O que está aqui **não descreve o sistema atual**. Guarda-se pelo valor histórico
> (decisões, números medidos, o que se tentou). Para o estado presente: `CLAUDE.md`,
> `DEPLOY.md`, `doc/architecture/`, `doc/adr/`.

## 2025-historico/ (arquivado em 2026-10-04, EV-0021)

Documentos que citavam a app `zabbix_api` (removida em 2025-01; hoje `inventory/`,
`monitoring/` e `integrations/zabbix/`), MariaDB/MySQL (o produto corre PostgreSQL 16 +
PostGIS), ou relatórios de sprints/fases de 2025. Cada ficheiro tem um banner no topo.
As tabelas `zabbix_api_site`, `zabbix_api_device`… continuam a existir no banco por
`Meta.db_table` — só o módulo Python desapareceu.

| Ficheiro | Caminho original | Título |
|---|---|---|
| [`REORGANIZATION_COMPLETE.md`](2025-historico/REORGANIZATION_COMPLETE.md) | `doc/REORGANIZATION_COMPLETE.md` | 📝 Documentation Reorganization — Final Summary |
| [`REORGANIZATION_COMPLETION_REPORT.md`](2025-historico/REORGANIZATION_COMPLETION_REPORT.md) | `doc/REORGANIZATION_COMPLETION_REPORT.md` | 📚 Documentation Reorganization Report |
| [`REORGANIZATION_PLAN.md`](2025-historico/REORGANIZATION_PLAN.md) | `doc/REORGANIZATION_PLAN.md` | 📚 Plano de Reorganização da Documentação v2.0.0 |
| [`LINK_VALIDATION_REPORT.md`](2025-historico/LINK_VALIDATION_REPORT.md) | `doc/LINK_VALIDATION_REPORT.md` | 🔗 Link Validation Report |
| [`REFATORAR.md`](2025-historico/REFATORAR.md) | `doc/developer/REFATORAR.md` | Modules & Editions — MapsProve (Rascunho) |
| [`FRONTEND_TESTING_MANUAL_PLAN.md`](2025-historico/FRONTEND_TESTING_MANUAL_PLAN.md) | `doc/reference/FRONTEND_TESTING_MANUAL_PLAN.md` | Manual Test Plan - Modular Frontend |
| [`TECHNICAL_REVIEW.md`](2025-historico/TECHNICAL_REVIEW.md) | `doc/reference/TECHNICAL_REVIEW.md` | Technical Review - Modified Files |
| [`TESTING_QUICK_REFERENCE.md`](2025-historico/TESTING_QUICK_REFERENCE.md) | `doc/reference/TESTING_QUICK_REFERENCE.md` | Quick Reference – Testing with MariaDB |
| [`TESTING_WITH_MARIADB.md`](2025-historico/TESTING_WITH_MARIADB.md) | `doc/reference/TESTING_WITH_MARIADB.md` | MariaDB Testing Guide (Docker) |
| [`operations_checklist.md`](2025-historico/operations_checklist.md) | `doc/reference/operations_checklist.md` | Operations Checklist - Django Maps |
| [`prometheus_static_version.md`](2025-historico/prometheus_static_version.md) | `doc/reference/prometheus_static_version.md` | Cache Busting and Prometheus Integration Summary |
| [`translation_report.md`](2025-historico/translation_report.md) | `doc/reference/translation_report.md` | Translation Status Report |
| [`DEPLOYMENT.md`](2025-historico/DEPLOYMENT.md) | `doc/operations/DEPLOYMENT.md` | Production Deployment Guide - MapsProveFiber |
| [`DEPLOYMENT_CHECKLIST_v2.0.0.md`](2025-historico/DEPLOYMENT_CHECKLIST_v2.0.0.md) | `doc/operations/DEPLOYMENT_CHECKLIST_v2.0.0.md` | DEPLOYMENT_CHECKLIST_v2.0.0.md (DEPRECATED) |
| [`MIGRATION_PRODUCTION_GUIDE.md`](2025-historico/MIGRATION_PRODUCTION_GUIDE.md) | `doc/operations/MIGRATION_PRODUCTION_GUIDE.md` | Guia de Aplicação da Migração em Produção |
| [`POSTGIS_SETUP_GUIDE.md`](2025-historico/POSTGIS_SETUP_GUIDE.md) | `doc/operations/POSTGIS_SETUP_GUIDE.md` | PostGIS Setup Guide (Phase 10) |
| [`STATUS_SERVICOS.md`](2025-historico/STATUS_SERVICOS.md) | `doc/operations/STATUS_SERVICOS.md` | Service Status - MapsProveFiber |
| [`MONITORING_COMMANDS_PHASE1.md`](2025-historico/MONITORING_COMMANDS_PHASE1.md) | `doc/operations/MONITORING_COMMANDS_PHASE1.md` | Monitoring Commands - Phase 1 Canary Rollout |
| [`SPRINT1_DEPLOYMENT_EXECUTION.md`](2025-historico/SPRINT1_DEPLOYMENT_EXECUTION.md) | `doc/operations/SPRINT1_DEPLOYMENT_EXECUTION.md` | Sprint 1 - Deployment Execution Checklist |
| [`SPRINT1_DEPLOYMENT_GUIDE.md`](2025-historico/SPRINT1_DEPLOYMENT_GUIDE.md) | `doc/operations/SPRINT1_DEPLOYMENT_GUIDE.md` | Sprint 1 Deployment Guide |
| [`SPRINT1_DEPLOYMENT_PACKAGE.md`](2025-historico/SPRINT1_DEPLOYMENT_PACKAGE.md) | `doc/operations/SPRINT1_DEPLOYMENT_PACKAGE.md` | Sprint 1 Deployment Package |
| [`SPRINT1_DEPLOYMENT_READY.md`](2025-historico/SPRINT1_DEPLOYMENT_READY.md) | `doc/operations/SPRINT1_DEPLOYMENT_READY.md` | Sprint 1 Deployment - Ready to Execute 🚀 |
| [`SPRINT1_DEPLOYMENT_REPORT.md`](2025-historico/SPRINT1_DEPLOYMENT_REPORT.md) | `doc/operations/SPRINT1_DEPLOYMENT_REPORT.md` | Sprint 1 - Deployment Report |
| [`SPRINT1_DOCKER_DEPLOYMENT_REPORT.md`](2025-historico/SPRINT1_DOCKER_DEPLOYMENT_REPORT.md) | `doc/operations/SPRINT1_DOCKER_DEPLOYMENT_REPORT.md` | Sprint 1 - Docker Deployment Report |
| [`SPRINT1_ENVIRONMENT_CONFIG.md`](2025-historico/SPRINT1_ENVIRONMENT_CONFIG.md) | `doc/operations/SPRINT1_ENVIRONMENT_CONFIG.md` | Sprint 1 Environment Configuration |
| [`SPRINT1_PREDEPLOYMENT_VALIDATION.md`](2025-historico/SPRINT1_PREDEPLOYMENT_VALIDATION.md) | `doc/operations/SPRINT1_PREDEPLOYMENT_VALIDATION.md` | Sprint 1 Pre-Deployment Validation |
| [`SPRINT1_QA_CHECKLIST.md`](2025-historico/SPRINT1_QA_CHECKLIST.md) | `doc/operations/SPRINT1_QA_CHECKLIST.md` | Sprint 1 QA Testing Checklist |
| [`SPRINT1_ROLLBACK_PLAN.md`](2025-historico/SPRINT1_ROLLBACK_PLAN.md) | `doc/operations/SPRINT1_ROLLBACK_PLAN.md` | Sprint 1 Rollback Plan |
| [`DEPLOY_EXECUTION_PHASE1.md`](2025-historico/DEPLOY_EXECUTION_PHASE1.md) | `doc/operations/DEPLOY_EXECUTION_PHASE1.md` | Deploy Staging - Phase 1 Execution Checklist |
| [`DEPLOY_PHASE1_COMPLETED.md`](2025-historico/DEPLOY_PHASE1_COMPLETED.md) | `doc/operations/DEPLOY_PHASE1_COMPLETED.md` | Phase 1 Deploy - COMPLETED |
| [`DEPLOY_STAGING_SPRINT3.md`](2025-historico/DEPLOY_STAGING_SPRINT3.md) | `doc/operations/DEPLOY_STAGING_SPRINT3.md` | Deploy Staging - Sprint 3 |
| [`PHASE7_DAY7_VERIFICATION.md`](2025-historico/PHASE7_DAY7_VERIFICATION.md) | `doc/operations/PHASE7_DAY7_VERIFICATION.md` | Phase 7 Day 7 - Monitoring Stack Verification Checklist |
| [`PHASE7_DEPLOYMENT_PLAN.md`](2025-historico/PHASE7_DEPLOYMENT_PLAN.md) | `doc/operations/PHASE7_DEPLOYMENT_PLAN.md` | Phase 7 - Spatial Radius Search Production Deployment Plan |
| [`PHASE10_STAGING_DEPLOYMENT.md`](2025-historico/PHASE10_STAGING_DEPLOYMENT.md) | `doc/operations/PHASE10_STAGING_DEPLOYMENT.md` | Phase 10 Staging Deployment Guide |
| [`SMOKE_TEST_REPORT_PHASE1.md`](2025-historico/SMOKE_TEST_REPORT_PHASE1.md) | `doc/operations/SMOKE_TEST_REPORT_PHASE1.md` | Smoke Test Execution Report - Sprint 3 Deploy |
| [`ROLLOUT_MONITORING.md`](2025-historico/ROLLOUT_MONITORING.md) | `doc/operations/ROLLOUT_MONITORING.md` | 📊 Guia de Monitoramento - Rollout Vue Dashboard |
| [`MONITORING_SETUP.md`](2025-historico/MONITORING_SETUP.md) | `doc/operations/MONITORING_SETUP.md` | Phase 7 - Monitoring Setup Guide |
| [`INSTRUCTIONS_CREATE_PR.md`](2025-historico/INSTRUCTIONS_CREATE_PR.md) | `doc/contributing/INSTRUCTIONS_CREATE_PR.md` | 🚀 Como Criar o Pull Request |

Dois ficheiros em `doc/architecture/ADR/` (`000-technical-review.md`,
`004-refactoring-plan.md`) eram cópias byte a byte de `TECHNICAL_REVIEW.md` e
`REFATORAR.md` e foram removidos; as cópias arquivadas são as de `reference/` e
`developer/`.

## Outros

- `roadmap/` — roadmaps antigos.
- `FIX_MENU_CACHE_BUSTING.md`, `NETWORK_DESIGN_FIXED.md`, `TESTE_NAVEGADOR.md`,
  `VALIDACAO_WEB.md` — notas de correção de 2025.
