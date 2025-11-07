
# MapsProveFiber

MapsProveFiber is a Django platform that aggregates Zabbix telemetry and exposes two integrated web experiences:
- **Maps Dashboard (`/maps_view/dashboard/`)** for real-time monitoring, diagnostics, and host status.
- **Fiber Route Builder (`/routes_builder/fiber-route-builder/`)** for planning optical routes (KML import) and power analysis.

The solution ships with native observability (Prometheus, structured logging, query tracing), asynchronous workloads with Celery, and secure integrations via `setup_app`.

---

## Quick Technical Overview
- **Framework:** Django 5.x, Channels, Celery
- **Frontend:** Django templates plus focused JS modules
- **Persistence:** MariaDB/MySQL (production) or SQLite (local dev)
- **Messaging/Cache:** Redis
- **Recommended infra:** Docker Compose for development; managed Redis and dedicated database for production
- **Observability:** `/healthz`, `/ready`, `/live`, `/celery/status`, Prometheus metrics at `/metrics/`

Key Django apps:
- `core`: settings, root URLs, metrics, middleware
- `maps_view`: network dashboard and visualizations
- `inventory`: authoritative models (Site, Device, Port, Route) + REST APIs at `/api/v1/inventory/`
- `monitoring`: health checks, combined status from inventory + Zabbix
- `integrations/zabbix`: resilient Zabbix API client (retry, circuit breaker, Prometheus metrics)
- `routes_builder`: _(zombie app - kept for migration compatibility only)_
- `setup_app`: secure credential management and configuration

---

## Documentation (v2.0.0)
Nova documentação reorganizada em uma estrutura limpa. Índice principal: [`doc/README.md`](./doc/README.md) ou interface web em `/setup_app/docs/`.

### Estrutura Atual

| Categoria | Pasta | Conteúdo Principal | Acesso Web |
|-----------|-------|--------------------|------------|
| Getting Started | `doc/getting-started/` | QUICKSTART (unificado), Troubleshooting | `/setup_app/docs/getting-started/QUICKSTART.md` |
| Guias (Dev & Ops) | `doc/guides/` | DEVELOPMENT, TESTING, DOCKER, OBSERVABILITY | `/setup_app/docs/guides/DEVELOPMENT.md` |
| Arquitetura | `doc/architecture/` | OVERVIEW, MODULES, DATA_FLOW, ADR | `/setup_app/docs/architecture/OVERVIEW.md` |
| API | `doc/api/` | ENDPOINTS, AUTHENTICATION, EXAMPLES | `/setup_app/docs/api/ENDPOINTS.md` |
| Operações | `doc/operations/` | DEPLOYMENT, MONITORING, TROUBLESHOOTING | `/setup_app/docs/operations/DEPLOYMENT.md` |
| Releases | `doc/releases/` | CHANGELOG, BREAKING_CHANGES, v2.0.0 | `/setup_app/docs/releases/README.md` |
| Contribuição | `doc/contributing/` | CODE_STYLE, PR_GUIDELINES, TESTING_STANDARDS | `/setup_app/docs/contributing/README.md` |
| Segurança (legado mantido) | `doc/security/` | SECURITY.md, práticas | `/setup_app/docs/security/SECURITY.md` |

### Acesso Rápido
- Índice Web: `http://localhost:8000/setup_app/docs/`
- Quebra de mudanças v2.0.0: [`doc/releases/v2.0.0/BREAKING_CHANGES_v2.0.0.md`](./doc/releases/v2.0.0/BREAKING_CHANGES_v2.0.0.md)
- Arquitetura: [`doc/architecture/OVERVIEW.md`](./doc/architecture/OVERVIEW.md)
- Deploy: [`doc/operations/DEPLOYMENT.md`](./doc/operations/DEPLOYMENT.md)
- API: [`doc/api/ENDPOINTS.md`](./doc/api/ENDPOINTS.md)
- Contribuir: [`doc/contributing/README.md`](./doc/contributing/README.md)

### O que foi Removido
Pastas e relatórios antigos (performance phases, debug reports, módulos legados) foram eliminados para reduzir ruído. Referências antigas nesta página que apontavam para `doc/developer/`, `doc/reference/`, `doc/reference-root/` e relatórios históricos agora estão obsoletas.

### Próximos Ajustes
- Consolidar QUICKSTART_LOCAL + TUTORIAL_DOCKER em um único `QUICKSTART.md`
- Unificar checklist de deployment dentro de `DEPLOYMENT.md`
- Preencher placeholders: MODULES.md, DATA_FLOW.md, ENDPOINTS.md completo

> Para navegação centralizada use o índice: [`doc/README.md`](./doc/README.md) ou o menu "Docs" na aplicação web.

---

## Getting Started
1. Ler o guia unificado: [`doc/getting-started/QUICKSTART.md`](./doc/getting-started/QUICKSTART.md)
2. Configure Docker using: [`doc/developer/DOCKER_SETUP.md`](./doc/developer/DOCKER_SETUP.md)
3. Run `docker compose up` (or `make run`) after adjusting `.env`
4. Visit `http://localhost:8000` and confirm the health checks at `/healthz`

For a non-Docker workflow, follow the local development instructions (runserver, migrations, superuser) in the same directory.

---

## Operations and Observability
- Health endpoints: see [`doc/developer/OBSERVABILITY.md`](./doc/developer/OBSERVABILITY.md)
- Celery and Redis monitoring: [`doc/reference/CELERY_MONITORING_CHECKLIST.md`](./doc/reference/CELERY_MONITORING_CHECKLIST.md) and [`doc/reference/REDIS_HIGH_AVAILABILITY.md`](./doc/reference/REDIS_HIGH_AVAILABILITY.md)
- Custom Prometheus metrics: [`doc/reference/prometheus_static_version.md`](./doc/reference/prometheus_static_version.md)

---

## Security
- Full practices in [`doc/security/SECURITY.md`](./doc/security/SECURITY.md)
- Generate/store Fernet keys through `setup_app`
- Never commit secrets; keep a secure `.env` per environment
- Review OWASP guidance and hardening tips in [`doc/reference/CONFIGURACAO_PERSISTENTE.md`](./doc/reference/CONFIGURACAO_PERSISTENTE.md)

---

## Contribution and Processes
- Development flow and essential commands: [`doc/developer/COMANDOS_RAPIDOS.md`](./doc/developer/COMANDOS_RAPIDOS.md)
- Contribution, PR, and i18n guidelines: [`doc/process/CONTRIBUTING.md`](./doc/process/CONTRIBUTING.md) and [`doc/reference/i18n_and_pr_guidelines.md`](./doc/reference/i18n_and_pr_guidelines.md)
- Automation and agent responsibilities: [`doc/process/AGENTS.md`](./doc/process/AGENTS.md)

---

## History and Planning
- Latest critical changes: [`doc/releases/CHANGELOG_20251025_REDIS.md`](./doc/releases/CHANGELOG_20251025_REDIS.md)
- Technical reports, performance updates, and roadmap: browse [`doc/reference/`](./doc/reference/)

---

## Next Steps
- Review test plans and checklists before opening pull requests
- Configure Prometheus/Grafana dashboards using the available metrics
- Evaluate upgrading Redis to a highly available deployment before production

---

## Daily Development
- Run `docker compose up` or `make run` per [`doc/developer/DOCKER_SETUP.md`](./doc/developer/DOCKER_SETUP.md).
- Routine shortcuts: [`doc/developer/COMANDOS_RAPIDOS.md`](./doc/developer/COMANDOS_RAPIDOS.md).
- Local observability (health, metrics, Celery): [`doc/developer/OBSERVABILITY.md`](./doc/developer/OBSERVABILITY.md).
- Contribution and PR conventions: [`doc/process/CONTRIBUTING.md`](./doc/process/CONTRIBUTING.md).

## Testing and Quality
- Quick testing guide: [`doc/reference/TESTING_QUICK_REFERENCE.md`](./doc/reference/TESTING_QUICK_REFERENCE.md).
- Detailed plans and bug reports: [`doc/reference/TEST_ERRORS_DETAILED_REPORT.md`](./doc/reference/TEST_ERRORS_DETAILED_REPORT.md).
- Recommended execution: `pytest -q` (or `make test`), and `pytest --cov --cov-report=term-missing` for coverage.
- CI: GitHub Actions in `.github/workflows/tests.yml` runs the full suite with `--cov-fail-under=45` on pushes/PRs to `main` and `inicial`.

## Deployment and Operations
- Full deployment checklist: [`doc/operations/DEPLOYMENT.md`](./doc/operations/DEPLOYMENT.md).
- Redis HA and graceful degradation: [`doc/reference/REDIS_HIGH_AVAILABILITY.md`](./doc/reference/REDIS_HIGH_AVAILABILITY.md) and [`doc/reference/REDIS_GRACEFUL_DEGRADATION.md`](./doc/reference/REDIS_GRACEFUL_DEGRADATION.md).
- Service status and quick troubleshooting: [`doc/operations/STATUS_SERVICOS.md`](./doc/operations/STATUS_SERVICOS.md).
- Continuous operations checklist: [`doc/reference/operations_checklist.md`](./doc/reference/operations_checklist.md).

## Support
- Issue tracker: [GitHub Issues](https://github.com/kaled182/provemaps_beta/issues)
- Technical discussions: [GitHub Discussions](https://github.com/kaled182/provemaps_beta/discussions)
- Security and responsible disclosure: [`doc/security/SECURITY.md`](./doc/security/SECURITY.md)

---

### © 2025 — Project **MapsProveFiber**
Maintained by Simples Internet.  
Documentation and code are released under the MIT License.
