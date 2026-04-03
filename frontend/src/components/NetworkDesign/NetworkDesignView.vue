<template>
  <div class="network-design-page">
    <!-- ── Fallback cables alert ────────────────────────────────── -->
    <div
      v-if="fallbackCables.length && !fallbackAlertDismissed"
      class="nd-fallback-alert"
    >
      <svg viewBox="0 0 20 20" style="width:16px;height:16px;flex-shrink:0;margin-top:1px" aria-hidden="true">
        <path d="M10 2a8 8 0 100 16A8 8 0 0010 2zm0 4a1 1 0 011 1v4a1 1 0 01-2 0V7a1 1 0 011-1zm0 8a1 1 0 100-2 1 1 0 000 2z" fill="currentColor"/>
      </svg>
      <span>
        <strong>{{ fallbackCables.length }} cabo(s) sem rota</strong> — rota perdida, redesenhe via
        <strong>Editar rota</strong>:
        {{ fallbackCables.map(c => c.name).join(', ') }}
      </span>
      <button class="nd-fallback-alert__close" @click="fallbackAlertDismissed = true" aria-label="Fechar">✕</button>
    </div>
    <!-- ── Global search bar ─────────────────────────────────── -->
    <div class="map-search-wrapper" v-click-outside="closeSearch">
      <div class="map-search-input-row">
        <svg class="map-search-icon" viewBox="0 0 20 20" aria-hidden="true">
          <circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="1.8"/>
          <line x1="12.5" y1="12.5" x2="17" y2="17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
        <input
          id="mapSearchInput"
          v-model="searchQuery"
          type="search"
          class="map-search-input"
          placeholder="Buscar cabo, device ou site…"
          autocomplete="off"
          @input="onSearchInput"
          @keydown.down.prevent="searchFocusNext(1)"
          @keydown.up.prevent="searchFocusNext(-1)"
          @keydown.enter.prevent="searchSelectFocused"
          @keydown.esc="closeSearch"
        />
        <span v-if="searchLoading" class="map-search-spinner" aria-hidden="true"></span>
      </div>
      <ul
        v-if="searchResults.length"
        class="map-search-dropdown"
        role="listbox"
        aria-label="Resultados da busca"
      >
        <template v-for="group in searchGroups" :key="group.type">
          <li class="map-search-group-label" role="presentation">{{ group.label }}</li>
          <li
            v-for="(item, iIdx) in group.items"
            :key="item.id + item.type"
            class="map-search-item"
            :class="{ focused: searchFocusIdx === group.startIdx + iIdx }"
            role="option"
            :aria-selected="searchFocusIdx === group.startIdx + iIdx"
            @click="selectSearchResult(item)"
            @mouseenter="searchFocusIdx = group.startIdx + iIdx"
          >
            <span class="map-search-item__icon" :data-type="item.type"></span>
            <span class="map-search-item__name">{{ item.name }}</span>
            <span v-if="item.subtitle" class="map-search-item__sub">{{ item.subtitle }}</span>
          </li>
        </template>
        <li v-if="!searchResults.length && !searchLoading" class="map-search-empty">Nenhum resultado.</li>
      </ul>
    </div>

    <div class="map-container">
      <div id="builderMap" class="map-canvas" role="presentation"></div>
    </div>

    <section
      id="routePointsPanel"
      class="floating-panel nd-panel-hidden"
      aria-labelledby="routePointsPanelTitle"
    >
      <div class="floating-panel__header">
        <div class="floating-panel__header-main">
          <h3 id="routePointsPanelTitle">Route points</h3>
          <div class="floating-panel__metric">
            Total distance: <span id="distanceKm">0.000</span> km
          </div>
        </div>
        <button
          id="toggleRoutePoints"
          type="button"
          class="panel-toggle-btn"
          aria-expanded="true"
          aria-controls="routePointsPanelBody"
        >
          <svg class="panel-toggle-icon" viewBox="0 0 20 20" aria-hidden="true">
            <path d="M5.5 7.5L10 12l4.5-4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span class="sr-only">Collapse route points</span>
        </button>
      </div>
      <div id="routePointsPanelBody" class="floating-panel__body" aria-hidden="false">
        <p class="floating-panel__description">
          Drag points to reorder them or right-click the map to access additional options.
        </p>
        <ul id="pointsList" class="route-points-list"></ul>
        <div class="floating-panel__footer">
          <button
            id="manualSaveRouteButton"
            type="button"
            class="footer-btn footer-btn--primary"
            @click="saveNetworkDesignRoute"
          >
            Salvar rota
          </button>
          <button
            id="manualCancelButton"
            type="button"
            class="footer-btn"
            @click="cancelNetworkDesignEditing"
          >
            Cancelar edição
          </button>
        </div>
      </div>
      <div class="panel-resize-handle" @mousedown.prevent="startPanelResize" title="Arraste para redimensionar"></div>
    </section>

    <div class="help-fab-wrapper" v-click-outside="closeHelpPopover">
      <div class="help-popover" :class="{ visible: helpOpen }" :aria-hidden="String(!helpOpen)">
        <div class="help-mode-label">{{ currentHelpTips.title }}</div>
        <ul class="help-list">
          <li v-for="(tip, i) in currentHelpTips.tips" :key="i">
            <span class="help-icon">{{ tip.icon }}</span>
            <span>{{ tip.text }}</span>
          </li>
        </ul>
      </div>
      <button
        type="button"
        class="help-fab"
        :class="{ active: helpOpen }"
        aria-label="Dicas de uso"
        :aria-expanded="String(helpOpen)"
        @click.stop="helpOpen = !helpOpen"
      >?</button>
    </div>

    <div id="contextMenu" class="hidden">
      <!-- Cable info header (shown when a cable is selected) -->
      <div id="contextCableInfo" class="hidden">
        <div class="ctx-cable-badges" id="contextCableBadges"></div>
        <p id="contextCableName">&mdash;</p>
      </div>

      <!-- Mapa vazio / sem seleção -->
      <div id="contextGeneralOptions" class="space-y-2">
        <h3>Ações do mapa</h3>
        <button id="contextLoadAll" type="button">
          <span id="contextLoadAllText">Recarregar cabos</span>
        </button>
        <button id="contextImportKML" type="button">Importar rota (KML)</button>
      </div>

      <!-- Cabo selecionado (preview) -->
      <div id="contextPreviewOptions" class="hidden space-y-2 mt-3">
        <h3>Cabo</h3>
        <button id="contextViewDetails" type="button">
          <svg viewBox="0 0 16 16" class="ctx-icon" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path stroke-linecap="round" d="M8 7v4M8 5.5v.5"/></svg>
          Ver detalhes
        </button>
        <button id="contextViewPhotos" type="button">
          <svg viewBox="0 0 16 16" class="ctx-icon" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1.5" y="3.5" width="13" height="9" rx="1.5"/><circle cx="8" cy="8" r="2"/><path stroke-linecap="round" d="M5.5 3.5l1-1.5h3l1 1.5"/></svg>
          Ver fotos
        </button>
        <button id="contextStartEdit" type="button">
          <svg viewBox="0 0 16 16" class="ctx-icon" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M2 12l8.5-8.5 2 2L4 14H2v-2z"/></svg>
          Editar rota
        </button>
        <button id="contextEditMetaPreview" type="button">
          <svg viewBox="0 0 16 16" class="ctx-icon" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="1.5"/><path stroke-linecap="round" d="M5 6h6M5 9h4"/></svg>
          Editar dados
        </button>
        <button id="contextDeletePreview" type="button" data-variant="danger">
          <svg viewBox="0 0 16 16" class="ctx-icon" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 4h10M6 4V2.5h4V4M5 4l.5 9M11 4l-.5 9"/></svg>
          Excluir cabo
        </button>
      </div>

      <!-- Editando cabo (rota ativa) -->
      <div id="contextSelectedOptions" class="hidden space-y-2 mt-3">
        <h3>Editando rota</h3>
        <button id="contextEditCable" type="button">
          <svg viewBox="0 0 16 16" class="ctx-icon" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="1.5"/><path stroke-linecap="round" d="M5 6h6M5 9h4"/></svg>
          Editar dados do cabo
        </button>
        <button id="contextSavePath" type="button">
          <svg viewBox="0 0 16 16" class="ctx-icon" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.5 9.5l3 3 8-8"/></svg>
          Salvar rota
        </button>
        <button id="contextCancelEdit" type="button">
          <svg viewBox="0 0 16 16" class="ctx-icon" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" d="M4 4l8 8M12 4l-8 8"/></svg>
          Cancelar edição
        </button>
        <button id="contextDeleteCable" type="button" data-variant="danger">
          <svg viewBox="0 0 16 16" class="ctx-icon" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 4h10M6 4V2.5h4V4M5 4l.5 9M11 4l-.5 9"/></svg>
          Excluir cabo
        </button>
      </div>

      <!-- Desenhando nova rota -->
      <div id="contextCreatingOptions" class="hidden space-y-2 mt-3">
        <h3>Nova rota</h3>
        <button id="contextSaveNewCable" type="button">
          <svg viewBox="0 0 16 16" class="ctx-icon" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.5 9.5l3 3 8-8"/></svg>
          Salvar novo cabo
        </button>
        <button id="contextClearNew" type="button">
          <svg viewBox="0 0 16 16" class="ctx-icon" fill="none" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" d="M4 4l8 8M12 4l-8 8"/></svg>
          Limpar pontos
        </button>
      </div>
    </div>

    <section
      id="cableDetailsPanel"
      class="floating-panel nd-panel-hidden"
      aria-labelledby="cableDetailsPanelTitle"
      :style="cableDetailPanelStyle"
    >
      <div class="floating-panel__header cable-detail-drag-handle" @mousedown.prevent="startCableDetailDrag">
        <h3 id="cableDetailsPanelTitle">Cable details</h3>
        <button id="closeCableDetails" type="button" class="panel-toggle-btn" aria-label="Fechar painel" @mousedown.stop>
          <svg viewBox="0 0 20 20" aria-hidden="true" style="width:18px;height:18px">
            <path d="M5 5l10 10M15 5L5 15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
      <div class="floating-panel__body">
        <div id="cableNoPathWarning" style="display:none;background:#7c2d12;color:#fed7aa;border-radius:6px;padding:8px 10px;margin-bottom:10px;font-size:12px;line-height:1.5;">
          ⚠️ Rota não encontrada. Use <strong>Editar rota</strong> para redesenhar o trajeto.
        </div>
        <dl class="cable-details-dl">
          <div class="cable-details-row">
            <dt>Nome</dt>
            <dd id="cableDetailName">—</dd>
          </div>
          <div class="cable-details-row">
            <dt>Distância</dt>
            <dd id="cableDetailDistance">—</dd>
          </div>
          <div class="cable-details-row" id="cableDetailLossRow" style="display:none">
            <dt>Perda estimada</dt>
            <dd id="cableDetailLoss" style="display:flex;align-items:center;gap:0.4rem">
              <span id="cableDetailLossValue">—</span>
              <span id="cableDetailLossWarn" style="display:none;color:#d97706;font-size:0.75rem;font-weight:600">⚠ &gt;30 dB</span>
            </dd>
          </div>
          <div class="cable-details-row">
            <dt>Origem</dt>
            <dd id="cableDetailOrigin">—</dd>
          </div>
          <div class="cable-details-row">
            <dt>Destino</dt>
            <dd id="cableDetailDestination">—</dd>
          </div>
          <div class="cable-details-row">
            <dt>Tipo</dt>
            <dd id="cableDetailType">—</dd>
          </div>
          <div class="cable-details-row">
            <dt>Grupo</dt>
            <dd id="cableDetailGroup">—</dd>
          </div>
          <div class="cable-details-row">
            <dt>Responsável</dt>
            <dd id="cableDetailResponsible">—</dd>
          </div>
          <div class="cable-details-row">
            <dt>Pasta</dt>
            <dd id="cableDetailFolder">—</dd>
          </div>
        </dl>

        <div class="floating-panel__footer">
          <button id="cableDetailMetaBtn" type="button" class="footer-btn footer-btn--primary">Editar dados</button>
          <div class="footer-btn-split">
            <button type="button" class="footer-btn footer-btn-split__main" @click="moveFolderPickerOpen = true" title="Mover para pasta">
              <svg viewBox="0 0 16 16" style="width:13px;height:13px;flex-shrink:0" aria-hidden="true">
                <path d="M1 4.5A1.5 1.5 0 012.5 3h3.25L7 4.5H13.5A1.5 1.5 0 0115 6v6a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 011 12V4.5z" fill="currentColor" opacity=".8"/>
              </svg>Pasta
            </button>
            <div
              class="footer-btn footer-btn-split__drag nd-cable-drag-handle"
              draggable="true"
              @dragstart="onCableDragStart"
              @dragend="onCableDragEnd"
              title="Arrastar para mover para pasta"
            >
              <svg viewBox="0 0 16 16" style="width:10px;height:10px" aria-hidden="true">
                <circle cx="5" cy="4" r="1.2" fill="currentColor"/><circle cx="11" cy="4" r="1.2" fill="currentColor"/>
                <circle cx="5" cy="8" r="1.2" fill="currentColor"/><circle cx="11" cy="8" r="1.2" fill="currentColor"/>
                <circle cx="5" cy="12" r="1.2" fill="currentColor"/><circle cx="11" cy="12" r="1.2" fill="currentColor"/>
              </svg>
            </div>
          </div>
          <button id="cableDetailEditBtn" type="button" class="footer-btn">Editar rota</button>
          <button id="cableDetailDeleteBtn" type="button" class="footer-btn footer-btn--danger">Excluir</button>
        </div>
      </div>
    </section>

    <!-- ── Layer control panel ───────────────────────────────── -->
    <div class="nd-layer-panel">
      <div class="nd-layer-panel__footer">
        <button
          type="button"
          class="nd-layer-panel__toggle"
          @click="layerPanelOpen = !layerPanelOpen"
          :aria-expanded="String(layerPanelOpen)"
          title="Controle de camadas"
        >
          <svg viewBox="0 0 20 20" aria-hidden="true" class="nd-layer-icon">
            <rect x="2" y="4" width="16" height="2.5" rx="1" fill="currentColor"/>
            <rect x="2" y="8.75" width="16" height="2.5" rx="1" fill="currentColor" opacity=".7"/>
            <rect x="2" y="13.5" width="16" height="2.5" rx="1" fill="currentColor" opacity=".4"/>
          </svg>
          <span>Camadas</span>
        </button>
        <button
          type="button"
          class="nd-layer-panel__gear"
          @click="adminOpen = true; adminTab = 'grupos'; loadAdminGroups()"
          title="Configurações"
        >
          <svg viewBox="0 0 20 20" aria-hidden="true" width="15" height="15">
            <path fill="currentColor" d="M10 13a3 3 0 100-6 3 3 0 000 6zm7.2-1.4l1.3-1a1 1 0 000-1.2l-1.3-1a6 6 0 00-.2-.6l.5-1.5a1 1 0 00-.5-1.2l-1.6-.7a1 1 0 00-1.2.4l-.8 1.3a6 6 0 00-.6 0l-1-1.3a1 1 0 00-1.2-.4l-1.5.5a1 1 0 00-.6 1l.1 1.6a6 6 0 00-.4.5L5 8.2a1 1 0 00-1.2.5l-.7 1.6a1 1 0 00.4 1.2l1.3.8v.6l-1.3.8a1 1 0 00-.4 1.2l.7 1.6A1 1 0 005 16.8l1.5-.5.5.4-.1 1.6a1 1 0 00.6 1l1.5.5a1 1 0 001.2-.4l.8-1.3.6-.1 1 1.3a1 1 0 001.2.4l1.6-.7a1 1 0 00.5-1.2l-.5-1.5.2-.6 1.3-1a1 1 0 000-1.2z"/>
          </svg>
        </button>
      </div>
      <div v-if="layerPanelOpen && (layerGroups.length || typeItems.length)" class="nd-layer-panel__body">
        <label class="nd-layer-row nd-layer-row--all">
          <input type="checkbox" v-model="layerAllVisible" @change="toggleAllLayers" />
          <span>Todos os cabos</span>
        </label>
        <div v-if="typeItems.length">
          <div class="nd-layer-divider nd-layer-section-label">Tipo</div>
          <label
            v-for="item in typeItems"
            :key="item.value"
            class="nd-layer-row"
          >
            <input
              type="checkbox"
              :checked="item.visible"
              @change="toggleTypeLayer(item)"
            />
            <span class="nd-layer-dot nd-layer-dot--type"></span>
            <span>{{ item.label }}</span>
            <span class="nd-layer-count">{{ item.count }}</span>
          </label>
        </div>
        <div v-if="layerGroups.length">
          <div class="nd-layer-divider nd-layer-section-label">Grupo</div>
          <label
            v-for="group in layerGroups"
            :key="group.id ?? '__none__'"
            class="nd-layer-row"
          >
            <input
              type="checkbox"
              :checked="layerState[group.id ?? '__none__']"
              @change="toggleGroupLayer(group)"
            />
            <span class="nd-layer-dot" :style="{ background: group.color }"></span>
            <span>{{ group.name }}</span>
            <span class="nd-layer-count">{{ group.count }}</span>
          </label>
        </div>
      </div>
    </div>

    <!-- ── Folder tree panel ──────────────────────────────── -->

    <!-- ── Admin modal ─────────────────────────────────────── -->
    <div v-if="adminOpen" class="nd-admin-overlay" @click.self="adminOpen = false">
      <div class="nd-admin-modal">
        <div class="nd-admin-header">
          <h3>Configurações</h3>
          <button type="button" class="nd-admin-close" @click="adminOpen = false">&times;</button>
        </div>
        <div class="nd-admin-tabs">
          <button type="button" :class="['nd-admin-tab', {active: adminTab==='grupos'}]" @click="adminTab='grupos'; loadAdminGroups()">Grupos de cabo</button>
          <button type="button" :class="['nd-admin-tab', {active: adminTab==='tipos'}]" @click="adminTab='tipos'; loadAdminTypes()">Tipos</button>
          <button type="button" :class="['nd-admin-tab', {active: adminTab==='pastas'}]" @click="adminTab='pastas'">Pastas</button>
        </div>

        <!-- Tab: Grupos de cabo -->
        <div v-if="adminTab==='grupos'" class="nd-admin-tab-body">
          <div class="nd-admin-add-row">
            <input v-model="newGroupName" class="nd-admin-input" placeholder="Nome do grupo..." maxlength="100" @keydown.enter.prevent="createAdminGroup" />
            <button type="button" class="nd-admin-btn-add" :disabled="!newGroupName.trim()" @click="createAdminGroup">Adicionar</button>
          </div>
          <div v-if="adminGroupsLoading" class="nd-admin-loading">Carregando…</div>
          <div v-else-if="!adminGroups.length" class="nd-admin-empty">Nenhum grupo cadastrado.</div>
          <ul v-else class="nd-admin-list">
            <li v-for="g in adminGroups" :key="g.id" class="nd-admin-list-item" :class="{ 'nd-admin-list-item--editing': editingGroupId === g.id }">
              <template v-if="editingGroupId === g.id">
                <div class="nd-admin-group-form">
                  <input v-model="editingGroupName" class="nd-admin-input" placeholder="Nome do grupo" @keydown.esc="editingGroupId = null" />
                  <div class="nd-admin-group-form-row">
                    <label>Qtd fibras</label>
                    <input v-model="editingGroupFiberCount" type="number" min="1" class="nd-admin-input nd-admin-input--sm" placeholder="ex: 24" />
                  </div>
                  <div class="nd-admin-group-form-row">
                    <label>Atenuação (dB/km)</label>
                    <input v-model="editingGroupAttenuation" type="number" step="0.001" min="0" class="nd-admin-input nd-admin-input--sm" placeholder="ex: 0.35" />
                  </div>
                  <div class="nd-admin-group-form-actions">
                    <button type="button" class="nd-admin-btn-save" @click="saveAdminGroup(g)">Salvar</button>
                    <button type="button" class="nd-admin-btn-cancel" @click="editingGroupId = null">Cancelar</button>
                  </div>
                </div>
              </template>
              <template v-else>
                <span class="nd-admin-item-name">{{ g.name }}</span>
                <span v-if="g.attenuation_db_per_km" class="nd-admin-item-badge">{{ g.attenuation_db_per_km }} dB/km</span>
                <button type="button" class="nd-admin-btn-icon" title="Editar" @click="editingGroupId = g.id; editingGroupName = g.name; editingGroupFiberCount = g.fiber_count ?? ''; editingGroupAttenuation = g.attenuation_db_per_km ?? ''">✏️</button>
                <button type="button" class="nd-admin-btn-icon nd-admin-btn-icon--danger" title="Excluir" @click="deleteAdminGroup(g)">🗑</button>
              </template>
            </li>
          </ul>
        </div>

        <!-- Tab: Tipos -->
        <div v-if="adminTab==='tipos'" class="nd-admin-tab-body">
          <div class="nd-admin-add-row">
            <input v-model="newTypeName" class="nd-admin-input" placeholder="Nome do tipo..." maxlength="50" @keydown.enter.prevent="createAdminType" />
            <button type="button" class="nd-admin-btn-add" :disabled="!newTypeName.trim()" @click="createAdminType">Adicionar</button>
          </div>
          <div v-if="adminTypesLoading" class="nd-admin-loading">Carregando…</div>
          <div v-else-if="!adminTypes.length" class="nd-admin-empty">Nenhum tipo cadastrado.</div>
          <ul v-else class="nd-admin-list">
            <li v-for="t in adminTypes" :key="t.id" class="nd-admin-list-item">
              <template v-if="editingTypeId === t.id">
                <input v-model="editingTypeName" class="nd-admin-input nd-admin-input--inline" @keydown.enter.prevent="saveAdminType(t)" @keydown.esc="editingTypeId = null" />
                <button type="button" class="nd-admin-btn-save" @click="saveAdminType(t)">OK</button>
                <button type="button" class="nd-admin-btn-cancel" @click="editingTypeId = null">✕</button>
              </template>
              <template v-else>
                <span class="nd-admin-item-name">{{ t.name }}</span>
                <span class="nd-layer-count">{{ t.cable_count ?? '' }}</span>
                <button type="button" class="nd-admin-btn-icon" title="Renomear" @click="editingTypeId = t.id; editingTypeName = t.name">✏️</button>
                <button type="button" class="nd-admin-btn-icon nd-admin-btn-icon--danger" title="Excluir" @click="deleteAdminType(t)">🗑</button>
              </template>
            </li>
          </ul>
        </div>

        <!-- Tab: Pastas -->
        <div v-if="adminTab==='pastas'" class="nd-admin-tab-body">
          <div v-if="!flatFolders.length" class="nd-admin-empty">Nenhuma pasta cadastrada.</div>
          <ul v-else class="nd-admin-list">
            <li v-for="folder in flatFolders" :key="folder.id" class="nd-admin-list-item" :style="{ paddingLeft: (folder.depth * 14 + 8) + 'px' }">
              <template v-if="editingFolderId === folder.id">
                <input v-model="editingFolderName" class="nd-admin-input nd-admin-input--inline" @keydown.enter.prevent="saveAdminFolder(folder)" @keydown.esc="editingFolderId = null" />
                <button type="button" class="nd-admin-btn-save" @click="saveAdminFolder(folder)">OK</button>
                <button type="button" class="nd-admin-btn-cancel" @click="editingFolderId = null">✕</button>
              </template>
              <template v-else>
                <svg viewBox="0 0 16 16" class="nd-folder-icon" aria-hidden="true" style="width:13px;height:13px;flex-shrink:0"><path d="M1 4.5A1.5 1.5 0 012.5 3h3.25L7 4.5H13.5A1.5 1.5 0 0115 6v6a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 011 12V4.5z" fill="currentColor" opacity=".7"/></svg>
                <span class="nd-admin-item-name">{{ folder.name }}</span>
                <span class="nd-layer-count">{{ folder.aggregate_count }}</span>
                <button type="button" class="nd-admin-btn-icon" title="Renomear" @click="editingFolderId = folder.id; editingFolderName = folder.name">✏️</button>
                <button type="button" class="nd-admin-btn-icon nd-admin-btn-icon--danger" title="Excluir" @click="deleteAdminFolder(folder)">🗑</button>
              </template>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div class="nd-folder-panel" v-click-outside="closeFolderCreate">
      <button
        type="button"
        class="nd-folder-panel__toggle"
        @click="folderPanelOpen = !folderPanelOpen"
        :aria-expanded="String(folderPanelOpen)"
        title="Pastas de cabos"
      >
        <svg viewBox="0 0 20 20" aria-hidden="true" class="nd-layer-icon">
          <path d="M2 5.5A1.5 1.5 0 013.5 4h4l1.5 2H16.5A1.5 1.5 0 0118 7.5v7A1.5 1.5 0 0116.5 16h-13A1.5 1.5 0 012 14.5v-9z" fill="none" stroke="currentColor" stroke-width="1.5"/>
        </svg>
        <span>Pastas</span>
        <span v-if="activeFolderId !== null" class="nd-folder-active-badge">Filtrado</span>
      </button>
      <div v-if="folderPanelOpen" class="nd-folder-panel__body">
        <!-- All cables row -->
        <div
          class="nd-folder-item nd-folder-item--all"
          :class="{ active: activeFolderId === null, 'nd-drop-target': dragOverFolderId === '__none__' }"
          @click="clearFolderFilter"
          @dragover.prevent="onFolderDragOver('__none__')"
          @dragleave="onFolderDragLeave"
          @drop.prevent="onFolderDrop(null)"
        >
          <span>Todos os cabos</span>
          <span class="nd-layer-count">{{ totalFolderCableCount }}</span>
        </div>
        <div class="nd-layer-divider"></div>

        <!-- Folder tree (flattened) -->
        <div v-if="flatFolders.length === 0" class="nd-folder-empty">Nenhuma pasta criada.</div>
        <template v-for="folder in flatFolders" :key="folder.id">
          <div
            class="nd-folder-item"
            :class="{ active: activeFolderId === folder.id, 'nd-drop-target': dragOverFolderId === folder.id }"
            :style="{ paddingLeft: (folder.depth * 14 + 8) + 'px' }"
            @click="selectFolder(folder)"
            @dragover.prevent="onFolderDragOver(folder.id)"
            @dragleave="onFolderDragLeave"
            @drop.prevent="onFolderDrop(folder.id)"
          >
            <button
              v-if="folder.children?.length"
              type="button"
              class="nd-folder-expand"
              :class="{ expanded: expandedFolders.has(folder.id) }"
              @click.stop="toggleFolderExpand(folder.id)"
              :aria-label="expandedFolders.has(folder.id) ? 'Recolher' : 'Expandir'"
            >▶</button>
            <span v-else class="nd-folder-leaf-indent"></span>
            <svg viewBox="0 0 16 16" class="nd-folder-icon" aria-hidden="true">
              <path d="M1 4.5A1.5 1.5 0 012.5 3h3.25L7 4.5H13.5A1.5 1.5 0 0115 6v6a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 011 12V4.5z" fill="currentColor" opacity=".7"/>
            </svg>
            <span class="nd-folder-name">{{ folder.name }}</span>
            <span class="nd-layer-count">{{ folder.aggregate_count }}</span>
            <button
              type="button"
              class="nd-folder-add-child"
              :title="'Nova subpasta em ' + folder.name"
              @click.stop="startFolderCreate(folder.id)"
            >+</button>
          </div>
          <!-- Inline create under this folder -->
          <div
            v-if="folderCreateParentId === folder.id"
            class="nd-folder-create-row"
            :style="{ paddingLeft: ((folder.depth + 1) * 14 + 8) + 'px' }"
          >
            <input
              ref="folderCreateInputEl"
              v-model="newFolderName"
              class="nd-folder-create-input"
              placeholder="Nome da pasta"
              @keydown.enter.prevent="createFolder"
              @keydown.esc="closeFolderCreate"
              maxlength="80"
            />
            <button type="button" class="nd-folder-create-ok" @click="createFolder">OK</button>
          </div>
        </template>

        <div class="nd-layer-divider"></div>
        <!-- Create folder — always visible -->
        <div class="nd-folder-create-row">
          <span v-if="folderCreateParentId && folderCreateParentId !== '__root__'" class="nd-folder-create-label">
            Sub de {{ flatFolders.find(f => f.id === folderCreateParentId)?.name }}
          </span>
          <input
            ref="folderCreateInputEl"
            v-model="newFolderName"
            class="nd-folder-create-input"
            placeholder="Nome da pasta..."
            @keydown.enter.prevent="createFolder"
            @keydown.esc="newFolderName = ''; folderCreateParentId = null"
            @focus="folderCreateParentId = folderCreateParentId || '__root__'"
            maxlength="80"
          />
          <button
            type="button"
            class="nd-folder-create-ok"
            :disabled="!newFolderName.trim()"
            @click="createFolder"
          >+</button>
        </div>
      </div>
    </div>

    <!-- ── Move-to-folder picker ────────────────────────── -->
    <div
      v-if="moveFolderPickerOpen"
      class="nd-move-folder-overlay"
      @click.self="moveFolderPickerOpen = false"
    >
      <div class="nd-move-folder-card">
        <div class="nd-move-folder-header">
          <span>Mover para pasta</span>
          <button type="button" class="nd-move-folder-close" @click="moveFolderPickerOpen = false">&times;</button>
        </div>
        <div class="nd-move-folder-list">
          <button type="button" class="nd-move-folder-item" :class="{ active: previewCableFolder === null }" @click="moveCableToFolder(null)">
            <span>Sem pasta</span>
          </button>
          <template v-for="folder in flatFolders" :key="folder.id">
            <button
              type="button"
              class="nd-move-folder-item"
              :class="{ active: previewCableFolder?.id === folder.id }"
              :style="{ paddingLeft: (folder.depth * 14 + 12) + 'px' }"
              @click="moveCableToFolder(folder.id)"
            >
              <svg viewBox="0 0 16 16" class="nd-folder-icon" aria-hidden="true" style="flex-shrink:0">
                <path d="M1 4.5A1.5 1.5 0 012.5 3h3.25L7 4.5H13.5A1.5 1.5 0 0115 6v6a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 011 12V4.5z" fill="currentColor" opacity=".7"/>
              </svg>
              <span>{{ folder.name }}</span>
            </button>
          </template>
        </div>
      </div>
    </div>

    <div id="toastHost" class="toast-host hidden"></div>
    <div id="confirmHost" class="confirm-host hidden"></div>

    <div id="manualSaveModal" class="modal-overlay opacity-0 pointer-events-none">
      <div id="manualSaveModalContent" class="modal-card opacity-0 scale-95">
        <button
          type="button"
          class="absolute top-4 right-4 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-2xl leading-none"
          @click="closeManualModal"
        >
          &times;
        </button>
        <h2 class="mb-1" id="manualSaveModalTitle">Salvar cabo manualmente</h2>

        <div class="modal-distance-badge">
          <span>Distância da rota:</span>
          <strong id="manualRouteDistance">0.000 km</strong>
        </div>
        <div id="manualLossEstimate" class="modal-loss-estimate" style="display:none">
          <span>Perda estimada:</span>
          <strong id="manualLossValue">—</strong>
          <span id="manualLossWarning" class="modal-loss-warning" style="display:none">⚠ Acima do limiar (30 dB)</span>
        </div>

        <!-- Tabs -->
        <div class="modal-tabs" role="tablist">
          <button
            id="tabBtnIdentification"
            class="modal-tab active"
            role="tab"
            aria-selected="true"
            aria-controls="tabPanelIdentification"
            type="button"
          >Identificação</button>
          <button
            id="tabBtnConnections"
            class="modal-tab"
            role="tab"
            aria-selected="false"
            aria-controls="tabPanelConnections"
            type="button"
          >Conexões</button>
          <button
            id="tabBtnHistory"
            class="modal-tab"
            role="tab"
            aria-selected="false"
            aria-controls="tabPanelHistory"
            type="button"
          >Histórico</button>
          <button
            id="tabBtnPhotos"
            class="modal-tab"
            role="tab"
            aria-selected="false"
            aria-controls="tabPanelPhotos"
            type="button"
          >Fotos</button>
        </div>

        <form id="manualSaveForm">
          <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken" />

          <!-- Tab: Identificação -->
          <div id="tabPanelIdentification" class="modal-tab-panel" role="tabpanel">
            <div class="modal-field">
              <label for="manualRouteName">Nome do cabo</label>
              <input
                id="manualRouteName"
                name="name"
                type="text"
                required
                placeholder="ex: Backbone Confresa"
                class="modal-input"
              />
            </div>
            <div class="modal-field">
              <label for="manualCableGroupSelect">Grupo do cabo</label>
              <div class="modal-select-row">
                <select id="manualCableGroupSelect" name="cable_group_id" class="modal-input">
                  <option value="">— Sem grupo —</option>
                </select>
                <button id="addCableGroupBtn" type="button" class="modal-add-btn" title="Novo grupo">+</button>
              </div>
            </div>
            <div class="modal-field">
              <label for="manualResponsibleSelect">Responsável</label>
              <select id="manualResponsibleSelect" name="responsible_user_id" class="modal-input">
                <option value="">— Sem responsável —</option>
              </select>
            </div>
            <div class="modal-field">
              <label for="manualFolderSelect">Pasta</label>
              <select id="manualFolderSelect" name="folder_id" class="modal-input">
                <option value="">— Sem pasta —</option>
              </select>
            </div>
            <div class="modal-field">
              <label for="manualCableTypeSelect">Tipo</label>
              <select id="manualCableTypeSelect" name="cable_type_id" class="modal-input">
                <option value="">— Sem tipo —</option>
              </select>
            </div>
          </div>

          <!-- Tab: Conexões -->
          <div id="tabPanelConnections" class="modal-tab-panel hidden" role="tabpanel">
            <div class="modal-grid-2">
              <div class="modal-field">
                <label for="manualOriginDeviceSelect">Dispositivo origem</label>
                <select id="manualOriginDeviceSelect" name="origin_device_id" required class="modal-input">
                  <option value="">Selecione...</option>
                </select>
              </div>
              <div class="modal-field">
                <label for="manualOriginPortSelect">Porta origem</label>
                <select id="manualOriginPortSelect" name="origin_port_id" required class="modal-input">
                  <option value="">Selecione...</option>
                </select>
              </div>
            </div>

            <div class="modal-single-port-row">
              <label for="manualSinglePortOnly">Monitorar apenas porta de origem</label>
              <input id="manualSinglePortOnly" name="single_port" type="checkbox" value="true" class="modal-checkbox" />
            </div>

            <div id="manualDestNotice" class="hidden modal-notice">
              Campos de destino desabilitados — apenas a porta de origem será monitorada.
            </div>

            <div class="modal-grid-2">
              <div class="modal-field">
                <label for="manualDestDeviceSelect">Dispositivo destino</label>
                <select id="manualDestDeviceSelect" name="dest_device_id" required class="modal-input">
                  <option value="">Selecione...</option>
                </select>
              </div>
              <div class="modal-field">
                <label for="manualDestPortSelect">Porta destino</label>
                <select id="manualDestPortSelect" name="dest_port_id" required class="modal-input">
                  <option value="">Selecione...</option>
                </select>
              </div>
            </div>
          </div>

          <!-- Tab: Histórico -->
          <div id="tabPanelHistory" class="modal-tab-panel hidden" role="tabpanel">
            <div id="auditLogList" class="audit-log-list">
              <p class="audit-log-empty">Salve o cabo primeiro para ver o histórico.</p>
            </div>
          </div>

          <!-- Tab: Fotos -->
          <div id="tabPanelPhotos" class="modal-tab-panel hidden" role="tabpanel">
            <!-- Upload area -->
            <div class="photo-upload-area" id="photoDropZone">
              <input type="file" id="photoFileInput" accept="image/jpeg,image/png,image/webp" multiple style="display:none" />
              <div class="photo-upload-prompt" id="photoUploadPrompt">
                <svg viewBox="0 0 24 24" style="width:32px;height:32px;color:var(--nd-panel-muted)" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3 21h18M3.75 3h16.5A.75.75 0 0121 3.75v13.5a.75.75 0 01-.75.75H3.75a.75.75 0 01-.75-.75V3.75A.75.75 0 013.75 3z"/>
                </svg>
                <span>Arraste fotos aqui ou <label for="photoFileInput" class="photo-upload-link">escolha arquivos</label></span>
                <span class="photo-upload-hint">JPG, PNG ou WEBP · máx. 10 MB cada</span>
              </div>
              <div id="photoUploadProgress" class="photo-upload-progress" style="display:none">
                <div class="photo-progress-bar"><div class="photo-progress-fill" id="photoProgressFill"></div></div>
                <span id="photoProgressLabel">Enviando…</span>
              </div>
            </div>
            <!-- Gallery -->
            <div id="photoGallery" class="photo-gallery">
              <p class="photo-empty" id="photoEmptyMsg">Salve o cabo primeiro para adicionar fotos.</p>
            </div>
          </div>

          <div class="modal-actions">
            <button type="button" class="modal-btn modal-btn--cancel" @click="closeManualModal">Cancelar</button>
            <button type="submit" class="modal-btn modal-btn--save">Salvar</button>
          </div>
        </form>
      </div>
    </div>

    <div
      id="importKmlModal"
      class="fixed inset-0 flex items-center justify-center bg-black/60 opacity-0 pointer-events-none transition-opacity duration-300 z-50"
    >
      <div
        id="importKmlModalContent"
        class="modal-card rounded-2xl shadow-2xl w-full max-w-md p-6 relative transform scale-95 opacity-0 transition-all duration-300 overflow-y-auto"
        style="max-height:90vh"
      >
        <button
          type="button"
          class="absolute top-4 right-4 text-gray-400 hover:text-gray-200 text-xl leading-none bg-transparent border-none cursor-pointer"
          @click="closeKmlModal"
          aria-label="Fechar"
        >
          &times;
        </button>

        <h2 class="text-lg font-semibold mb-2">Importar rota via KML</h2>

        <p class="text-xs text-gray-400 mb-3 leading-relaxed">
          Vincule o arquivo <strong>.kml</strong> aos dispositivos monitorados. Você pode monitorar apenas a porta de origem (uma via) ou definir dispositivos de origem e destino distintos.
        </p>

        <div class="rounded-lg px-3 py-2 text-xs text-blue-300 mb-4 leading-relaxed" style="background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.3)">
          O arquivo deve conter um <em>LineString</em> com a sequência de pontos (origem → destino) que representa o cabo físico.
        </div>

        <form id="importKmlForm" enctype="multipart/form-data" class="space-y-3">
          <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken" />

          <!-- Nome da rota -->
          <div>
            <label class="block text-xs font-medium mb-1">Nome da rota</label>
            <input
              type="text"
              name="name"
              required
              placeholder="Ex: Backbone GYN → BSB"
              class="nd-kml-input w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
            />
          </div>

          <!-- Grupo do cabo -->
          <div>
            <label class="block text-xs font-medium mb-1">Grupo do cabo</label>
            <select
              id="kmlCableGroupSelect"
              name="cable_group_id"
              class="nd-kml-input w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
            >
              <option value="">— Sem grupo —</option>
            </select>
          </div>

          <!-- Responsável -->
          <div>
            <label class="block text-xs font-medium mb-1">Responsável</label>
            <select
              id="kmlResponsibleSelect"
              name="responsible_user_id"
              class="nd-kml-input w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
            >
              <option value="">— Sem responsável —</option>
            </select>
          </div>

          <!-- Dispositivo origem -->
          <div>
            <label class="block text-xs font-medium mb-1">Dispositivo origem</label>
            <select
              name="origin_device_id"
              id="kmlOriginDeviceSelect"
              required
              data-placeholder="Selecione..."
              class="nd-kml-input w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
            >
              <option value="">Selecione...</option>
            </select>
          </div>

          <!-- Porta origem -->
          <div>
            <label class="block text-xs font-medium mb-1">Porta origem</label>
            <select
              name="origin_port_id"
              id="kmlOriginPortSelect"
              required
              class="nd-kml-input w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
            >
              <option value="">Selecione...</option>
            </select>
          </div>

          <!-- Monitorar apenas porta de origem -->
          <div class="flex items-center justify-between">
            <label for="kmlSinglePortOnly" class="text-xs cursor-pointer select-none">Monitorar apenas porta de origem</label>
            <input
              type="checkbox"
              id="kmlSinglePortOnly"
              name="single_port"
              value="true"
              class="w-4 h-4 cursor-pointer flex-shrink-0"
              style="accent-color:#3b82f6"
            />
          </div>

          <div
            id="kmlDestNotice"
            class="hidden text-xs text-blue-300 rounded-lg px-3 py-2"
            style="background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.25)"
          >
            Campos de destino desabilitados — apenas a porta de origem será monitorada.
          </div>

          <!-- Dispositivo destino -->
          <div>
            <label class="block text-xs font-medium mb-1">Dispositivo destino</label>
            <select
              name="dest_device_id"
              id="kmlDestDeviceSelect"
              required
              data-placeholder="Selecione..."
              class="nd-kml-input w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
            >
              <option value="">Selecione...</option>
            </select>
          </div>

          <!-- Porta destino -->
          <div>
            <label class="block text-xs font-medium mb-1">Porta destino</label>
            <select
              name="dest_port_id"
              id="kmlDestPortSelect"
              required
              class="nd-kml-input w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
            >
              <option value="">Selecione...</option>
            </select>
          </div>

          <!-- Arquivo KML -->
          <div>
            <label class="block text-xs font-medium mb-1">Arquivo KML</label>
            <input
              type="file"
              name="kml_file"
              accept=".kml"
              required
              class="nd-kml-input w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
            />
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button type="button" class="nd-kml-btn-cancel px-4 py-2 rounded-lg text-sm font-medium cursor-pointer" @click="closeKmlModal">
              Cancelar
            </button>
            <button type="submit" class="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer bg-blue-600 border-none text-white hover:bg-blue-700 transition">
              Importar rota
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>

</template>

<script setup>
import { ref, computed, onMounted, nextTick, onUnmounted } from 'vue';
import { initializeNetworkDesignApp, flyToLocation, highlightSearchResult, cancelNetworkDesignEditing, saveNetworkDesignRoute } from '@/features/networkDesign/fiberRouteBuilder.js';
import { getLoadedGroups, setGroupLayerVisible, setFolderFilter, getFallbackCables, setApiGroups, getGroupCounts, getTypeCounts, setTypeFilter } from '@/features/networkDesign/modules/cableService.js';
import { request as apiRequest } from '@/features/networkDesign/modules/apiClient.js';
import { initializeKmlModal, cleanupKmlModal } from '@/features/networkDesign/partials/import_kml.js';

const csrfToken = ref(window.CSRF_TOKEN || '');
const helpOpen = ref(false);
const closeHelpPopover = () => { helpOpen.value = false; };

// ── Cable Details panel — draggable + centered initial position ──────────
const cableDetailPos = ref(null); // null = centered; { left, top } = dragged

const cableDetailPanelStyle = computed(() => {
  if (cableDetailPos.value) {
    return {
      left: `${cableDetailPos.value.left}px`,
      top: `${cableDetailPos.value.top}px`,
      transform: 'none',
    };
  }
  // Centered horizontally, 80px from top
  return {
    left: '50%',
    top: '80px',
    transform: 'translateX(-50%)',
  };
});

function startCableDetailDrag(e) {
  const panel = document.getElementById('cableDetailsPanel');
  if (!panel) return;

  const rect = panel.getBoundingClientRect();
  // On first drag, lock in current rendered position
  if (!cableDetailPos.value) {
    cableDetailPos.value = { left: rect.left, top: rect.top };
  }

  const startLeft = cableDetailPos.value.left;
  const startTop = cableDetailPos.value.top;
  const startX = e.clientX;
  const startY = e.clientY;
  const mapEl = panel.closest('.network-design-page') || document.body;
  const mapRect = mapEl.getBoundingClientRect();

  const onMove = (me) => {
    const dx = me.clientX - startX;
    const dy = me.clientY - startY;
    const newLeft = Math.max(0, Math.min(mapRect.width - rect.width, startLeft + dx));
    const newTop = Math.max(0, Math.min(mapRect.height - 60, startTop + dy));
    cableDetailPos.value = { left: newLeft, top: newTop };
  };
  const onUp = () => {
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    document.body.style.userSelect = '';
  };

  document.body.style.userSelect = 'none';
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}

// Reset to centered when panel closes
window.__ndResetCableDetailPos = () => { cableDetailPos.value = null; };


// ── Route Points panel resize ────────────────────────────────────────────
const PANEL_HEIGHT_KEY = 'nd_route_panel_height';
const _DEFAULT_PANEL_HEIGHT = 420;

function _applyPanelHeight(px) {
  document.getElementById('routePointsPanel')?.style.setProperty('--route-panel-height', `${px}px`);
}

function startPanelResize(e) {
  const panel = document.getElementById('routePointsPanel');
  if (!panel) return;
  const startY = e.clientY;
  const startH = panel.getBoundingClientRect().height;
  const minH = 120;
  const maxH = Math.round(window.innerHeight * 0.8);

  const onMove = (me) => {
    const newH = Math.min(maxH, Math.max(minH, startH + (me.clientY - startY)));
    _applyPanelHeight(newH);
  };
  const onUp = (me) => {
    const newH = Math.min(maxH, Math.max(minH, startH + (me.clientY - startY)));
    _applyPanelHeight(newH);
    try { localStorage.setItem(PANEL_HEIGHT_KEY, String(newH)); } catch (_) {}
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    document.body.style.userSelect = '';
  };

  document.body.style.userSelect = 'none';
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}

// Restore saved height on mount
onMounted(() => {
  try {
    const saved = parseInt(localStorage.getItem(PANEL_HEIGHT_KEY) || '', 10);
    if (saved >= 120) _applyPanelHeight(saved);
    else _applyPanelHeight(_DEFAULT_PANEL_HEIGHT);
  } catch (_) {
    _applyPanelHeight(_DEFAULT_PANEL_HEIGHT);
  }
});

const helpMode = ref('visualizacao'); // 'visualizacao' | 'preview' | 'desenho' | 'edicao'

const HELP_TIPS = {
  visualizacao: {
    title: 'Modo visualização',
    tips: [
      { icon: '🖱️', text: 'Clique com botão direito em um cabo para ver detalhes ou editar.' },
      { icon: '🔍', text: 'Use a barra de busca para encontrar cabos, dispositivos ou sites.' },
      { icon: '📁', text: 'Filtre cabos por pasta, tipo ou grupo nos painéis laterais.' },
      { icon: '➕', text: 'Clique no mapa para iniciar o desenho de um novo cabo.' },
    ],
  },
  preview: {
    title: 'Cabo selecionado',
    tips: [
      { icon: '✏️', text: 'Clique em "Editar dados" para alterar nome, grupo, tipo e responsável.' },
      { icon: '🗺️', text: 'Clique em "Editar rota" para redesenhar o trajeto do cabo no mapa.' },
      { icon: '📂', text: 'Use o botão Pasta para mover o cabo para outra pasta.' },
      { icon: '⎋', text: 'Pressione Esc para fechar o painel de detalhes.' },
    ],
  },
  desenho: {
    title: 'Desenhando rota',
    tips: [
      { icon: '🖱️', text: 'Clique no mapa para adicionar pontos ao trajeto do cabo.' },
      { icon: '↕️', text: 'Arraste os marcadores para ajustar a posição ou reordene na lista.' },
      { icon: '🗑️', text: 'Clique com botão direito em um marcador para removê-lo.' },
      { icon: '⎋', text: 'Pressione Esc para cancelar o desenho e descartar os pontos.' },
    ],
  },
  edicao: {
    title: 'Editando rota',
    tips: [
      { icon: '🖱️', text: 'Clique no mapa para adicionar novos pontos ao trajeto.' },
      { icon: '↕️', text: 'Arraste os marcadores para ajustar o percurso do cabo.' },
      { icon: '💾', text: 'Clique com botão direito e selecione Salvar para concluir.' },
      { icon: '⎋', text: 'Pressione Esc para cancelar sem salvar as alterações.' },
    ],
  },
};

const currentHelpTips = computed(() => HELP_TIPS[helpMode.value] || HELP_TIPS.visualizacao);

window.__ndSetHelpMode = (mode) => { helpMode.value = mode; };

// ── Global search state ──────────────────────────────────────────────────
const searchQuery = ref('');
const searchResults = ref([]);
const searchLoading = ref(false);
const searchFocusIdx = ref(-1);
let searchDebounceTimer = null;

const TYPE_LABELS = { cable: 'Cabos', device: 'Dispositivos', site: 'Sites' };
const TYPE_ORDER  = ['cable', 'device', 'site'];

const searchGroups = computed(() => {
  const map = {};
  for (const item of searchResults.value) {
    if (!map[item.type]) map[item.type] = [];
    map[item.type].push(item);
  }
  let startIdx = 0;
  return TYPE_ORDER
    .filter(t => map[t]?.length)
    .map(t => {
      const items = map[t];
      const group = { type: t, label: TYPE_LABELS[t], items, startIdx };
      startIdx += items.length;
      return group;
    });
});

function onSearchInput() {
  clearTimeout(searchDebounceTimer);
  const q = searchQuery.value.trim();
  if (q.length < 2) { searchResults.value = []; return; }
  searchDebounceTimer = setTimeout(() => runSearch(q), 300);
}

async function runSearch(q) {
  searchLoading.value = true;
  searchFocusIdx.value = -1;
  try {
    const res = await fetch(`/api/v1/inventory/search/?q=${encodeURIComponent(q)}`, { credentials: 'same-origin' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    searchResults.value = data.results || [];
  } catch {
    searchResults.value = [];
  } finally {
    searchLoading.value = false;
  }
}

function closeSearch() {
  searchResults.value = [];
  searchFocusIdx.value = -1;
}

function searchFocusNext(dir) {
  const total = searchResults.value.length;
  if (!total) return;
  searchFocusIdx.value = (searchFocusIdx.value + dir + total) % total;
}

function searchSelectFocused() {
  const flat = searchResults.value;
  const idx = searchFocusIdx.value;
  if (idx >= 0 && idx < flat.length) selectSearchResult(flat[idx]);
}

function selectSearchResult(item) {
  if (item.lat != null && item.lng != null) {
    const zoom = item.type === 'cable' ? 13 : 15;
    flyToLocation(item.lng, item.lat, zoom);
    setTimeout(() => highlightSearchResult(item), 900);
  }
  searchQuery.value = item.name;
  closeSearch();
}

// ── Layer control state ──────────────────────────────────────────────────
const LAYER_STORAGE_KEY = 'nd_layer_visibility';
const LAYER_COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f97316','#84cc16'];

const layerPanelOpen = ref(false);
const layerGroups = ref([]);   // [{ id, name, color, count }]
const layerState = ref({});    // { groupKey: boolean }
const layerAllVisible = ref(true);
const fallbackCables = ref([]);  // cables with no stored path
const fallbackAlertDismissed = ref(false);

function refreshLayerGroups() {
  fallbackCables.value = getFallbackCables();
  fallbackAlertDismissed.value = false;
  const raw = getLoadedGroups();
  // Load persisted visibility
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(LAYER_STORAGE_KEY) || '{}'); } catch (_) {}

  const counts = getGroupCounts();
  const groups = raw.map((g, i) => ({
    ...g,
    color: LAYER_COLORS[i % LAYER_COLORS.length],
    count: counts.get(g.id ?? null) ?? 0,
  }));

  // Count cables per group
  // We rely on getLoadedGroups returning the same groups the polylines have
  const state = {};
  groups.forEach(g => {
    const key = g.id ?? '__none__';
    state[key] = saved[key] !== undefined ? saved[key] : true;
  });

  layerGroups.value = groups;
  layerState.value = state;
  layerAllVisible.value = Object.values(state).every(v => v);

  // Apply persisted visibility immediately
  groups.forEach(g => {
    const key = g.id ?? '__none__';
    if (!state[key]) setGroupLayerVisible(g.id, false);
  });
}

function toggleGroupLayer(group) {
  const key = group.id ?? '__none__';
  const newVal = !layerState.value[key];
  layerState.value[key] = newVal;
  setGroupLayerVisible(group.id, newVal);
  layerAllVisible.value = Object.values(layerState.value).every(v => v);
  persistLayerState();
}

function toggleAllLayers() {
  const visible = layerAllVisible.value;
  const newState = {};
  layerGroups.value.forEach(g => {
    const key = g.id ?? '__none__';
    newState[key] = visible;
    setGroupLayerVisible(g.id, visible);
  });
  layerState.value = newState;
  persistLayerState();
}

function persistLayerState() {
  try { localStorage.setItem(LAYER_STORAGE_KEY, JSON.stringify(layerState.value)); } catch (_) {}
}

// ── Type filter state ────────────────────────────────────────────────────
const typeItems = ref([]);   // [{ value (id string), label, count, visible }]
// Map of type id → name, populated when cables load
const _typeNameMap = new Map();

function refreshTypeItems() {
  const counts = getTypeCounts();
  const items = [];
  for (const [value, count] of counts.entries()) {
    if (value && count > 0) {
      items.push({ value, label: _typeNameMap.get(value) || value, count, visible: true });
    }
  }
  typeItems.value = items;
}

function toggleTypeLayer(item) {
  item.visible = !item.visible;
  _applyTypeFilter();
}

function _applyTypeFilter() {
  const hidden = typeItems.value.filter(t => !t.visible);
  if (hidden.length === 0) {
    setTypeFilter(null);
  } else {
    const visible = new Set(typeItems.value.filter(t => t.visible).map(t => t.value));
    // Also always include cables with no type (empty string)
    visible.add('');
    setTypeFilter(visible);
  }
}

window.__ndRefreshTypeItems = refreshTypeItems;

// Pre-load cable type names for the layer panel labels
async function _fetchTypeNames() {
  try {
    const r = await fetch('/api/v1/inventory/cable-types/', { credentials: 'same-origin' });
    if (!r.ok) return;
    const data = await r.json();
    (data.results || []).forEach(t => _typeNameMap.set(String(t.id), t.name));
  } catch (_) {}
}
_fetchTypeNames();

// Expose so fiberRouteBuilder can call it after cables are loaded
window.__ndRefreshLayerGroups = refreshLayerGroups;

// ── Folder tree state ─────────────────────────────────────────────────────
const folderPanelOpen = ref(false);
const folderTree = ref([]);              // raw tree from API
const expandedFolders = ref(new Set()); // Set of expanded folder IDs
const activeFolderId = ref(null);       // currently filtered folder
const folderCreateParentId = ref(null); // '__root__', folder.id, or null
const newFolderName = ref('');
const folderCreateInputEl = ref(null);
const moveFolderPickerOpen = ref(false);
const previewCableFolder = ref(null);   // { id, name } or null, for current preview cable
const isDraggingCable = ref(false);
const dragOverFolderId = ref(null);     // folder.id or '__none__' while dragging over

/** Flat list of visible tree nodes with depth info, respecting expand state */
/** Recursively sum cable_count for a node and all its descendants */
function aggregateCableCount(node) {
  return (node.cable_count || 0) + (node.children || []).reduce((s, c) => s + aggregateCableCount(c), 0);
}

const flatFolders = computed(() => {
  function flatten(nodes, depth) {
    const result = [];
    for (const node of nodes) {
      result.push({ ...node, depth, aggregate_count: aggregateCableCount(node) });
      if (expandedFolders.value.has(node.id) && node.children?.length) {
        result.push(...flatten(node.children, depth + 1));
      }
    }
    return result;
  }
  return flatten(folderTree.value, 0);
});

const totalFolderNoFolderCount = ref(0);

/** Total cable count across all folders + unfoldered */
const totalFolderCableCount = computed(() => {
  function sumTree(nodes) {
    return nodes.reduce((s, n) => s + (n.cable_count || 0) + sumTree(n.children || []), 0);
  }
  return sumTree(folderTree.value) + totalFolderNoFolderCount.value;
});

async function loadFolderTree() {
  try {
    const data = await apiRequest('/cable-folders/');
    folderTree.value = data.tree || [];
    totalFolderNoFolderCount.value = data.no_folder_count || 0;
    // Auto-expand root folders if tree is small
    if (folderTree.value.length <= 5) {
      const s = new Set(expandedFolders.value);
      folderTree.value.forEach(n => s.add(n.id));
      expandedFolders.value = s;
    }
  } catch (err) {
    console.warn('[FolderTree] load failed:', err.message);
  }
}

function toggleFolderExpand(id) {
  const s = new Set(expandedFolders.value);
  s.has(id) ? s.delete(id) : s.add(id);
  expandedFolders.value = s;
}

function collectFolderIds(node, ids = new Set()) {
  ids.add(node.id);
  for (const child of (node.children || [])) {
    collectFolderIds(child, ids);
  }
  return ids;
}

function selectFolder(folder) {
  activeFolderId.value = folder.id;
  const ids = collectFolderIds(folder);
  setFolderFilter(folder.id, ids);
}

function clearFolderFilter() {
  activeFolderId.value = null;
  setFolderFilter(null, null);
}

function startFolderCreate(parentId) {
  folderCreateParentId.value = parentId;
  newFolderName.value = '';
  nextTick(() => {
    const el = Array.isArray(folderCreateInputEl.value)
      ? folderCreateInputEl.value[0]
      : folderCreateInputEl.value;
    el?.focus();
  });
}

function closeFolderCreate() {
  folderCreateParentId.value = null;
  newFolderName.value = '';
}

async function createFolder() {
  const name = newFolderName.value.trim();
  if (!name) return;
  const parentId = (!folderCreateParentId.value || folderCreateParentId.value === '__root__')
    ? null
    : folderCreateParentId.value;
  try {
    await apiRequest('/cable-folders/create/', {
      method: 'POST',
      body: JSON.stringify({ name, parent_id: parentId }),
    });
    newFolderName.value = '';
    folderCreateParentId.value = null;
    await loadFolderTree();
  } catch (err) {
    alert(err.message || 'Erro ao criar pasta.');
  }
}

function onCableDragStart(e) {
  const cableId = window.__ndPreviewCableId;
  if (!cableId) { e.preventDefault(); return; }
  e.dataTransfer.setData('text/plain', String(cableId));
  e.dataTransfer.effectAllowed = 'move';
  isDraggingCable.value = true;
  if (!folderPanelOpen.value) folderPanelOpen.value = true;
}

function onCableDragEnd() {
  isDraggingCable.value = false;
  dragOverFolderId.value = null;
}

function onFolderDragOver(folderId) {
  dragOverFolderId.value = folderId;
}

function onFolderDragLeave(e) {
  if (!e.currentTarget.contains(e.relatedTarget)) {
    dragOverFolderId.value = null;
  }
}

async function onFolderDrop(folderId) {
  isDraggingCable.value = false;
  dragOverFolderId.value = null;
  await moveCableToFolder(folderId);
}

async function moveCableToFolder(folderId) {
  const cableId = window.__ndPreviewCableId;
  if (!cableId) return;
  try {
    await apiRequest(`/fibers/${cableId}/move-folder/`, {
      method: 'POST',
      body: JSON.stringify({ folder_id: folderId }),
    });
    moveFolderPickerOpen.value = false;
    const folderName = folderId === null ? null : flatFolders.value.find(f => f.id === folderId)?.name ?? null;
    previewCableFolder.value = folderId === null ? null : { id: folderId, name: folderName };
    const el = document.getElementById('cableDetailFolder');
    if (el) el.textContent = folderName ?? '—';
    await loadFolderTree();
  } catch (err) {
    alert(err.message || 'Erro ao mover cabo.');
  }
}

// Bridge: fiberRouteBuilder calls this when preview cable changes
window.__ndOnPreviewFolderChanged = (folder) => {
  previewCableFolder.value = folder;
};

// ── Admin panel state ─────────────────────────────────────────────────────
const adminOpen = ref(false);
const adminTab = ref('grupos');
const adminGroups = ref([]);
const adminGroupsLoading = ref(false);
const newGroupName = ref('');
const editingGroupId = ref(null);
const editingGroupName = ref('');
const editingGroupFiberCount = ref('');
const editingGroupAttenuation = ref('');

const adminTypes = ref([]);
const adminTypesLoading = ref(false);
const newTypeName = ref('');
const editingTypeId = ref(null);
const editingTypeName = ref('');

const editingFolderId = ref(null);
const editingFolderName = ref('');

async function loadCableGroupsFromApi() {
  try {
    const data = await apiRequest('/cable-groups/');
    const groups = data.results || [];
    setApiGroups(groups);
    refreshLayerGroups();
    return groups;
  } catch (err) {
    console.warn('[Admin] loadCableGroupsFromApi failed:', err.message);
    return [];
  }
}
window.__ndLoadCableGroupsFromApi = loadCableGroupsFromApi;

async function loadAdminGroups() {
  adminGroupsLoading.value = true;
  try {
    const groups = await loadCableGroupsFromApi();
    adminGroups.value = groups;
  } finally {
    adminGroupsLoading.value = false;
  }
}

async function createAdminGroup() {
  const name = newGroupName.value.trim();
  if (!name) return;
  try {
    const g = await apiRequest('/cable-groups/create/', { method: 'POST', body: JSON.stringify({ name }) });
    adminGroups.value.push(g);
    newGroupName.value = '';
    await loadCableGroupsFromApi();
  } catch (err) {
    alert(err.message || 'Erro ao criar grupo.');
  }
}

async function saveAdminGroup(group) {
  const name = editingGroupName.value.trim();
  if (!name) return;
  const fc = editingGroupFiberCount.value;
  const att = editingGroupAttenuation.value;
  const body = {
    name,
    fiber_count: fc !== '' ? parseInt(fc, 10) : null,
    attenuation_db_per_km: att !== '' ? parseFloat(att) : null,
  };
  try {
    const updated = await apiRequest(`/cable-groups/${group.id}/`, { method: 'PATCH', body: JSON.stringify(body) });
    const idx = adminGroups.value.findIndex(g => g.id === group.id);
    if (idx !== -1) adminGroups.value[idx] = { ...adminGroups.value[idx], ...updated };
    editingGroupId.value = null;
    await loadCableGroupsFromApi();
  } catch (err) {
    alert(err.message || 'Erro ao salvar grupo.');
  }
}

async function deleteAdminGroup(group) {
  if (!confirm(`Excluir grupo "${group.name}"? Cabos neste grupo ficarão sem grupo.`)) return;
  try {
    await apiRequest(`/cable-groups/${group.id}/delete/`, { method: 'DELETE' });
    adminGroups.value = adminGroups.value.filter(g => g.id !== group.id);
    await loadCableGroupsFromApi();
    // Reload cables so polylines drop the deleted group reference
    if (typeof window.__ndReloadAllCables === 'function') {
      window.__ndReloadAllCables();
    }
  } catch (err) {
    alert(err.message || 'Erro ao excluir grupo.');
  }
}

// ── Admin: Tipos ─────────────────────────────────────────────────────────
async function loadAdminTypes() {
  adminTypesLoading.value = true;
  try {
    const data = await apiRequest('/cable-types/');
    adminTypes.value = data.results || [];
  } catch (err) {
    alert(err.message || 'Erro ao carregar tipos.');
  } finally {
    adminTypesLoading.value = false;
  }
}

async function createAdminType() {
  const name = newTypeName.value.trim();
  if (!name) return;
  try {
    const t = await apiRequest('/cable-types/create/', { method: 'POST', body: JSON.stringify({ name }) });
    adminTypes.value.push(t);
    newTypeName.value = '';
    // Reload modal type select
    if (typeof window.__ndReloadCableTypes === 'function') window.__ndReloadCableTypes();
  } catch (err) {
    alert(err.message || 'Erro ao criar tipo.');
  }
}

async function saveAdminType(type) {
  const name = editingTypeName.value.trim();
  if (!name) return;
  try {
    const updated = await apiRequest(`/cable-types/${type.id}/`, { method: 'PATCH', body: JSON.stringify({ name }) });
    const idx = adminTypes.value.findIndex(t => t.id === type.id);
    if (idx !== -1) adminTypes.value[idx] = { ...adminTypes.value[idx], ...updated };
    editingTypeId.value = null;
    if (typeof window.__ndReloadCableTypes === 'function') window.__ndReloadCableTypes();
  } catch (err) {
    alert(err.message || 'Erro ao renomear tipo.');
  }
}

async function deleteAdminType(type) {
  if (!confirm(`Excluir tipo "${type.name}"? Cabos deste tipo ficarão sem tipo.`)) return;
  try {
    await apiRequest(`/cable-types/${type.id}/delete/`, { method: 'DELETE' });
    adminTypes.value = adminTypes.value.filter(t => t.id !== type.id);
    if (typeof window.__ndReloadCableTypes === 'function') window.__ndReloadCableTypes();
    if (typeof window.__ndReloadAllCables === 'function') window.__ndReloadAllCables();
  } catch (err) {
    alert(err.message || 'Erro ao excluir tipo.');
  }
}

async function saveAdminFolder(folder) {
  const name = editingFolderName.value.trim();
  if (!name) return;
  try {
    await apiRequest(`/cable-folders/${folder.id}/`, { method: 'PATCH', body: JSON.stringify({ name }) });
    editingFolderId.value = null;
    await loadFolderTree();
  } catch (err) {
    alert(err.message || 'Erro ao renomear pasta.');
  }
}

async function deleteAdminFolder(folder) {
  if (!confirm(`Excluir pasta "${folder.name}"? Cabos nesta pasta ficarão sem pasta.`)) return;
  try {
    await apiRequest(`/cable-folders/${folder.id}/delete/`, { method: 'DELETE' });
    editingFolderId.value = null;
    await loadFolderTree();
  } catch (err) {
    alert(err.message || 'Erro ao excluir pasta.');
  }
}

// Refresh folder counts after cables reload
window.__ndRefreshFolderCounts = loadFolderTree;

// v-click-outside directive
const vClickOutside = {
  mounted(el, binding) {
    el._clickOutsideHandler = (e) => {
      if (!el.contains(e.target)) binding.value(e);
    };
    document.addEventListener('click', el._clickOutsideHandler);
  },
  unmounted(el) {
    document.removeEventListener('click', el._clickOutsideHandler);
  },
};

const ensureFiberGlobals = () => {
  if (!Array.isArray(window.__FIBER_DEVICE_OPTIONS)) {
    window.__FIBER_DEVICE_OPTIONS = [];
  }
};

const waitForKmlModal = async (retries = 5) => {
  for (let attempt = 0; attempt < retries; attempt += 1) {
    const ready = await initializeKmlModal(attempt > 0);
    if (ready) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 120 * (attempt + 1)));
  }
  console.warn('[NetworkDesign] KML modal could not be initialized.');
  return false;
};

const closeManualModal = () => {
  if (typeof window.closeManualSaveModal === 'function') {
    window.closeManualSaveModal();
  }
};

const closeKmlModal = () => {
  if (typeof window.closeKmlModal === 'function') {
    window.closeKmlModal();
  }
};

onMounted(async () => {
  console.log('[NetworkDesignView] Component mounting...');
  document.title = 'Network Design | ProveMaps';

  // IMPORTANTE: Limpar elementos órfãos de reloads anteriores (F5)
  const orphanedElements = [
    'toastHost',
    'confirmHost',
    'contextMenu',
    'manualSaveModal',
    'importKmlModal'
  ];
  
  orphanedElements.forEach(id => {
    const bodyElement = document.body.querySelector(`#${id}`);
    if (bodyElement && bodyElement.parentElement === document.body) {
      console.log(`[NetworkDesignView] Removing orphaned element #${id} from document.body`);
      bodyElement.remove();
    }
  });

  ensureFiberGlobals();

  // IMPORTANTE: NetworkDesign refatorado para usar Provider Pattern
  // Funciona com qualquer provider configurado (Mapbox, Google Maps, etc.)
  try {
    console.log('[NetworkDesignView] Initializing map provider system...');
    
    // Pre-load provider antes de inicializar NetworkDesign
    const { getMapProvider, getCurrentProviderName } = await import('@/providers/maps/MapProviderFactory.js');
    
    const providerName = await getCurrentProviderName();
    console.log(`[NetworkDesignView] 🗺️ Configured provider: ${providerName}`);
    
    // Carregar provider (Google, Mapbox, etc.)
    const provider = await getMapProvider();
    
    if (!provider.isLoaded()) {
      throw new Error(`Provider ${providerName} failed to load`);
    }
    
    console.log(`[NetworkDesignView] ✅ ${providerName} provider ready`);
    
  } catch (error) {
    console.error('[NetworkDesignView] ❌ Failed to initialize map provider:', error);
    
    alert(
      `Erro ao inicializar sistema de mapas.\n\n` +
      `Detalhes: ${error.message}\n\n` +
      `Possíveis causas:\n` +
      `- Chave/token da API não configurado no sistema\n` +
      `- Problema de conexão com o serviço de mapas\n` +
      `- Provider de mapas não suportado\n\n` +
      `Configure em: Sistema > Configuração > Mapas\n\n` +
      `Por favor, recarregue a página (F5).`
    );
    return;
  }

  await nextTick();

  await waitForKmlModal();
  initializeNetworkDesignApp({ force: true });
  loadFolderTree();
  loadCableGroupsFromApi();

  if (!csrfToken.value && window.CSRF_TOKEN) {
    csrfToken.value = window.CSRF_TOKEN;
  }
  
  console.log('[NetworkDesignView] Component mounted successfully');
});

onUnmounted(() => {
  console.log('[NetworkDesignView] Component unmounting, cleaning up...');
  
  closeKmlModal();
  cleanupKmlModal();
  
  // Call the comprehensive cleanup function
  if (typeof window.destroyNetworkDesignApp === 'function') {
    window.destroyNetworkDesignApp();
  } else if (typeof window.clearMapAndResetState === 'function') {
    window.clearMapAndResetState();
  }
  
  console.log('[NetworkDesignView] Cleanup complete.');
});
</script>

<style scoped>
:global(:root) {
  --nd-bg: #f9fafb;
  --nd-text: #111827;
  --nd-muted: #6b7280;
  --nd-panel-bg: #ffffff;
  --nd-panel-border: #e5e7eb;
  --nd-panel-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --nd-panel-text: #111827;
  --nd-panel-muted: #6b7280;
  --nd-chip-bg: #dbeafe;
  --nd-chip-text: #1e40af;
  --nd-list-bg: #f9fafb;
  --nd-list-border: #e5e7eb;
  --nd-list-item-hover: #f3f4f6;
  --nd-btn-bg: #fef2f2;
  --nd-btn-border: #fecaca;
  --nd-btn-text: #b91c1c;
  --nd-help-emphasis: #b45309;
  --nd-shortcut-bg: #f3f4f6;
  --nd-shortcut-border: #d1d5db;
  --nd-context-bg: #ffffff;
  --nd-context-border: #e5e7eb;
  --nd-context-text: #111827;
  --nd-context-hover: #f3f4f6;
  --nd-modal-bg: #ffffff;
  --nd-modal-text: #111827;
  --nd-modal-muted: #6b7280;
  --nd-input-bg: #ffffff;
  --nd-input-border: #d1d5db;
}

.network-design-page {
  position: relative;
  height: 100%;
  width: 100%;
  overflow: hidden;
  color: var(--nd-text);
  background: var(--nd-bg);
}

:global(.dark),
:global([data-theme='dark']) {
  --nd-bg: #111827;
  --nd-text: #f9fafb;
  --nd-muted: #9ca3af;
  --nd-panel-bg: #1f2937;
  --nd-panel-border: #374151;
  --nd-panel-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
  --nd-panel-text: #f9fafb;
  --nd-panel-muted: #9ca3af;
  --nd-chip-bg: #1e3a8a;
  --nd-chip-text: #93c5fd;
  --nd-list-bg: #111827;
  --nd-list-border: #374151;
  --nd-list-item-hover: #374151;
  --nd-btn-bg: #7f1d1d;
  --nd-btn-border: #991b1b;
  --nd-btn-text: #fecaca;
  --nd-help-emphasis: #fbbf24;
  --nd-shortcut-bg: #374151;
  --nd-shortcut-border: #4b5563;
  --nd-context-bg: #1f2937;
  --nd-context-border: #374151;
  --nd-context-text: #f9fafb;
  --nd-context-hover: #374151;
  --nd-modal-bg: #1f2937;
  --nd-modal-text: #f9fafb;
  --nd-modal-muted: #9ca3af;
  --nd-input-bg: #111827;
  --nd-input-border: #374151;
}

.map-container {
  position: relative;
  height: 100%;
  width: 100%;
}

.map-canvas {
  height: 100%;
  width: 100%;
}

.floating-panel {
  position: absolute;
  right: 24px;
  width: min(360px, calc(100% - 48px));
  max-height: calc(100% - 160px);
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1.4rem;
  background: var(--nd-panel-bg);
  border-radius: 12px;
  border: 1px solid var(--nd-panel-border);
  box-shadow: var(--nd-panel-shadow);
  z-index: 35;
  color: var(--nd-panel-text);
  overflow: hidden;
  overflow-y: auto;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.floating-panel.nd-panel-hidden {
  opacity: 0;
  pointer-events: none;
  transform: translateY(-8px);
}

.floating-panel.collapsed {
  gap: 0;
  padding-bottom: 1rem;
}

#routePointsPanel {
  top: 60px;
  height: var(--route-panel-height, auto);
  max-height: min(80vh, calc(100vh - 120px));
  min-height: 120px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

#routePointsPanel .floating-panel__body {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.route-points-list {
  overflow-y: auto;
}

.panel-resize-handle {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 8px;
  cursor: ns-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.4;
  transition: opacity 0.15s;
}

.panel-resize-handle:hover,
.panel-resize-handle:active {
  opacity: 1;
}

.panel-resize-handle::after {
  content: '';
  width: 32px;
  height: 3px;
  border-radius: 99px;
  background: var(--nd-panel-text);
}

/* Help FAB + Popover */
.help-fab-wrapper {
  position: absolute;
  bottom: 32px;
  right: 24px;
  z-index: 35;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
}

.help-fab {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--nd-panel-bg);
  border: 1px solid var(--nd-panel-border);
  box-shadow: var(--nd-panel-shadow);
  color: var(--nd-panel-muted);
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s ease, color 0.2s ease;
  flex-shrink: 0;
}

.help-fab:hover,
.help-fab.active {
  background: var(--nd-chip-bg);
  color: var(--nd-chip-text);
}

.help-popover {
  width: min(320px, calc(100vw - 48px));
  background: var(--nd-panel-bg);
  border: 1px solid var(--nd-panel-border);
  border-radius: 12px;
  box-shadow: var(--nd-panel-shadow);
  padding: 1.1rem 1.2rem;
  opacity: 0;
  pointer-events: none;
  transform: translateY(6px);
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.help-popover.visible {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.floating-panel h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--nd-panel-text);
  letter-spacing: 0.01em;
}

.floating-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.floating-panel__header-main {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.floating-panel__metric {
  font-size: 0.82rem;
  color: var(--nd-panel-muted);
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  border: 1px solid var(--nd-panel-border);
  background: var(--nd-list-bg);
}

.panel-toggle-btn {
  border: 1px solid var(--nd-panel-border);
  background: var(--nd-chip-bg);
  color: var(--nd-panel-text);
  border-radius: 999px;
  height: 32px;
  width: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.panel-toggle-btn:hover {
  background: var(--nd-list-item-hover);
}

.panel-toggle-icon {
  width: 18px;
  height: 18px;
  transition: transform 0.2s ease;
}

.floating-panel.collapsed .panel-toggle-icon {
  transform: rotate(-90deg);
}

.floating-panel__body {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.floating-panel.collapsed .floating-panel__body {
  display: none;
}

.floating-panel__description {
  margin: 0;
  font-size: 0.85rem;
  color: var(--nd-panel-muted);
}

.route-points-list {
  list-style: none;
  margin: 0;
  padding: 0.75rem;
  border: 1px dashed var(--nd-list-border);
  border-radius: 16px;
  background: var(--nd-list-bg);
  flex: 1;
  overflow-y: auto;
}

.route-points-list li {
  padding: 0.45rem 0.6rem;
  border-radius: 0.65rem;
  font-size: 0.85rem;
  color: var(--nd-panel-text);
  cursor: grab;
  transition: background 0.2s ease, transform 0.2s ease;
}

.route-points-list li + li {
  margin-top: 0.45rem;
}

.route-points-list li.bg-blue-100 {
  background: rgba(37, 99, 235, 0.18);
}

.route-points-list li.bg-blue-50 {
  background: rgba(191, 219, 254, 0.4);
}

:global(.dark .network-design-page .route-points-list li.bg-blue-100),
:global([data-theme='dark'] .network-design-page .route-points-list li.bg-blue-100) {
  background: rgba(59, 130, 246, 0.35);
  color: #f8fafc;
}

:global(.dark .network-design-page .route-points-list li.bg-blue-50),
:global([data-theme='dark'] .network-design-page .route-points-list li.bg-blue-50) {
  background: rgba(191, 219, 254, 0.18);
  color: #f8fafc;
}

.floating-panel__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding-top: 0.5rem;
}
#cableDetailsPanel .floating-panel__footer {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
  justify-content: unset;
}
#cableDetailsPanel .floating-panel__footer .footer-btn,
#cableDetailsPanel .floating-panel__footer .footer-btn-split {
  width: 100%;
  justify-content: center;
}

.footer-btn {
  background: var(--nd-btn-bg);
  color: var(--nd-btn-text);
  border: 1px solid var(--nd-btn-border);
  border-radius: 999px;
  padding: 0.42rem 0.85rem;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.footer-btn:hover {
  background: rgba(248, 113, 113, 0.22);
  border-color: rgba(248, 113, 113, 0.45);
}

.footer-btn--primary {
  background: var(--nd-chip-bg);
  color: var(--nd-chip-text);
  border-color: transparent;
}

.footer-btn--primary:hover {
  background: #bfdbfe;
  border-color: transparent;
}

.footer-btn--danger {
  background: var(--nd-btn-bg);
  color: var(--nd-btn-text);
  border-color: var(--nd-btn-border);
}

/* Cable Details Panel */
#cableDetailsPanel {
  /* position controlled via Vue :style binding */
  right: unset;
  max-height: min(90vh, calc(100vh - 80px));
  overflow-y: auto;
}

.cable-detail-drag-handle {
  cursor: grab;
  user-select: none;
}

.cable-detail-drag-handle:active {
  cursor: grabbing;
}

.cable-details-dl {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  margin: 0;
}

.cable-details-row {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.cable-details-row dt {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--nd-panel-muted);
}

.cable-details-row dd {
  margin: 0;
  font-size: 0.88rem;
  color: var(--nd-panel-text);
  word-break: break-word;
}

.help-mode-label {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--nd-help-emphasis);
  margin-bottom: 0.25rem;
}

.help-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  font-size: 0.85rem;
  color: var(--nd-panel-muted);
}

.help-list li {
  display: flex;
  gap: 0.55rem;
  align-items: flex-start;
}

.help-icon {
  flex-shrink: 0;
  font-size: 1rem;
  line-height: 1.3;
}

@media (max-width: 1024px) {
  .floating-panel {
    left: 24px;
    right: 24px;
    width: auto;
    max-height: 60vh;
  }

  #routePointsPanel {
    top: auto;
    bottom: calc(32px + 18vh);
  }

  .help-fab-wrapper {
    bottom: 24px;
    right: 24px;
  }
}

.toast-host {
  position: fixed;
  top: 1.25rem;
  right: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  z-index: 60;
  pointer-events: none;
}

.toast-card {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  background: var(--surface-card);
  color: var(--text-primary);
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-primary);
  transition: opacity 0.16s ease;
  pointer-events: auto;
}

.toast-card.toast-success {
  border-left: 4px solid #22c55e;
}

.toast-card.toast-error {
  border-left: 4px solid #ef4444;
}

.toast-card.toast-warning {
  border-left: 4px solid #f97316;
}

.toast-card.toast-info {
  border-left: 4px solid #3b82f6;
}

.confirm-host {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 55;
  pointer-events: none;
}

:global(.confirm-backdrop) {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  pointer-events: auto;
}

:global(.confirm-card) {
  position: relative;
  background: var(--surface-card);
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: var(--shadow-lg);
  max-width: 400px;
  width: calc(100% - 2rem);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  z-index: 1;
  pointer-events: auto;
  color: #f9fafb;
}
:global(.confirm-card h3) {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  color: #f9fafb;
}
:global(.confirm-card p) {
  font-size: 0.875rem;
  margin: 0;
  color: #9ca3af;
  line-height: 1.5;
}
:global(.confirm-buttons) {
  display: flex;
  gap: 0.625rem;
  justify-content: flex-end;
  margin-top: 0.25rem;
}
:global(.confirm-buttons button) {
  padding: 0.5rem 1.1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: opacity .15s;
}
:global(.confirm-buttons button:hover) { opacity: 0.85; }
:global(.confirm-buttons button[data-variant='secondary']) {
  background: transparent;
  border: 1px solid #374151;
  color: #f9fafb;
}
:global(.confirm-buttons button[data-variant='primary']) {
  background: #3b82f6;
  color: #fff;
}
:global(.confirm-buttons button[data-variant='danger']) {
  background: #dc2626;
  color: #fff;
}

#contextMenu {
  width: 260px;
  background: var(--nd-context-bg);
  border-radius: 12px;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.18);
  padding: 1rem;
  color: var(--nd-context-text);
  border: 1px solid var(--nd-context-border);
}

#contextMenu.hidden {
  display: none;
}

#contextMenu h3 {
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--nd-context-text);
}

#contextMenu button {
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.75rem;
  border-radius: 0.6rem;
  transition: background-color 0.2s ease;
  font-size: 0.875rem;
  color: var(--nd-context-text);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.ctx-icon {
  width: 14px; height: 14px; flex-shrink: 0; opacity: 0.65;
}
.ctx-cable-badges {
  display: flex; flex-wrap: wrap; gap: 0.25rem; margin-bottom: 0.375rem;
}
.ctx-badge {
  font-size: 0.65rem; font-weight: 600; padding: 1px 6px;
  border-radius: 999px; line-height: 1.6;
}
.ctx-badge--type { background: #dbeafe; color: #1e40af; }
.ctx-badge--group { background: #f3f4f6; color: #374151; }
:global(.dark) .ctx-badge--type,
:global([data-theme='dark']) .ctx-badge--type { background: #1e3a8a; color: #93c5fd; }
:global(.dark) .ctx-badge--group,
:global([data-theme='dark']) .ctx-badge--group { background: #374151; color: #d1d5db; }

#contextMenu button:hover {
  background-color: var(--nd-context-hover);
}

#contextMenu button[data-variant='danger'] {
  color: #dc2626;
}

:global(.dark) #contextMenu button[data-variant='danger'],
:global([data-theme='dark']) #contextMenu button[data-variant='danger'] {
  color: #f87171;
}

#contextMenu button[data-variant='danger']:hover {
  background-color: #fef2f2;
}

:global(.dark) #contextMenu button[data-variant='danger']:hover,
:global([data-theme='dark']) #contextMenu button[data-variant='danger']:hover {
  background-color: #7f1d1d;
}

#contextCableInfo {
  margin-bottom: 0.75rem;
  border-bottom: 1px solid var(--nd-context-border);
  padding-bottom: 0.75rem;
}

#contextCableName {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--nd-context-text);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(17, 24, 39, 0.75);
  z-index: 52;
  transition: opacity 0.3s ease;
}

:global(.dark) .modal-overlay,
:global([data-theme='dark']) .modal-overlay {
  background: rgba(0, 0, 0, 0.85);
}

.modal-card {
  background: var(--nd-modal-bg);
  border-radius: 0.75rem;
  width: 100%;
  max-width: 540px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 1.5rem;
  position: relative;
  transition: opacity 0.3s ease, transform 0.3s ease;
  color: var(--nd-modal-text);
  border: 1px solid var(--nd-panel-border);
  box-shadow: var(--nd-panel-shadow);
}

.network-design-page .modal-card label {
  color: var(--nd-modal-text);
}

.network-design-page .modal-card p,
.network-design-page .modal-card .text-slate-500,
.network-design-page .modal-card .text-gray-500,
.network-design-page .modal-card .text-gray-600 {
  color: var(--nd-modal-muted);
}

.network-design-page .modal-card input,
.network-design-page .modal-card select,
.network-design-page .modal-card textarea {
  background: var(--nd-input-bg);
  color: var(--nd-modal-text);
  border-color: var(--nd-input-border);
}

.network-design-page #importKmlModalContent {
  color: var(--nd-modal-text);
}

.network-design-page #importKmlModalContent h2 {
  color: var(--nd-modal-text);
}

.network-design-page #importKmlModalContent p,
.network-design-page #importKmlModalContent .text-gray-500,
.network-design-page #importKmlModalContent .text-gray-600,
.network-design-page #importKmlModalContent .text-gray-700 {
  color: var(--nd-modal-muted);
}

.network-design-page #importKmlModalContent input,
.network-design-page #importKmlModalContent select,
.network-design-page #importKmlModalContent textarea {
  background: var(--nd-input-bg);
  color: var(--nd-modal-text);
  border-color: var(--nd-input-border);
}

.network-design-page #importKmlModalContent .bg-gray-100 {
  background: var(--nd-list-bg);
}

.network-design-page .nd-kml-input {
  background: var(--nd-input-bg);
  color: var(--nd-modal-text);
  border: 1px solid var(--nd-input-border);
}

.network-design-page .nd-kml-btn-cancel {
  background: transparent;
  border: 1px solid var(--nd-input-border);
  color: var(--nd-modal-text);
}

.network-design-page .modal-card .bg-blue-50 {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1e40af;
}

:global(.dark) .network-design-page .modal-card .bg-blue-50,
:global([data-theme='dark']) .network-design-page .modal-card .bg-blue-50 {
  background: #1e3a8a;
  border-color: #1e40af;
  color: #93c5fd;
}

/* ── Modal tabs & form ───────────────────────────────────── */
.modal-distance-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--nd-list-bg);
  border: 1px solid var(--nd-panel-border);
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
  color: var(--nd-modal-muted);
}
.modal-distance-badge strong {
  color: var(--nd-modal-text);
  font-weight: 600;
}

.modal-loss-estimate {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--nd-list-bg);
  border: 1px solid var(--nd-panel-border);
  border-radius: 0.375rem;
  padding: 0.4rem 0.75rem;
  margin-top: -0.6rem;
  margin-bottom: 1rem;
  font-size: 0.8rem;
  color: var(--nd-modal-muted);
}
.modal-loss-estimate strong {
  color: var(--nd-modal-text);
  font-weight: 600;
}
.modal-loss-estimate--warning {
  border-color: #f59e0b;
  background: #fffbeb;
}
:global(.dark) .modal-loss-estimate--warning,
:global([data-theme='dark']) .modal-loss-estimate--warning {
  border-color: #d97706;
  background: #1c1506;
}
.modal-loss-warning {
  color: #d97706;
  font-weight: 600;
  margin-left: auto;
}

.modal-tabs {
  display: flex;
  border-bottom: 2px solid var(--nd-panel-border);
  margin-bottom: 1rem;
}
.modal-tab {
  flex: 1;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--nd-modal-muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.modal-tab:hover {
  color: var(--nd-modal-text);
}
.modal-tab.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}
.modal-tab-panel {
  display: block;
}
.modal-tab-panel.hidden {
  display: none !important;
}

.modal-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-bottom: 0.75rem;
}
.modal-field label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--nd-modal-text);
}
.modal-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  border: 1px solid var(--nd-input-border);
  border-radius: 0.375rem;
  background: var(--nd-input-bg);
  color: var(--nd-modal-text);
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}
.modal-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}
.modal-select-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.modal-select-row .modal-input {
  flex: 1;
  min-width: 0;
}
.modal-add-btn {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--nd-input-border);
  border-radius: 0.375rem;
  background: var(--nd-input-bg);
  color: var(--nd-modal-text);
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.modal-add-btn:hover {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.modal-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}
.modal-single-port-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
  color: var(--nd-modal-muted);
}
.modal-checkbox {
  width: 1rem;
  height: 1rem;
}
.modal-notice {
  font-size: 0.8125rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
  background: var(--nd-list-bg);
  color: var(--nd-modal-muted);
  border: 1px solid var(--nd-panel-border);
  margin-bottom: 0.75rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--nd-panel-border);
}
.modal-btn {
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 0.375rem;
  border: none;
  cursor: pointer;
  transition: background 0.15s;
}
.modal-btn--cancel {
  background: var(--nd-list-bg);
  color: var(--nd-modal-muted);
  border: 1px solid var(--nd-panel-border);
}
.modal-btn--cancel:hover {
  background: var(--nd-panel-border);
}
.modal-btn--save {
  background: #2563eb;
  color: #fff;
}
.modal-btn--save:hover {
  background: #1d4ed8;
}

/* ── Fallback cables alert ───────────────────────────────── */
.nd-fallback-alert {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 900;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: #7c2d12;
  color: #fed7aa;
  border: 1px solid #ea580c;
  border-radius: 8px;
  padding: 10px 14px;
  max-width: 520px;
  font-size: 13px;
  line-height: 1.5;
  box-shadow: 0 4px 16px rgba(0,0,0,.4);
}
.nd-fallback-alert__close {
  margin-left: auto;
  background: none;
  border: none;
  color: #fed7aa;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0 2px;
  flex-shrink: 0;
}
.nd-fallback-alert__close:hover { color: #fff; }

/* ── Layer control panel ─────────────────────────────────── */
.nd-layer-panel {
  position: absolute;
  bottom: 32px;
  left: 24px;
  z-index: 35;
  display: flex;
  flex-direction: column-reverse;
  align-items: flex-start;
  gap: 0.25rem;
}
.nd-layer-panel__footer {
  display: flex;
  align-items: stretch;
  gap: 0.25rem;
}
.nd-layer-panel__toggle {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.75rem;
  background: var(--nd-panel-bg);
  border: 1px solid var(--nd-panel-border);
  border-radius: 0.5rem;
  box-shadow: var(--nd-panel-shadow);
  color: var(--nd-panel-text);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.nd-layer-panel__toggle:hover { background: var(--nd-list-bg); }
.nd-layer-panel__gear {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.4rem 0.5rem;
  background: var(--nd-panel-bg);
  border: 1px solid var(--nd-panel-border);
  border-radius: 0.5rem;
  box-shadow: var(--nd-panel-shadow);
  color: var(--nd-panel-text);
  cursor: pointer;
  transition: background 0.15s;
  opacity: 0.75;
}
.nd-layer-panel__gear:hover { background: var(--nd-list-bg); opacity: 1; }
.nd-layer-icon { width: 16px; height: 16px; flex-shrink: 0; }
.nd-layer-panel__body {
  background: var(--nd-panel-bg);
  border: 1px solid var(--nd-panel-border);
  border-radius: 0.5rem;
  box-shadow: var(--nd-panel-shadow);
  padding: 0.5rem 0;
  min-width: 180px;
}
.nd-layer-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.75rem;
  font-size: 0.8125rem;
  color: var(--nd-panel-text);
  cursor: pointer;
  transition: background 0.1s;
}
.nd-layer-row:hover { background: var(--nd-list-bg); }
.nd-layer-row--all { font-weight: 600; }
.nd-layer-row input[type="checkbox"] { accent-color: var(--nd-accent, #3b82f6); flex-shrink: 0; }
.nd-layer-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.nd-layer-count {
  margin-left: auto;
  font-size: 0.6875rem;
  color: var(--nd-modal-muted);
  background: var(--nd-list-bg);
  padding: 0.05rem 0.35rem;
  border-radius: 999px;
}
.nd-layer-divider {
  height: 1px;
  background: var(--nd-panel-border);
  margin: 0.25rem 0;
}
.nd-layer-section-label {
  height: auto;
  background: transparent;
  margin: 0.4rem 0 0.1rem;
  padding: 0 0.5rem;
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--nd-modal-muted);
}
.nd-layer-dot--type {
  background: linear-gradient(135deg, #6366f1 50%, #a855f7 50%);
}

/* ── Global search bar ───────────────────────────────────── */
.map-search-wrapper {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  width: min(420px, calc(100vw - 120px));
  z-index: 410;
}
.map-search-input-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--nd-modal-bg, #fff);
  border: 1px solid var(--nd-panel-border, #d1d5db);
  border-radius: 0.5rem;
  padding: 0.45rem 0.75rem;
  box-shadow: 0 2px 8px rgba(0,0,0,.15);
}
.map-search-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: var(--nd-modal-muted, #6b7280);
}
.map-search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.875rem;
  color: var(--nd-modal-text, #111827);
  min-width: 0;
}
.map-search-input::placeholder { color: var(--nd-modal-muted, #9ca3af); }
.map-search-input::-webkit-search-cancel-button { cursor: pointer; }
.map-search-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--nd-panel-border, #d1d5db);
  border-top-color: var(--nd-accent, #3b82f6);
  border-radius: 50%;
  animation: ndSpin .6s linear infinite;
  flex-shrink: 0;
}
@keyframes ndSpin { to { transform: rotate(360deg); } }
.map-search-dropdown {
  list-style: none;
  margin: 0.25rem 0 0;
  padding: 0.25rem 0;
  background: var(--nd-modal-bg, #fff);
  border: 1px solid var(--nd-panel-border, #d1d5db);
  border-radius: 0.5rem;
  box-shadow: 0 4px 16px rgba(0,0,0,.18);
  max-height: 320px;
  overflow-y: auto;
}
.map-search-group-label {
  padding: 0.35rem 0.875rem 0.2rem;
  font-size: 0.6875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--nd-modal-muted, #6b7280);
}
.map-search-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.875rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--nd-modal-text, #111827);
  transition: background 0.1s;
}
.map-search-item.focused,
.map-search-item:hover {
  background: var(--nd-list-bg, #f3f4f6);
}
.map-search-item__icon {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  flex-shrink: 0;
  background-size: 11px;
  background-repeat: no-repeat;
  background-position: center;
}
.map-search-item__icon[data-type="cable"]  { background-color: #dbeafe; }
.map-search-item__icon[data-type="device"] { background-color: #fef9c3; }
.map-search-item__icon[data-type="site"]   { background-color: #dcfce7; }
.map-search-item__name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.map-search-item__sub {
  font-size: 0.75rem;
  color: var(--nd-modal-muted, #6b7280);
  white-space: nowrap;
}
.map-search-empty {
  padding: 0.75rem 0.875rem;
  font-size: 0.8125rem;
  color: var(--nd-modal-muted, #6b7280);
  text-align: center;
}

/* ── Audit log ───────────────────────────────────────────── */
.audit-log-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 220px;
  overflow-y: auto;
  padding-right: 0.25rem;
}
.audit-log-empty {
  font-size: 0.8125rem;
  color: var(--nd-modal-muted);
  text-align: center;
  padding: 1.5rem 0;
}
.audit-log-entry {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
  background: var(--nd-list-bg);
  border: 1px solid var(--nd-panel-border);
  font-size: 0.8125rem;
}
.audit-log-entry__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.audit-log-badge {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  border-radius: 0.25rem;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.audit-log-badge--created  { background: #dcfce7; color: #166534; }
.audit-log-badge--updated  { background: #dbeafe; color: #1e40af; }
.audit-log-badge--deleted  { background: #fee2e2; color: #991b1b; }
:global(.dark) .audit-log-badge--created,
:global([data-theme='dark']) .audit-log-badge--created  { background: #14532d; color: #86efac; }
:global(.dark) .audit-log-badge--updated,
:global([data-theme='dark']) .audit-log-badge--updated  { background: #1e3a8a; color: #93c5fd; }
:global(.dark) .audit-log-badge--deleted,
:global([data-theme='dark']) .audit-log-badge--deleted  { background: #7f1d1d; color: #fca5a5; }
.audit-log-entry__meta {
  color: var(--nd-modal-muted);
  font-size: 0.75rem;
}
.audit-log-loading {
  font-size: 0.8125rem;
  color: var(--nd-modal-muted);
  text-align: center;
  padding: 1.5rem 0;
}

/* ── Photo gallery ───────────────────────────────────────── */
.photo-upload-area {
  border: 2px dashed var(--nd-panel-border);
  border-radius: 0.5rem;
  padding: 1rem;
  text-align: center;
  margin-bottom: 0.75rem;
  transition: border-color 0.15s;
}
.photo-upload-area.dragover { border-color: var(--nd-chip-text); }
.photo-upload-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8125rem;
  color: var(--nd-modal-muted);
}
.photo-upload-link {
  background: none; border: none; cursor: pointer;
  color: var(--nd-chip-text); font-size: inherit; padding: 0;
  text-decoration: underline;
}
.photo-upload-hint { font-size: 0.72rem; color: var(--nd-panel-muted); }
.photo-upload-progress { display: flex; flex-direction: column; gap: 0.25rem; align-items: center; }
.photo-progress-bar { width: 100%; height: 4px; background: var(--nd-panel-border); border-radius: 2px; overflow: hidden; }
.photo-progress-fill { height: 100%; background: var(--nd-chip-text); width: 0%; transition: width 0.2s; }
.photo-gallery {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.375rem;
  max-height: 220px;
  overflow-y: auto;
}
.photo-thumb {
  position: relative;
  height: 72px;
  border-radius: 0.3rem;
  overflow: hidden;
  background: var(--nd-list-bg);
  cursor: pointer;
}
.photo-thumb img {
  width: 100%; height: 100%; object-fit: cover;
  transition: opacity 0.15s;
}
.photo-thumb:hover img { opacity: 0.85; }
.photo-thumb__del {
  position: absolute; top: 3px; right: 3px;
  background: rgba(0,0,0,0.55); color: #fff;
  border: none; border-radius: 50%;
  width: 20px; height: 20px; font-size: 0.75rem;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity 0.15s;
}
.photo-thumb:hover .photo-thumb__del { opacity: 1; }
.photo-thumb__caption {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: rgba(0,0,0,0.5); color: #fff;
  font-size: 0.625rem; padding: 2px 4px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.photo-empty {
  font-size: 0.8125rem; color: var(--nd-modal-muted);
  text-align: center; padding: 1.5rem 0;
  grid-column: 1 / -1;
}

/* ── Folder tree panel ───────────────────────────────────── */
.nd-folder-panel {
  position: absolute;
  top: 64px;
  left: 14px;
  z-index: 35;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
}
.nd-folder-panel__toggle {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.75rem;
  background: var(--nd-panel-bg);
  border: 1px solid var(--nd-panel-border);
  border-radius: 0.5rem;
  box-shadow: var(--nd-panel-shadow);
  color: var(--nd-panel-text);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}
.nd-folder-panel__toggle:hover { background: var(--nd-list-bg); }
.nd-folder-active-badge {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: #dbeafe;
  color: #1e40af;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
}
:global(.dark) .nd-folder-active-badge,
:global([data-theme='dark']) .nd-folder-active-badge {
  background: #1e3a8a;
  color: #93c5fd;
}
.nd-folder-panel__body {
  background: var(--nd-panel-bg);
  border: 1px solid var(--nd-panel-border);
  border-radius: 0.5rem;
  box-shadow: var(--nd-panel-shadow);
  padding: 0.4rem 0;
  min-width: 200px;
  max-width: 260px;
  max-height: calc(100vh - 160px);
  overflow-y: auto;
}
.nd-folder-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.5rem 0.35rem 8px;
  font-size: 0.8125rem;
  color: var(--nd-panel-text);
  cursor: pointer;
  transition: background 0.1s;
  border-radius: 0.25rem;
  margin: 0 0.25rem;
}
.nd-folder-item:hover { background: var(--nd-list-bg); }
.nd-folder-item.active {
  background: var(--nd-chip-bg);
  color: var(--nd-chip-text);
  font-weight: 600;
}
.nd-folder-item--all { font-weight: 600; padding-left: 8px !important; }
.nd-folder-icon {
  width: 13px;
  height: 13px;
  color: #f59e0b;
  flex-shrink: 0;
}
.nd-folder-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nd-folder-expand {
  background: none;
  border: none;
  padding: 0;
  width: 14px;
  height: 14px;
  font-size: 0.55rem;
  color: var(--nd-panel-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.15s;
}
.nd-folder-expand.expanded { transform: rotate(90deg); }
.nd-folder-leaf-indent { width: 14px; flex-shrink: 0; }
.nd-folder-add-child {
  background: none;
  border: none;
  padding: 0 2px;
  font-size: 0.9rem;
  color: var(--nd-panel-muted);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.1s;
  line-height: 1;
  flex-shrink: 0;
}
.nd-folder-item:hover .nd-folder-add-child { opacity: 1; }
.nd-folder-empty {
  padding: 0.5rem 0.875rem;
  font-size: 0.8rem;
  color: var(--nd-panel-muted);
  text-align: center;
}
.nd-drop-target {
  background: color-mix(in srgb, var(--nd-chip-bg) 60%, transparent) !important;
  outline: 2px dashed var(--nd-chip-text, #6366f1);
  outline-offset: -2px;
}
.nd-cable-drag-handle {
  cursor: grab;
  user-select: none;
}
.nd-cable-drag-handle:active { cursor: grabbing; }
.footer-btn-split {
  display: flex;
  border-radius: 0.375rem;
  overflow: hidden;
  width: 100%;
}
.footer-btn-split .footer-btn {
  border-radius: 0;
}
.footer-btn-split .footer-btn:first-child {
  border-radius: 0.375rem 0 0 0.375rem;
  border-right: none;
  flex: 1;
  text-align: center;
}
.footer-btn-split__drag {
  border-left: 1px solid var(--nd-btn-border);
  padding: 0.3rem 0.4rem;
  display: flex;
  align-items: center;
  border-radius: 0 0.375rem 0.375rem 0 !important;
  opacity: 0.7;
}
.footer-btn-split__drag:hover { opacity: 1; }
.nd-folder-create-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.5rem;
  margin: 0 0.25rem;
}
.nd-folder-create-label {
  width: 100%;
  font-size: 0.7rem;
  color: var(--nd-panel-muted);
  padding: 0 0.25rem;
}
.nd-folder-create-input {
  flex: 1;
  font-size: 0.8rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--nd-input-border);
  border-radius: 0.25rem;
  background: var(--nd-input-bg);
  color: var(--nd-modal-text);
  outline: none;
  min-width: 0;
}
.nd-folder-create-input:focus { border-color: #2563eb; }
.nd-folder-create-ok {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.5rem;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  flex-shrink: 0;
}
.nd-folder-new-root {
  width: 100%;
  text-align: left;
  padding: 0.35rem 0.875rem;
  font-size: 0.8rem;
  color: var(--nd-panel-muted);
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.1s;
}
.nd-folder-new-root:hover { color: #2563eb; }

/* ── Move-to-folder picker ────────────────────────────────── */
.nd-move-folder-overlay {
  position: fixed;
  inset: 0;
  z-index: 54;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.45);
}
.nd-move-folder-card {
  background: var(--nd-panel-bg);
  border: 1px solid var(--nd-panel-border);
  border-radius: 0.75rem;
  box-shadow: var(--nd-panel-shadow);
  width: min(280px, calc(100vw - 32px));
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.nd-move-folder-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--nd-panel-border);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--nd-panel-text);
}
.nd-move-folder-close {
  background: none;
  border: none;
  font-size: 1.2rem;
  color: var(--nd-panel-muted);
  cursor: pointer;
  line-height: 1;
  padding: 0 2px;
}
.nd-move-folder-list {
  overflow-y: auto;
  padding: 0.4rem 0;
}
.nd-move-folder-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
  text-align: left;
  padding: 0.4rem 1rem;
  font-size: 0.8125rem;
  color: var(--nd-panel-text);
  background: none;
  border: none;
  cursor: pointer;
  transition: background 0.1s;
}
.nd-move-folder-item:hover { background: var(--nd-list-bg); }
.nd-move-folder-item.active {
  background: var(--nd-chip-bg);
  color: var(--nd-chip-text);
  font-weight: 600;
}

.opacity-0 {
  opacity: 0;
}

.opacity-100 {
  opacity: 1;
}

.pointer-events-none {
  pointer-events: none;
}

.scale-95 {
  transform: scale(0.95);
}

.scale-100 {
  transform: scale(1);
}

/* ── Admin panel ──────────────────────────────────────────────── */

.nd-admin-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.55);
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nd-admin-modal {
  background: var(--nd-modal-bg, var(--surface-card));
  color: var(--nd-modal-text, var(--text-primary));
  border-radius: .75rem;
  width: 100%;
  max-width: 480px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 48px rgba(0,0,0,.5);
  border: 1px solid rgba(255,255,255,.08);
}

.nd-admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: .875rem 1rem;
  border-bottom: 1px solid rgba(255,255,255,.08);
}
.nd-admin-header h3 { margin: 0; font-size: .9375rem; font-weight: 600; }
.nd-admin-close {
  background: none; border: none; color: var(--nd-modal-muted, #94a3b8);
  font-size: 1.25rem; cursor: pointer; line-height: 1; padding: 0;
}

.nd-admin-tabs {
  display: flex;
  border-bottom: 1px solid rgba(255,255,255,.08);
  flex-shrink: 0;
}
.nd-admin-tab {
  flex: 1; padding: .625rem .75rem; font-size: .8125rem; font-weight: 500;
  background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--nd-modal-muted, #94a3b8); cursor: pointer; transition: all .15s;
}
.nd-admin-tab.active { color: #60a5fa; border-bottom-color: #60a5fa; }
.nd-admin-tab:hover:not(.active) { color: var(--nd-modal-text, #f1f5f9); }

.nd-admin-tab-body {
  padding: .75rem 1rem;
  overflow-y: auto;
  flex: 1;
}

.nd-admin-add-row {
  display: flex; gap: .5rem; margin-bottom: .75rem;
}
.nd-admin-input {
  flex: 1; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12);
  border-radius: .375rem; padding: .375rem .625rem; color: inherit; font-size: .8125rem;
}
.nd-admin-input:focus { outline: none; border-color: #60a5fa; }
.nd-admin-input--inline { min-width: 0; }
.nd-admin-input--sm { width: 90px; flex: none; }
.nd-admin-list-item--editing { flex-direction: column; align-items: stretch; padding: 0.5rem 0.625rem; }
.nd-admin-group-form { display: flex; flex-direction: column; gap: 0.4rem; width: 100%; }
.nd-admin-group-form-row { display: flex; align-items: center; gap: 0.5rem; }
.nd-admin-group-form-row label { font-size: 0.75rem; color: rgba(255,255,255,.5); width: 110px; flex-shrink: 0; }
.nd-admin-group-form-actions { display: flex; gap: 0.5rem; margin-top: 0.25rem; }
.nd-admin-item-badge {
  font-size: 0.7rem; background: rgba(96,165,250,.15); color: #60a5fa;
  border: 1px solid rgba(96,165,250,.25); border-radius: 0.25rem;
  padding: 0.1rem 0.375rem; white-space: nowrap;
}
.nd-admin-btn-add {
  padding: .375rem .75rem; background: #2563eb; color: #fff; border: none;
  border-radius: .375rem; font-size: .8125rem; cursor: pointer; white-space: nowrap;
}
.nd-admin-btn-add:disabled { opacity: .4; cursor: not-allowed; }
.nd-admin-btn-add:not(:disabled):hover { background: #1d4ed8; }

.nd-admin-loading, .nd-admin-empty {
  font-size: .8125rem; color: var(--nd-modal-muted, #94a3b8);
  text-align: center; padding: 1rem 0;
}

.nd-admin-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .25rem; }
.nd-admin-list-item {
  display: flex; align-items: center; gap: .375rem;
  padding: .375rem .5rem; border-radius: .375rem;
  background: rgba(255,255,255,.04);
  font-size: .8125rem;
}
.nd-admin-item-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.nd-admin-btn-icon {
  background: none; border: none; cursor: pointer; padding: .125rem .25rem;
  font-size: .875rem; border-radius: .25rem; flex-shrink: 0;
  opacity: .7; transition: opacity .15s;
}
.nd-admin-btn-icon:hover { opacity: 1; }
.nd-admin-btn-icon--danger:hover { color: #f87171; }
.nd-admin-btn-save {
  padding: .25rem .5rem; background: #16a34a; color: #fff; border: none;
  border-radius: .25rem; font-size: .75rem; cursor: pointer; flex-shrink: 0;
}
.nd-admin-btn-cancel {
  padding: .25rem .375rem; background: rgba(255,255,255,.1); color: inherit; border: none;
  border-radius: .25rem; font-size: .75rem; cursor: pointer; flex-shrink: 0;
}
</style>
