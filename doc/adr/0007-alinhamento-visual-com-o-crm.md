# ADR 0007 — Alinhamento visual com o CRM: tokens compartilhados, shell e migração incremental

| Campo            | Valor                                                       |
|------------------|-------------------------------------------------------------|
| Estado           | **Proposto**                                                |
| Data             | 2026-10-04                                                  |
| Decisores        | Equipe Técnica Simples Internet — Paulo Marcelino           |
| Tags             | `frontend`, `design-system`, `tailwind`, `branding`, `lgpd` |
| Substitui        | —                                                           |
| Substituído por  | —                                                           |

---

## 1. Contexto e Problema

Pedido do Paulo (2026-10-04): «repaginar trazendo o mesmo visual do CRM para
que os produtos fiquem padronizados».

**Como o CRM é feito** (ADR 0016 do CRM, verificado no código):

- Tailwind CSS 3.4 + Headless UI Vue; sem kit de UI; `cn()` = clsx +
  tailwind-merge. Ícones `lucide-vue-next`.
- Fontes **auto-hospedadas** (LGPD): Inter (UI), JetBrains Mono (números,
  IDs, datas), Outfit (marca, títulos, KPIs). CDN de fontes proibido.
- Paleta: **primary teal `#42B4B8`** (500; 600 `#38989C`, 700 `#2D7A7D`,
  50 `#F0FAFB`, 100 `#D9F2F4`, 200 `#B4E1E4`); neutros Slate servidos por
  variáveis `--n-50…950` que **invertem no escuro**; `surface` (branco /
  `#182225`) e `canvas` (`#F8FAFC` / `#0F1517`); semânticas `success #16A34A`,
  `warning #F59E0B`, `danger #DC2626`, `info #0EA5E9`.
- Shell: **header fixo de duas linhas, sem sidebar** (linha 1: marca,
  busca, Reportar, tema, sino, utilizador; linha 2: nav horizontal com
  dropdowns). Conteúdo em largura total, `bg-canvas`.
- Densidade compacta: `text-sm`, cartões `p-4` com borda `neutral-200` e sem
  sombra, `rounded-md` (6 px) em controles e `rounded-lg` (8 px) em cartões.
- Modo escuro por classe `.dark` em `<html>`, preferência em `localStorage`.

**Como o ProVeMaps é hoje:** CSS próprio com variáveis em
`frontend/src/assets/theme.css` (dark/light por `data-theme`), acento
**verde `#22c55e`/`#10b981`**, menu lateral (`TheNavMenu.vue`, 1.200 linhas),
`@phosphor-icons/vue`, Tailwind e FontAwesome **via CDN** em
`base_spa.html` (motivo do CSP com `unsafe-inline`/`unsafe-eval`), 124
componentes `.vue` com estilos scoped (vários acima de 1.500 linhas) e três
motores de gráfico diferentes.

Migrar 86 mil linhas de frontend para Tailwind de uma vez não cabe em
nenhuma sessão e quebraria o produto em produção.

## 2. Drivers da Decisão

- **D-1 — Mesma marca, mesmo comportamento.** Teal, tipografia, shell e
  componentes base iguais ao CRM.
- **D-2 — Incremental e seguro.** Cada fase entrega algo visível sem quebrar
  o mapa, que é o coração do produto.
- **D-3 — Uma fonte de tokens para os dois produtos.** Mudar a marca uma vez,
  refletir nos dois.
- **D-4 — LGPD.** Nada de CDN para fontes/ícones.

## 3. Opções Consideradas

### Opção A — Só trocar valores das variáveis em `theme.css`

**Prós:** dias, não semanas; risco baixo. **Contras:** não traz o shell, os
componentes nem o modo escuro por classe; o resultado «parece» mas não é o
mesmo sistema.

### Opção B — Reescrever o frontend em Tailwind de uma vez

**Prós:** resultado idêntico ao CRM. **Contras:** meses; congela o produto;
os módulos de mapa e gráficos estão no meio de outra correção (levantamento
2026-10-04).

### Opção C — Tokens compartilhados + shell novo + migração por componente (recomendada)

**Prós:** o primeiro passo (tokens) já aproxima a marca; o shell dá a
identidade; os componentes migram quando são tocados, usando o mesmo
`tailwind.config` do CRM. **Contras:** convivência de dois estilos durante
a transição; exige disciplina para não criar CSS novo fora dos tokens.

## 4. Decisão (proposta)

Escolher a **Opção C**, em quatro fases, cada uma fechando num deploy:

**Fase 1 — Tokens e fontes (1 sessão).**
Criar `frontend/src/design-system/tokens.css` com as variáveis do CRM
(`--n-*`, `--surface`, `--canvas`, primary teal, semânticas) e um
mapeamento das variáveis atuais de `theme.css` para elas (ex.:
`--accent-primary` → `rgb(var(--primary-500))`, `--bg-primary` →
`rgb(var(--canvas))`, `--surface-card` → `rgb(var(--surface))`). Auto-hospedar
Inter, JetBrains Mono e Outfit em `frontend/public/fonts/` e remover o
Tailwind e o FontAwesome via CDN de `base_spa.html` (permite apertar o CSP).
Resultado: toda a app muda para teal/Slate sem tocar em componentes.

**Fase 2 — Shell (1 a 2 sessões).**
`AppLayout.vue` com header de duas linhas, `useNavSections` com as seções do
ProVeMaps (Mapa, Inventário, Monitoramento, Projeto de Rede, Vídeo,
Configuração, Sistema), `MobileDrawer`, `TemaToggle` (classe `.dark`),
`UserMenu`, botão **Reportar** (liga ao ADR 0006). O mapa ocupa toda a área
abaixo do header. `TheNavMenu.vue` é removido.

**Fase 3 — Primitivos e componentes (contínua).**
Introduzir Tailwind 3.4 **local** (`tailwind.config.ts` idêntico ao do CRM,
`@tailwindcss/forms`, `cn()`), `lucide-vue-next`, e portar os primitivos do
CRM (`Button`, `Input`, `Select`, `Modal`, `Checkbox`, `Label`,
`DataTable`, `ConfirmDialog`). Regra: componente **tocado** migra para os
primitivos; componente novo nasce neles. Prioridade: os modais gigantes que
o levantamento já manda partir (`FiberCableDetailModal`, `SiteDetailsModal`,
`PortTrafficModal`), que ganham o `TimeSeriesChart` único.

**Fase 4 — Pacote compartilhado.**
Extrair `tailwind.config`, `tokens.css`, fontes e primitivos para um pacote
`@simplesinternet/design-system` consumido pelos dois produtos (repositório
próprio ou pasta publicada), para que a padronização deixe de ser cópia.

Decisões que ficam para o Paulo antes da Fase 2: (a) manter busca global no
header (existe `useFuzzySearch`); (b) como o mapa convive com a linha 2 do
header em ecrãs pequenos (recolher a nav em modo mapa); (c) se a página de
login adota a mascote animada do CRM ou só a paleta.

## 5. Consequências

### Positivas

- Marca unificada já na Fase 1, com risco controlado.
- Remoção do CDN melhora segurança (CSP) e LGPD.
- Os componentes gigantes são partidos ao mesmo tempo que ganham o visual.

### Negativas

- Dois estilos coexistem durante a Fase 3.
- Capturas de tela, documentação e vídeos de treinamento ficam
  desatualizados a cada fase.

### Neutras

- Os gráficos passam a ler cores dos tokens (hoje hex fixo); o CRM tem o
  mesmo problema e beneficia do pacote da Fase 4.

## 6. Referências

- CRM: `docs/adr/0016-design-system-ui-foundation.md`,
  `frontend/tailwind.config.ts`, `frontend/src/style.css`,
  `frontend/src/layouts/AppLayout.vue`, `frontend/src/design-system/`.
- ProVeMaps: `frontend/src/assets/theme.css`, `backend/templates/base_spa.html`.
- [Levantamento 2026-10-04](../analysis/2026-10-04-levantamento-geral.md)
