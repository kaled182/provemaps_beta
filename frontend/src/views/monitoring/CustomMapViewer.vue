<template>
  <div class="custom-map-viewer">
    <!-- Toolbar -->
    <div class="map-toolbar">
      <div class="toolbar-left">
        <button @click="$router.back()" class="btn-back">
          <i class="fas fa-arrow-left"></i>
          Voltar
        </button>
        <div class="map-title">
          <h2>{{ mapData.name }}</h2>
          <span class="map-category">{{ mapData.category }}</span>
        </div>
      </div>
      
      <div class="toolbar-right">
        <button @click="showInventoryPanel = !showInventoryPanel" class="btn-toolbar">
          <i class="fas fa-layer-group"></i>
          Gerenciar Itens
        </button>
        <button @click="toggleFullscreen" class="btn-toolbar">
          <i :class="isFullscreen ? 'fas fa-compress' : 'fas fa-expand'"></i>
        </button>
      </div>
    </div>

    <!-- Main Content -->
    <div class="map-content">
      <!-- Mapa Google Maps -->
      <div ref="mapContainer" class="map-container"></div>

      <!-- Painel Lateral: Gerenciar Itens -->
      <transition name="slide">
        <div v-if="showInventoryPanel" class="inventory-panel">
          <div class="panel-header">
            <h3>Itens do Mapa</h3>
            <button @click="showInventoryPanel = false" class="btn-close-panel">×</button>
          </div>

          <div class="panel-tabs">
            <button 
              v-for="category in inventoryCategories" 
              :key="category.key"
              @click="activeCategory = category.key"
              :class="['tab-btn', { active: activeCategory === category.key }]"
            >
              <i :class="category.icon"></i>
              {{ category.label }}
              <span class="badge">{{ getAvailableCount(category.key) }}</span>
            </button>
          </div>

          <div class="panel-content">
            <div class="search-box">
              <i class="fas fa-search"></i>
              <input 
                v-model="searchQuery" 
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
                      @click="toggleSiteExpansion(siteGroup.site_id)" 
                      class="btn-expand"
                      :title="isSiteExpanded(siteGroup.site_id) ? 'Colapsar' : 'Expandir'"
                    >
                      <i :class="isSiteExpanded(siteGroup.site_id) ? 'fas fa-chevron-down' : 'fas fa-chevron-right'"></i>
                    </button>
                    
                    <label class="site-checkbox">
                      <input 
                        type="checkbox" 
                        :checked="isSiteSelected(siteGroup.site_id, siteGroup.devices)"
                        :indeterminate.prop="isSitePartiallySelected(siteGroup.site_id, siteGroup.devices)"
                        @change="toggleSite(siteGroup.site_id, siteGroup.devices)"
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
                            @change="toggleItem(device.id)"
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
                          <button @click="focusOnItem(device)" class="btn-focus">
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
                      @click="toggleCameraSiteExpansion(siteGroup.site_name)" 
                      class="btn-expand"
                      :title="isCameraSiteExpanded(siteGroup.site_name) ? 'Colapsar' : 'Expandir'"
                    >
                      <i :class="isCameraSiteExpanded(siteGroup.site_name) ? 'fas fa-chevron-down' : 'fas fa-chevron-right'"></i>
                    </button>
                    
                    <label class="site-checkbox">
                      <input 
                        type="checkbox" 
                        :checked="isCameraSiteSelected(siteGroup.site_name, siteGroup.cameras)"
                        :indeterminate.prop="isCameraSitePartiallySelected(siteGroup.site_name, siteGroup.cameras)"
                        @change="toggleCameraSite(siteGroup.site_name, siteGroup.cameras)"
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
                            @change="toggleItem(camera.id)"
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
                          <button @click="focusOnItem(camera)" class="btn-focus">
                            <i class="fas fa-crosshairs"></i>
                          </button>
                        </div>
                      </div>
                    </div>
                  </transition>
                </div>
              </template>
              
              <!-- Lista simples para outras categorias (cabos, racks) -->
              <template v-else>
                <div 
                  v-for="item in filteredItems" 
                  :key="item.id"
                  class="item-row"
                  @mouseenter="highlightCable(item.id)"
                  @mouseleave="unhighlightCable(item.id)"
                >
                  <label class="item-checkbox">
                    <input 
                      type="checkbox" 
                      :checked="isItemSelected(item.id)"
                      @change="toggleItem(item.id)"
                    >
                    <span class="item-name">{{ item.name }}</span>
                  </label>
                  <div class="item-info">
                    <span v-if="item.status" :class="['status-badge', item.status]">
                      {{ getStatusLabel(item.status) }}
                    </span>
                    <button @click="focusOnItem(item)" class="btn-focus">
                      <i class="fas fa-crosshairs"></i>
                    </button>
                  </div>
                </div>
              </template>
            </div>

            <div class="panel-footer">
              <button @click="selectAll" class="btn-panel btn-secondary">
                Selecionar Todos
              </button>
              <button @click="saveMapItems" class="btn-panel btn-primary">
                Salvar
              </button>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- Legend -->
    <div class="map-legend">
      <div class="legend-item" v-for="status in statusLegend" :key="status.key">
        <span :class="['legend-marker', status.key]"></span>
        <span class="legend-label">{{ status.label }}</span>
      </div>
    </div>

    <!-- Site Details Modal -->
    <SiteDetailsModal 
      :is-open="showSiteModal" 
      :site="selectedSite"
      @close="showSiteModal = false"
    />

    <!-- Fiber Cable Quick Modal -->
    <FiberCableQuickModal
      :show="showCableModal"
      :cable="selectedCable"
      @close="showCableModal = false"
      @openFullDetails="openCableFullDetails"
    />

    <!-- Fiber Cable Detail Modal -->
    <FiberCableDetailModal
      :show="showCableDetailModal"
      :cable="selectedCable"
      :can-edit="true"
      @close="showCableDetailModal = false"
      @save="handleCableSave"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useSystemConfig } from '@/composables/useSystemConfig'
import { loadGoogleMaps } from '@/utils/googleMapsLoader'
import { getMapStyles } from '@/utils/mapStyles'
import { useUiStore } from '@/stores/ui'
// ✅ LAZY LOADING: Bibliotecas de mapas carregadas sob demanda
import { loadMapbox } from '@/composables/map/providers/useMapbox'
import { loadLeaflet } from '@/composables/map/providers/useLeaflet'
import { loadMarkerClusterer } from '@/composables/map/providers/useMarkerClusterer'
import { runMapboxStyleDiagnostics, MAPBOX_STYLE_DIAGNOSTICS_DEFAULTS } from '@/utils/mapboxDiagnostics'
import SiteDetailsModal from '@/components/SiteDetailsModal.vue'
import FiberCableQuickModal from '@/components/FiberCableQuickModal.vue'
import FiberCableDetailModal from '@/components/FiberCableDetailModal.vue'

// Variáveis para bibliotecas lazy loaded
let mapboxgl = null
let L = null
let MarkerClusterer = null

const route = useRoute()
const { get, post } = useApi()
const { configForm, loadSystemConfig } = useSystemConfig()
const uiStore = useUiStore()

const mapContainer = ref(null)
const googleMap = ref(null)
const currentMapProvider = ref('google') // Armazena o provedor ativo
// Usar Maps para diffing eficiente - rastrea markers e polylines por ID
const activeMarkers = new Map() // { deviceId: markerInstance }
const activePolylines = new Map() // { cableId: polylineInstance }
const markerClusterer = ref(null) // Clusterer para agrupar markers próximos
const showInventoryPanel = ref(false)
const activeCategory = ref('devices')
const searchQuery = ref('')
const isFullscreen = ref(false)
const isInitialLoad = ref(true) // Flag para controlar animação inicial

let detachZoomListener = null

const DEFAULT_ZOOM_FALLBACK = 12
const MAPBOX_MARKER_SIZE_RULES = {
  minZoom: 5,
  maxZoom: 16,
  minSize: 10,
  maxSize: 18,
  minBorder: 2,
  maxBorder: 3
}

const clampNumber = (value, min, max) => Math.min(max, Math.max(min, value))

const getActiveMapZoom = () => {
  if (!googleMap.value || typeof googleMap.value.getZoom !== 'function') {
    return DEFAULT_ZOOM_FALLBACK
  }
  const zoom = googleMap.value.getZoom()
  return Number.isFinite(zoom) ? zoom : DEFAULT_ZOOM_FALLBACK
}

const computeMapboxMarkerDimensions = (zoom) => {
  const clampedZoom = clampNumber(
    zoom,
    MAPBOX_MARKER_SIZE_RULES.minZoom,
    MAPBOX_MARKER_SIZE_RULES.maxZoom
  )
  const zoomSpan = Math.max(
    1,
    MAPBOX_MARKER_SIZE_RULES.maxZoom - MAPBOX_MARKER_SIZE_RULES.minZoom
  )
  const ratio = (clampedZoom - MAPBOX_MARKER_SIZE_RULES.minZoom) / zoomSpan
  const size =
    MAPBOX_MARKER_SIZE_RULES.minSize +
    (MAPBOX_MARKER_SIZE_RULES.maxSize - MAPBOX_MARKER_SIZE_RULES.minSize) * ratio
  const border =
    MAPBOX_MARKER_SIZE_RULES.minBorder +
    (MAPBOX_MARKER_SIZE_RULES.maxBorder - MAPBOX_MARKER_SIZE_RULES.minBorder) * ratio

  return {
    size: Math.round(size),
    border: Math.max(1, Math.round(border))
  }
}

const applyMapboxMarkerDimensions = (marker, zoom) => {
  const element = typeof marker?.getElement === 'function' ? marker.getElement() : null
  if (!element) {
    return
  }
  const { size, border } = computeMapboxMarkerDimensions(zoom)
  element.style.width = `${size}px`
  element.style.height = `${size}px`
  element.style.borderWidth = `${border}px`
}

const updateMapboxMarkerSizes = () => {
  if (currentMapProvider.value !== 'mapbox' || activeMarkers.size === 0) {
    return
  }
  const zoom = getActiveMapZoom()
  activeMarkers.forEach((marker) => {
    if (typeof marker?._applySize === 'function') {
      marker._applySize(zoom)
    } else {
      applyMapboxMarkerDimensions(marker, zoom)
    }
  })
}

const resetZoomListener = () => {
  if (typeof detachZoomListener === 'function') {
    try {
      detachZoomListener()
    } catch (error) {
      console.warn('[CustomMapViewer] Falha ao remover listener de zoom:', error)
    }
  }
  detachZoomListener = null
}

const registerMapboxZoomListener = () => {
  resetZoomListener()
  if (!googleMap.value || typeof googleMap.value.on !== 'function') {
    return
  }
  const mapInstance = googleMap.value
  const handler = () => updateMapboxMarkerSizes()
  mapInstance.on('zoom', handler)
  detachZoomListener = () => {
    if (mapInstance && typeof mapInstance.off === 'function') {
      mapInstance.off('zoom', handler)
    }
  }
}

// Modal de detalhes do site
const showSiteModal = ref(false)
const selectedSite = ref(null)

// Modal de detalhes do cabo
const showCableModal = ref(false)
const showCableDetailModal = ref(false)
const selectedCable = ref(null)

// Mapa de sites para lookup correto no click do marker
const sitesMap = ref(new Map())

const mapData = ref({
  id: null,
  name: 'Carregando...',
  category: 'backbone',
  description: ''
})

const selectedItems = ref({
  devices: [],
  cables: [],
  cameras: [],
  racks: []
})

const expandedSites = ref(new Set())
const selectedSites = ref(new Set())
const expandedCameraSites = ref(new Set())
const selectedCameraSites = ref(new Set())

const inventoryCategories = [
  { key: 'devices', label: 'Equipamentos', icon: 'fas fa-server' },
  { key: 'cables', label: 'Cabos', icon: 'fas fa-network-wired' },
  { key: 'cameras', label: 'Câmeras', icon: 'fas fa-video' },
  { key: 'racks', label: 'Racks', icon: 'fas fa-database' }
]

const statusLegend = [
  { key: 'online', label: 'Online' },
  { key: 'warning', label: 'Atenção' },
  { key: 'critical', label: 'Crítico' },
  { key: 'offline', label: 'Offline' }
]

const availableItems = ref({
  devices: [],
  cables: [],
  cameras: [],
  racks: []
})

const filteredItems = computed(() => {
  const items = availableItems.value[activeCategory.value] || []
  if (!searchQuery.value) return items
  
  const query = searchQuery.value.toLowerCase()
  return items.filter(item => 
    item.name.toLowerCase().includes(query) ||
    (item.description && item.description.toLowerCase().includes(query))
  )
})

const devicesBySite = computed(() => {
  if (activeCategory.value !== 'devices') return []
  
  const devices = filteredItems.value
  const siteMap = new Map()
  
  devices.forEach(device => {
    const siteKey = device.site_id
    if (!siteMap.has(siteKey)) {
      siteMap.set(siteKey, {
        site_id: siteKey,
        site_name: device.site_name,
        devices: []
      })
    }
    siteMap.get(siteKey).devices.push(device)
  })
  
  return Array.from(siteMap.values()).sort((a, b) => 
    a.site_name.localeCompare(b.site_name)
  )
})

const camerasBySite = computed(() => {
  if (activeCategory.value !== 'cameras') return []
  
  const cameras = filteredItems.value
  const siteMap = new Map()
  
  cameras.forEach(camera => {
    const siteName = camera.site_name || 'Sem Site'
    if (!siteMap.has(siteName)) {
      siteMap.set(siteName, {
        site_name: siteName,
        cameras: []
      })
    }
    siteMap.get(siteName).cameras.push(camera)
  })
  
  return Array.from(siteMap.values()).sort((a, b) => 
    a.site_name.localeCompare(b.site_name)
  )
})

const getSelectedCount = (category) => {
  return selectedItems.value[category]?.length || 0
}

const getAvailableCount = (category) => {
  return availableItems.value[category]?.length || 0
}

const isItemSelected = (itemId) => {
  return selectedItems.value[activeCategory.value]?.includes(itemId)
}

const getStatusLabel = (status) => {
  // Garantir que status seja uma string
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
    // Aliases para status de cabos
    'up': 'ONLINE',
    'down': 'OFFLINE',
    'degraded': 'ATENÇÃO',
    'operational': 'ONLINE',
    'unavailable': 'OFFLINE'
  }
  
  return labels[statusStr] || 'DESCONHECIDO'
}

const toggleSiteExpansion = (siteId) => {
  if (expandedSites.value.has(siteId)) {
    expandedSites.value.delete(siteId)
  } else {
    expandedSites.value.add(siteId)
  }
}

const isSiteExpanded = (siteId) => {
  return expandedSites.value.has(siteId)
}

const toggleSite = (siteId, devices) => {
  const deviceIds = devices.map(d => d.id)
  const allSelected = deviceIds.every(id => selectedItems.value.devices.includes(id))
  
  console.log(`[toggleSite] Site ${siteId}, deviceIds:`, deviceIds)
  console.log(`[toggleSite] allSelected:`, allSelected)
  console.log(`[toggleSite] selectedItems.devices ANTES:`, selectedItems.value.devices)
  
  if (allSelected) {
    // Desmarcar todos os devices do site
    selectedItems.value.devices = selectedItems.value.devices.filter(
      id => !deviceIds.includes(id)
    )
    selectedSites.value.delete(siteId)
    console.log(`[toggleSite] DESMARCANDO site ${siteId}`)
  } else {
    // Marcar todos os devices do site
    deviceIds.forEach(id => {
      if (!selectedItems.value.devices.includes(id)) {
        selectedItems.value.devices.push(id)
      }
    })
    selectedSites.value.add(siteId)
    console.log(`[toggleSite] MARCANDO site ${siteId}`)
  }
  
  console.log(`[toggleSite] selectedItems.devices DEPOIS:`, selectedItems.value.devices)
  updateMap()
}

const isSiteSelected = (siteId, devices) => {
  const deviceIds = devices.map(d => d.id)
  return deviceIds.length > 0 && deviceIds.every(id => selectedItems.value.devices.includes(id))
}

const isSitePartiallySelected = (siteId, devices) => {
  const deviceIds = devices.map(d => d.id)
  const selectedCount = deviceIds.filter(id => selectedItems.value.devices.includes(id)).length
  return selectedCount > 0 && selectedCount < deviceIds.length
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

// Funções específicas para câmeras
const toggleCameraSiteExpansion = (siteName) => {
  if (expandedCameraSites.value.has(siteName)) {
    expandedCameraSites.value.delete(siteName)
  } else {
    expandedCameraSites.value.add(siteName)
  }
}

const isCameraSiteExpanded = (siteName) => {
  return expandedCameraSites.value.has(siteName)
}

const toggleCameraSite = (siteName, cameras) => {
  const cameraIds = cameras.map(c => c.id)
  const allSelected = cameraIds.every(id => selectedItems.value.cameras.includes(id))
  
  if (allSelected) {
    selectedItems.value.cameras = selectedItems.value.cameras.filter(
      id => !cameraIds.includes(id)
    )
    selectedCameraSites.value.delete(siteName)
  } else {
    cameraIds.forEach(id => {
      if (!selectedItems.value.cameras.includes(id)) {
        selectedItems.value.cameras.push(id)
      }
    })
    selectedCameraSites.value.add(siteName)
  }
  
  updateMap()
}

const isCameraSiteSelected = (siteName, cameras) => {
  const cameraIds = cameras.map(c => c.id)
  return cameraIds.length > 0 && cameraIds.every(id => selectedItems.value.cameras.includes(id))
}

const isCameraSitePartiallySelected = (siteName, cameras) => {
  const cameraIds = cameras.map(c => c.id)
  const selectedCount = cameraIds.filter(id => selectedItems.value.cameras.includes(id)).length
  return selectedCount > 0 && selectedCount < cameraIds.length
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

// Função unificada para atualizar todo o mapa (markers + polylines)
const updateMap = (animateItemId = null) => {
  if (!googleMap.value) {
    console.warn('[CustomMapViewer] Google Map não inicializado ainda')
    return
  }
  
  console.log('[CustomMapViewer] updateMap chamado - usando diffing incremental')
  // Atualizar incrementalmente (adiciona novos, remove antigos, atualiza existentes)
  updateMapMarkers(animateItemId)
  updateCablePolylines()
}

const toggleItem = (itemId) => {
  const category = activeCategory.value
  const index = selectedItems.value[category].indexOf(itemId)
  
  if (index > -1) {
    // Desmarcar - sem animação
    selectedItems.value[category].splice(index, 1)
    console.log(`[CustomMapViewer] Item ${itemId} desmarcado da categoria ${category}`)
    updateMap() // Atualizar sem animação
  } else {
    // Marcar - com animação apenas deste item
    selectedItems.value[category].push(itemId)
    console.log(`[CustomMapViewer] Item ${itemId} marcado na categoria ${category}`)
    
    // Se for device, animar apenas este
    if (category === 'devices') {
      updateMap(itemId)
    } else {
      updateMap()
    }
  }
}

const selectAll = () => {
  const category = activeCategory.value
  const allIds = availableItems.value[category].map(item => item.id)
  selectedItems.value[category] = [...allIds]
  console.log(`[CustomMapViewer] Todos os ${allIds.length} items selecionados na categoria ${category}`)
  
  // Atualizar todo o mapa
  updateMap()
}

// Função para limpar TODAS as overlays - versão otimizada com Maps
const clearAllOverlays = () => {
  console.log('[CustomMapViewer] Limpando todas as overlays')
  console.log('[CustomMapViewer] Total markers:', activeMarkers.size)
  console.log('[CustomMapViewer] Total polylines:', activePolylines.size)
  
  // Limpar clusterer primeiro
  if (markerClusterer.value) {
    markerClusterer.value.clearMarkers()
    markerClusterer.value = null
  }
  
  // Limpar todos os markers
  activeMarkers.forEach((marker, id) => {
    try {
      clearMarkerListeners(marker)
      if (typeof marker.setMap === 'function') {
        marker.setMap(null)
      } else if (typeof marker.remove === 'function') {
        marker.remove()
      }
    } catch (e) {
      console.error(`[CustomMapViewer] Erro ao remover marker ${id}:`, e)
    }
  })
  activeMarkers.clear()
  
  // Limpar todas as polylines
  activePolylines.forEach((polyline, id) => {
    try {
      clearPolylineListeners(polyline)
      if (typeof polyline.setMap === 'function') {
        polyline.setMap(null)
      } else if (currentMapProvider.value === 'mapbox') {
        if (polyline.layerId && googleMap.value.getLayer(polyline.layerId)) {
          googleMap.value.removeLayer(polyline.layerId)
        }
        if (polyline.sourceId && googleMap.value.getSource(polyline.sourceId)) {
          googleMap.value.removeSource(polyline.sourceId)
        }
      } else if (currentMapProvider.value === 'osm' && typeof polyline.remove === 'function') {
        polyline.remove()
      }
    } catch (e) {
      console.error(`[CustomMapViewer] Erro ao remover polyline ${id}:`, e)
    }
  })
  activePolylines.clear()
  
  console.log('[CustomMapViewer] Todas as overlays removidas')
}

const focusOnItem = (item) => {
  if (!googleMap.value) return
  
  // Para devices e cameras que têm lat/lng diretamente
  if (item.lat && item.lng) {
    googleMap.value.setCenter({ lat: parseFloat(item.lat), lng: parseFloat(item.lng) })
    googleMap.value.setZoom(15)
    return
  }
  
  // Para cabos que têm path_coordinates
  if (item.path_coordinates && item.path_coordinates.length > 0) {
    // Centralizar no ponto médio do cabo
    const midIndex = Math.floor(item.path_coordinates.length / 2)
    const midPoint = item.path_coordinates[midIndex]
    
    if (midPoint && midPoint.lat && midPoint.lng) {
      googleMap.value.setCenter({ 
        lat: parseFloat(midPoint.lat), 
        lng: parseFloat(midPoint.lng) 
      })
      googleMap.value.setZoom(13) // Zoom menor para ver mais da rota
    }
  }
}

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
  document.querySelector('.custom-map-viewer').classList.toggle('fullscreen')
}

const loadMapData = async () => {
  try {
    const mapId = route.params.mapId
    console.log('[CustomMapViewer] Carregando mapa ID:', mapId)
    
    if (mapId === 'default') {
      // Mapa padrão: carregar tudo
      mapData.value = {
        id: 'default',
        name: 'Mapa Completo',
        category: route.params.category || 'backbone',
        description: 'Visualização completa de todos os equipamentos'
      }
      console.log('[CustomMapViewer] Mapa padrão configurado')
    } else {
      // Carregar mapa customizado
      const response = await fetch(`/inventory/api/v1/maps/custom/${mapId}/`, {
        credentials: 'include'
      })
      
      if (!response.ok) {
        throw new Error(`Erro ao carregar mapa: ${response.status}`)
      }
      
      const data = await response.json()
      mapData.value = data.map
      selectedItems.value = data.selected_items || selectedItems.value
      console.log('[CustomMapViewer] Mapa customizado carregado:', mapData.value.name)
    }
  } catch (error) {
    console.error('[CustomMapViewer] Erro ao carregar mapa:', error)
    // Fallback para mapa padrão
    mapData.value = {
      id: 'default',
      name: 'Mapa Completo',
      category: route.params.category || 'backbone',
      description: 'Visualização completa de todos os equipamentos'
    }
  }
}

const loadInventoryItems = async () => {
  try {
    console.log('[CustomMapViewer] Iniciando carregamento do inventário...')
    
    // 1. Carregar Sites para obter lat/lng
    const sitesResponse = await fetch('/api/v1/sites/?page_size=500', {
      credentials: 'include'
    })
    
    if (!sitesResponse.ok) {
      throw new Error(`Erro ao carregar sites: ${sitesResponse.status}`)
    }
    
    const sitesData = await sitesResponse.json()
    const sites = Array.isArray(sitesData) ? sitesData : (sitesData.results || [])
    console.log(`[CustomMapViewer] ${sites.length} sites carregados`)
    
    // Criar mapa de sites por ID para lookup de coordenadas
    // Usar a ref global em vez de variável local
    sitesMap.value.clear()
    sites.forEach(site => {
      if (site.id) {
        sitesMap.value.set(String(site.id), site)
      }
    })
    
    console.log('═══════════════════════════════════════════════════════')
    console.log('🗺️  SITES NO MAPA:')
    console.log('═══════════════════════════════════════════════════════')
    console.log(`Total de sites no mapa: ${sitesMap.value.size}`)
    console.log('IDs dos sites:', Array.from(sitesMap.value.keys()))
    console.log('═══════════════════════════════════════════════════════')
    
    // 2. Carregar devices (equipamentos)
    const devicesResponse = await fetch('/api/v1/devices/?page_size=1000', {
      credentials: 'include'
    })
    
    if (!devicesResponse.ok) {
      throw new Error(`Erro ao carregar devices: ${devicesResponse.status}`)
    }
    
    const devicesData = await devicesResponse.json()
    const devices = Array.isArray(devicesData) ? devicesData : (devicesData.results || [])
    console.log(`[CustomMapViewer] ${devices.length} devices carregados`)
    
    // DEBUG: Verificar estrutura do primeiro device
    if (devices.length > 0) {
      console.log('═══════════════════════════════════════════════════════')
      console.log('🔍 ESTRUTURA DO PRIMEIRO DEVICE:')
      console.log('═══════════════════════════════════════════════════════')
      const firstDevice = devices[0]
      console.log('Objeto completo:', firstDevice)
      console.log('Campos disponíveis:', Object.keys(firstDevice))
      console.log('  - site:', firstDevice.site)
      console.log('  - site_id:', firstDevice.site_id)
      console.log('  - site_name:', firstDevice.site_name)
      console.log('═══════════════════════════════════════════════════════')
    }
    
    // 3. Carregar status do Zabbix para cada device
    const hostsResponse = await fetch('/maps_view/api/dashboard/data/', {
      credentials: 'include'
    })
    
    if (!hostsResponse.ok) {
      throw new Error(`Erro ao carregar hosts: ${hostsResponse.status}`)
    }
    
    const hostsData = await hostsResponse.json()
    const hostsArray = hostsData.hosts_status || hostsData.hosts || []
    console.log(`[CustomMapViewer] ${hostsArray.length} hosts do Zabbix carregados`)
    
    // DEBUG: Estrutura completa do primeiro host
    if (hostsArray.length > 0) {
      console.log('═══════════════════════════════════════════════════════')
      console.log('🔍 ESTRUTURA DO PRIMEIRO HOST DO ZABBIX:')
      console.log('═══════════════════════════════════════════════════════')
      const firstHost = hostsArray[0]
      console.log('Objeto completo:', firstHost)
      console.log('Campos disponíveis:', Object.keys(firstHost))
      console.log('  - id:', firstHost.id)
      console.log('  - device_id:', firstHost.device_id)
      console.log('  - name:', firstHost.name)
      console.log('  - display_name:', firstHost.display_name)
      console.log('  - zabbix_hostid:', firstHost.zabbix_hostid)
      console.log('  - availability:', firstHost.availability)
      console.log('  - status:', firstHost.status)
      console.log('═══════════════════════════════════════════════════════')
    } else {
      console.error('❌ NENHUM HOST RETORNADO PELO DASHBOARD!')
      console.log('Resposta completa do dashboard:', hostsData)
    }
    
    // DEBUG: Expor dados globalmente para inspeção
    window.debugCustomMap = window.debugCustomMap || {}
    window.debugCustomMap.hostsFromZabbix = hostsArray
    window.debugCustomMap.devicesFromInventory = devices
    
    console.log('═══════════════════════════════════════════════════════')
    console.log('DEBUG: Digite no console para inspecionar:')
    console.log('  window.debugCustomMap.hostsFromZabbix')
    console.log('  window.debugCustomMap.devicesFromInventory')
    console.log('  window.debugCustomMap.statusMap')
    console.log('═══════════════════════════════════════════════════════')
    
    if (hostsArray.length > 0) {
      console.log('Exemplo de HOST do Zabbix:', hostsArray[0])
    }
    
    if (devices.length > 0) {
      console.log('Exemplo de DEVICE do inventário:', devices[0])
    }
    
    // Criar mapa de status por device_id, name e zabbix_hostid
    const statusMap = new Map()
    hostsArray.forEach((host, index) => {
      // Converter availability do Zabbix para nosso formato de status
      // availability: "1" = Available (online), "2" = Unavailable (offline), "0" = Unknown
      const availability = String(host.availability || host.available || '0')
      let mappedStatus = 'offline'
      
      if (availability === '1') {
        mappedStatus = 'online'
      } else if (availability === '2') {
        mappedStatus = 'offline'
      } else {
        mappedStatus = 'unknown'
      }
      
      // Mapear por ID (tentar device_id primeiro, depois id)
      const deviceId = host.device_id || host.id
      if (deviceId) {
        statusMap.set(String(deviceId), mappedStatus)
      }
      
      // Mapear por nome (normalizado)
      if (host.name) {
        statusMap.set(String(host.name).toLowerCase(), mappedStatus)
      }
      if (host.display_name) {
        statusMap.set(String(host.display_name).toLowerCase(), mappedStatus)
      }
      
      // Mapear por zabbix_hostid ou hostid
      const zabbixId = host.zabbix_hostid || host.hostid
      if (zabbixId) {
        statusMap.set(`zabbix_${zabbixId}`, mappedStatus)
      }
      
      // Log do mapeamento (apenas primeiros 3)
      if (index < 3) {
        console.log(`  Host #${index + 1}: "${host.name}" → device_id=${deviceId}, availability=${availability} → status="${mappedStatus}"`)
      }
    })
    
    console.log(`[CustomMapViewer] StatusMap: ${statusMap.size} entradas criadas`)
    
    // DEBUG: Expor statusMap globalmente
    window.debugCustomMap.statusMap = statusMap
    window.debugCustomMap.statusMapArray = Array.from(statusMap.entries())
    
    console.log('Primeiras 5 entradas do StatusMap:')
    Array.from(statusMap.entries()).slice(0, 5).forEach(([key, value]) => {
      console.log(`  "${key}" => "${value}"`)
    })
    
    // 4. Processar devices individuais com localização do site
    const devicesWithLocation = []
    
    devices.forEach((device, index) => {
      if (!device) return
      
      // DEBUG para primeiro device
      if (index === 0) {
        console.log('═══════════════════════════════════════════════════════')
        console.log('🔍 DEBUG - LOOKUP DE SITE:')
        console.log('═══════════════════════════════════════════════════════')
        console.log(`Device: ${device.name}`)
        console.log(`  device.site: "${device.site}" (tipo: ${typeof device.site})`)
        console.log(`  String(device.site): "${String(device.site)}"`)
        console.log(`  sitesMap tem chave "${String(device.site)}"? ${sitesMap.value.has(String(device.site))}`)
        console.log(`  Chaves no sitesMap:`, Array.from(sitesMap.value.keys()))
        console.log('═══════════════════════════════════════════════════════')
      }
      
      // Pegar coordenadas do site usando a ref global
      const site = sitesMap.value.get(String(device.site))
      if (!site) {
        console.warn(`[CustomMapViewer] Site ${device.site} não encontrado para device ${device.name}`)
        return
      }
      
      const lat = parseFloat(site.latitude)
      const lng = parseFloat(site.longitude)
      
      // Só adicionar se tiver coordenadas válidas
      if (isNaN(lat) || isNaN(lng)) return
      
      // Pegar status do Zabbix para este device específico (tentar várias estratégias)
      let status = null
      
      // Estratégia 1: Por device.id
      status = statusMap.get(String(device.id))
      
      // Estratégia 2: Por device.name (normalizado)
      if (!status && device.name) {
        status = statusMap.get(String(device.name).toLowerCase())
      }
      
      // Estratégia 3: Por zabbix_hostid
      if (!status && device.zabbix_hostid) {
        status = statusMap.get(`zabbix_${device.zabbix_hostid}`)
      }
      
      // Garantir que status seja uma string válida
      if (!status || status === 'unknown') {
        status = 'offline'
      }
      
      // Log de debug para primeiro device
      if (index === 0) {
        console.log(`[CustomMapViewer] DEBUG - Primeiro device:`)
        console.log(`  - ID: ${device.id}`)
        console.log(`  - Name: ${device.name}`)
        console.log(`  - Zabbix ID: ${device.zabbix_hostid}`)
        console.log(`  - Status encontrado: "${status}"`)
        console.log(`  - StatusMap tem entrada para ID? ${statusMap.has(String(device.id))}`)
        console.log(`  - StatusMap tem entrada para name? ${statusMap.has(String(device.name).toLowerCase())}`)
        if (device.zabbix_hostid) {
          console.log(`  - StatusMap tem entrada para zabbix_${device.zabbix_hostid}? ${statusMap.has(`zabbix_${device.zabbix_hostid}`)}`)
        }
      }
      
      devicesWithLocation.push({
        id: device.id,
        name: device.name || `Device ${device.id}`,
        type: device.device_type || 'device',
        lat: lat,
        lng: lng,
        status: status,
        ip: device.primary_ip4 || device.ip_address || 'N/A',
        location: site.city || site.location || 'N/A',
        site: device.site,        // ✅ Manter campo 'site' para lookup do sitesMap
        site_id: device.site,     // ✅ Manter site_id também para compatibilidade
        site_name: site.name || site.display_name,
        device_type: device.device_type,
        serial_number: device.serial_number
      })
    })
    
    availableItems.value.devices = devicesWithLocation
    console.log(`[CustomMapViewer] ${devicesWithLocation.length} devices com localização processados`)
    
    // DEBUG: Resumo de status
    console.log('═══════════════════════════════════════════════════════')
    console.log('📊 RESUMO DE STATUS DOS DEVICES:')
    console.log('═══════════════════════════════════════════════════════')
    const statusSummary = devicesWithLocation.reduce((acc, device) => {
      acc[device.status] = (acc[device.status] || 0) + 1
      return acc
    }, {})
    console.log('Distribuição de status:', statusSummary)
    console.log('Total devices:', devicesWithLocation.length)
    console.log('Total hosts do Zabbix:', hostsArray.length)
    console.log('StatusMap size:', statusMap.size)
    console.log('═══════════════════════════════════════════════════════')
    
    // 5. Carregar cabos de fibra com rotas
    try {
      const cablesResponse = await fetch('/api/v1/fiber-cables/', {
        credentials: 'include'
      })
      
      if (cablesResponse.ok) {
        const cablesData = await cablesResponse.json()
        const cables = Array.isArray(cablesData) ? cablesData : (cablesData.results || [])
        
        console.log('[CustomMapViewer] Raw cables data:', cables.slice(0, 2))
        
        // Mapear status dos cabos de fibra
        availableItems.value.cables = cables.map(cable => {
          const pathCoords = cable.path_coordinates || []
          
          // Normalizar status do cabo para formato UI
          // Backend retorna: "up", "down", "degraded", "unknown"
          // UI usa: "online", "offline", "warning", "critical", "unknown"
          let uiStatus = 'unknown'
          const backendStatus = (cable.status || 'unknown').toLowerCase()
          
          switch (backendStatus) {
            case 'up':
            case 'operational':
              uiStatus = 'online'
              break
            case 'down':
            case 'unavailable':
              uiStatus = 'offline'
              break
            case 'degraded':
            case 'warning':
              uiStatus = 'warning'
              break
            case 'critical':
              uiStatus = 'critical'
              break
            default:
              uiStatus = 'unknown'
          }
          
          return {
            id: cable.id,
            name: cable.name,
            status: uiStatus,
            original_status: cable.status,
            description: cable.description || '',
            path_coordinates: pathCoords,
            site_a_name: cable.site_a_name,
            site_b_name: cable.site_b_name,
            length_km: cable.length_km,
            is_connected: cable.is_connected,
            connection_status: cable.connection_status
          }
        })
        
        // DEBUG: Resumo de status dos cabos
        console.log('═══════════════════════════════════════════════════════')
        console.log('📡 RESUMO DE STATUS DOS CABOS:')
        console.log('═══════════════════════════════════════════════════════')
        const cableStatusSummary = availableItems.value.cables.reduce((acc, cable) => {
          acc[cable.status] = (acc[cable.status] || 0) + 1
          return acc
        }, {})
        console.log('Distribuição de status:', cableStatusSummary)
        console.log('Total cabos:', availableItems.value.cables.length)
        if (availableItems.value.cables.length > 0) {
          console.log('Exemplo do primeiro cabo:', availableItems.value.cables[0])
        }
        console.log('═══════════════════════════════════════════════════════')
        
        console.log(`[CustomMapViewer] ${availableItems.value.cables.length} cabos carregados`)
      }
    } catch (error) {
      console.warn('[CustomMapViewer] Erro ao carregar cabos:', error)
      availableItems.value.cables = []
    }
    
    // 6. Carregar câmeras
    try {
      const camerasResponse = await fetch('/api/v1/cameras/', {
        credentials: 'include'
      })
      
      if (camerasResponse.ok) {
        const camerasData = await camerasResponse.json()
        const cameras = Array.isArray(camerasData) ? camerasData : (camerasData.results || [])
        
        availableItems.value.cameras = cameras.map(camera => ({
          id: camera.id,
          name: camera.display_name || camera.name || `Câmera ${camera.id}`,
          status: camera.status || camera.stream_status || 'offline',
          description: camera.description || '',
          site_name: camera.site_name,
          lat: camera.latitude || null,
          lng: camera.longitude || null
        }))
        
        console.log(`[CustomMapViewer] ${availableItems.value.cameras.length} câmeras carregadas`)
      }
    } catch (error) {
      console.warn('[CustomMapViewer] Erro ao carregar câmeras:', error)
      availableItems.value.cameras = []
    }
    
    // 7. Racks (placeholder por enquanto)
    availableItems.value.racks = []
    
    console.log('[CustomMapViewer] Inventário completo:', {
      devices: availableItems.value.devices.length,
      cables: availableItems.value.cables.length,
      cameras: availableItems.value.cameras.length,
      racks: availableItems.value.racks.length
    })
  } catch (error) {
    console.error('[CustomMapViewer] Erro ao carregar inventário:', error)
  }
}

const destroyCurrentMap = () => {
  console.log('[CustomMapViewer] 🗑️ Destruindo mapa atual:', currentMapProvider.value)
  resetZoomListener()
  
  // Limpar markers e polylines
  activeMarkers.forEach(marker => {
    try {
      clearMarkerListeners(marker)
    } catch (error) {
      console.warn('[CustomMapViewer] Falha ao limpar listeners do marker durante destruição:', error)
    }

    if (typeof marker.setMap === 'function') {
      marker.setMap(null)
    } else if (typeof marker.remove === 'function') {
      marker.remove()
    }
  })
  activeMarkers.clear()
  
  activePolylines.forEach(polyline => {
    try {
      clearPolylineListeners(polyline)
    } catch (error) {
      console.warn('[CustomMapViewer] Falha ao limpar listeners da polyline durante destruição:', error)
    }

    if (typeof polyline.setMap === 'function') {
      polyline.setMap(null)
    } else if (currentMapProvider.value === 'mapbox') {
      if (polyline.layerId && googleMap.value?.getLayer(polyline.layerId)) {
        googleMap.value.removeLayer(polyline.layerId)
      }
      if (polyline.sourceId && googleMap.value?.getSource(polyline.sourceId)) {
        googleMap.value.removeSource(polyline.sourceId)
      }
    } else if (currentMapProvider.value === 'osm' && typeof polyline.remove === 'function') {
      polyline.remove()
    }
  })
  activePolylines.clear()
  
  // Destruir instância do mapa
  if (googleMap.value) {
    if (currentMapProvider.value === 'mapbox') {
      googleMap.value.remove()
    } else if (currentMapProvider.value === 'osm') {
      googleMap.value.remove()
    }
    // Google Maps não precisa de remove() explícito
    googleMap.value = null
  }
  
  // Limpar container
  if (mapContainer.value) {
    mapContainer.value.innerHTML = ''
  }
  
  console.log('[CustomMapViewer] ✅ Mapa destruído')
}

const initMap = async () => {
  if (!mapContainer.value) {
    console.warn('[CustomMapViewer] Container do mapa não encontrado')
    return
  }
  
  try {
    // Carregar configurações do sistema primeiro
    console.log('[CustomMapViewer] Carregando configurações do sistema...')
    await loadSystemConfig()
    
    // Verificar qual provedor de mapa está configurado
    const mapProvider = configForm.value.MAP_PROVIDER || 'google'
    console.log(`[CustomMapViewer] 🔄 Provedor de mapa selecionado: ${mapProvider}`)
    
    // 🔒 EXCLUSÃO MÚTUA: Destruir mapa anterior se mudou de provider
    if (googleMap.value && currentMapProvider.value !== mapProvider) {
      console.log(`[CustomMapViewer] ⚠️ Trocando de ${currentMapProvider.value} para ${mapProvider}`)
      destroyCurrentMap()
    }
    
    // Inicializar o provider selecionado (sem fallback)
    if (mapProvider === 'google') {
      await initGoogleMap()
    } else if (mapProvider === 'mapbox') {
      await initMapboxMap()
    } else if (mapProvider === 'osm') {
      await initOpenStreetMap()
    } else {
      console.error(`[CustomMapViewer] Provedor de mapa não suportado: ${mapProvider}`)
      throw new Error(`Provedor de mapa '${mapProvider}' não suportado`)
    }
  } catch (error) {
    console.error('[CustomMapViewer] Erro ao inicializar mapa:', error)
    alert('❌ Erro ao carregar o mapa:\n' + error.message + '\n\nVerifique o console para mais detalhes.')
  }
}

const initGoogleMap = async () => {
  // Carregar Google Maps API se necessário
  console.log('[CustomMapViewer] Iniciando carregamento do Google Maps...')
  await loadGoogleMaps()
  
  if (!window.google?.maps) {
    throw new Error('Google Maps API não carregou corretamente')
  }
  resetZoomListener()
  
  currentMapProvider.value = 'google'
  console.log('[CustomMapViewer] Google Maps API disponível, criando mapa...')
  
  // Obter configurações do banco de dados
  const mapZoom = parseInt(configForm.value.MAP_DEFAULT_ZOOM) || 12
  const mapLat = parseFloat(configForm.value.MAP_DEFAULT_LAT) || -15.7801
  const mapLng = parseFloat(configForm.value.MAP_DEFAULT_LNG) || -47.9292
  const mapType = configForm.value.MAP_TYPE || 'roadmap'
  const mapTheme = configForm.value.MAP_THEME || 'light'
  const enableStreetView = configForm.value.ENABLE_STREET_VIEW !== false
  const enableTraffic = configForm.value.ENABLE_TRAFFIC === true
  const enableFullscreen = configForm.value.ENABLE_FULLSCREEN !== false
  
  console.log('[CustomMapViewer] Configurações:', {
    zoom: mapZoom,
    center: { lat: mapLat, lng: mapLng },
    type: mapType,
    theme: mapTheme,
    streetView: enableStreetView,
    traffic: enableTraffic,
    fullscreen: enableFullscreen
  })
    
    // Determinar tema efetivo usando uiStore (tema do usuário) ao invés do sistema
    const userTheme = uiStore.theme
    const effectiveTheme = userTheme || 'dark'
    const mapStyles = getMapStyles(effectiveTheme, effectiveTheme)
    
    console.log('[CustomMapViewer] Aplicando estilos:', {
      userTheme,
      effectiveTheme,
      stylesCount: mapStyles.length,
      firstStyle: mapStyles[0]
    })
    
    googleMap.value = new google.maps.Map(mapContainer.value, {
      center: { lat: mapLat, lng: mapLng },
      zoom: mapZoom,
      mapTypeId: mapType,  // terrain, roadmap, satellite, hybrid
      styles: mapStyles,
      mapTypeControl: true,
      streetViewControl: enableStreetView,
      fullscreenControl: enableFullscreen,
      zoomControl: true,
      // Opções adicionais para remover grid e otimizar renderização
      disableDefaultUI: false,
      clickableIcons: true,
      backgroundColor: effectiveTheme === 'dark' ? '#242f3e' : '#F1F3F4',  // Azul noite (dark) / Cinza Cloud (light)
      // Configurações de renderização para evitar artifacts/grid
      gestureHandling: 'greedy',
      tilt: 0,  // Vista 2D sem inclinação (evita artifacts 3D)
      restriction: null,  // Sem restrição de área
      minZoom: 3,
      maxZoom: 20
    })
    
    // Habilitar camada de tráfego se configurado
    if (enableTraffic) {
      const trafficLayer = new google.maps.TrafficLayer()
      trafficLayer.setMap(googleMap.value)
      console.log('[CustomMapViewer] Camada de tráfego ativada')
    }
    
    console.log('[CustomMapViewer] Mapa criado com sucesso - Tipo:', googleMap.value.getMapTypeId())
    console.log('[CustomMapViewer] Mapa zoom:', googleMap.value.getZoom())
    console.log('[CustomMapViewer] Mapa center:', googleMap.value.getCenter().toString())
    
    // Watch para mudanças de tema do usuário (uiStore)
    watch(
      () => uiStore.theme,
      (newTheme) => {
        console.log('[CustomMapViewer] Tema do usuário alterado para:', newTheme)
        if (googleMap.value) {
          const newStyles = getMapStyles(newTheme, newTheme)
          const newBgColor = newTheme === 'dark' ? '#242f3e' : '#F1F3F4'
          googleMap.value.setOptions({
            styles: newStyles,
            backgroundColor: newBgColor
          })
          console.log('[CustomMapViewer] Estilos do mapa atualizados para:', newTheme)
          
          // Atualizar polylines com nova espessura baseada no tema
          updateCablePolylines()
        }
      },
      { immediate: false }
    )
    
    // ✅ ATUALIZAR MAPA após inicialização completa do Google Maps
    console.log('[CustomMapViewer] Google Maps pronto - aplicando seleção inicial')
    updateMap()
}

const MAPBOX_STYLE_PRESETS = {
  streets: 'mapbox://styles/mapbox/streets-v12',
  'streets-v12': 'mapbox://styles/mapbox/streets-v12',
  'street-v12': 'mapbox://styles/mapbox/streets-v12',
  satellite: 'mapbox://styles/mapbox/satellite-v9',
  'satellite-v9': 'mapbox://styles/mapbox/satellite-v9',
  'satellite-streets': 'mapbox://styles/mapbox/satellite-streets-v12',
  'satellite-streets-v12': 'mapbox://styles/mapbox/satellite-streets-v12',
  outdoors: 'mapbox://styles/mapbox/outdoors-v12',
  'outdoors-v12': 'mapbox://styles/mapbox/outdoors-v12',
  terrain: 'mapbox://styles/mapbox/outdoors-v12',
  light: 'mapbox://styles/mapbox/light-v11',
  'light-v11': 'mapbox://styles/mapbox/light-v11',
  dark: 'mapbox://styles/mapbox/dark-v11',
  'dark-v11': 'mapbox://styles/mapbox/dark-v11',
  navigation: 'mapbox://styles/mapbox/navigation-day-v1',
  'navigation-day': 'mapbox://styles/mapbox/navigation-day-v1',
  'navigation-day-v1': 'mapbox://styles/mapbox/navigation-day-v1',
  'navigation-night': 'mapbox://styles/mapbox/navigation-night-v1',
  'navigation-night-v1': 'mapbox://styles/mapbox/navigation-night-v1'
}

const mapboxDiagnosticsState = {
  running: false
}

const resolveMapboxStyle = (rawStyle, sourceLabel) => {
  const style = (rawStyle || '').trim()
  if (!style) {
    return ''
  }

  const lower = style.toLowerCase()

  if (style.startsWith('mapbox://') || style.startsWith('http://') || style.startsWith('https://')) {
    return style
  }

  if (MAPBOX_STYLE_PRESETS[lower]) {
    console.log(`[CustomMapViewer] Normalizando estilo Mapbox (${sourceLabel}):`, style, '→', MAPBOX_STYLE_PRESETS[lower])
    return MAPBOX_STYLE_PRESETS[lower]
  }

  console.warn(`[CustomMapViewer] Estilo Mapbox inválido (${sourceLabel}):`, style)
  return ''
}

const buildStyleValidationUrl = (styleUrl, token) => {
  if (!styleUrl) {
    return null
  }

  if (styleUrl.startsWith('mapbox://styles/')) {
    const stylePath = styleUrl.substring('mapbox://styles/'.length)
    return `https://api.mapbox.com/styles/v1/${stylePath}?access_token=${token}`
  }

  if (styleUrl.startsWith('https://api.mapbox.com') || styleUrl.startsWith('http://api.mapbox.com')) {
    try {
      const url = new URL(styleUrl)
      if (!url.searchParams.has('access_token')) {
        url.searchParams.set('access_token', token)
      }
      return url.toString()
    } catch (error) {
      console.warn('[CustomMapViewer] URL de estilo Mapbox inválida:', styleUrl, error)
      return null
    }
  }

  // URLs externas não podem ser validadas com antecedência (CORS), assumir válidas
  return null
}

const validateMapboxStyleReachability = async (styleUrl, token) => {
  const validationUrl = buildStyleValidationUrl(styleUrl, token)
  if (!validationUrl) {
    console.log('[CustomMapViewer] Validação pulada (sem URL) para estilo:', styleUrl)
    return true
  }

  try {
    const response = await fetch(validationUrl, { method: 'GET', mode: 'cors' })
    if (response.ok) {
      console.log('[CustomMapViewer] Estilo disponível:', styleUrl)
      return true
    }

    const status = response.status
    let detail = ''
    try {
      const raw = await response.text()
      detail = raw.slice(0, 140)
    } catch (readError) {
      detail = String(readError)
    }
    console.warn(`[CustomMapViewer] Estilo Mapbox indisponível (${status}) para ${styleUrl}:`, detail)
    return false
  } catch (error) {
    console.error('[CustomMapViewer] Erro ao validar estilo Mapbox:', styleUrl, error)
    return false
  }
}

const buildMapboxStyleCandidates = () => {
  const customStyle = resolveMapboxStyle(configForm.value.MAPBOX_CUSTOM_STYLE, 'custom')
  const configuredStyle = resolveMapboxStyle(configForm.value.MAPBOX_STYLE, 'config')

  const styles = Array.from(new Set([
    customStyle,
    configuredStyle,
    'mapbox://styles/mapbox/streets-v12',
    'mapbox://styles/mapbox/streets-v11',
    'mapbox://styles/mapbox/outdoors-v12',
    'mapbox://styles/mapbox/light-v11',
    'mapbox://styles/mapbox/dark-v11',
    'mapbox://styles/mapbox/satellite-streets-v12',
    'mapbox://styles/mapbox/satellite-v9'
  ].filter(Boolean)))

  return {
    styles,
    customStyle,
    configuredStyle
  }
}

const runAutomaticMapboxDiagnostics = async ({ token, styles, center, zoom }) => {
  if (mapboxDiagnosticsState.running) {
    console.log('[CustomMapViewer] Diagnóstico Mapbox já em execução, ignorando chamada')
    return null
  }

  mapboxDiagnosticsState.running = true
  try {
    const diagnosticStyles = styles?.length ? styles : MAPBOX_STYLE_DIAGNOSTICS_DEFAULTS
    console.log('[CustomMapViewer] Iniciando diagnóstico automático Mapbox com estilos:', diagnosticStyles.map((s) => (typeof s === 'string' ? s : s.url)))
    const results = await runMapboxStyleDiagnostics({
      mapboxgl,
      token,
      styles: diagnosticStyles,
      center,
      zoom,
      verbose: true
    })
    console.log('[CustomMapViewer] Diagnóstico Mapbox concluído:', results)
    return results
  } catch (diagnosticError) {
    console.error('[CustomMapViewer] Falha ao executar diagnóstico Mapbox:', diagnosticError)
    return null
  } finally {
    mapboxDiagnosticsState.running = false
  }
}

const createMapboxInstanceForStyle = ({ styleUrl, center, zoom }) => {
  const containerEl = mapContainer.value
  if (!containerEl) {
    throw new Error('Container do mapa não encontrado para inicializar o Mapbox')
  }

  // Garantir que o container esteja limpo para evitar avisos do Mapbox
  if (containerEl.firstChild) {
    containerEl.replaceChildren()
  }

  console.log(`[CustomMapViewer] Tentando carregar estilo Mapbox: ${styleUrl}`)

  return new Promise((resolve, reject) => {
    let settled = false

    const map = new mapboxgl.Map({
      container: containerEl,
      style: styleUrl,
      center,
      zoom,
      attributionControl: true,
      cooperativeGestures: true,
      pitch: 0,
      bearing: 0
    })

    const settle = (error) => {
      if (settled) {
        return
      }
      settled = true

      map.off('load', onLoad)
      map.off('error', onError)
      window.clearTimeout(timeoutId)

      if (error) {
        try {
          map.remove()
        } catch (removeError) {
          console.warn('[CustomMapViewer] Falha ao remover instância Mapbox após erro:', removeError)
        }

        const normalized = error instanceof Error ? error : new Error(String(error))
        normalized.mapboxStyle = styleUrl
        reject(normalized)
      } else {
        resolve(map)
      }
    }

    const onLoad = () => {
      console.log(`[CustomMapViewer] ✅ Estilo Mapbox carregado: ${styleUrl}`)
      settle()
    }

    const onError = (event) => {
      const rawError = event?.error || event
      let detailMessage = 'Erro desconhecido ao carregar Mapbox'

      if (rawError) {
        if (rawError instanceof Error) {
          detailMessage = rawError.message
        } else if (typeof rawError === 'string') {
          detailMessage = rawError
        } else if (typeof rawError?.message === 'string') {
          detailMessage = rawError.message
        }
      }

      console.error(`[CustomMapViewer] ❌ Mapbox erro (${styleUrl}):`, rawError)
      settle(new Error(detailMessage))
    }

    const timeoutId = window.setTimeout(() => {
      console.warn(`[CustomMapViewer] ⏱️ Timeout ao carregar estilo Mapbox (${styleUrl})`)
      settle(new Error('Timeout ao carregar Mapbox'))
    }, 30000)

    map.once('load', onLoad)
    map.once('error', onError)
  })
}

const initMapboxMap = async () => {
  console.log('[CustomMapViewer] Iniciando Mapbox com lógica direta (sem proxy)...')
  console.log('[CustomMapViewer] configForm completo:', JSON.stringify(configForm.value, null, 2))
  resetZoomListener()

  const mapboxToken = (configForm.value.MAPBOX_TOKEN || '').trim()
  if (!mapboxToken) {
    console.error('[CustomMapViewer] Token do Mapbox não configurado')
    console.error('[CustomMapViewer] Campos disponíveis em configForm:', Object.keys(configForm.value))
    throw new Error('Token do Mapbox não configurado. Configure em Setup > Mapas.')
  }

  // ✅ LAZY LOADING: Carregar Mapbox apenas quando necessário
  if (!mapboxgl) {
    console.log('[CustomMapViewer] Carregando biblioteca Mapbox sob demanda...')
    mapboxgl = await loadMapbox()
  }

  mapboxgl.accessToken = mapboxToken
  console.log('[CustomMapViewer] mapboxgl.version:', mapboxgl.version)

  let candidateStyles = []
  let selectedStyle = ''
  let mapZoom = parseInt(configForm.value.MAP_DEFAULT_ZOOM) || 12
  let mapLat = parseFloat(configForm.value.MAP_DEFAULT_LAT) || -15.7801
  let mapLng = parseFloat(configForm.value.MAP_DEFAULT_LNG) || -47.9292

  try {
    currentMapProvider.value = 'mapbox'

    const { styles, customStyle, configuredStyle } = buildMapboxStyleCandidates()
    candidateStyles = styles

    if (candidateStyles.length === 0) {
      candidateStyles.push('mapbox://styles/mapbox/streets-v12')
    }

    const styleErrors = []

    for (const styleCandidate of candidateStyles) {
      let reachable = true
      try {
        reachable = await validateMapboxStyleReachability(styleCandidate, mapboxToken)
      } catch (validationError) {
        reachable = false
        console.warn('[CustomMapViewer] Validação do estilo Mapbox falhou (exceção):', styleCandidate, validationError)
      }

      if (!reachable) {
        console.warn('[CustomMapViewer] Estilo reprovado na validação, pulando tentativa direta:', styleCandidate)
        styleErrors.push({ style: styleCandidate, message: 'Validação falhou (HTTP ou CORS)' })
        continue
      }

      try {
        const mapInstance = await createMapboxInstanceForStyle({
          styleUrl: styleCandidate,
          center: [mapLng, mapLat],
          zoom: mapZoom
        })

        googleMap.value = mapInstance
        selectedStyle = styleCandidate
        break
      } catch (attemptError) {
        console.warn('[CustomMapViewer] Falha ao aplicar estilo Mapbox:', styleCandidate, attemptError)
        styleErrors.push({ style: styleCandidate, message: attemptError.message })
      }
    }

    if (!googleMap.value) {
      const aggregated = styleErrors.map((entry) => `${entry.style}: ${entry.message}`).join(' | ')
      throw new Error(aggregated ? `Falha ao carregar estilos Mapbox. Detalhes: ${aggregated}` : 'Nenhum estilo Mapbox pôde ser carregado. Verifique o token e tente novamente.')
    }

    googleMap.value.addControl(new mapboxgl.NavigationControl(), 'top-right')
    googleMap.value.addControl(new mapboxgl.ScaleControl({ unit: 'metric' }))

    const preferredStyle = customStyle || configuredStyle
    if (preferredStyle && preferredStyle !== selectedStyle) {
      console.warn(`[CustomMapViewer] Estilo preferido (${preferredStyle}) indisponível. Aplicando fallback ${selectedStyle}`)
    } else if (!preferredStyle) {
      console.warn('[CustomMapViewer] Nenhum estilo Mapbox personalizado configurado. Utilizando fallback automático', selectedStyle)
    }

    console.log('[CustomMapViewer] Mapbox inicializado com sucesso!', {
      style: selectedStyle,
      zoom: mapZoom,
      center: [mapLng, mapLat]
    })

    registerMapboxZoomListener()
    updateMapboxMarkerSizes()
    
    console.log('[CustomMapViewer] 🎯 Mapbox inicializado')
    console.log('[CustomMapViewer] Devices selecionados:', selectedItems.value.devices.length)
    console.log('[CustomMapViewer] Cabos selecionados:', selectedItems.value.cables.length)
    
    // Aguardar 500ms para garantir que o mapa está completamente renderizado
    setTimeout(() => {
      console.log('[CustomMapViewer] 🚀 Renderizando overlays após delay...')
      updateMap()
    }, 500)
  } catch (error) {
    console.error('[CustomMapViewer] Erro detalhado ao inicializar Mapbox:')
    console.error('  - Message:', error.message)
    console.error('  - Stack:', error.stack)
    console.error('  - Error object:', error)

    // Executar diagnóstico expandido em caso de falha
    runAutomaticMapboxDiagnostics({
      token: mapboxToken,
      styles: candidateStyles,
      center: [mapLng, mapLat],
      zoom: mapZoom
    }).catch((diagnosticError) => {
      console.error('[CustomMapViewer] Diagnóstico automático falhou:', diagnosticError)
    })
    throw error
  }
}

const initOpenStreetMap = async () => {
  console.log('[CustomMapViewer] Iniciando OpenStreetMap com Leaflet...')
  
  // ✅ LAZY LOADING: Carregar Leaflet apenas quando necessário
  if (!L) {
    console.log('[CustomMapViewer] Carregando biblioteca Leaflet sob demanda...')
    L = await loadLeaflet()
  }
  
  console.log('[CustomMapViewer] L disponível:', !!L)
  console.log('[CustomMapViewer] L.version:', L.version)
  
  currentMapProvider.value = 'osm'
  resetZoomListener()
  
  const mapZoom = parseInt(configForm.value.MAP_DEFAULT_ZOOM) || 12
  const mapLat = parseFloat(configForm.value.MAP_DEFAULT_LAT) || -15.7801
  const mapLng = parseFloat(configForm.value.MAP_DEFAULT_LNG) || -47.9292
  
  googleMap.value = L.map(mapContainer.value).setView([mapLat, mapLng], mapZoom)
  
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(googleMap.value)
  
  console.log('[CustomMapViewer] OpenStreetMap inicializado com sucesso')
  
  // ✅ ATUALIZAR MAPA após inicialização completa do OSM
  console.log('[CustomMapViewer] OSM pronto - aplicando seleção inicial')
  updateMap()
}

// ==========================================
// CAMADA DE ABSTRAÇÃO PARA MÚLTIPLOS PROVEDORES
// ==========================================

// Criar marker compatível com todos os provedores
const createMarker = ({ lat, lng, title, icon, animation }) => {
  if (currentMapProvider.value === 'google') {
    return new google.maps.Marker({
      position: { lat, lng },
      map: googleMap.value,
      title,
      icon,
      animation
    })
  } else if (currentMapProvider.value === 'mapbox') {
    // Criar HTML element para o marker customizado
    const el = document.createElement('div')
    el.className = 'mapbox-marker'
    el.style.borderRadius = '50%'
    el.style.backgroundColor = icon?.fillColor || '#10b981'
    el.style.borderStyle = 'solid'
    el.style.borderColor = '#ffffff'
    el.style.borderWidth = '2px'
    el.style.boxShadow = '0 1px 3px rgba(0,0,0,0.25)'
    el.style.cursor = 'pointer'
    el.title = title
    
    const marker = new mapboxgl.Marker(el)
      .setLngLat([lng, lat])
      .addTo(googleMap.value)
    
    // Adicionar propriedades compatíveis
    marker._listeners = {}
    marker._status = icon?.statusKey || 'offline'
    marker.setMap = (map) => map ? marker.addTo(map) : marker.remove()
    marker.getPosition = () => ({ lat: () => lat, lng: () => lng })
    marker._applySize = (zoomOverride) => {
      const zoom = Number.isFinite(zoomOverride) ? zoomOverride : getActiveMapZoom()
      applyMapboxMarkerDimensions(marker, zoom)
    }
    marker.setIcon = (newIcon) => {
      if (newIcon?.fillColor) {
        el.style.backgroundColor = newIcon.fillColor
      }
      marker._status = newIcon?.statusKey || marker._status
      marker._applySize()
    }
    marker._applySize()
    
    return marker
  } else if (currentMapProvider.value === 'osm') {
    // Criar ícone customizado para Leaflet
    const iconColor = icon?.fillColor || '#10b981'
    const leafletIcon = L.divIcon({
      className: 'leaflet-custom-marker',
      html: `<div style="width: 30px; height: 30px; border-radius: 50%; background-color: ${iconColor}; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
      iconSize: [30, 30],
      iconAnchor: [15, 15]
    })
    
    const marker = L.marker([lat, lng], { icon: leafletIcon, title })
      .addTo(googleMap.value)
    
    // Adicionar propriedades compatíveis
    marker._listeners = {}
    marker.setMap = (map) => map ? marker.addTo(map) : marker.remove()
    marker.getPosition = () => ({ lat: () => lat, lng: () => lng })
    marker.setIcon = (newIcon) => {
      if (newIcon?.fillColor) {
        const newLeafletIcon = L.divIcon({
          className: 'leaflet-custom-marker',
          html: `<div style="width: 30px; height: 30px; border-radius: 50%; background-color: ${newIcon.fillColor}; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
          iconSize: [30, 30],
          iconAnchor: [15, 15]
        })
        marker.setIcon(newLeafletIcon)
      }
    }
    
    return marker
  }
}

// Adicionar listener de evento compatível
const addMarkerListener = (marker, event, callback) => {
  if (currentMapProvider.value === 'google') {
    marker.addListener(event, callback)
  } else if (currentMapProvider.value === 'mapbox') {
    const eventMap = { click: 'click' }
    const mapboxEvent = eventMap[event] || event
    marker.getElement().addEventListener(mapboxEvent, callback)
    if (!marker._listeners[event]) marker._listeners[event] = []
    marker._listeners[event].push(callback)
  } else if (currentMapProvider.value === 'osm') {
    const leafletEvent = event === 'click' ? 'click' : event
    marker.on(leafletEvent, callback)
    if (!marker._listeners[event]) marker._listeners[event] = []
    marker._listeners[event].push(callback)
  }
}

// Limpar listeners de marker
const clearMarkerListeners = (marker) => {
  if (currentMapProvider.value === 'google') {
    google.maps.event.clearInstanceListeners(marker)
  } else if (currentMapProvider.value === 'mapbox') {
    if (marker._listeners) {
      Object.entries(marker._listeners).forEach(([event, callbacks]) => {
        callbacks.forEach(cb => marker.getElement().removeEventListener(event, cb))
      })
      marker._listeners = {}
    }
  } else if (currentMapProvider.value === 'osm') {
    if (marker._listeners) {
      Object.entries(marker._listeners).forEach(([event, callbacks]) => {
        callbacks.forEach(cb => marker.off(event, cb))
      })
      marker._listeners = {}
    }
  }
}

// Criar polyline compatível
const createPolyline = ({ path, strokeColor, strokeOpacity, strokeWeight }) => {
  if (currentMapProvider.value === 'google') {
    return new google.maps.Polyline({
      path,
      geodesic: true,
      strokeColor,
      strokeOpacity,
      strokeWeight,
      map: googleMap.value
    })
  } else if (currentMapProvider.value === 'mapbox') {
    // Mapbox usa layers e sources
    const sourceId = `polyline-${Date.now()}-${Math.random()}`
    const layerId = `layer-${sourceId}`
    
    googleMap.value.addSource(sourceId, {
      type: 'geojson',
      data: {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: path.map(p => [p.lng, p.lat])
        }
      }
    })
    
    googleMap.value.addLayer({
      id: layerId,
      type: 'line',
      source: sourceId,
      layout: {
        'line-join': 'round',
        'line-cap': 'round'
      },
      paint: {
        'line-color': strokeColor,
        'line-opacity': strokeOpacity,
        'line-width': strokeWeight
      }
    })
    
    // Retornar objeto compatível
    const polylineObj = {
      sourceId,
      layerId,
      _listeners: {},
      setMap: (map) => {
        if (!map) {
          if (googleMap.value.getLayer(layerId)) {
            googleMap.value.removeLayer(layerId)
          }
          if (googleMap.value.getSource(sourceId)) {
            googleMap.value.removeSource(sourceId)
          }
        }
      },
      setOptions: ({ strokeColor: color, strokeOpacity: opacity, strokeWeight: weight }) => {
        if (googleMap.value.getLayer(layerId)) {
          if (color) googleMap.value.setPaintProperty(layerId, 'line-color', color)
          if (opacity !== undefined) googleMap.value.setPaintProperty(layerId, 'line-opacity', opacity)
          if (weight) googleMap.value.setPaintProperty(layerId, 'line-width', weight)
        }
      },
      addListener: (event, callback) => {
        if (event === 'click') {
          googleMap.value.on('click', layerId, callback)
          if (!polylineObj._listeners[event]) polylineObj._listeners[event] = []
          polylineObj._listeners[event].push(callback)
        }
      }
    }

    return polylineObj
  } else if (currentMapProvider.value === 'osm') {
    const latlngs = path.map(p => [p.lat, p.lng])
    const polyline = L.polyline(latlngs, {
      color: strokeColor,
      opacity: strokeOpacity,
      weight: strokeWeight
    }).addTo(googleMap.value)
    
    polyline._listeners = {}
    polyline.setMap = (map) => map ? polyline.addTo(map) : polyline.remove()
    
    return polyline
  }
}

// Adicionar listener de polyline
const addPolylineListener = (polyline, event, callback) => {
  if (currentMapProvider.value === 'google') {
    polyline.addListener(event, callback)
  } else if (currentMapProvider.value === 'mapbox') {
    if (polyline.layerId && event === 'click') {
      googleMap.value.on('click', polyline.layerId, callback)
      if (!polyline._listeners[event]) polyline._listeners[event] = []
      polyline._listeners[event].push(callback)
    }
  } else if (currentMapProvider.value === 'osm') {
    const leafletEvent = event === 'click' ? 'click' : event
    polyline.on(leafletEvent, callback)
    if (!polyline._listeners[event]) polyline._listeners[event] = []
    polyline._listeners[event].push(callback)
  }
}

// Limpar listeners de polyline
const clearPolylineListeners = (polyline) => {
  if (currentMapProvider.value === 'google') {
    google.maps.event.clearInstanceListeners(polyline)
  } else if (currentMapProvider.value === 'mapbox') {
    if (polyline._listeners && polyline.layerId) {
      Object.entries(polyline._listeners).forEach(([event, callbacks]) => {
        callbacks.forEach(cb => googleMap.value.off(event, polyline.layerId, cb))
      })
      polyline._listeners = {}
    }
  } else if (currentMapProvider.value === 'osm') {
    if (polyline._listeners) {
      Object.entries(polyline._listeners).forEach(([event, callbacks]) => {
        callbacks.forEach(cb => polyline.off(event, cb))
      })
      polyline._listeners = {}
    }
  }
}

const updateCablePolylines = () => {
  if (!googleMap.value) {
    console.warn('[CustomMapViewer] Google Map não inicializado ainda')
    return
  }
  
  console.log('[CustomMapViewer] updateCablePolylines com diffing')
  const currentCableIds = new Set(selectedItems.value.cables)
  
  // Detectar tema ativo para ajustar espessura da linha
  const isDarkMode = uiStore.theme === 'dark'
  const strokeWeight = isDarkMode ? 2 : 3 // Linha mais fina no modo noturno
  const strokeOpacity = isDarkMode ? 0.7 : 0.8 // Opacidade reduzida no modo noturno
  
  // 1. REMOVER polylines de cabos desmarcados
  activePolylines.forEach((polyline, id) => {
    if (!currentCableIds.has(id)) {
      console.log(`[CustomMapViewer] Removendo polyline do cabo ${id}`)
      clearPolylineListeners(polyline)
      if (typeof polyline.setMap === 'function') {
        polyline.setMap(null)
      } else if (currentMapProvider.value === 'mapbox') {
        if (polyline.layerId && googleMap.value.getLayer(polyline.layerId)) {
          googleMap.value.removeLayer(polyline.layerId)
        }
        if (polyline.sourceId && googleMap.value.getSource(polyline.sourceId)) {
          googleMap.value.removeSource(polyline.sourceId)
        }
      }
      activePolylines.delete(id)
    }
  })
  
  // 2. ADICIONAR/ATUALIZAR polylines de cabos selecionados
  const selectedCables = availableItems.value.cables.filter(cable => 
    currentCableIds.has(cable.id) && cable.path_coordinates && cable.path_coordinates.length > 0
  )
  
  console.log(`[CustomMapViewer] ${selectedCables.length} cabos para processar`)
  
  selectedCables.forEach((cable) => {
    // Se já existe, atualizar cor E espessura baseado no tema
    if (activePolylines.has(cable.id)) {
      const existingPolyline = activePolylines.get(cable.id)
      const statusColors = {
        online: '#10b981',
        offline: '#ef4444',
        warning: '#f59e0b',
        critical: '#dc2626',
        unknown: '#6b7280'
      }
      const newColor = statusColors[cable.status] || statusColors.unknown
      existingPolyline.setOptions({ 
        strokeColor: newColor,
        strokeWeight: strokeWeight,
        strokeOpacity: strokeOpacity
      })
      return
    }
    
    // Criar nova polyline
    const path = cable.path_coordinates.map(coord => ({
      lat: parseFloat(coord.lat),
      lng: parseFloat(coord.lng)
    }))
    
    const validPath = path.filter(point => !isNaN(point.lat) && !isNaN(point.lng))
    
    if (validPath.length < 2) {
      console.warn(`[CustomMapViewer] Cabo ${cable.name} sem coordenadas suficientes`)
      return
    }
    
    const statusColors = {
      online: '#10b981',
      offline: '#ef4444',
      warning: '#f59e0b',
      critical: '#dc2626',
      unknown: '#6b7280'
    }
    
    // Usar função de abstração para criar polyline
    const polyline = createPolyline({
      path: validPath,
      strokeColor: statusColors[cable.status] || statusColors.unknown,
      strokeOpacity: strokeOpacity,
      strokeWeight: strokeWeight
    })
    
    polyline.cableData = cable
    
    // Usar função de abstração para adicionar listener
    addPolylineListener(polyline, 'click', () => {
      selectedCable.value = cable
      showCableDetailModal.value = true
    })
    
    activePolylines.set(cable.id, polyline)
  })
  
  console.log(`[CustomMapViewer] ${activePolylines.size} polylines ativas`)
}

// Função para destacar cabo quando mouse passa sobre item no painel
const highlightCable = (cableId) => {
  if (activeCategory.value !== 'cables') return
  
  const polyline = activePolylines.get(cableId)
  if (!polyline) return
  
  const isDarkMode = uiStore.theme === 'dark'
  
  // Salvar configuração original se ainda não salvou
  if (!polyline.originalOptions) {
    polyline.originalOptions = {
      strokeWeight: isDarkMode ? 2 : 3,
      strokeOpacity: isDarkMode ? 0.7 : 0.8
    }
  }
  
  // Aplicar efeito glow
  polyline.setOptions({
    strokeWeight: 5,
    strokeOpacity: 1,
    zIndex: 1000
  })
  
  console.log(`[highlightCable] Destacando cabo ${cableId}`)
}

// Função para remover destaque do cabo
const unhighlightCable = (cableId) => {
  if (activeCategory.value !== 'cables') return
  
  const polyline = activePolylines.get(cableId)
  if (!polyline || !polyline.originalOptions) return
  
  // Restaurar configuração original
  polyline.setOptions({
    strokeWeight: polyline.originalOptions.strokeWeight,
    strokeOpacity: polyline.originalOptions.strokeOpacity,
    zIndex: 1
  })
  
  console.log(`[unhighlightCable] Removendo destaque do cabo ${cableId}`)
}

const updateMapMarkers = (animateItemId = null) => {
  if (!googleMap.value) {
    console.warn('[CustomMapViewer] Google Map não inicializado ainda')
    return
  }
  
  console.log('[CustomMapViewer] updateMapMarkers com diffing (SEM clustering)')
  const currentDeviceIds = new Set(selectedItems.value.devices)
  
  console.log(`[updateMapMarkers] selectedItems.value.devices:`, selectedItems.value.devices)
  console.log(`[updateMapMarkers] currentDeviceIds (Set):`, Array.from(currentDeviceIds))
  console.log(`[updateMapMarkers] activeMarkers.keys():`, Array.from(activeMarkers.keys()))
  
  // 1. REMOVER markers de devices desmarcados
  activeMarkers.forEach((marker, id) => {
    if (!currentDeviceIds.has(id)) {
      console.log(`[CustomMapViewer] Removendo marker do device ${id}`)
      clearMarkerListeners(marker)
      marker.setMap(null)
      activeMarkers.delete(id)
    }
  })
  
  // 2. ADICIONAR/ATUALIZAR markers de devices selecionados
  const selectedDevices = availableItems.value.devices.filter(device => 
    currentDeviceIds.has(device.id) && device.lat && device.lng
  )
  
  console.log(`[CustomMapViewer] ${selectedDevices.length} devices para processar`)
  
  selectedDevices.forEach((device) => {
    // Se já existe, atualizar apenas o ícone se o status mudou
    if (activeMarkers.has(device.id)) {
      const existingMarker = activeMarkers.get(device.id)
      existingMarker.setIcon(getMarkerIcon(device.status))
      return
    }
    
    // Criar novo marker
    const lat = parseFloat(device.lat)
    const lng = parseFloat(device.lng)
    
    if (isNaN(lat) || isNaN(lng)) {
      console.error(`[CustomMapViewer] Coordenadas inválidas para ${device.name}`)
      return
    }
    
    // Buscar site no mapa
    const actualSite = sitesMap.value.get(String(device.site))
    if (!actualSite) {
      console.warn(`[CustomMapViewer] Site ${device.site} não encontrado para ${device.name}`)
      return
    }
    
    const shouldAnimate = isInitialLoad.value || (animateItemId && device.id === animateItemId)
    
    // Usar função de abstração para criar marker
    const marker = createMarker({
      lat,
      lng,
      title: device.name,
      icon: getMarkerIcon(device.status),
      animation: shouldAnimate ? (currentMapProvider.value === 'google' ? google.maps.Animation.DROP : null) : null
    })
    
    marker.siteData = actualSite
    
    // Usar função de abstração para adicionar listener
    addMarkerListener(marker, 'click', () => {
      console.log('🔥 MARKER CLICADO! Site:', marker.siteData.name)
      selectedSite.value = marker.siteData
      showSiteModal.value = true
    })
    
    activeMarkers.set(device.id, marker)
  })

  if (currentMapProvider.value === 'mapbox') {
    updateMapboxMarkerSizes()
  }
  
  console.log(`[CustomMapViewer] ${activeMarkers.size} markers ativos após update`)
  
  // Ajustar bounds apenas na carga inicial (somente Google Maps)
  if (isInitialLoad.value && activeMarkers.size > 0) {
    if (currentMapProvider.value === 'google') {
      const bounds = new google.maps.LatLngBounds()
      activeMarkers.forEach(marker => bounds.extend(marker.getPosition()))
      googleMap.value.fitBounds(bounds)
      
      if (activeMarkers.size === 1) {
        const listener = google.maps.event.addListener(googleMap.value, 'idle', () => {
          if (googleMap.value.getZoom() > 15) {
            googleMap.value.setZoom(15)
          }
          google.maps.event.removeListener(listener)
        })
      }
    } else if (currentMapProvider.value === 'mapbox') {
      const bounds = new mapboxgl.LngLatBounds()
      activeMarkers.forEach(marker => {
        if (typeof marker.getLngLat === 'function') {
          bounds.extend(marker.getLngLat())
        }
      })

      if (!bounds.isEmpty()) {
        googleMap.value.fitBounds(bounds, { padding: 80, maxZoom: 15 })
      }
    }
  }
}

const getStatusColor = (status) => {
  const colors = {
    online: '#10b981',
    warning: '#f59e0b',
    critical: '#ef4444',
    offline: '#6b7280'
  }
  return colors[status] || colors.offline
}

// Função para obter ícone do marcador baseado no status
const getMarkerIcon = (status) => {
  const colors = {
    online: '#10b981',
    warning: '#f59e0b',
    critical: '#ef4444',
    offline: '#6b7280'
  }
  const circlePath = typeof window !== 'undefined' && window.google?.maps?.SymbolPath?.CIRCLE !== undefined
    ? window.google.maps.SymbolPath.CIRCLE
    : 0
  const fillColor = colors[status] || colors.offline
  
  return {
    path: circlePath,
    fillColor,
    fillOpacity: 0.9,
    strokeColor: '#fff',
    strokeWeight: 1.6,
    scale: 6,
    statusKey: status
  }
}

const saveMapItems = async () => {
  try {
    const mapId = route.params.mapId
    if (mapId === 'default') {
      alert('Não é possível salvar alterações no mapa padrão')
      return
    }
    
    const response = await fetch(`/inventory/api/v1/maps/custom/${mapId}/items/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
      },
      body: JSON.stringify({
        selected_items: selectedItems.value
      })
    })
    
    if (!response.ok) {
      throw new Error(`Erro ao salvar: ${response.status}`)
    }
    
    alert('Itens salvos com sucesso!')
    console.log('[CustomMapViewer] Itens salvos com sucesso')
  } catch (error) {
    console.error('[CustomMapViewer] Erro ao salvar itens:', error)
    alert('Erro ao salvar itens do mapa')
  }
}

// Observar mudanças nos items selecionados e atualizar mapa
watch(() => selectedItems.value.devices, () => {
  if (!googleMap.value) return
  console.log('[CustomMapViewer] Devices selecionados alterados → updateMap')
  updateMap()
}, { deep: true })

watch(() => selectedItems.value.cables, () => {
  if (!googleMap.value) return
  console.log('[CustomMapViewer] Cabos selecionados alterados → updateMap')
  updateMap()
}, { deep: true })

// 🔄 WATCHER: Detecta mudanças no provider e reinicializa o mapa (EXCLUSÃO MÚTUA)
watch(
  () => configForm.value.MAP_PROVIDER,
  async (newProvider, oldProvider) => {
    if (!mapContainer.value || !oldProvider) return // Ignora primeira inicialização
    
    console.log(`[CustomMapViewer] 🔄 Provider mudou: ${oldProvider} → ${newProvider}`)
    console.log('[CustomMapViewer] 🗑️ Destruindo mapa anterior...')
    
    // Destruir mapa anterior
    if (googleMap.value) {
      destroyCurrentMap()
    }
    
    console.log(`[CustomMapViewer] 🆕 Inicializando ${newProvider}...`)
    // Inicializar novo mapa
    await initMap()
  }
)

// Função para abrir detalhes completos do cabo
const openCableFullDetails = (cable) => {
  console.log('[CustomMapViewer] Abrir detalhes completos do cabo:', cable.name)
  showCableModal.value = false
  selectedCable.value = cable
  showCableDetailModal.value = true
}

// Função para salvar alterações do cabo
const handleCableSave = async (cable) => {
  console.log('[CustomMapViewer] Salvando cabo:', cable)
  // TODO: Implementar salvamento no backend
  showCableDetailModal.value = false
  // Recarregar inventário para atualizar dados
  await loadInventoryItems()
  updateMap()
}

onMounted(async () => {
  console.log('[CustomMapViewer] Componente montado, iniciando carregamento...')
  
  // 1. Carregar inventário primeiro
  await loadInventoryItems()
  
  // 2. Carregar dados do mapa
  await loadMapData()
  
  // 3. Se for mapa default, selecionar todos os items automaticamente
  const mapId = route.params.mapId
  if (mapId === 'default') {
    if (availableItems.value.devices.length > 0) {
      selectedItems.value.devices = availableItems.value.devices.map(d => d.id)
      console.log(`[CustomMapViewer] Mapa default: ${selectedItems.value.devices.length} devices selecionados automaticamente`)
    }
    
    if (availableItems.value.cables.length > 0) {
      selectedItems.value.cables = availableItems.value.cables.map(c => c.id)
      console.log(`[CustomMapViewer] Mapa default: ${selectedItems.value.cables.length} cabos selecionados automaticamente`)
    }
  }

  if (typeof window !== 'undefined') {
    window.__runMapboxStyleDiagnostics = async (overrideStyles) => {
      const token = (configForm.value.MAPBOX_TOKEN || '').trim()
      const lat = parseFloat(configForm.value.MAP_DEFAULT_LAT) || -15.7801
      const lng = parseFloat(configForm.value.MAP_DEFAULT_LNG) || -47.9292
      const zoom = parseInt(configForm.value.MAP_DEFAULT_ZOOM) || 12
      const candidateSet = buildMapboxStyleCandidates()
      const styles = overrideStyles && overrideStyles.length ? overrideStyles : candidateSet.styles

      console.log('[CustomMapViewer] Executando diagnóstico manual de estilos Mapbox...', { styles, lat, lng, zoom, candidateSet })
      const results = await runAutomaticMapboxDiagnostics({
        token,
        styles,
        center: [lng, lat],
        zoom
      })
      console.log('[CustomMapViewer] Resultado diagnóstico manual:', results)
      return results
    }
  }
  
  // 4. Inicializar mapa (updateMap() será chamado automaticamente após concluir init)
  await initMap()
  
  // 5. Marcar que o carregamento inicial foi concluído
  // Aguardar um pouco para garantir que a animação inicial aconteceu
  setTimeout(() => {
    isInitialLoad.value = false
    console.log('[CustomMapViewer] Carregamento inicial concluído - animações desativadas')
  }, 2000)
  
  console.log('[CustomMapViewer] ✓ onMounted completo')
})

onBeforeUnmount(() => {
  console.log('[CustomMapViewer] Limpando recursos antes de desmontar')
  
  // 1. Limpar MarkerClusterer
  if (markerClusterer.value) {
    markerClusterer.value.clearMarkers()
    if (typeof markerClusterer.value.setMap === 'function') {
      markerClusterer.value.setMap(null)
    }
    markerClusterer.value = null
  }
  
  // 2. Limpar todos os markers do Map
  activeMarkers.forEach((marker) => {
    try {
      clearMarkerListeners(marker)
    } catch (error) {
      console.warn('[CustomMapViewer] Falha ao limpar listeners do marker ao desmontar:', error)
    }

    if (typeof marker.setMap === 'function') {
      marker.setMap(null)
    } else if (typeof marker.remove === 'function') {
      marker.remove()
    }
  })
  activeMarkers.clear()
  
  // 3. Limpar todas as polylines do Map
  activePolylines.forEach((polyline) => {
    try {
      clearPolylineListeners(polyline)
    } catch (error) {
      console.warn('[CustomMapViewer] Falha ao limpar listeners da polyline ao desmontar:', error)
    }

    if (typeof polyline.setMap === 'function') {
      polyline.setMap(null)
    } else if (currentMapProvider.value === 'mapbox') {
      if (polyline.layerId && googleMap.value?.getLayer(polyline.layerId)) {
        googleMap.value.removeLayer(polyline.layerId)
      }
      if (polyline.sourceId && googleMap.value?.getSource(polyline.sourceId)) {
        googleMap.value.removeSource(polyline.sourceId)
      }
    } else if (currentMapProvider.value === 'osm' && typeof polyline.remove === 'function') {
      polyline.remove()
    }
  })
  activePolylines.clear()
  
  // 4. Limpar listeners do mapa
  if (googleMap.value) {
    if (currentMapProvider.value === 'mapbox' && typeof googleMap.value.remove === 'function') {
      googleMap.value.remove()
    } else if (currentMapProvider.value === 'osm' && typeof googleMap.value.remove === 'function') {
      googleMap.value.remove()
    }
    if (currentMapProvider.value === 'google') {
      google.maps.event.clearInstanceListeners(googleMap.value)
    }
    googleMap.value = null
  }
  
  // 5. Remover event listener do window
  window.removeEventListener('google-maps-loaded', initMap)
  
  console.log('[CustomMapViewer] Recursos limpos')
})
</script>

<style scoped>
.custom-map-viewer {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  /* Ajustar margem baseado no estado do menu */
  margin-left: var(--nav-menu-width, 72px);
  transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.3s ease;
}

/* Quando o menu está expandido */
:root[data-nav-menu-open="true"] .custom-map-viewer {
  margin-left: 280px;
}

/* Quando o menu está colapsado */
:root[data-nav-menu-open="false"] .custom-map-viewer {
  margin-left: 72px;
}

.map-toolbar {
  height: 64px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  z-index: 1000;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.btn-back {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-back:hover {
  background: rgba(255, 255, 255, 0.1);
}

.map-title h2 {
  margin: 0;
  font-size: 18px;
  color: #fff;
}

.map-category {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  text-transform: uppercase;
  font-weight: 600;
}

.btn-toolbar {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-toolbar:hover {
  background: rgba(16, 185, 129, 0.2);
  border-color: rgba(16, 185, 129, 0.5);
}

.map-content {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
}

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

/* Transi\u00e7\u00e3o de expand/collapse */
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

.item-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.item-name {
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-subtitle {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-subtitle i {
  font-size: 10px;
}

.item-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.ip-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.ip-badge i {
  font-size: 9px;
}

.camera-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
  display: flex;
  align-items: center;
  gap: 4px;
}

.camera-badge i {
  font-size: 10px;
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

.map-legend {
  position: absolute;
  bottom: 24px;
  left: 24px;
  background: rgba(30, 33, 57, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  backdrop-filter: blur(10px);
  z-index: 100;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.legend-item:last-child {
  margin-bottom: 0;
}

.legend-marker {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #fff;
}

.legend-marker.online {
  background: #10b981;
}

.legend-marker.warning {
  background: #f59e0b;
}

.legend-marker.critical {
  background: #ef4444;
}

.legend-marker.offline {
  background: #6b7280;
}

.legend-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
}

.custom-map-viewer.fullscreen {
  z-index: 10000;
}

/* ==========================================
   LIGHT THEME OVERRIDES
   ========================================== */
:root[data-theme="light"] .custom-map-viewer,
html:not(.dark)[data-theme="light"] .custom-map-viewer {
  background: var(--bg-primary);
}

:root[data-theme="light"] .map-toolbar,
html:not(.dark)[data-theme="light"] .map-toolbar {
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .btn-back,
html:not(.dark)[data-theme="light"] .btn-back,
:root[data-theme="light"] .btn-toolbar,
html:not(.dark)[data-theme="light"] .btn-toolbar {
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.1);
  color: var(--text-primary);
}

:root[data-theme="light"] .btn-back:hover,
html:not(.dark)[data-theme="light"] .btn-back:hover,
:root[data-theme="light"] .btn-toolbar:hover,
html:not(.dark)[data-theme="light"] .btn-toolbar:hover {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.3);
}

:root[data-theme="light"] .map-title h2,
html:not(.dark)[data-theme="light"] .map-title h2 {
  color: var(--text-primary);
}

:root[data-theme="light"] .map-category,
html:not(.dark)[data-theme="light"] .map-category {
  color: var(--text-tertiary);
}

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

:root[data-theme="light"] .panel-header,
html:not(.dark)[data-theme="light"] .panel-header,
:root[data-theme="light"] .panel-tabs,
html:not(.dark)[data-theme="light"] .panel-tabs {
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .tab-btn,
html:not(.dark)[data-theme="light"] .tab-btn {
  color: var(--text-tertiary);
}

:root[data-theme="light"] .search-box input,
html:not(.dark)[data-theme="light"] .search-box input {
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.1);
  color: var(--text-primary);
}

:root[data-theme="light"] .search-box i,
html:not(.dark)[data-theme="light"] .search-box i {
  color: var(--text-tertiary);
}

:root[data-theme="light"] .site-row,
html:not(.dark)[data-theme="light"] .site-row {
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.08);
}

:root[data-theme="light"] .site-row:hover,
html:not(.dark)[data-theme="light"] .site-row:hover {
  background: rgba(16, 185, 129, 0.05);
  border-color: rgba(16, 185, 129, 0.2);
}

:root[data-theme="light"] .site-name,
html:not(.dark)[data-theme="light"] .site-name,
:root[data-theme="light"] .device-name,
html:not(.dark)[data-theme="light"] .device-name {
  color: var(--text-primary);
}

:root[data-theme="light"] .site-count,
html:not(.dark)[data-theme="light"] .site-count,
:root[data-theme="light"] .device-info,
html:not(.dark)[data-theme="light"] .device-info {
  color: var(--text-tertiary);
}

:root[data-theme="light"] .btn-expand,
html:not(.dark)[data-theme="light"] .btn-expand {
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.1);
  color: var(--text-tertiary);
}

:root[data-theme="light"] .map-legend,
html:not(.dark)[data-theme="light"] .map-legend {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .legend-label,
html:not(.dark)[data-theme="light"] .legend-label {
  color: var(--text-secondary);
}

:root[data-theme="light"] .item-name,
html:not(.dark)[data-theme="light"] .item-name {
  color: var(--text-primary);
}

:root[data-theme="light"] .btn-panel.btn-secondary,
html:not(.dark)[data-theme="light"] .btn-panel.btn-secondary {
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.1);
  color: var(--text-primary);
}

:root[data-theme="light"] .btn-panel.btn-secondary:hover,
html:not(.dark)[data-theme="light"] .btn-panel.btn-secondary:hover {
  background: rgba(0, 0, 0, 0.1);
}

/* ==========================================
   MAPBOX MARKERS - Garantir visibilidade
   ========================================== */
.mapbox-marker {
  display: block !important;
  width: 30px !important;
  height: 30px !important;
  z-index: 1000 !important;
  position: relative !important;
  pointer-events: auto !important;
}

.mapboxgl-marker {
  z-index: 1000 !important;
}
</style>
