# Plano de Evolução — Network/NetworkDesign/

> **Como usar este arquivo:** À medida que cada tarefa for concluída, marque `[x]` na checkbox correspondente e adicione uma nota com a data e o que foi feito. Tarefas em andamento ficam com `[-]`.

---

## Fase 1 — Limpeza Visual e Otimização de Tela (Quick Wins)

> Objetivo: Ganhar área útil de mapa e melhorar a primeira impressão do usuário.

### 1.1 Refatoração do Painel "Route Points"
- [x] Painel fica **oculto por padrão** (nd-panel-hidden com transição opacity/transform)
  - _2026-03-23: classe `nd-panel-hidden` adicionada ao template; lógica de show/hide em onPathChange e loadFiberDetail_
- [x] Aparece ao adicionar o primeiro ponto ou ao entrar em modo de edição de cabo existente
- [x] Painel é redimensionável ou tem tamanho proporcional à viewport
  - _2026-04-03: alça de resize na base do painel; drag ajusta altura; persiste em localStorage_
- [x] Fecha automaticamente ao cancelar/salvar a edição (`cancelEditing` chama `setRoutePointsPanelVisible(false)`)

### 1.2 Minimização da Caixa de Dicas (Tips)
- [x] Substituir caixa fixa por botão FAB flutuante "?" no canto inferior direito
  - _2026-03-23: `#helpFab` + `#helpPopover` substituem o `#helpPanel` original_
- [x] Ao clicar, popover elegante abre/fecha com transição suave; fecha ao clicar fora
- [x] Dicas se adaptam ao contexto atual (modo edição, modo visualização, etc.)
  - _2026-04-03: 4 conjuntos de dicas (visualizacao/preview/desenho/edicao); __ndSetHelpMode chamado nas transições de estado_

### 1.3 Menus de Contexto (Right-click)
- [x] Implementado menu de contexto no mapa (clique direito sobre cabos/elementos)
  - _Concluído: modal editor com opções Editar, Salvar, Cancelar, Deletar_
- [x] Adicionar ação "Ver detalhes" que abre painel lateral sem entrar em modo edição
  - _2026-03-23: right-click abre modo preview → painel Cable Details (read-only) com Editar/Excluir_
- [x] Separar fluxo de preview vs edição no context menu
  - _2026-03-23: seção contextPreviewOptions (Ver detalhes / Editar rota / Excluir) vs contextSelectedOptions (editando)_
- [ ] Refinar opções do menu por tipo de elemento (cabo, caixa, ponto de emenda) — fase 3+

### 1.4 Correções de UX e Estabilidade
- [x] Tecla ESC cancela edição corretamente em modo de cabo existente
- [x] Tecla ESC cancela durante criação manual de rota nova (quando `getPath().length > 0`)
  - _2026-04-03: fix em fiberRouteBuilder.js — antes só verificava activeFiberId, não detectava rota nova sem ID_
- [x] Botão cancelar no modal reset state corretamente
- [x] Bug "Fill in all required fields" ao salvar corrigido

---

## Fase 2 — Evolução da Estrutura de Dados e Modais

> Objetivo: Preparar o "motor" do sistema para receber informações mais ricas.

### 2.1 Modelagem de Novos Cadastros Base
- [x] **Grupos de Cabos** — modelo no banco com campos:
  - `nome`, `fabricante`, `quantidade_fibras`, `atenuacao_db_por_km`
  - _2026-03-23: model CableGroup + FK cable_group em FiberCable + migration 0057_
- [x] **Responsáveis** — migrado para usuários do sistema (`auth.User`)
  - _2026-03-23: model Responsible + migrations 0058/0059 (legado)_
  - _2026-04-03: campo `responsible_user` FK para `auth.User` + migration 0062; select no modal usa `/api/users/`_
- [x] Migrations e serializers para Grupos de Cabos
  - _2026-03-23: migrations 0057–0059 aplicadas_
- [x] Endpoints REST: `GET/POST /api/v1/inventory/cable-groups/`
  - _2026-03-23: api/cable_groups.py + urls_api.py_
- [x] Endpoints REST: `PATCH /api/v1/inventory/cable-groups/<id>/` e `DELETE /api/v1/inventory/cable-groups/<id>/delete/`
  - _2026-04-03: api_update_cable_group + api_delete_cable_group adicionados_
- [x] Endpoints REST: `GET/POST /api/v1/inventory/responsibles/` (legado mantido)
  - _2026-03-23: api/responsibles.py + urls_api.py_

### 2.2 Modernização do Modal de Salvamento de Cabo
- [x] Modal "Save cable manually" com selects de dispositivo e porta funcionando
  - _Concluído: dropdown de device e port restaurados e funcionando_
- [x] Validação de coordenadas do dispositivo corrigida (usa Site.latitude/longitude)
- [x] Adicionar campo **Grupo do Cabo** (select populado da API, criação inline com +)
  - _2026-03-23: manualCableGroupSelect + addCableGroupBtn + loadCableGroups()_
- [x] Adicionar campo **Pasta/Organização** no modal de salvamento (picker hierárquico)
  - _2026-04-03: select hierárquico adicionado na aba Identificação; pré-seleciona a pasta do cabo no edit; folder_id enviado no payload_
- [x] Adicionar campo **Responsável** (select de usuários do sistema)
  - _2026-04-03: select usa `/api/users/?is_active=true`; payload envia `responsible_user_id`_
- [x] Reorganizar modal em abas: "Identificação" | "Conexões"
  - _2026-03-23: tab switching JS + CSS modal-tabs/modal-tab/modal-tab-panel_

### 2.3 Histórico e Anexos (Audit & Docs)
- [x] Log automático de criação/edição/exclusão: quem fez, quando
  - _2026-03-23: model FiberCableAuditLog + migration 0060 + _log_audit() em create/update/delete_
- [x] Exibir histórico na aba "Histórico" do modal de edição
  - _2026-03-23: endpoint GET /api/v1/inventory/fibers/{id}/audit-log/ + tab JS + CSS_
- [x] Upload de fotos da instalação (armazenamento local)
  - _2026-04-03: model FiberCablePhoto + migration 0065 + api/cable_photos.py + aba "Fotos" no modal com galeria, lightbox e drag & drop_

### 2.4 Painel Admin de Grupos e Pastas (Configurações)
- [x] Botão de engrenagem integrado no rodapé do painel Camadas
  - _2026-04-03: `.nd-layer-panel__footer` com toggle Camadas + gear icon lado a lado; removido FAB flutuante_
- [x] Modal "Configurações" com submenu: Grupos de Cabo | Pastas
  - _2026-04-03: nd-admin-modal com nd-admin-tabs_
- [x] CRUD de Grupos de Cabo inline (criar, renomear, excluir com confirmação)
  - _2026-04-03: createAdminGroup / saveAdminGroup / deleteAdminGroup; chama PATCH/DELETE na API_
- [x] CRUD de Pastas inline (criar root, criar subpasta, renomear, excluir)
  - _2026-04-03: createFolder / saveAdminFolder / deleteAdminFolder_
- [x] Criação/exclusão de grupos reflete em tempo real no painel Camadas
  - _2026-04-03: loadCableGroupsFromApi() chama setApiGroups + refreshLayerGroups após cada operação_

---

## Fase 3 — Organização Hierárquica e Navegação Avançada

> Objetivo: Ajudar o usuário a encontrar o que precisa em uma rede que não para de crescer.

### 3.1 Sistema de Pastas (Tree View)
- [x] Modelo `CableFolder` no banco (hierarquia com `parent_id`)
  - _2026-03-24: model CableFolder + FK folder em FiberCable + migrations 0061_
- [x] Endpoints REST: `GET/POST /api/v1/inventory/cable-folders/` + PATCH/DELETE/move-folder
  - _2026-03-24: api/cable_folders.py + urls_api.py_
- [x] Painel lateral retrátil com árvore de pastas
  - _2026-03-24: nd-folder-panel no NetworkDesignView, expand/collapse, filtro de mapa_
- [x] Ao clicar em uma pasta, o mapa filtra e exibe apenas os cabos dela
  - _2026-03-24: setFolderFilter() em cableService + combina com filtro de grupo_
- [x] Filtro de pasta persiste corretamente após recarregar todos os cabos
  - _2026-04-03: bloco reapply no final de loadAllCablesForVisualization; activeFolderFilterIds persiste no módulo_
- [x] Filtro hierárquico: selecionar pasta pai mostra cabos de todas as subpastas
  - _2026-04-03: collectFolderIds() recursivo + activeFolderFilterIds (Set); _getEffectiveVisibility usa .has()_
- [x] Contagem de cabos por pasta mostra total agregado (pasta + subpastas)
  - _2026-04-03: aggregateCableCount() recursivo + campo aggregate_count em flatFolders; template atualizado_
- [x] "Mover para pasta" na aba Cable Details (picker modal)
  - _2026-03-24: POST fibers/{id}/move-folder/ + nd-move-folder-card_
- [x] Criação inline de pasta (root e subpasta) no painel
  - _2026-03-24: startFolderCreate / createFolder + input inline_
- [x] Drag & drop para mover cabos entre pastas
  - _2026-04-03: handle de 6 pontos no botão Pasta (split button); drag abre painel automaticamente; drop em pasta chama move-folder API_

### 3.2 Controle de Camadas (Map Layers)
- [x] Painel de layers com switches para ligar/desligar por grupo de cabo
  - _2026-03-24: botão "Camadas" no canto inferior esquerdo, toggle por CableGroup + "Sem grupo"_
- [x] Estado das camadas persiste no localStorage do usuário
  - _2026-03-24: nd_layer_visibility salvo/restaurado automaticamente_
- [x] Contagem de cabos por grupo reflete dados reais carregados
  - _2026-04-03: getGroupCounts() em cableService; refreshLayerGroups usa counts reais_
- [x] Categorias pré-definidas (Backbone/Distribuição/Drop) — depende de campo cable_type no modelo
  - _2026-04-03: campo cable_type em FiberCable + migration 0063; select no modal Identificação; seção "Tipo" no painel Camadas com filtro independente_

### 3.3 Busca Global
- [x] Barra de pesquisa rápida no topo do mapa
  - _2026-03-24: input centrado, debounce 300ms, v-click-outside fecha dropdown_
- [x] Busca por nome de cabo, dispositivo, site
  - _2026-03-24: endpoint GET /api/v1/inventory/search/?q= (6 resultados por tipo)_
- [x] Resultado centraliza o mapa no elemento encontrado
  - _2026-03-24: map.flyTo via getMapInstance(); zoom 13 cabos / 15 device+site_
- [x] Destacar o elemento selecionado no mapa (highlight visual temporário)
  - _2026-04-03: highlightSearchResult() — cabos piscam em amarelo (setPaintProperty), dispositivos/sites ganham círculo pulsante via Mapbox GL source/layer; timeout 900ms pós-flyTo_

---

## Fase 4 — Inteligência Operacional

> Objetivo: Transformar o mapa de um "desenho" em uma ferramenta viva de operação.

### 4.1 Cálculo Automático e Orçamento Óptico
- [x] Distância total calculada automaticamente durante desenho da rota
  - _Concluído: exibido em "Total distance: X.XXX km" no painel Route Points_
- [x] Cruzar distância com `atenuacao_db_por_km` do grupo do cabo
  - _2026-04-03: opções do select carregam data-attenuation; _updateLossEstimate() calcula loss = attenuation × km_
- [x] Exibir estimativa de perda de sinal (dB) no modal ao salvar
  - _2026-04-03: #manualLossEstimate exibe "Perda estimada: X.XX dB", atualiza em tempo real ao desenhar ou trocar grupo_
- [x] Alertar quando perda estimada ultrapassar limiar configurável
  - _2026-04-03: limiar padrão 30 dB; borda amarela + "⚠ Acima do limiar (30 dB)"_

### 4.2 Porta Destino e Conexões de Fibras
- [x] "Porta destino" exibe corretamente (fix do bug "— (porta única)")
  - _2026-04-03: lógica de fallback para portas únicas corrigida no modal_
- [ ] Visualização gráfica do splicing (fibra a fibra) — fase futura

---

## Fase 5 — Monitoramento em Tempo Real
> ⚠️ **Estas implementações devem ser feitas APÓS a conclusão de tudo em Network/NetworkDesign.**
> **Local de implementação: `/monitoring/backbone`** — mapa padrão de monitoramento existente.

### 5.1 Status Visual Dinâmico (em `/monitoring/backbone`)
- [x] Vincular alertas do Zabbix ao mapa em tempo real (polling ou WebSocket)
  - _2026-04-03: polling a cada 30s via /api/v1/monitoring/hosts/status/; startStatusPolling/stopStatusPolling no ciclo de vida_
- [x] Cabos mudam de cor conforme status:
  - Verde = operacional | Amarelo = degradado | Vermelho = rompido/crítico
  - _2026-04-03: status do cabo derivado dos devices endpoint (origin_device_id/destination_device_id); useMapPolylines já aplica statusColors_
- [x] Tooltip no hover mostra último status recebido e timestamp
  - _2026-04-03: badge "status-poll-badge" exibe online/offline count + "X seg atrás"; CableOpticalTooltip já existia_

### 5.2 Modo "Área de Manutenção" (em `/monitoring/backbone`)
- [x] Ferramenta de seleção por polígono desenhado no mapa
  - _2026-04-03: botão FAB "Manutenção" no canto inferior esquerdo; cursor crosshair ao entrar no modo; cliques adicionam vértices_
- [x] Identifica automaticamente cabos e equipamentos dentro da área
  - _2026-04-03: ray casting PIP client-side contra `availableItems.cables` e `availableItems.devices`; funciona com os 3 providers (Google/Mapbox/Leaflet)_
- [x] Gera lista exportável (CSV) dos elementos afetados
  - _2026-04-03: painel lateral `MaintenanceAreaPanel.vue` com botão CSV; agrupa devices por site; exibe status de cada item_
- [ ] Integração futura: disparo de notificação/alerta para clientes da área e responsaveis pela manutenção da area selecionada.

---

## Pendências Prioritárias — NetworkDesign (próximos passos)

> O que ainda falta concluir antes de migrar para Fase 5.

| Prioridade | Item | Fase | Observação |
|-----------|------|------|------------|
| ~~Média~~ | ~~Categorias pré-definidas de camada (Backbone/Drop)~~ | 3.2 | ✅ Concluído 2026-04-03 |
| ~~Baixa~~ | ~~Dicas contextuais (modo edição vs visualização)~~ | 1.2 | ✅ Concluído 2026-04-03 |
| ~~Baixa~~ | ~~Painel Route Points redimensionável~~ | 1.1 | ✅ Concluído 2026-04-03 |
| ~~Baixa~~ | ~~Drag & drop de cabos entre pastas~~ | 3.1 | ✅ Concluído 2026-04-03 |
| ~~Baixa~~ | ~~Upload de fotos da instalação~~ | 2.3 | ✅ Concluído 2026-04-03 — armazenamento local |

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
| 2026-03-23 | 2.1 | Modelo Responsible + endpoints REST | Claude | model + migrations 0058/0059 + api/responsibles.py |
| 2026-03-23 | 2.2 | Modal com abas + campos Grupo e Responsável | Claude | tab switching JS/CSS + loadCableGroups/Responsibles + payload |
| 2026-03-23 | fix | Crash ao voltar para NetworkDesign/ | Claude | cleanupCableService antes de cleanupMap + safeRemovePolyline |
| 2026-03-23 | 2.3 | Audit log de criação/edição/exclusão | Claude | FiberCableAuditLog + migration 0060 + aba Histórico no modal |
| 2026-03-24 | 3.3 | Busca global (cabo/device/site) | Claude | api/search.py + barra Vue com debounce + flyTo no mapa |
| 2026-03-24 | 3.1 | Sistema de Pastas completo | Claude | CableFolder model + API + painel Vue + filtro de mapa + mover cabo |
| 2026-04-03 | 1.4 | ESC durante criação de rota nova | Claude | getPath().length > 0 em fiberRouteBuilder.js |
| 2026-04-03 | 2.1 | responsible_user FK para auth.User | Claude | migration 0062 + select usa /api/users/ + payload responsible_user_id |
| 2026-04-03 | 2.1 | Endpoints PATCH/DELETE cable-groups | Claude | api_update_cable_group + api_delete_cable_group |
| 2026-04-03 | 2.4 | Painel admin Configurações (grupos + pastas) | Claude | gear icon no rodapé Camadas + modal CRUD inline |
| 2026-04-03 | 2.4 | Grupos refletem em tempo real no painel Camadas | Claude | setApiGroups + loadCableGroupsFromApi + getGroupCounts |
| 2026-04-03 | 3.1 | Filtro de pasta persiste após reload dos cabos | Claude | reapply block no loadAllCablesForVisualization |
| 2026-04-03 | 3.1 | Filtro hierárquico de subpastas | Claude | collectFolderIds() + activeFolderFilterIds (Set) |
| 2026-04-03 | 3.1 | Contagem agregada de cabos por pasta | Claude | aggregateCableCount() + aggregate_count em flatFolders |
| 2026-04-03 | 2.2 | Campo Pasta no modal de salvar cabo | Claude | folder_id no payload + backend create/update_metadata + select hierárquico |
| 2026-04-03 | 3.2 | Categorias pré-definidas (Tipo de cabo) | Claude | cable_type no model + migration 0063 + select modal + seção Tipo no painel Camadas com filtro |
| 2026-04-03 | 3.3 | Highlight de elemento na busca | Claude | highlightSearchResult(): cabo → setPaintProperty amarelo; device/site → circle layer temp |
| 2026-04-03 | 4.1 | Estimativa de perda óptica em tempo real | Claude | _updateLossEstimate() + data-attenuation nas opções; alerta >30 dB |
| 2026-04-03 | 3.1 | Drag & drop de cabos entre pastas | Claude | split button no Cable Details; dragstart → pasta droppable com highlight; onFolderDrop chama move-folder |

---

## Notas Técnicas

- **Frontend:** Vue 3 SPA (Vite) em `frontend/src/components/NetworkDesign/` e `frontend/src/features/networkDesign/`
- **Backend:** Django REST API em `backend/inventory/api/fibers.py` e `backend/inventory/models/`
- **Mapa:** Mapbox (padrão) via provider pattern — `frontend/src/providers/maps/`
- **Build:** Após alterações no frontend, executar `npm run build` no host (não dentro do Docker)
- **Docker:** Alterações Python requerem `docker restart docker-web-1`
- **Monitoramento:** Fases 5.1 e 5.2 pertencem a `/monitoring/backbone`, não ao NetworkDesign
