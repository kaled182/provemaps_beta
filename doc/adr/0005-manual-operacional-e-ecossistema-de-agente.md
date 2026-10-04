# ADR 0005 — `CLAUDE.md` como manual operacional canônico e ecossistema de agente versionado

| Campo            | Valor                                                       |
|------------------|-------------------------------------------------------------|
| Estado           | **Proposto**                                                |
| Data             | 2026-10-04                                                  |
| Decisores        | Equipe Técnica Simples Internet — Paulo Marcelino           |
| Tags             | `processo`, `agente-ia`, `tooling`, `documentação`          |
| Substitui        | —                                                           |
| Substituído por  | —                                                           |

---

## 1. Contexto e Problema

O ProVeMaps não tinha um briefing canônico para sessões de Claude Code. O que
existia estava espalhado e desatualizado:

- `doc/process/AGENTS.md` cita apps que não existem (`routes_builder`,
  `zabbix_api`), MariaDB como banco (o produto roda PostGIS), Jest em
  `maps_view/static/js` e targets de `make` inexistentes.
- `.github/copilot-instructions.md` afirma uso de `django-environ` para
  segredos (só o cliente Zabbix usa) e cita caminhos errados.
- Não havia convenção de ADR viva (três ADRs legados em
  `doc/architecture/ADR/`), nem lockfile de skills, nem `.mcp.json`, nem
  `.editorconfig`, nem regra de memória entre sessões.

Resultado: cada sessão redescobre o projeto e repete erros já conhecidos.
No CRM Simples Internet o problema foi resolvido com um `CLAUDE.md`
operacional, `skills-lock.json` + `make skills`, `.mcp.json`, ADRs MADR,
memória de sessão e hooks. Pedido do Paulo (2026-10-04): trazer a mesma
mecânica para o ProVeMaps.

## 2. Drivers da Decisão

- **D-1 — Uma fonte de verdade para regras.** Regras vivem num ficheiro que o
  assistente lê sempre; estado vive onde pode ser verificado (Git, Central).
- **D-2 — Reprodutível em máquina nova.** Quem clona o repo repõe o
  ecossistema com um comando.
- **D-3 — Zero impacto no produto.** Tooling não adiciona dependências de
  runtime, não muda visual nem estrutura.
- **D-4 — Paridade com o CRM.** Mesmos nomes, mesma convenção, mesmos gestos,
  para que a equipe trabalhe igual nos dois produtos.

## 3. Opções Consideradas

### Opção A — Corrigir `AGENTS.md` e `copilot-instructions.md` no lugar

**Prós:** menor diff. **Contras:** mantém três ficheiros concorrentes;
nenhum é lido por omissão pelo Claude Code; não resolve skills, MCP, memória.

### Opção B — `CLAUDE.md` na raiz como manual canônico + ecossistema versionado (escolhida)

**Prós:** o Claude Code carrega `CLAUDE.md` automaticamente; a estrutura é
a do CRM (precedência, regras de trabalho, red flags, memória); `skills-lock.json`
dá reprodutibilidade; ADRs dão trilha de decisões.
**Contras:** ficheiro grande que precisa de manutenção; parte do mecanismo
(hooks, memória) vive fora do repo, em `~/.claude/`, e tem de ser montada por
máquina.

## 4. Decisão

Escolhemos a **Opção B**. Concretamente, nesta primeira entrega:

1. **`CLAUDE.md`** na raiz, com as mesmas seções do CRM adaptadas ao
   ProVeMaps: regras de trabalho vinculativas, identidade, princípios,
   stack, estrutura, convenções, workflow, red flags, «sempre fazer»,
   precedência de skills, ativação do `task-observer`, memória ao fim de
   sessão. `doc/process/AGENTS.md` passa a apontar para ele.
2. **Skills versionadas** por `skills-lock.json` (fonte da verdade) +
   `scripts/skills-install.sh` + `make skills`. `.claude/` fica no
   `.gitignore`. Conjunto inicial: `find-skills`, `skill-creator`,
   `web-design-guidelines`, `task-observer`, as quatro `vue-*-best-practices`
   e `impeccable` (só `critique`/`audit`). O registro público não tem skills
   para Django/DRF/Celery/PostGIS; se aparecerem, entram pelo mesmo lock.
3. **`.mcp.json`** versionado com `code-review-graph` e `playwright`, sem
   `cwd` absoluto; ativação por máquina em `.claude/settings.local.json`.
4. **ADRs** em `doc/adr/` com README e template MADR, numeração continuando
   a dos legados.
5. **`.editorconfig`** igual ao do CRM.
6. **`.gitignore`**: entradas do ecossistema de agente e correção do padrão
   global `test_*.py` que escondia testes legítimos.
7. **Memória de sessão** em `~/.claude/projects/<slug>/memory/` com
   `MEMORY.md`, `livro_*`, `feedback_*`, `estado_da_sessao.md` — mesma
   convenção do CRM; criada por máquina, nunca versionada.

Fica **fora** desta entrega e depende de decisão própria: hooks globais
(`PreToolUse` RTK, `Stop` com lembrete de memória e regeneração do quadro),
plugins do harness (`superpowers`, `claude-code-setup`), proxies de tokens
(RTK, Headroom) e a Central de Evolução (ADR 0006). O guia de montagem por
máquina é `doc/ferramentas-agente.md`.

## 5. Consequências

### Positivas

- Toda sessão abre com o mesmo briefing e as mesmas regras.
- `make skills` repõe o ecossistema; o lock tem hashes reais.
- Trilha de decisões (ADRs) e inventário de ferramentas auditáveis.

### Negativas

- O `CLAUDE.md` exige disciplina: cada padrão novo tem de entrar lá.
- Hooks e memória continuam por máquina; sem o hook `Stop`, a regra de memória
  depende do assistente lembrar-se.

### Neutras

- `.github/copilot-instructions.md` mantém-se para outros agentes, mas passa
  a remeter ao `CLAUDE.md`.

## 6. Referências

- CRM Simples Internet: `CLAUDE.md`, `docs/prompt-replicar-setup.md`,
  `docs/ferramentas-agente.md`, `docs/adr/0042-central-de-evolucao.md`.
- [`doc/ferramentas-agente.md`](../ferramentas-agente.md)
- [`doc/analysis/2026-10-04-levantamento-geral.md`](../analysis/2026-10-04-levantamento-geral.md)
