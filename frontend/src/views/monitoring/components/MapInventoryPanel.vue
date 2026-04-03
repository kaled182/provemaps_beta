<template>
  <transition name="slide">
    <div v-if="isVisible" class="inventory-panel">
      <div class="panel-header">
        <h3>Itens do Mapa</h3>
        <button @click="$emit('close')" class="btn-close-panel">×</button>
      </div>

      <div class="panel-tabs">
        <button 
          v-for="category in categories" 
          :key="category.key"
          @click="$emit('update:activeCategory', category.key)"
          :class="['tab-btn', { active: activeCategory === category.key }]"
        >
          <i :class="category.icon"></i>
          {{ category.label }}
          <span class="badge">{{ getCategoryCount(category.key) }}</span>
        </button>
      </div>

      <div class="panel-content">
        <div class="search-box">
          <i class="fas fa-search"></i>
          <input 
            :value="searchQuery" 
            @input="$emit('update:searchQuery', $event.target.value)"
            type="text" 
            placeholder="Buscar itens..."
          >
        </div>

        <!-- Lista de Itens -->
        <div class="items-list">
          <!-- Hierarquia de Sites (apenas para devices) -->
          <template v-if="activeCategory === 'devices'">
            <div v-for="siteGroup in devicesBySite" :key="'site-' + siteGroup.site_id" class="site-group">
              <!-- Linha do Site -->
              <div class="site-row">
                <button 
                  @click="$emit('toggle-site-expansion', siteGroup.site_id)" 
                  class="btn-expand"
                  :title="isSiteExpanded(siteGroup.site_id) ? 'Colapsar' : 'Expandir'"
                >
                  <i :class="isSiteExpanded(siteGroup.site_id) ? 'fas fa-chevron-down' : 'fas fa-chevron-right'"></i>
                </button>
                
                <label class="site-checkbox">
                  <input 
                    type="checkbox" 
                    :checked="isSiteFullySelected(siteGroup.site_id, siteGroup.devices)"
                    :indeterminate.prop="isSitePartiallySelected(siteGroup.site_id, siteGroup.devices)"
                    @change="$emit('toggle-site', siteGroup.site_id, siteGroup.devices)"
                  >
                  <div class="site-details">
                    <span class="site-name">
                      <i class="fas fa-map-marker-alt"></i>
                      {{ siteGroup.site_name }}
                    </span>
                    <span class="site-count">{{ siteGroup.devices.length }} equipamento(s)</span>
                  </div>
                </label>
                
                <div class="site-status-summary">
                  <template v-for="(count, status) in getSiteStatusSummary(siteGroup.devices)" :key="status">
                    <span v-if="count > 0" :class="['status-dot', status]" :title="`${count} ${getStatusLabel(status)}`">
                      {{ count }}
                    </span>
                  </template>
                </div>
              </div>
              
              <!-- Devices do Site (colapsável) -->
              <transition name="expand">
                <div v-if="isSiteExpanded(siteGroup.site_id)" class="devices-list">
                  <div 
                    v-for="device in siteGroup.devices" 
                    :key="device.id"
                    class="device-row"
                  >
                    <label class="device-checkbox">
                      <input 
                        type="checkbox" 
                        :checked="isItemSelected(device.id)"
                        @change="$emit('toggle-item', device.id)"
                      >
                      <div class="device-details">
                        <span class="device-name">{{ device.name }}</span>
                        <span v-if="device.ip && device.ip !== 'N/A'" class="device-ip">
                          <i class="fas fa-network-wired"></i> {{ device.ip }}
                        </span>
                      </div>
                    </label>
                    <div class="device-info">
                      <span v-if="device.status" :class="['status-badge', device.status]">
                        {{ getStatusLabel(device.status) }}
                      </span>
                      <span v-else class="status-badge offline">
                        Offline
                      </span>
                      <button @click="$emit('focus-item', device)" class="btn-focus">
                        <i class="fas fa-crosshairs"></i>
                      </button>
                    </div>
                  </div>
                </div>
              </transition>
            </div>
          </template>
          
          <!-- Hierarquia de Sites para Câmeras -->
          <template v-else-if="activeCategory === 'cameras'">
            <div v-for="siteGroup in camerasBySite" :key="'camera-site-' + siteGroup.site_name" class="site-group">
              <!-- Linha do Site -->
              <div class="site-row">
                <button 
                  @click="$emit('toggle-camera-site-expansion', siteGroup.site_name)" 
                  class="btn-expand"
                  :title="isCameraSiteExpanded(siteGroup.site_name) ? 'Colapsar' : 'Expandir'"
                >
                  <i :class="isCameraSiteExpanded(siteGroup.site_name) ? 'fas fa-chevron-down' : 'fas fa-chevron-right'"></i>
                </button>
                
                <label class="site-checkbox">
                  <input 
                    type="checkbox" 
                    :checked="isCameraSiteFullySelected(siteGroup.site_name, siteGroup.cameras)"
                    :indeterminate.prop="isCameraSitePartiallySelected(siteGroup.site_name, siteGroup.cameras)"
                    @change="$emit('toggle-camera-site', siteGroup.site_name, siteGroup.cameras)"
                  >
                  <div class="site-details">
                    <span class="site-name">
                      <i class="fas fa-map-marker-alt"></i>
                      {{ siteGroup.site_name }}
                    </span>
                    <span class="site-count">{{ siteGroup.cameras.length }} câmera(s)</span>
                  </div>
                </label>
                
                <div class="site-status-summary">
                  <template v-for="(count, status) in getCameraSiteStatusSummary(siteGroup.cameras)" :key="status">
                    <span v-if="count > 0" :class="['status-dot', status]" :title="`${count} ${status === 'online' ? 'ONLINE' : 'OFFLINE'}`">
                      {{ count }}
                    </span>
                  </template>
                </div>
              </div>
              
              <!-- Câmeras do Site (colapsável) -->
              <transition name="expand">
                <div v-if="isCameraSiteExpanded(siteGroup.site_name)" class="devices-list">
                  <div 
                    v-for="camera in siteGroup.cameras" 
                    :key="camera.id"
                    class="device-row"
                  >
                    <label class="device-checkbox">
                      <input 
                        type="checkbox" 
                        :checked="isItemSelected(camera.id)"
                        @change="$emit('toggle-item', camera.id)"
                      >
                      <div class="device-details">
                        <span class="device-name">{{ camera.name }}</span>
                      </div>
                    </label>
                    <div class="device-info">
                      <span v-if="camera.status" :class="['status-badge', camera.status]">
                        {{ getStatusLabel(camera.status) }}
                      </span>
                      <span v-else class="status-badge offline">
                        Offline
                      </span>
                      <button @click="$emit('focus-item', camera)" class="btn-focus">
                        <i class="fas fa-crosshairs"></i>
                      </button>
                    </div>
                  </div>
                </div>
              </transition>
            </div>
          </template>
          
          <!-- Hierarquia de pastas para cabos -->
          <template v-else-if="activeCategory === 'cables'">
            <!-- Modo busca: lista plana filtrada -->
            <template v-if="searchQuery">
              <div
                v-for="cable in filteredItems"
                :key="cable.id"
                class="item-row"
                @mouseenter="$emit('highlight-cable', cable.id)"
                @mouseleave="$emit('unhighlight-cable', cable.id)"
              >
                <label class="item-checkbox">
                  <input
                    type="checkbox"
                    :checked="isItemSelected(cable.id)"
                    @change="$emit('toggle-item', cable.id)"
                  >
                  <span class="item-name">{{ cable.name }}</span>
                </label>
                <div class="item-info">
                  <span v-if="cable.status" :class="['status-badge', cable.status]">
                    {{ getStatusLabel(cable.status) }}
                  </span>
                  <button @click="$emit('focus-item', cable)" class="btn-focus">
                    <i class="fas fa-crosshairs"></i>
                  </button>
                </div>
              </div>
            </template>

            <!-- Modo árvore: pastas + cabos sem pasta -->
            <template v-else>
              <template v-for="row in cableTreeRows" :key="row.key">
                <!-- Linha de pasta -->
                <div v-if="row.type === 'folder'" class="folder-row" :style="{ paddingLeft: (12 + row.depth * 16) + 'px' }">
                  <button class="btn-expand" @click="toggleFolder(row.folder.id)">
                    <i :class="isFolderExpanded(row.folder.id) ? 'fas fa-chevron-down' : 'fas fa-chevron-right'"></i>
                  </button>
                  <label class="folder-checkbox">
                    <input
                      type="checkbox"
                      :checked="isFolderFullySelected(row.folder)"
                      :indeterminate.prop="isFolderPartiallySelected(row.folder)"
                      @change="toggleFolderCables(row.folder)"
                    >
                    <div class="folder-details">
                      <span class="folder-name">
                        <i class="fas fa-folder" style="color:#f59e0b;margin-right:4px;font-size:11px"></i>
                        {{ row.folder.name }}
                      </span>
                      <span class="folder-count">{{ row.folder.cable_count }} cabo(s)</span>
                    </div>
                  </label>
                </div>

                <!-- Cabo dentro de pasta -->
                <div
                  v-else-if="row.type === 'cable'"
                  class="item-row item-row--indented"
                  :style="{ paddingLeft: (28 + row.depth * 16) + 'px' }"
                  @mouseenter="$emit('highlight-cable', row.cable.id)"
                  @mouseleave="$emit('unhighlight-cable', row.cable.id)"
                >
                  <label class="item-checkbox">
                    <input
                      type="checkbox"
                      :checked="isItemSelected(row.cable.id)"
                      @change="$emit('toggle-item', row.cable.id)"
                    >
                    <span class="item-name">{{ row.cable.name }}</span>
                  </label>
                  <div class="item-info">
                    <span v-if="row.cable.status" :class="['status-badge', row.cable.status]">
                      {{ getStatusLabel(row.cable.status) }}
                    </span>
                    <button @click="$emit('focus-item', row.cable)" class="btn-focus">
                      <i class="fas fa-crosshairs"></i>
                    </button>
                  </div>
                </div>

                <!-- Cabeçalho "Sem pasta" -->
                <div v-else-if="row.type === 'no-folder-header'" class="folder-row">
                  <button class="btn-expand" @click="toggleFolder('__no_folder__')">
                    <i :class="isFolderExpanded('__no_folder__') ? 'fas fa-chevron-down' : 'fas fa-chevron-right'"></i>
                  </button>
                  <label class="folder-checkbox">
                    <input
                      type="checkbox"
                      :checked="isNoFolderFullySelected(row.cables)"
                      :indeterminate.prop="isNoFolderPartiallySelected(row.cables)"
                      @change="toggleNoFolderCables(row.cables)"
                    >
                    <div class="folder-details">
                      <span class="folder-name" style="color:rgba(255,255,255,0.5)">
                        <i class="fas fa-folder-open" style="color:#64748b;margin-right:4px;font-size:11px"></i>
                        Sem pasta
                      </span>
                      <span class="folder-count">{{ row.cables.length }} cabo(s)</span>
                    </div>
                  </label>
                </div>
              </template>
            </template>
          </template>

          <!-- Lista simples para racks -->
          <template v-else>
            <div
              v-for="item in filteredItems"
              :key="item.id"
              class="item-row"
            >
              <label class="item-checkbox">
                <input
                  type="checkbox"
                  :checked="isItemSelected(item.id)"
                  @change="$emit('toggle-item', item.id)"
                >
                <span class="item-name">{{ item.name }}</span>
              </label>
              <div class="item-info">
                <span v-if="item.status" :class="['status-badge', item.status]">
                  {{ getStatusLabel(item.status) }}
                </span>
                <button @click="$emit('focus-item', item)" class="btn-focus">
                  <i class="fas fa-crosshairs"></i>
                </button>
              </div>
            </div>
          </template>
        </div>

        <div class="panel-footer">
          <button @click="$emit('select-all')" class="btn-panel btn-secondary">
            Selecionar Todos
          </button>
          <button @click="$emit('save')" class="btn-panel btn-primary">
            Salvar
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  isVisible: Boolean,
  activeCategory: String,
  searchQuery: String,
  categories: Array,
  availableItems: Object,
  selectedItems: Object,
  expandedSites: Set,
  expandedCameraSites: Set,
  devicesBySite: Array,
  camerasBySite: Array,
  filteredItems: Array,
  foldersTree: { type: Array, default: () => [] }
})

// ── Folder expansion (local state) ──────────────────────────────────────────
const expandedFolders = ref(new Set())

function toggleFolder(id) {
  const next = new Set(expandedFolders.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedFolders.value = next
}

function isFolderExpanded(id) {
  return expandedFolders.value.has(id)
}

// ── Cable tree rows ──────────────────────────────────────────────────────────
// Returns a flat list of { type, key, depth, folder?, cable?, cables? } for rendering
const cableTreeRows = computed(() => {
  const rows = []
  const cables = props.availableItems.cables || []

  // Group cables by folder_id
  const byFolder = new Map()
  cables.forEach(c => {
    const k = c.folder_id ?? null
    if (!byFolder.has(k)) byFolder.set(k, [])
    byFolder.get(k).push(c)
  })

  function walkFolder(folder, depth) {
    rows.push({ type: 'folder', key: `folder-${folder.id}`, folder, depth })
    if (isFolderExpanded(folder.id)) {
      for (const child of (folder.children || [])) {
        walkFolder(child, depth + 1)
      }
      for (const cable of (byFolder.get(folder.id) || [])) {
        rows.push({ type: 'cable', key: `cable-${cable.id}`, cable, depth: depth + 1 })
      }
    }
  }

  for (const folder of (props.foldersTree || [])) {
    walkFolder(folder, 0)
  }

  // "Sem pasta" section
  const noCables = byFolder.get(null) || []
  if (noCables.length > 0) {
    rows.push({ type: 'no-folder-header', key: '__no_folder__', cables: noCables })
    if (isFolderExpanded('__no_folder__')) {
      for (const cable of noCables) {
        rows.push({ type: 'cable', key: `cable-${cable.id}`, cable, depth: 1 })
      }
    }
  }

  return rows
})

// Returns all cable ids in a folder and its sub-folders recursively
function collectFolderCableIds(folder) {
  const cables = props.availableItems.cables || []
  const ids = cables.filter(c => c.folder_id === folder.id).map(c => c.id)
  for (const child of (folder.children || [])) {
    ids.push(...collectFolderCableIds(child))
  }
  return ids
}

function isFolderFullySelected(folder) {
  const ids = collectFolderCableIds(folder)
  return ids.length > 0 && ids.every(id => props.selectedItems.cables?.includes(id))
}

function isFolderPartiallySelected(folder) {
  const ids = collectFolderCableIds(folder)
  const count = ids.filter(id => props.selectedItems.cables?.includes(id)).length
  return count > 0 && count < ids.length
}

function isNoFolderFullySelected(cables) {
  return cables.length > 0 && cables.every(c => props.selectedItems.cables?.includes(c.id))
}

function isNoFolderPartiallySelected(cables) {
  const count = cables.filter(c => props.selectedItems.cables?.includes(c.id)).length
  return count > 0 && count < cables.length
}

const emit = defineEmits([
  'close',
  'update:activeCategory',
  'update:searchQuery',
  'toggle-site-expansion',
  'toggle-camera-site-expansion',
  'toggle-site',
  'toggle-camera-site',
  'toggle-item',
  'focus-item',
  'highlight-cable',
  'unhighlight-cable',
  'select-all',
  'save'
])

function toggleFolderCables(folder) {
  const ids = collectFolderCableIds(folder)
  const allSelected = isFolderFullySelected(folder)
  ids.forEach(id => {
    const selected = props.selectedItems.cables?.includes(id)
    if (allSelected && selected) emit('toggle-item', id)
    else if (!allSelected && !selected) emit('toggle-item', id)
  })
}

function toggleNoFolderCables(cables) {
  const allSelected = isNoFolderFullySelected(cables)
  cables.forEach(c => {
    const selected = props.selectedItems.cables?.includes(c.id)
    if (allSelected && selected) emit('toggle-item', c.id)
    else if (!allSelected && !selected) emit('toggle-item', c.id)
  })
}

const getCategoryCount = (category) => {
  return props.availableItems[category]?.length || 0
}

const isItemSelected = (itemId) => {
  return props.selectedItems[props.activeCategory]?.includes(itemId)
}

const isSiteExpanded = (siteId) => {
  return props.expandedSites.has(siteId)
}

const isCameraSiteExpanded = (siteName) => {
  return props.expandedCameraSites.has(siteName)
}

const isSiteFullySelected = (siteId, devices) => {
  const deviceIds = devices.map(d => d.id)
  return deviceIds.length > 0 && deviceIds.every(id => props.selectedItems.devices.includes(id))
}

const isSitePartiallySelected = (siteId, devices) => {
  const deviceIds = devices.map(d => d.id)
  const selectedCount = deviceIds.filter(id => props.selectedItems.devices.includes(id)).length
  return selectedCount > 0 && selectedCount < deviceIds.length
}

const isCameraSiteFullySelected = (siteName, cameras) => {
  const cameraIds = cameras.map(c => c.id)
  return cameraIds.length > 0 && cameraIds.every(id => props.selectedItems.cameras.includes(id))
}

const isCameraSitePartiallySelected = (siteName, cameras) => {
  const cameraIds = cameras.map(c => c.id)
  const selectedCount = cameraIds.filter(id => props.selectedItems.cameras.includes(id)).length
  return selectedCount > 0 && selectedCount < cameraIds.length
}

const getSiteStatusSummary = (devices) => {
  const statusCount = {
    online: 0,
    warning: 0,
    critical: 0,
    offline: 0
  }
  
  devices.forEach(device => {
    if (statusCount.hasOwnProperty(device.status)) {
      statusCount[device.status]++
    }
  })
  
  return statusCount
}

const getCameraSiteStatusSummary = (cameras) => {
  const statusCount = {
    online: 0,
    offline: 0
  }
  
  cameras.forEach(camera => {
    const status = String(camera.status || 'offline').toLowerCase()
    if (status === 'online' || status === 'active' || status === 'streaming') {
      statusCount.online++
    } else {
      statusCount.offline++
    }
  })
  
  return statusCount
}

const getStatusLabel = (status) => {
  const statusStr = String(status || 'offline').toLowerCase()
  
  const labels = {
    'online': 'ONLINE',
    'warning': 'ATENÇÃO',
    'critical': 'CRÍTICO',
    'offline': 'OFFLINE',
    'unknown': 'DESCONHECIDO',
    '0': 'OFFLINE',
    'null': 'OFFLINE',
    'undefined': 'OFFLINE',
    'up': 'ONLINE',
    'down': 'OFFLINE',
    'degraded': 'ATENÇÃO',
    'operational': 'ONLINE',
    'unavailable': 'OFFLINE'
  }
  
  return labels[statusStr] || 'DESCONHECIDO'
}
</script>

<style scoped>
.inventory-panel {
  position: absolute;
  top: 0;
  right: 0;
  width: 400px;
  height: 100%;
  background: rgba(30, 33, 57, 0.95);
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(10px);
  z-index: 1000;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}

.panel-header {
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  color: #fff;
}

.btn-close-panel {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.6);
  font-size: 32px;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.panel-tabs {
  display: flex;
  padding: 16px 16px 0 16px;
  gap: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  overflow-x: auto;
}

.tab-btn {
  flex: 1;
  padding: 12px 8px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  transition: all 0.2s;
  white-space: nowrap;
}

.tab-btn.active {
  color: #10b981;
  border-bottom-color: #10b981;
}

.tab-btn i {
  font-size: 16px;
}

.badge {
  padding: 2px 8px;
  background: rgba(16, 185, 129, 0.2);
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;
}

.tab-btn.active .badge {
  background: rgba(16, 185, 129, 0.3);
}

.panel-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.search-box {
  margin: 16px;
  position: relative;
}

.search-box i {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: rgba(255, 255, 255, 0.4);
}

.search-box input {
  width: 100%;
  padding: 10px 12px 10px 40px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
}

.search-box input:focus {
  outline: none;
  border-color: rgba(16, 185, 129, 0.5);
}

.items-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 16px;
}

.site-group {
  margin-bottom: 4px;
}

.site-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  transition: all 0.2s;
}

.site-row:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(16, 185, 129, 0.3);
}

.btn-expand {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.btn-expand:hover {
  background: rgba(16, 185, 129, 0.2);
  border-color: rgba(16, 185, 129, 0.5);
  color: #10b981;
}

.btn-expand i {
  font-size: 10px;
}

.site-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  flex: 1;
  min-width: 0;
}

.site-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  flex-shrink: 0;
}

.site-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.site-name {
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.site-name i {
  color: #10b981;
  font-size: 12px;
  flex-shrink: 0;
}

.site-count {
  color: rgba(255, 255, 255, 0.5);
  font-size: 11px;
}

.site-status-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.status-dot {
  padding: 3px 7px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
}

.status-dot.online {
  background: rgba(16, 185, 129, 0.3);
  color: #10b981;
}

.status-dot.warning {
  background: rgba(245, 158, 11, 0.3);
  color: #f59e0b;
}

.status-dot.critical {
  background: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.status-dot.offline {
  background: rgba(107, 114, 128, 0.3);
  color: #9ca3af;
}

.devices-list {
  margin-top: 4px;
  padding-left: 32px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.device-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  transition: all 0.2s;
}

.device-row:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(16, 185, 129, 0.2);
}

.device-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  flex: 1;
  min-width: 0;
}

.device-checkbox input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  flex-shrink: 0;
}

.device-details {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}

.device-name {
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.device-ip {
  color: rgba(139, 92, 246, 0.8);
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.device-ip i {
  font-size: 9px;
}

.device-info {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

/* Transição de expand/collapse */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 1000px;
}

/* ── Folder rows ─────────────────────────────────────────────────────────── */
.folder-row {
  display: flex;
  align-items: center;
  padding: 7px 12px 7px 12px;
  gap: 4px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  transition: background 0.15s;
}

.folder-row:hover {
  background: rgba(255, 255, 255, 0.04);
}

.folder-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  flex: 1;
  min-width: 0;
}

.folder-checkbox input[type="checkbox"] {
  width: 15px;
  height: 15px;
  cursor: pointer;
  flex-shrink: 0;
}

.folder-details {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.folder-name {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.folder-count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
}

.item-row--indented {
  margin-bottom: 0;
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  background: rgba(0, 0, 0, 0.12);
}

.item-row--indented:hover {
  background: rgba(16, 185, 129, 0.06);
}

/* ── Cable item rows ─────────────────────────────────────────────────────── */
.item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  transition: all 0.2s;
}

.item-row:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(16, 185, 129, 0.3);
}

.item-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  flex: 1;
  min-width: 0;
}

.item-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  flex-shrink: 0;
}

.item-name {
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.status-badge.online {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.status-badge.warning {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.status-badge.critical {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.status-badge.offline {
  background: rgba(107, 114, 128, 0.2);
  color: #9ca3af;
}

.status-badge.unknown {
  background: rgba(107, 114, 128, 0.1);
  color: #9ca3af;
  font-style: italic;
}

.btn-focus {
  padding: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-focus:hover {
  background: rgba(16, 185, 129, 0.2);
  border-color: rgba(16, 185, 129, 0.5);
  color: #10b981;
}

.panel-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  gap: 12px;
}

.btn-panel {
  flex: 1;
  padding: 12px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-panel.btn-primary {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #fff;
}

.btn-panel.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);
}

.btn-panel.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
}

.btn-panel.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* ==========================================
   LIGHT THEME OVERRIDES
   ========================================== */
:root[data-theme="light"] .inventory-panel,
html:not(.dark)[data-theme="light"] .inventory-panel {
  background: rgba(255, 255, 255, 0.95);
  border-left: 1px solid rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .panel-header h3,
html:not(.dark)[data-theme="light"] .panel-header h3 {
  color: var(--text-primary);
}

:root[data-theme="light"] .btn-close-panel,
html:not(.dark)[data-theme="light"] .btn-close-panel {
  color: var(--text-tertiary);
}

:root[data-theme="light"] .tab-btn,
html:not(.dark)[data-theme="light"] .tab-btn {
  color: var(--text-secondary);
}

:root[data-theme="light"] .search-box input,
html:not(.dark)[data-theme="light"] .search-box input {
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.1);
  color: var(--text-primary);
}

:root[data-theme="light"] .site-row,
html:not(.dark)[data-theme="light"] .site-row,
:root[data-theme="light"] .device-row,
html:not(.dark)[data-theme="light"] .device-row,
:root[data-theme="light"] .item-row,
html:not(.dark)[data-theme="light"] .item-row {
  background: rgba(0, 0, 0, 0.02);
  border: 1px solid rgba(0, 0, 0, 0.05);
}

:root[data-theme="light"] .site-name,
html:not(.dark)[data-theme="light"] .site-name,
:root[data-theme="light"] .device-name,
html:not(.dark)[data-theme="light"] .device-name,
:root[data-theme="light"] .item-name,
html:not(.dark)[data-theme="light"] .item-name {
  color: var(--text-primary);
}

:root[data-theme="light"] .site-count,
html:not(.dark)[data-theme="light"] .site-count {
  color: var(--text-tertiary);
}

:root[data-theme="light"] .btn-panel.btn-secondary,
html:not(.dark)[data-theme="light"] .btn-panel.btn-secondary {
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.1);
  color: var(--text-tertiary);
}
</style>
