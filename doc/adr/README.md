# Architecture Decision Records (ADRs) — ProVeMaps

Índice canônico das decisões arquiteturais do projeto. Cada ADR documenta
**uma** decisão: o contexto, as alternativas consideradas, a escolha feita
e as suas consequências. A convenção é a mesma do CRM Simples Internet
(`docs/adr/README.md` daquele repositório), para os dois produtos se lerem
da mesma maneira.

> **Imutabilidade.** Após um ADR ser marcado como `Aceito`, o seu conteúdo
> deixa de ser editado em substância. Mudanças de rumo geram um **novo** ADR
> que `Substitui` o anterior, mantendo a trilha histórica intacta.

---

## 1. Como ler um ADR

Formato **MADR (Markdown ADR) 3.x** adaptado, em **português**.

### Cabeçalho (tabela de metadados)

```markdown
| Campo            | Valor                                                |
|------------------|------------------------------------------------------|
| Estado           | **Aceito**                                           |
| Data             | 2026-10-04                                           |
| Decisores        | Equipe Técnica Simples Internet — Paulo Marcelino    |
| Tags             | `mapas`, `zabbix`, ...                               |
| Substitui        | — (ou: ADR 000X)                                     |
| Substituído por  | — (ou: ADR 00YY)                                     |
```

### Estrutura

1. **Contexto e Problema** — o que motivou a decisão; restrições e riscos.
2. **Drivers da Decisão** — critérios que pesaram.
3. **Opções Consideradas** — alternativas avaliadas, com prós e contras.
4. **Decisão** — a escolha feita, com a sua forma concreta.
5. **Consequências** — Positivas, Negativas, Neutras.
6. **Alternativas comparativas** (opcional).
7. **Referências** — internas e externas.

### Convenção de estado

- `Proposto` — em discussão ativa, ainda não vinculativo.
- `Aceito` — vincula a equipe; o código deve respeitar.
- `Substituído` — preservado por valor histórico; ler também o sucessor.
- `Descontinuado` — revogado e nada o substituiu.

---

## 2. Convenção de nomeação

```
NNNN-titulo-em-kebab-case.md
```

- **NNNN**: sequencial com zero-padding a 4 dígitos. Nunca reciclado.
- A numeração continua a dos ADRs legados em
  [`doc/architecture/ADR/`](../architecture/ADR/) (`001`; os antigos `000` e `004` eram cópias de documentos de referência e estão em [`doc/archive/2025-historico/`](../archive/2025-historico/)),
  que ficam onde estão por valor histórico. O próximo ADR é **`0008`**.
- Template: [`doc/templates/adr.md`](../templates/adr.md).

---

## 3. Estado de cada ADR

| #    | Título | Estado | Tags |
|------|--------|--------|------|
| [000](../archive/2025-historico/TECHNICAL_REVIEW.md) | Revisão técnica inicial (legado, **arquivado** 2026-10-04) | Histórico | `legado` |
| [001](../architecture/ADR/001-fiber-route-builder.md) | Fiber Route Builder (legado) | Aceito | `legado`, `rotas` |
| [004](../archive/2025-historico/REFATORAR.md) | Plano de refatoração 2.0 (legado, **arquivado** 2026-10-04) | Histórico | `legado`, `refatoração` |
| [0005](0005-manual-operacional-e-ecossistema-de-agente.md) | `CLAUDE.md` como manual operacional canônico + ecossistema de agente versionado (skills-lock, MCP, ADRs, memória) | Aceito | `processo`, `agente-ia`, `tooling` |
| [0006](0006-central-de-evolucao-provemaps.md) | Central de Evolução no ProVeMaps — fila de trabalho observada, não escrita | Aceito | `processo`, `evolucao`, `agente-ia` |
| [0007](0007-alinhamento-visual-com-o-crm.md) | Alinhamento visual com o CRM — tokens compartilhados, shell e migração incremental | Aceito | `frontend`, `design-system`, `tailwind`, `branding` |

---

## 4. Como propor um novo ADR

1. `ls doc/adr/` → próximo número sequencial.
2. Copia [`doc/templates/adr.md`](../templates/adr.md) para
   `NNNN-titulo-em-kebab-case.md`.
3. Marca como `Proposto`.
4. Abre PR com título `docs(adr): NNNN <título curto>`.
5. Merge muda o estado para `Aceito`; atualiza a tabela §3.
6. Se substituir outro, edita o antigo **só** para preencher
   `Substituído por` (única exceção à imutabilidade).
