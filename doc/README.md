# 📚 ProVeMaps Documentation

Welcome to the ProVeMaps (formerly MapsProveFiber) documentation: guides for developers, operators and contributors.

**Product version**: see [`VERSION`](../VERSION) and [`CHANGELOG.md`](../CHANGELOG.md)  
**Last Updated**: 2026-10-04  
**Architecture**: Modular Django multi-app (refactor of 2025-01) + Vue 3 SPA  
**Canonical operating manual**: [`CLAUDE.md`](../CLAUDE.md) — read it first; where a page here disagrees with it, `CLAUDE.md` wins.

> Documents that describe a state the project no longer has (the removed `zabbix_api`
> app, MariaDB/MySQL, 2025 sprint reports) live in [`archive/`](archive/README.md) with a
> "Histórico" banner. Nothing outside `archive/`, `reports/`, `roadmap/` and `releases/`
> should describe them as current. If you find one, open an `EV-` item (see `CLAUDE.md`).

---

## 🚀 Quick Start

New to ProVeMaps? Start here:

- **[Getting Started](getting-started/)** — installation, first run, basic configuration
- **[Development Guide](guides/DEVELOPMENT.md)** — daily commands, local setup, debugging
- **[Docker Guide](guides/DOCKER.md)** — run with Docker Compose (dev stack on port 8100)
- **[`DEPLOY.md`](../DEPLOY.md)** — production deployment (compose profiles, nginx + certbot)

---

## 📖 Documentation Structure

### 🎯 [Getting Started](getting-started/)
- `QUICKSTART.md` — quick installation and setup
- `INSTALLATION_GUIDE.md` — full installation walkthrough

### 📘 [Guides](guides/)
- `DEVELOPMENT.md` — local development, commands, workflows
- `DOCKER.md` — Docker Compose, containers, volumes
- `TESTING.md` — test suite, coverage, CI
- `OBSERVABILITY.md` — metrics, health checks, logging
- `POSTGIS_PATTERNS.md` — spatial query patterns
- `PLAYWRIGHT_BEST_PRACTICES.md` — E2E conventions
- `testing/` — validation checklists and E2E setup (`TESTS_E2E_SETUP.md`, `TESTING_GUIDE.md`, …)
- Feature guides: `CUSTOM_MAPS_SYSTEM.md`, `VIDEO_STREAMING_WHEP.md`, `CAMERA_INVENTORY_INTEGRATION.md`, `WHATSAPP_CONTACTS_IMPLEMENTATION.md`, …

### 🏗️ [Architecture](architecture/)
- `OVERVIEW.md` — modular design, apps and boundaries
- `MODULES.md` — each Django app and its responsibilities
- `DATA_FLOW.md` — request flows, caching (SWR), WebSocket
- `FIBER_PHYSICAL_HIERARCHY.md`, `FIBER_OSP_MANAGEMENT_SYSTEM.md` — fibre domain model
- `ADR/` — legacy ADR `001-fiber-route-builder.md` only; current decisions are in [`adr/`](adr/README.md)

### 📐 [ADRs](adr/) — Architecture Decision Records (MADR)
- `0005` — `CLAUDE.md` as the operating manual and the agent ecosystem
- `0006` — Central de Evolução (the `EV-` queue)
- `0007` — visual alignment with the CRM (design system, phases)

### 🔎 [Analysis](analysis/)
- `2026-10-04-levantamento-geral.md` — full project survey; origin of the `EV-` queue in `CLAUDE.md`

### 🔌 [API](api/)
- `ENDPOINTS.md` — endpoint reference (`/api/v1/inventory/*`, `/maps_view/api/*`, `/setup_app/api/*`)
- `AUTHENTICATION.md` — auth, sessions, 2FA, permissions
- `EXAMPLES.md` — usage examples

### ⚙️ [Operations](operations/)
- [`../DEPLOY.md`](../DEPLOY.md) — **the** deployment guide (root of the repo)
- `MONITORING.md` — Prometheus, Grafana, alerts
- `DOCKER_PRODUCTION.md` — production compose notes
- `REDIS_HA.md` — Redis high availability
- `dashboards/` — Grafana dashboards

### 🔧 [Troubleshooting](troubleshooting/)
- `DOCKER_CELERY_FIX.md`, `ZABBIX_IMPORT_FIX.md`, `SOLUCAO_ENDPOINTS_PORTAS.md`, `SOLUCAO_MODAL_FIBRAS_COMPLETA.md`, …

### 🤝 [Contributing](contributing/)
- `README.md` — how to contribute (see also `CLAUDE.md` §5 and §9)
- `CODE_STYLE.md`, `PR_GUIDELINES.md`, `TESTING_STANDARDS.md`

### 📦 [Releases](releases/)
Release notes of the 2025 "2.0.x" refactor line. The current changelog is [`../CHANGELOG.md`](../CHANGELOG.md).

### 🧭 [Roadmap](roadmap/) · 🗂️ [Reports](reports/) · 🏛️ [Archive](archive/README.md)
Historical planning, execution journals and superseded documents. They are kept for
traceability and **may describe components that no longer exist**.

---

## 🎯 Quick Links

### For Developers
- [Local setup](guides/DEVELOPMENT.md) · [Running tests](guides/TESTING.md) · [API examples](api/EXAMPLES.md) · [Architecture](architecture/OVERVIEW.md)

### For Operators
- [Deployment](../DEPLOY.md) · [Monitoring](operations/MONITORING.md) · [Troubleshooting](troubleshooting/)

### For Contributors
- [`CLAUDE.md`](../CLAUDE.md) · [Contributing](contributing/README.md) · [Code style](contributing/CODE_STYLE.md) · [PR guidelines](contributing/PR_GUIDELINES.md)

---

## 🏗️ Architecture Overview

```
backend/
├── core/            settings root, URLs, ASGI, middleware, auth + 2FA, health
├── inventory/       source of truth for the physical network (sites, devices, ports, cables, routes)
├── monitoring/      inventory + Zabbix state
├── integrations/zabbix/   resilient client and the single Zabbix gateway (zabbix_request)
├── maps_view/       dashboard, SWR cache, realtime (WebSocket)
├── setup_app/       runtime configuration, encrypted credentials
└── service_accounts/, telemetry/, gpon/, dwdm/
frontend/src/        Vue 3 SPA (Vite, Pinia, Chart.js, providers/maps/)
```

Details: [architecture/OVERVIEW.md](architecture/OVERVIEW.md) and `CLAUDE.md` §3–§4.

---

## 📊 System Status

| Endpoint | Purpose |
|----------|---------|
| `/healthz/` | Full health check (DB + cache + storage) |
| `/ready/` | Readiness probe |
| `/live/` | Liveness probe |
| `/metrics/` | Prometheus metrics |

---

## 🆘 Getting Help

- **Technical owner**: Paulo Marcelino — `paulo@simplesinternet.net.br`
- **Bugs and ideas**: open an `EV-` item in the quadro of `CLAUDE.md` (triage is Paulo's)
- **Deployment issues**: [`DEPLOY.md`](../DEPLOY.md)
- **API questions**: [api/ENDPOINTS.md](api/ENDPOINTS.md)

---

**Last Updated**: 2026-10-04 (EV-0021)
