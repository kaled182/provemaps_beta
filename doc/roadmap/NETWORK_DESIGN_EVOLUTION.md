# Plano de Evolução — Network/NetworkDesign/

> **Como usar este arquivo:** À medida que cada tarefa for concluída, marque `[x]` na checkbox correspondente e adicione uma nota com a data e o que foi feito. Tarefas em andamento ficam com `[-]`.

---

## Fase 1 — Limpeza Visual e Otimização de Tela (Quick Wins)

> Objetivo: Ganhar área útil de mapa e melhorar a primeira impressão do usuário.

### 1.1 Refatoração do Painel "Route Points"
- [x] Painel fica **oculto por padrão** (nd-panel-hidden com transição opacity/transform)
  - _2026-03-23: classe `nd-panel-hidden` adicionada ao template; lógica de show/hide em onPathChange e loadFiberDetail_
- [x] Aparece ao adicionar o primeiro ponto ou ao entrar em modo de edição de cabo existente
- [ ] Painel é redimensionável ou tem tamanho proporcional à viewport
- [x] Fecha automaticamente ao cancelar/salvar a edição (`cancelEditing` chama `setRoutePointsPanelVisible(false)`)

### 1.2 Minimização da Caixa de Dicas (Tips)
- [x] Substituir caixa fixa por botão FAB flutuante "?" no canto inferior direito
  - _2026-03-23: `#helpFab` + `#helpPopover` substituem o `#helpPanel` original_
- [x] Ao clicar, popover elegante abre/fecha com transição suave; fecha ao clicar fora
- [ ] Dicas se adaptam ao contexto atual (modo edição, modo visualização, etc.)

### 1.3 Menus de Contexto (Right-click)
- [x] Implementado menu de contexto no mapa (clique direito sobre cabos/elementos)
  - _Concluído: modal editor com opções Editar, Salvar, Cancelar, Deletar_
- [x] Adicionar ação "Ver detalhes" que abre painel lateral sem entrar em modo edição
  - _2026-03-23: right-click abre modo preview → painel Cable Details (read-only) com Editar/Excluir_
- [x] Separar fluxo de preview vs edição no context menu
  - _2026-03-23: seção contextPreviewOptions (Ver detalhes / Editar rota / Excluir) vs contextSelectedOptions (editando)_
- [ ] Refinar opções do menu por tipo de elemento (cabo, caixa, ponto de emenda) — fase 3+

---

## Fase 2 — Evolução da Estrutura de Dados e Modais

> Objetivo: Preparar o "motor" do sistema para receber informações mais ricas.

### 2.1 Modelagem de Novos Cadastros Base
- [ ] **Grupos de Cabos** — modelo no banco com campos:
  - `nome` (ex: "ASU 12FO", "FO Geleado 36FO")
  - `fabricante`
  - `quantidade_fibras`
  - `atenuacao_db_por_km` (para cálculo óptico futuro)
- [ ] **Responsáveis / Equipes** — modelo com campos:
  - `nome`, `email`, `telefone`
  - `tipo` (técnico / equipe / terceirizado)
- [ ] Migrations e serializers DRF para os novos modelos
- [ ] Endpoints REST: `GET/POST /api/v1/inventory/cable-groups/` e `/responsibles/`

### 2.2 Modernização do Modal de Salvamento de Cabo
- [x] Modal "Save cable manually" com selects de dispositivo e porta funcionando
  - _Concluído: dropdown de device e port restaurados e funcionando_
- [x] Validação de coordenadas do dispositivo corrigida (usa Site.latitude/longitude)
- [ ] Adicionar campo **Grupo do Cabo** (select populado da API)
- [ ] Adicionar campo **Pasta/Organização** (hierarquia de pastas — ver Fase 3)
- [ ] Adicionar campo **Responsável** (select ou autocomplete)
- [ ] Reorganizar modal em abas: "Identificação" | "Conexões" | "Detalhes"

### 2.3 Histórico e Anexos (Audit & Docs)
- [ ] Log automático de criação/edição: quem fez, quando, o que mudou
- [ ] Seção de upload de fotos da instalação (armazenamento em S3 ou local)
- [ ] Exibir histórico na aba "Detalhes" do modal de edição

---

## Fase 3 — Organização Hierárquica e Navegação Avançada

> Objetivo: Ajudar o usuário a encontrar o que precisa em uma rede que não para de crescer.

### 3.1 Sistema de Pastas (Tree View)
- [ ] Modelo `CableFolder` no banco (hierarquia com `parent_id`)
- [ ] Painel lateral retrátil com árvore de pastas
  - Exemplo: `Pará > Santana do Araguaia > Backbone > Cabo X`
- [ ] Drag & drop para mover cabos entre pastas
- [ ] Ao clicar em uma pasta, o mapa filtra e exibe apenas os cabos dela

### 3.2 Controle de Camadas (Map Layers)
- [ ] Painel de layers com switches para ligar/desligar categorias:
  - Backbone, Distribuição, Drop de Cliente, Caixas de Emenda, Dispositivos
- [ ] Estado das camadas persiste no localStorage do usuário
- [ ] Atalho de teclado para alternar layers rapidamente

### 3.3 Busca Global
- [ ] Barra de pesquisa rápida no topo do mapa
- [ ] Busca por nome de cabo, dispositivo, site, endereço
- [ ] Resultado centraliza o mapa no elemento encontrado e o destaca

---

## Fase 4 — Inteligência Operacional e Integração

> Objetivo: Transformar o mapa de um "desenho" em uma ferramenta viva de operação.

### 4.1 Cálculo Automático e Orçamento Óptico
- [x] Distância total calculada automaticamente durante desenho da rota
  - _Concluído: exibido em "Total distance: X.XXX km" no painel Route Points_
- [ ] Cruzar distância com `atenuacao_db_por_km` do grupo do cabo
- [ ] Exibir estimativa de perda de sinal (dB) no modal ao salvar
- [ ] Alertar quando perda estimada ultrapassar limiar configurável

### 4.2 Status Visual Dinâmico
- [ ] Vincular alertas do Zabbix ao mapa em tempo real (polling ou WebSocket)
- [ ] Cabos mudam de cor conforme status:
  - Verde = operacional | Amarelo = degradado | Vermelho = rompido/crítico
- [ ] Tooltip no hover mostra último status recebido e timestamp

### 4.3 Modo "Área de Manutenção"
- [ ] Ferramenta de seleção por polígono desenhado no mapa
- [ ] Identifica automaticamente cabos, caixas e clientes dentro da área
- [ ] Gera lista exportável (CSV/PDF) dos elementos afetados
- [ ] Integração futura: disparo de notificação/alerta para clientes da área

---

## Registro de Progresso

| Data | Fase | Tarefa | Responsável | Notas |
|------|------|--------|-------------|-------|
| 2026-03-23 | — | Criação deste plano | Claude + Paulo | Baseado na proposta de evolução aprovada |
| 2026-03-23 | 2.2 | Modal save cable com device/port selects | Claude | Restaurados selects, validação coords corrigida |
| 2026-03-23 | 4.1 | Distância total na rota | — | Já existia, confirmado funcionando |
| 2026-03-23 | 1.1 | Route Points panel oculto por padrão | Claude | nd-panel-hidden + setRoutePointsPanelVisible() |
| 2026-03-23 | 1.2 | Tips como botão FAB "?" com popover | Claude | #helpFab + #helpPopover substituem painel fixo |
| 2026-03-23 | 1.3 | Painel de detalhes + preview de cabo | Claude | previewCable() + CableDetailsPanel + contextPreviewOptions |

---

## Notas Técnicas

- **Frontend:** Vue 3 SPA (Vite) em `frontend/src/components/NetworkDesign/` e `frontend/src/features/networkDesign/`
- **Backend:** Django REST API em `backend/inventory/api/fibers.py` e `backend/inventory/models/`
- **Mapa:** Mapbox (padrão) via provider pattern — `frontend/src/providers/maps/`
- **Build:** Após alterações no frontend, executar `npm run build` no container e `collectstatic`
- **Docker:** Alterações Python requerem `docker restart docker-web-1`
