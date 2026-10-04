# ADR 0006 — Central de Evolução no ProVeMaps: fila de trabalho observada, não escrita

| Campo            | Valor                                                       |
|------------------|-------------------------------------------------------------|
| Estado           | **Aceito** (Paulo, 2026-10-04 — Opção B, Central própria)                                                |
| Data             | 2026-10-04                                                  |
| Decisores        | Equipe Técnica Simples Internet — Paulo Marcelino           |
| Tags             | `processo`, `evolucao`, `agente-ia`, `auditoria`            |
| Substitui        | —                                                           |
| Substituído por  | —                                                           |

---

## 1. Contexto e Problema

No CRM, o quadro «o que falta» deixou de ser texto escrito à mão no
`CLAUDE.md` e passou a ser **vista gerada** de uma base (ADR 0042 do CRM):
itens `EV-NNNN` com tipo, estado, impacto e prioridade; triagem só do Paulo;
«feito» derivado de commits `fecha EV-NNNN` alcançáveis a partir do `git_sha`
implantado; botão 📣 no cabeçalho para qualquer utilizador reportar; aviso
automático aos 14 dias.

O ProVeMaps hoje tem o oposto: 68 relatórios de sprint em `doc/reports/`, 30
documentos de roadmap, três planos de refatoração e nenhum lugar único que
diga o que está aberto. O levantamento de 2026-10-04 produziu uma lista de
~40 problemas concretos que precisa de um dono e de uma ordem. Sem a Central,
essa lista vai para o `CLAUDE.md` à mão e começa a apodrecer no dia seguinte.

## 2. Drivers da Decisão

- **D-1 — Estado observado > estado escrito.** «Feito» procura-se no Git.
- **D-2 — Um pedido de cada vez.** A fila tem ordem (prioridade, depois
  identificador) e o assistente pega no primeiro.
- **D-3 — Triagem é do Paulo.** O assistente escreve itens com prova, não lê
  a Entrada nem promove nada.
- **D-4 — Paridade com o CRM.** Mesmo vocabulário, mesmos estados, mesmo
  verbo de commit.

## 3. Opções Consideradas

### Opção A — Reutilizar a Central do CRM, com campo `produto`

**Prós:** zero código novo no ProVeMaps; uma só fila para a equipe; UI, sino
e triagem já existem.
**Contras:** o fecho automático depende do `git_sha` **do ProVeMaps**, logo o
hook do ProVeMaps teria de chamar a API do CRM (acoplamento entre produtos e
entre deploys); utilizadores do ProVeMaps que não têm conta no CRM não
conseguem reportar pelo botão 📣; o quadro gerado no `CLAUDE.md` do ProVeMaps
viria de outro sistema.

### Opção B — Portar a Central como app Django `evolucao` no ProVeMaps (recomendada)

**Prós:** cada produto fecha os seus itens com o seu `git_sha`; o botão 📣
funciona para quem usa o ProVeMaps; mesma forma, dados separados; a app é
pequena (modelo, 5 endpoints, uma view, um render do quadro, dois scripts).
**Contras:** duas filas para a equipe olhar; código duplicado em dois stacks
(FastAPI/SQLAlchemy no CRM, Django/DRF aqui).

### Opção C — Quadro manual no `CLAUDE.md` (estado atual)

**Prós:** nada a construir. **Contras:** foi exatamente o que o CRM
abandonou depois de encontrar cinco linhas falsas no quadro.

## 4. Decisão

Escolher a **Opção B**, com a Opção A registrada como alternativa caso o
Paulo prefira uma fila única. Forma concreta:

1. **App `backend/evolucao/`** com modelo `EvolucaoItem`: `codigo` `EV-NNNN`
   (único), `tipo` ∈ {problema, ideia}, `titulo`, `descricao`, `estado` ∈
   {entrada, aceite, a_fazer, feito, recusado}, `recusa_motivo`, `impacto` ∈
   {bloqueia, atrasa, incomoda}, `prioridade` 1–4 (NULL = por triar),
   `etiquetas`, `autor`, `contexto` JSON (rota, viewport, navegador,
   `request_id`), `origem` ∈ {humano, agente}, `evidencia` JSON (obrigatória
   quando `origem=agente`), `fechado_por` JSON `{commit, mensagem, deploy_em}`,
   `alerta_parado_em`, timestamps. Contador atômico para o código.
2. **API** `/api/v1/evolucao/itens/` (POST sem gate; GET com visibilidade por
   autor ou `is_staff`; PATCH de triagem só `is_staff`, auditado) e
   `/etiquetas/`. Anexos via `FileField` simples.
3. **Frontend**: rota `/admin/sistema/evolucao` com listas por estado e abas
   Problemas/Ideias/Tudo; botão **Reportar** (ícone `Megaphone`) no cabeçalho
   abrindo `ReportarModal.vue` que captura contexto automaticamente.
4. **Fecho observado**: `/healthz` passa a devolver `git_sha` (cozido na
   imagem pelo build) e `iniciado_em`; `scripts/evolucao_fechados.sh` lê o
   SHA implantado e extrai `fecha|resolve|closes|fixes EV-NNNN` dos commits
   alcançáveis; `backend/scripts/evolucao_fechar.py` marca `feito`. Ambos
   fail-closed e silenciosos (são chamados por hook).
5. **Quadro gerado**: `backend/scripts/evolucao_quadro.py` reescreve o bloco
   entre `<!-- EVOLUCAO:INICIO -->` e `<!-- EVOLUCAO:FIM -->` no `CLAUDE.md`,
   ordenado por prioridade e depois código, problemas antes de ideias.
6. **Aviso aos 14 dias**: tarefa Celery beat diária que notifica `is_staff`
   sobre itens abertos parados.
7. **`make deploy` recusa árvore suja** e grava `GIT_SHA` no build.
8. **Seed**: os problemas do levantamento de 2026-10-04 entram como itens
   `origem=agente` com evidência `{ficheiro, linha}`, estado `entrada`, para
   o Paulo triar.

Até a app existir, o `CLAUDE.md` traz um quadro **manual** marcado como
provisório, com os mesmos códigos `EV-NNNN` que o seed vai usar.

## 5. Consequências

### Positivas

- Fila única por produto, com ordem e dono; «feito» verificável.
- O assistente abre itens com prova durante o trabalho, em vez de deixar
  TODOs no código.

### Negativas

- Trabalho de implementação (estimativa: 2 a 3 sessões) antes do primeiro
  item de produto.
- Mais uma superfície que precisa de testes e de permissões corretas.

### Neutras

- Os 68 relatórios em `doc/reports/` passam a ser histórico; não se apagam
  nesta decisão.

## 6. Referências

- CRM: `docs/adr/0042-central-de-evolucao.md`, `backend/app/evolucao/`,
  `backend/scripts/evolucao_quadro.py`, `scripts/evolucao_fechados.sh`,
  `docs/superpowers/plans/2026-09-03-central-de-evolucao-fatia-2.md`.
- [ADR 0005](0005-manual-operacional-e-ecossistema-de-agente.md)
