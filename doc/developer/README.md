# MapsProveFiber Documentation (Developers)

This folder gathers the main guides for developers:

- [DOCKER_SETUP.md](./DOCKER_SETUP.md): Complete guide to run the project with Docker (detalhes avançados além do quickstart)
- [../getting-started/QUICKSTART.md](../getting-started/QUICKSTART.md): Guia unificado (local + Docker) — substitui QUICKSTART_LOCAL.md
- [COMANDOS_RAPIDOS.md](./COMANDOS_RAPIDOS.md): Day-to-day command reference
- [OBSERVABILITY.md](./OBSERVABILITY.md): Health endpoints and Prometheus metrics

## Tests and Continuous Quality
- For a quick local smoke run, execute `pytest --maxfail=1 -q`.
- For coverage, run `coverage run -m pytest` followed by `coverage report --show-missing`.
- The GitHub Actions pipeline (`.github/workflows/tests.yml`) executes the same commands and fails if `coverage report` drops below 45% (`--fail-under=45`).
- Resolve CI failures before merging; coordinate any threshold changes with the team.

## Additional topics
- Security: .env usage, Fernet keys, OWASP recommendations (see [`../security/SECURITY.md`](../security/SECURITY.md))
- Redis in production: [`../reference/REDIS_HIGH_AVAILABILITY.md`](../reference/REDIS_HIGH_AVAILABILITY.md)

Refer to this directory for the latest standardized information.
