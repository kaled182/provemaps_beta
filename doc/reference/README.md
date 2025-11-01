# Reference Library — MapsProveFiber

Este diretório concentra documentação de profundidade para arquitetura, operação avançada e histórico do projeto. Utilize-o como material de apoio após ler os guias introdutórios em [`doc/getting-started/`](../getting-started/) e [`doc/developer/`](../developer/).

## Navegação Rápida
- **Arquitetura & ADRs**: [`adr_fiber_route_builder.md`](./adr_fiber_route_builder.md), [`TECHNICAL_REVIEW.md`](./TECHNICAL_REVIEW.md)
- **Infraestrutura & Observabilidade**: [`REDIS_HIGH_AVAILABILITY.md`](./REDIS_HIGH_AVAILABILITY.md), [`prometheus_static_version.md`](./prometheus_static_version.md), [`operations_checklist.md`](./operations_checklist.md)
- **Performance & Escalabilidade**: sequência [`performance_phase1.md`](./performance_phase1.md) → [`performance_phase6.md`](./performance_phase6.md)
- **Testes & Qualidade**: [`TESTING_QUICK_REFERENCE.md`](./TESTING_QUICK_REFERENCE.md), [`TEST_ERRORS_DETAILED_REPORT.md`](./TEST_ERRORS_DETAILED_REPORT.md), [`TESTING_WITH_MARIADB.md`](./TESTING_WITH_MARIADB.md)
- **Relatórios Históricos**: [`PROJECT_STATUS_REPORT.md`](./PROJECT_STATUS_REPORT.md), [`FINAL_CONSOLIDATED_REPORT.md`](./FINAL_CONSOLIDATED_REPORT.md), [`FASE4_SUCCESS_REPORT.md`](./FASE4_SUCCESS_REPORT.md)
- **Apps Específicos**:
	- [`maps_view/`](./maps_view/) — guias do dashboard e integrações de mapa
	- [`modules/`](./modules/) — documentação legada dos módulos JS do fiber builder

## Como Usar
1. **Planejamento/Arquitetura**: comece pelos ADRs e revisões técnicas para contexto histórico.
2. **Operação em Produção**: consulte os guias de Redis HA, checklist operacional e alertas Prometheus antes de liberar novas versões.
3. **Performance & Troubleshooting**: use os relatórios de fases de performance e as análises de erros como material de diagnóstico.
4. **Testes**: siga os planos e listas de verificação para garantir cobertura de QA em releases críticos.

## Convenções
- Títulos e arquivos seguem snake_case em português.
- Links são relativos a esta pasta para facilitar leitura no GitHub ou no VS Code.
- Conteúdo histórico permanece intacto para rastreabilidade; arquivos mais antigos estão marcados em notas iniciais quando necessário.

> Dica: use `Ctrl+P` no VS Code e busque pelo nome do arquivo citado para abrir rapidamente qualquer referência.
