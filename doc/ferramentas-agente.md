# Ferramentas de agente — inventário e guia de montagem

> **Âmbito.** Ferramentas que assistem o desenvolvimento com Claude Code
> (skills, MCP, plugins, hooks, memória). **Nenhuma altera o produto**: não
> mudam design, arquitetura nem dependências de runtime.
>
> **Precedência, vinculativa:** o `CLAUDE.md` e os ADRs **vencem sempre**
> qualquer skill ou ferramenta aqui listada.

Última revisão: **2026-10-04**. Espelha `docs/ferramentas-agente.md` do CRM;
o que está marcado **por máquina** não vive no repositório e tem de ser
montado em cada estação (há um roteiro na §5).

---

## 1. O que mudou nesta ronda (2026-10-04) e o que NÃO mudou

**Mudou (versionado):** `CLAUDE.md` (novo), `skills-lock.json` (novo, 9
skills com hashes gerados pelo CLI), `scripts/skills-install.sh`,
alvo `make skills`, `.mcp.json`, `.editorconfig`, `.gitignore` (bloco do
ecossistema de agente e correção do padrão `test_*.py`), `doc/adr/` (README,
template, ADRs 0005–0007), `doc/templates/adr.md`,
`doc/analysis/2026-10-04-levantamento-geral.md`, este documento,
`doc/process/AGENTS.md` (passa a ponteiro), `.github/workflows/tests.yml`
(job de testes do frontend).

**Não mudou:** nada em `backend/*` de produto, nada em `frontend/src/`,
nenhuma dependência em `requirements.txt` ou `package.json`, nenhum hook.

---

## 2. Inventário

### 2.1 Skills versionadas (`skills-lock.json` → `make skills`)

Vivem em `.claude/skills/` (ignorado). O lockfile é a fonte da verdade.

| Skill | Origem | Para quê |
|---|---|---|
| `find-skills` | `vercel-labs/skills` | procurar/instalar skills novas |
| `skill-creator` | `anthropics/skills` | escrever skills próprias do projeto |
| `web-design-guidelines` | `vercel-labs/agent-skills` | auditoria de acessibilidade (WCAG) |
| `task-observer` | `rebelytics/one-skill-to-rule-them-all` | diário de fricções da sessão |
| `vue-best-practices` | `vuejs-ai/skills` | Composition API, `<script setup>` |
| `vue-pinia-best-practices` | `vuejs-ai/skills` | stores Pinia |
| `vue-router-best-practices` | `vuejs-ai/skills` | guards, params, ciclo de vida |
| `vue-testing-best-practices` | `vuejs-ai/skills` | Vitest + Vue Test Utils |
| `impeccable` | `pbakaus/impeccable` | crítica de UI — **só `critique`/`audit`** |

**Procurado e não encontrado** (`skills find`, 2026-10-04): `django`,
`django rest framework`, `celery`, `postgis`. Quando existir uma skill
oficial de Django, entra pelo lock. O CRM tem ainda `fastapi`, que não se
aplica aqui.

**Armadilhas medidas:**

- `skills experimental_install` escreve em `.agents/skills/`; o Claude Code
  lê `.claude/skills/`. Usar sempre `skills add ... -a claude-code`.
- Dentro de um loop com pipe, o CLI consome o stdin e o loop corre uma vez
  só: o script redireciona `</dev/null`.
- Skills novas só entram na **sessão seguinte**.
- `impeccable` como **plugin** instala hooks `PostToolUse` em `Edit|Write` e
  as regras dele põem Inter e Outfit (as fontes do nosso design system) na
  lista negra. Como skill, é invocável a pedido e não impõe nada.

### 2.2 Servidores MCP (`.mcp.json`, versionado)

| Servidor | Comando | Para quê |
|---|---|---|
| `code-review-graph` | `uvx code-review-graph serve` | grafo de conhecimento do código; mais barato que Grep/Read para explorar impacto. Base em `.code-review-graph/` (ignorada, pode chegar a centenas de MB). **Não se atualiza sozinho**: `build_or_update_graph_tool` após mudanças grandes. |
| `playwright` | `npx @playwright/mcp@latest` | smoke em browser real contra o SPA |

Ativação **por máquina** em `.claude/settings.local.json`:

```json
{ "enabledMcpjsonServers": ["code-review-graph", "playwright"] }
```

Sem `cwd` absoluto no `.mcp.json`: um caminho de máquina num ficheiro
versionado é sempre defeito (lição do CRM: deixava o grafo vazio).

### 2.3 Plugins do harness (por máquina, `~/.claude/settings.json`)

Ainda **não ativados** para este projeto. Recomendação, na ordem do CRM:

| Plugin | Para quê | Hooks | Decisão |
|---|---|---|---|
| `superpowers@claude-plugins-official` | disciplina brainstorm → plano → TDD | ver `claude plugin details` | **recomendado** |
| `claude-code-setup@claude-plugins-official` | recomendador read-only de automações | 0 | recomendado |
| `claude-mem@thedotmack` | memória entre sessões (captura automática) | sim | opcional — Paulo decide |
| `ui-ux-pro-max@ui-ux-pro-max-skill` | referência de design | — | opcional |

Antes de ativar **qualquer** plugin: `claude plugin details <nome>` e olhar a
linha **Hooks**. Um plugin com `PostToolUse` corre em cada edição e é decisão
consciente, não efeito lateral. O CLI não tem `install`; usa-se
`claude plugin enable <nome>`.

### 2.4 Proxies de tokens (por máquina, perguntar ao Paulo antes)

- **RTK** — reescreve comandos de CLI para versões econômicas; hook
  `PreToolUse` no Bash. Binário instalado à mão.
- **Headroom** — comprime o contexto. Se for adotado, três coisas têm de ficar
  escritas: um `ANTHROPIC_BASE_URL` personalizado desliga a janela de 1M
  (lançar `headroom wrap claude --1m`); desativa o Remote Control; a telemetria
  vem ligada no `wrap` (`HEADROOM_BEACON=off`). Usar `wrap`, não `init`.
  **Proibido** `headroom learn` escrever em ficheiros de contexto ou memória.

### 2.5 Hooks (por máquina, `~/.claude/settings.json`)

Nenhum instalado para este projeto. O CRM usa dois e este projeto deve
ganhar os mesmos quando a Central existir (ADR 0006):

- `PreToolUse` (matcher `Bash`) → `rtk hook claude`, se RTK for adotado.
- `Stop` com `asyncRewake` → script que (a) se o último commit for mais
  recente que a última gravação de memória, re-acorda o assistente com o
  lembrete dos gestos de memória; (b) regenera o bloco `EVOLUCAO` do
  `CLAUDE.md`; (c) corre `evolucao_fechados.sh | evolucao_fechar.py` para
  fechar itens cujo commit `fecha EV-NNNN` já está implantado. Silencioso
  fora deste repositório; nunca rebenta.

O script equivalente do CRM (`lembrar-memoria-crm.sh`) não está versionado
em nenhum dos repos: tem de ser escrito aqui quando a Fase 2 arrancar.

### 2.6 Memória do assistente (por máquina)

`~/.claude/projects/<slug-do-caminho>/memory/`, nunca versionada:

- `MEMORY.md` — índice: tabela de livros, «Onde se mexeu por último»,
  «Como manter isto honesto».
- `livro_<area>.md` — `livro_mapas`, `livro_graficos`, `livro_inventario`,
  `livro_zabbix`, `livro_sistema`; cada um com Feito (nº de PR/SHA), roteiro,
  páginas.
- `feedback_<tema>[_AAAA_MM_DD].md` — lições e armadilhas.
- `project_<tema>.md` — contexto de um trabalho longo.
- `estado_da_sessao.md` — `em_curso` | `finalizada` (escrito ao pegar no
  item).

A memória é auxiliar de sessão, **não é fonte de verdade humana**: o que
importa promove-se para `doc/` (ADR, análise, runbook).

---

## 3. Convenções de documentação adotadas do CRM

- ADRs em `doc/adr/` (MADR, 4 dígitos, imutáveis depois de `Aceito`),
  template em `doc/templates/adr.md`.
- Levantamentos e auditorias em `doc/analysis/AAAA-MM-DD-<slug>.md`.
- Nada de `.md` de planeamento solto na raiz (vai para `*.local.md`).
- Links Markdown relativos, não wikilinks (o repositório não é um vault
  Obsidian; se um dia for, copiar `.obsidian/app.json` do CRM).

---

## 4. O que foi avaliado e recusado (com fundamento)

- **Copiar o `skills-lock.json` do CRM tal e qual** — traria `fastapi`, que
  não se aplica, e omitiria a verificação de que não há skills de Django.
- **Instalar `impeccable` como plugin** — pelos hooks e pela lista negra de
  fontes (ver §2.1).
- **Escrever o lockfile à mão** — os `computedHash` seriam inventados; o
  ficheiro foi gerado pelo CLI real.
- **Hooks no repositório** (`.claude/settings.json` versionado) — o CRM
  mantém-nos por máquina, de propósito: contêm caminhos locais e decisões
  por programador.
- **Portar já a Central de Evolução** — é código de produto (modelo, API,
  UI, Celery); fica para o ADR 0006, com decisão do Paulo entre fila
  própria e fila partilhada com o CRM.

---

## 5. Repor tudo numa máquina nova (roteiro)

```bash
# 0. clonar e ler
git clone git@github.com:kaled182/provemaps_beta.git && cd provemaps_beta
cat CLAUDE.md | head -120

# 1. skills
npm install -g skills
make skills                       # repõe .claude/skills/ a partir do lock
# verificar: ls .claude/skills  → 9 pastas

# 2. MCP (por máquina)
mkdir -p .claude && cat > .claude/settings.local.json <<'JSON'
{ "enabledMcpjsonServers": ["code-review-graph", "playwright"] }
JSON
uv tool install code-review-graph   # ou deixar o uvx resolver na primeira vez

# 3. plugins (mostrar hooks antes de ativar)
claude plugin details superpowers@claude-plugins-official
claude plugin enable  superpowers@claude-plugins-official
claude plugin enable  claude-code-setup@claude-plugins-official

# 4. memória
mkdir -p ~/.claude/projects/<slug>/memory
printf 'finalizada\n' > ~/.claude/projects/<slug>/memory/estado_da_sessao.md
# criar MEMORY.md e livro_*.md seguindo §2.6

# 5. (opcional, decisão do Paulo) RTK / Headroom / hooks — §2.4 e §2.5
```

Verificar em vez de afirmar: `ls .claude/skills | wc -l` → 9;
`claude plugin details <cada um>`; `git status` limpo (nada do ecossistema
deve aparecer como não rastreado).
