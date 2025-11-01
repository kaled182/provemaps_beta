# Documentação do MapsProveFiber (Desenvolvedores)

Esta pasta reúne os principais guias para desenvolvedores:

- [DOCKER_SETUP.md](./DOCKER_SETUP.md): Guia completo para rodar o projeto via Docker
- [QUICKSTART_LOCAL.md](./QUICKSTART_LOCAL.md): Guia rápido para desenvolvimento local
- [COMANDOS_RAPIDOS.md](./COMANDOS_RAPIDOS.md): Comandos essenciais para o dia a dia
- [OBSERVABILITY.md](./OBSERVABILITY.md): Endpoints de saúde e métricas Prometheus

## Testes e Qualidade Contínua
- Para uma checagem rápida local, execute `pytest --maxfail=1 -q`.
- Para coletar cobertura, utilize `pytest --cov --cov-report=term-missing`.
- O pipeline GitHub Actions (`.github/workflows/tests.yml`) executa `pytest --cov` em pull requests e aplica `--cov-fail-under=45`.
- Falhas no CI devem ser tratadas antes do merge; alinhe evoluções de cobertura com a equipe ao ajustar o limite.

## Outros tópicos importantes
- Segurança: Uso de .env, chaves Fernet, recomendações OWASP (veja [`../security/SECURITY.md`](../security/SECURITY.md))
- Redis em produção: [`../reference/REDIS_HIGH_AVAILABILITY.md`](../reference/REDIS_HIGH_AVAILABILITY.md)

Consulte sempre este diretório para informações atualizadas e padronizadas.
