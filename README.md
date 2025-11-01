
# MapsProveFiber

MapsProveFiber é uma plataforma Django que reúne telemetria do Zabbix e entrega duas experiências web integradas:
- **Maps Dashboard (`/maps_view/dashboard/`)** para monitoramento em tempo real, diagnósticos e status de hosts.
- **Fiber Route Builder (`/routes_builder/fiber-route-builder/`)** para planejamento, importação de rotas ópticas (KML) e análise de potência.

A solução oferece observabilidade nativa (Prometheus, logs estruturados, rastreamento de queries), tarefas assíncronas com Celery e integrações seguras via `setup_app`.

---

## Visão Técnica Rápida
- **Framework:** Django 5.x, Channels, Celery
- **Frontend:** Templates Django + módulos JS especializados
- **Persistência:** MariaDB/MySQL (produção) ou SQLite (dev local)
- **Mensageria/Cache:** Redis
- **Infra recomendada:** Docker Compose em desenvolvimento; Redis gerenciado e banco dedicado em produção
- **Observabilidade:** `/healthz`, `/ready`, `/live`, `/celery/status`, métricas Prometheus em `/metrics/`

Principais apps Django:
- `core`: settings, URLs raiz, métricas, middlewares
- `maps_view`: dashboard de rede e visualizações
- `routes_builder`: rotas ópticas, importação KML, metadados
- `inventory`: modelos (Site, Device, Port) e sincronizações
- `setup_app`: gerenciamento seguro de credenciais e configuração
- `zabbix_api`: integração resiliente com a API do Zabbix

---

## Mapa da Documentação
Toda a documentação foi consolidada na pasta [`doc/`](./doc/). Use os guias abaixo como ponto de partida:

- **Início Rápido:** [`doc/getting-started/`](./doc/getting-started/) — onboarding local e tutorial Docker
- **Guia do Desenvolvedor:** [`doc/developer/`](./doc/developer/) — comandos diários, setup, observabilidade
- **Operações & Deploy:** [`doc/operations/`](./doc/operations/) — procedimentos, status de serviços, guias de produção
- **Processos & Contribuição:** [`doc/process/`](./doc/process/) — papéis, contribuição, governança
- **Segurança & Compliance:** [`doc/security/`](./doc/security/) — recomendações de secrets, OWASP, controles
- **Releases & Histórico:** [`doc/releases/`](./doc/releases/) — changelogs e relatórios
- **Referências Técnicas:** [`doc/reference/`](./doc/reference/) — ADRs, planos de teste, guias de infraestrutura, Redis HA, métricas
- **API & Especificações:** [`doc/reference-root/`](./doc/reference-root/) — documentação pública de API

> Para dependências externas e notas legadas consulte `doc/reference/` (subpastas `maps_view/` e `modules/`).

---

## Como Começar
1. Leia o guia de onboarding local: [`doc/getting-started/QUICKSTART_LOCAL.md`](./doc/getting-started/QUICKSTART_LOCAL.md)
2. Configure o ambiente Docker seguindo: [`doc/developer/DOCKER_SETUP.md`](./doc/developer/DOCKER_SETUP.md)
3. Execute `docker compose up` (ou `make run`) após ajustar `.env`
4. Acesse `http://localhost:8000` e confirme health checks em `/healthz`

Para executar sem Docker, consulte as instruções de desenvolvimento local (`runserver`, migrações, superusuário) no mesmo diretório.

---

## Operação e Observabilidade
- Endpoints de saúde: detalhes em [`doc/developer/OBSERVABILITY.md`](./doc/developer/OBSERVABILITY.md)
- Monitoramento Celery e Redis: veja [`doc/reference/CELERY_MONITORING_CHECKLIST.md`](./doc/reference/CELERY_MONITORING_CHECKLIST.md) e [`doc/reference/REDIS_HIGH_AVAILABILITY.md`](./doc/reference/REDIS_HIGH_AVAILABILITY.md)
- Métricas Prometheus customizadas: [`doc/reference/prometheus_static_version.md`](./doc/reference/prometheus_static_version.md)

---

## Segurança
- Práticas completas em [`doc/security/SECURITY.md`](./doc/security/SECURITY.md)
- Geração/armazenamento de chaves Fernet via `setup_app`
- Segredos nunca versionados; use `.env` seguro por ambiente
- Consulte também a diretriz OWASP e recomendações de hardening em [`doc/reference/CONFIGURACAO_PERSISTENTE.md`](./doc/reference/CONFIGURACAO_PERSISTENTE.md)

---

## Contribuição e Processos
- Fluxo de desenvolvimento e comandos essenciais: [`doc/developer/COMANDOS_RAPIDOS.md`](./doc/developer/COMANDOS_RAPIDOS.md)
- Guia de contribuição, PRs e i18n: [`doc/process/CONTRIBUTING.md`](./doc/process/CONTRIBUTING.md) e [`doc/reference/i18n_and_pr_guidelines.md`](./doc/reference/i18n_and_pr_guidelines.md)
- Papéis de agentes e automações: [`doc/process/AGENTS.md`](./doc/process/AGENTS.md)

---

## Histórico e Planejamento
- Últimas mudanças críticas: [`doc/releases/CHANGELOG_20251025_REDIS.md`](./doc/releases/CHANGELOG_20251025_REDIS.md)
- Relatórios técnicos, desempenho e roadmap: veja a coleção em [`doc/reference/`](./doc/reference/)

---

## Próximos Passos
- Revise os planos de testes e checklists antes de pull requests
- Configure dashboards Prometheus/Grafana com base nas métricas fornecidas
- Avalie migração de Redis para ambiente altamente disponível antes de produção

---

## Desenvolvimento Diário
- Rode `docker compose up` ou `make run` conforme o guia [`doc/developer/DOCKER_SETUP.md`](./doc/developer/DOCKER_SETUP.md).
- Comandos e atalhos de rotina: [`doc/developer/COMANDOS_RAPIDOS.md`](./doc/developer/COMANDOS_RAPIDOS.md).
- Observabilidade local (health, métricas, Celery): [`doc/developer/OBSERVABILITY.md`](./doc/developer/OBSERVABILITY.md).
- Convenções de contribuição e PRs: [`doc/process/CONTRIBUTING.md`](./doc/process/CONTRIBUTING.md).

## Testes e Qualidade
- Guia rápido de testes: [`doc/reference/TESTING_QUICK_REFERENCE.md`](./doc/reference/TESTING_QUICK_REFERENCE.md).
- Planos detalhados e relatórios de bugs: [`doc/reference/TEST_ERRORS_DETAILED_REPORT.md`](./doc/reference/TEST_ERRORS_DETAILED_REPORT.md).
- Execução recomendada: `pytest -q` (ou `make test`), e `pytest --cov --cov-report=term-missing` para cobertura.
- CI: GitHub Actions em `.github/workflows/tests.yml` roda a suíte completa com `--cov-fail-under=45` em pushes/PRs para `main` e `inicial`.

## Deploy e Operações
- Checklist completo de deploy: [`doc/operations/DEPLOYMENT.md`](./doc/operations/DEPLOYMENT.md).
- Estratégias Redis HA e degradação graciosa: [`doc/reference/REDIS_HIGH_AVAILABILITY.md`](./doc/reference/REDIS_HIGH_AVAILABILITY.md) e [`doc/reference/REDIS_GRACEFUL_DEGRADATION.md`](./doc/reference/REDIS_GRACEFUL_DEGRADATION.md).
- Status dos serviços e troubleshooting rápido: [`doc/operations/STATUS_SERVICOS.md`](./doc/operations/STATUS_SERVICOS.md).
- Checklist operacional contínuo: [`doc/reference/operations_checklist.md`](./doc/reference/operations_checklist.md).

## Suporte
- Issue tracker: [GitHub Issues](https://github.com/kaled182/mapsprovefiber/issues)
- Discussões técnicas: [GitHub Discussions](https://github.com/kaled182/mapsprovefiber/discussions)
- Segurança e disclosure responsável: [`doc/security/SECURITY.md`](./doc/security/SECURITY.md)

---

### © 2025 — Projeto **MapsProveFiber**
Mantido por Simples Internet.  
Documentação e código sob licença MIT.
