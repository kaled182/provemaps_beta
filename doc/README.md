# 📚 MapsProveFiber Documentation

Welcome to the MapsProveFiber documentation! This wiki provides comprehensive guides for developers, operators, and contributors.

**Version**: v2.0.0  
**Last Updated**: 2025-01-07  
**Architecture**: Modular Django Multi-App

---

## 🚀 Quick Start

New to MapsProveFiber? Start here:

- **[Getting Started Guide](getting-started/)** — Installation, first run, basic configuration
- **[Development Guide](guides/DEVELOPMENT.md)** — Daily commands, local setup, debugging
- **[Docker Guide](guides/DOCKER.md)** — Run with Docker Compose

---

## 📖 Documentation Structure

### 🎯 [Getting Started](getting-started/)
First steps for new developers and operators.

- `QUICKSTART.md` — Quick installation and setup
- `TROUBLESHOOTING.md` — Common issues and solutions

### 📘 [Guides](guides/)
Day-to-day development and operations guides.

- `DEVELOPMENT.md` — Local development, commands, workflows
- `DOCKER.md` — Docker Compose, containers, volumes
- `TESTING.md` — Test suite, coverage, CI/CD
- `OBSERVABILITY.md` — Metrics, health checks, logging

### 🏗️ [Architecture](architecture/)
System design, module structure, and architecture decisions.

- `OVERVIEW.md` — Architecture v2.0.0 (modular design)
- `MODULES.md` — Description of each Django app
- `DATA_FLOW.md` — Request flows and data patterns
- `ADR/` — Architecture Decision Records

### 🔌 [API](api/)
REST API documentation and usage examples.

- `ENDPOINTS.md` — Complete endpoint reference
- `AUTHENTICATION.md` — Auth, permissions, RBAC
- `EXAMPLES.md` — Usage examples (cURL, Python, JavaScript)

### ⚙️ [Operations](operations/)
Deployment, monitoring, and production operations.

- `DEPLOYMENT.md` — Production deployment guide
- `MIGRATION.md` — Database migration procedures
- `MONITORING.md` — Prometheus, Grafana, alerts
- `TROUBLESHOOTING.md` — Diagnostic and resolution

### 📦 [Releases](releases/)
Version history, changelogs, and migration guides.

- `CHANGELOG.md` — Consolidated changelog
- `BREAKING_CHANGES.md` — All breaking changes by version
- `v2.0.0/` — Version 2.0.0 specific documentation

### 🤝 [Contributing](contributing/)
Guidelines for contributors.

- `README.md` — How to contribute
- `CODE_STYLE.md` — Code standards and conventions
- `PR_GUIDELINES.md` — Pull request guidelines
- `TESTING_STANDARDS.md` — Test quality standards

---

## 🎯 Quick Links

### For Developers
- [Local Setup](guides/DEVELOPMENT.md#local-setup)
- [Running Tests](guides/TESTING.md)
- [API Examples](api/EXAMPLES.md)
- [Architecture Overview](architecture/OVERVIEW.md)

### For Operators
- [Deployment Checklist](operations/DEPLOYMENT.md)
- [Monitoring Setup](operations/MONITORING.md)
- [Troubleshooting Guide](operations/TROUBLESHOOTING.md)
- [Migration Guide](operations/MIGRATION.md)

### For Contributors
- [Contributing Guide](contributing/README.md)
- [Code Style](contributing/CODE_STYLE.md)
- [Pull Request Guidelines](contributing/PR_GUIDELINES.md)

---

## 🔍 Finding Documentation

### By Topic

| Topic | Documentation |
|-------|---------------|
| **Installation** | [getting-started/QUICKSTART.md](getting-started/QUICKSTART.md) |
| **Development** | [guides/DEVELOPMENT.md](guides/DEVELOPMENT.md) |
| **Testing** | [guides/TESTING.md](guides/TESTING.md) |
| **Docker** | [guides/DOCKER.md](guides/DOCKER.md) |
| **API Reference** | [api/ENDPOINTS.md](api/ENDPOINTS.md) |
| **Architecture** | [architecture/OVERVIEW.md](architecture/OVERVIEW.md) |
| **Deployment** | [operations/DEPLOYMENT.md](operations/DEPLOYMENT.md) |
| **Monitoring** | [operations/MONITORING.md](operations/MONITORING.md) |
| **Troubleshooting** | [operations/TROUBLESHOOTING.md](operations/TROUBLESHOOTING.md) |
| **Changelog** | [releases/CHANGELOG.md](releases/CHANGELOG.md) |
| **Breaking Changes** | [releases/BREAKING_CHANGES.md](releases/BREAKING_CHANGES.md) |
| **Contributing** | [contributing/README.md](contributing/README.md) |

### By Role

| I am a... | Start here |
|-----------|------------|
| **New Developer** | [getting-started/QUICKSTART.md](getting-started/QUICKSTART.md) → [guides/DEVELOPMENT.md](guides/DEVELOPMENT.md) |
| **Frontend Developer** | [guides/DEVELOPMENT.md](guides/DEVELOPMENT.md) → [api/EXAMPLES.md](api/EXAMPLES.md) |
| **Backend Developer** | [architecture/OVERVIEW.md](architecture/OVERVIEW.md) → [guides/TESTING.md](guides/TESTING.md) |
| **DevOps Engineer** | [operations/DEPLOYMENT.md](operations/DEPLOYMENT.md) → [operations/MONITORING.md](operations/MONITORING.md) |
| **QA Engineer** | [guides/TESTING.md](guides/TESTING.md) → [api/ENDPOINTS.md](api/ENDPOINTS.md) |
| **Contributor** | [contributing/README.md](contributing/README.md) → [contributing/PR_GUIDELINES.md](contributing/PR_GUIDELINES.md) |

---

## 🏗️ Architecture Overview

MapsProveFiber v2.0.0 uses a **modular Django architecture**:

```
MapsProveFiber
├── inventory/        # Authoritative data (Site, Device, Port, Route)
├── monitoring/       # Health checks, combined status
├── integrations/     # External APIs (Zabbix client)
├── maps_view/        # Real-time dashboard
├── routes_builder/   # Fiber route calculation (deprecated)
└── core/             # Django settings, URLs, metrics
```

**Key Features**:
- ✅ Modular design with separation of concerns
- ✅ Resilient Zabbix client (circuit breaker, retry, metrics)
- ✅ REST API (`/api/v1/inventory/*`)
- ✅ Prometheus metrics + health checks
- ✅ Graceful degradation (Redis optional)

See [architecture/OVERVIEW.md](architecture/OVERVIEW.md) for detailed design.

---

## 📊 System Status

### Health Checks

| Endpoint | Purpose |
|----------|---------|
| `/healthz/` | Full health check (DB + cache + storage) |
| `/ready/` | Readiness probe (can serve traffic) |
| `/live/` | Liveness probe (process alive) |
| `/metrics/` | Prometheus metrics |

### Current Version

**v2.0.0** (Modular Architecture)
- ✅ All legacy code removed (`zabbix_api/`)
- ✅ Inventory as single source of truth
- ✅ Resilient integrations with circuit breaker
- ✅ API-first design
- ✅ Complete observability stack

See [releases/v2.0.0/](releases/v2.0.0/) for release notes.

---

## 🚨 Breaking Changes (v2.0.0)

⚠️ **Important**: Version 2.0.0 introduces breaking changes.

**Key Changes**:
- ❌ Module `zabbix_api` removed → use `inventory`, `monitoring`, `integrations/zabbix`
- ❌ Endpoints `/zabbix_api/*` removed → use `/api/v1/inventory/*`
- ✅ Migration guide available: [releases/v2.0.0/BREAKING_CHANGES.md](releases/v2.0.0/BREAKING_CHANGES.md)

---

## 🆘 Getting Help

### Documentation Issues
- **Missing information?** Open an issue: `Documentation: [topic]`
- **Broken links?** Report in GitHub issues
- **Suggestions?** See [contributing/README.md](contributing/README.md)

### Technical Support
- **Development issues**: Check [operations/TROUBLESHOOTING.md](operations/TROUBLESHOOTING.md)
- **Deployment issues**: See [operations/DEPLOYMENT.md](operations/DEPLOYMENT.md)
- **API questions**: Review [api/ENDPOINTS.md](api/ENDPOINTS.md)

---

## 📝 Contributing to Documentation

Help us improve the docs!

1. **Found a typo?** Fix it and submit a PR
2. **Missing documentation?** Create an issue or draft a new guide
3. **Unclear explanation?** Suggest improvements

See [contributing/README.md](contributing/README.md) for guidelines.

---

## 📚 Related Resources

### External Documentation
- [Django 5.x Documentation](https://docs.djangoproject.com/en/5.0/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Docker Documentation](https://docs.docker.com/)

### Project Links
- **GitHub Repository**: [kaled182/provemaps_beta](https://github.com/kaled182/provemaps_beta)
- **Issue Tracker**: GitHub Issues
- **Project Board**: GitHub Projects

---

**Last Updated**: 2025-01-07  
**Documentation Version**: v2.0.0  
**Maintained by**: Don Jonhn

**🎉 Welcome to MapsProveFiber! Let's build something great together.**
