<template>
  <div class="custom-map-viewer" @contextmenu.prevent="onViewerContextMenu">
    <!-- Main Content -->
    <div class="map-content">
      <!-- Mapa: criado pelo provider configurado (providers/maps) -->
      <div ref="mapContainer" class="map-container"></div>

      <!-- Painel Lateral: Gerenciar Itens (lazy: só monta após 1ª abertura, depois mantém estado) -->
      <MapInventoryPanel
        v-if="inventoryPanelMounted"
        :is-visible="showInventoryPanel"
        :active-category="activeCategory"
        :search-query="searchQuery"
        :categories="inventoryCategories"
        :available-items="availableItems"
        :selected-items="selectedItems"
        :expanded-sites="expandedSites"
        :expanded-camera-sites="expandedCameraSites"
        :devices-by-site="devicesBySite"
        :cameras-by-site="camerasBySite"
        :filtered-items="filteredItems"
        :folders-tree="foldersTree"
        @close="showInventoryPanel = false"
        @update:activeCategory="activeCategory = $event"
        @update:searchQuery="searchQuery = $event"
        @toggle-site-expansion="toggleSiteExpansion"
        @toggle-camera-site-expansion="toggleCameraSiteExpansion"
        @toggle-site="toggleSite"
        @toggle-camera-site="toggleCameraSite"
        @toggle-item="toggleItem"
        @focus-item="focusOnItem"
        @highlight-cable="highlightCable"
        @unhighlight-cable="unhighlightCable"
        @select-all="selectAll"
        @save="saveMapItems"
      />
    </div>

    <!-- Botão Reenquadrar -->
    <button
      class="map-fit-btn"
      title="Reenquadrar mapa para mostrar todos os itens"
      @click="fitAllItemsBounds"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 256 256" fill="currentColor">
        <path d="M168,48a8,8,0,0,1,8-8h32a8,8,0,0,1,8,8V80a8,8,0,0,1-16,0V64H176A8,8,0,0,1,168,48ZM216,168a8,8,0,0,0-8,8v16H192a8,8,0,0,0,0,16h32a8,8,0,0,0,8-8V176A8,8,0,0,0,216,168ZM88,208H72V192a8,8,0,0,0-16,0v32a8,8,0,0,0,8,8H88a8,8,0,0,0,0-16ZM40,88a8,8,0,0,0,8-8V64H64a8,8,0,0,0,0-16H32a8,8,0,0,0-8,8V80A8,8,0,0,0,40,88Z"/>
      </svg>
      Reenquadrar
    </button>

    <!-- Legend -->
    <MapLegend :status-legend="statusLegend" />

    <!-- Context Menu (botão direito) -->
    <MapContextMenu
      :visible="ctxMenu.visible"
      :x="ctxMenu.x"
      :y="ctxMenu.y"
      :map-name="mapData.name"
      :map-category="mapData.category"
      :maintenance-active="maintenanceMode"
      :is-fullscreen="isFullscreen"
      @action="onCtxMenuAction"
      @close="ctxMenu.visible = false"
    />

    <!-- Painel de resultado da Área de Manutenção (Fase 5.2) -->
    <MaintenanceAreaPanel
      v-if="maintenanceMode"
      :visible="maintenanceMode"
      :vertex-count="maintenanceVertices.length"
      :affected-cables="affectedCables"
      :affected-devices="affectedDevices"
      @close="exitMaintenanceMode"
      @clear="clearMaintenanceArea"
      @export-csv="exportMaintenanceCSV"
      @notify="showNotifyModal = true"
    />

    <!-- Modal de notificação de área de manutenção -->
    <MaintenanceNotifyModal
      v-if="showNotifyModal"
      :visible="showNotifyModal"
      :cables="affectedCables"
      :devices="affectedDevices"
      @close="showNotifyModal = false"
      @sent="onNotifySent"
    />

    <!-- In-app alert badge de notificação enviada -->
    <transition name="toast-slide">
      <div v-if="notifyBadge.visible" class="notify-sent-badge">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <span>{{ notifyBadge.message }}</span>
        <button class="nsb-close" @click="notifyBadge.visible = false">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </transition>

    <!-- Status badge — live Zabbix polling indicator (Fase 5.1) -->
    <div class="status-poll-badge" :class="{ 'status-poll-badge--stale': !lastStatusUpdate }">
      <span class="spb-dot" :class="`spb-dot--${statusSummary.offline > 0 ? 'warning' : 'ok'}`"></span>
      <span class="spb-counts">
        <span class="spb-online">{{ statusSummary.online }} online</span>
        <template v-if="statusSummary.offline > 0">
          · <span class="spb-offline">{{ statusSummary.offline }} offline</span>
        </template>
      </span>
      <span v-if="lastUpdateLabel" class="spb-time">· {{ lastUpdateLabel }}</span>
      <span v-else class="spb-time">· aguardando…</span>
    </div>

    <!-- Site Details Modal (lazy: monta na 1ª abertura) -->
    <SiteDetailsModal
      v-if="showSiteModal"
      :is-open="showSiteModal"
      :site="selectedSite"
      @close="showSiteModal = false"
    />

    <!-- Fiber Cable Quick Modal (lazy) -->
    <FiberCableQuickModal
      v-if="showCableModal"
      :show="showCableModal"
      :cable="selectedCable"
      @close="showCableModal = false"
      @openFullDetails="openCableFullDetails"
    />

    <!-- Fiber Cable Detail Modal (lazy: chunk de ~3.8k linhas) -->
    <FiberCableDetailModal
      v-if="showCableDetailModal"
      :show="showCableDetailModal"
      :cable="selectedCable"
      :can-edit="true"
      @close="showCableDetailModal = false"
      @save="handleCableSave"
    />

    <!-- Cable Optical Tooltip (lazy) -->
    <CableOpticalTooltip
      v-if="showCableTooltip"
      :visible="showCableTooltip"
      :cable-data="hoveredCable"
      :position="tooltipPosition"
      @close="showCableTooltip = false"
      @open-details="openCableDetailsFromTooltip"
    />

    <!-- Toast notification -->
    <transition name="toast-slide">
      <div v-if="toast.visible" :class="['map-toast', `map-toast--${toast.type}`]">
        <span class="map-toast__icon">
          <svg v-if="toast.type === 'success'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <svg v-else-if="toast.type === 'error'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </span>
        <span class="map-toast__msg">{{ toast.message }}</span>
      </div>
    </transition>
  </div>
</template>

<script setup>
/**
 * CustomMapViewer — mapa de monitoramento (backbone / mapas personalizados).
 *
 * EV-0012c: deixou de ter um ramo `if provider === …` por função. O mapa vem
 * da `MapProviderFactory` (google | mapbox | osm, conforme a configuração) e
 * marcadores, cabos, área de manutenção, cursor e redimensionamento falam só
 * a interface `IMap`. Estado em tempo real: `useRealtimeStatus` (EV-0014).
 */
import { ref, shallowRef, computed, onMounted, onBeforeUnmount, watch, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { useRealtimeStatus, availabilityToStatus } from '@/composables/useRealtimeStatus'
import { createMap, getMapConfig } from '@/providers/maps/MapProviderFactory.js'
import { useMapSelection } from '@/composables/map/useMapSelection'
import { useMapData } from '@/composables/map/useMapData'
import MapLegend from './components/MapLegend.vue'
import MapContextMenu from './components/MapContextMenu.vue'

// Componentes pesados: lazy via defineAsyncComponent — só baixam o JS quando renderizados.
// Modais (SiteDetails, FiberCable*, CableOpticalTooltip, MaintenanceNotify) são montados
// só quando v-if=true. MapInventoryPanel e MaintenanceAreaPanel podem ficar lazy também:
// só montam quando o usuário abre o painel/área. Evita ~10k linhas de Vue no bundle inicial.
const SiteDetailsModal = defineAsyncComponent(() => import('@/components/SiteDetailsModal.vue'))
const FiberCableQuickModal = defineAsyncComponent(() => import('@/components/FiberCableQuickModal.vue'))
const FiberCableDetailModal = defineAsyncComponent(() => import('@/components/FiberCableDetailModal.vue'))
const CableOpticalTooltip = defineAsyncComponent(() => import('@/components/CableOpticalTooltip.vue'))
const MapInventoryPanel = defineAsyncComponent(() => import('./components/MapInventoryPanel.vue'))
const MaintenanceAreaPanel = defineAsyncComponent(() => import('./components/MaintenanceAreaPanel.vue'))
const MaintenanceNotifyModal = defineAsyncComponent(() => import('./components/MaintenanceNotifyModal.vue'))

const route = useRoute()
const uiStore = useUiStore()

const mapContainer = ref(null)
const map = shallowRef(null) // IMap (providers/maps)
const providerName = ref('')

// ── Cores por estado (eram de useMapMarkers / useMapPolylines) ─────────────
const DEVICE_STATUS_COLORS = {
  online: '#10b981',
  unknown: '#10b981', // presumido online até o Zabbix dizer o contrário
  warning: '#f59e0b',
  offline: '#f59e0b', // mesmo tom de atenção — atrai o olhar para resolver
  critical: '#ef4444',
}
const CABLE_STATUS_COLORS = {
  up: '#10b981',
  down: '#ef4444',
  degraded: '#f59e0b',
  online: '#10b981',
  offline: '#ef4444',
  warning: '#f59e0b',
  critical: '#dc2626',
  unknown: '#6b7280',
}
const DEVICE_MARKER_SIZE = 14
const MAINTENANCE_STYLE = { strokeColor: '#f59e0b', strokeOpacity: 0.9, strokeWeight: 2, fillColor: '#f59e0b', fillOpacity: 0.12 }
const DEFAULT_CENTER = { lat: -15.7801, lng: -47.9292 }
const DEFAULT_ZOOM = 12

const deviceColor = (status) => DEVICE_STATUS_COLORS[status] || DEVICE_STATUS_COLORS.offline
const cableColor = (status) => CABLE_STATUS_COLORS[status] || CABLE_STATUS_COLORS.unknown
const cableBaseStyle = () => {
  const dark = uiStore.theme === 'dark'
  return { strokeWeight: dark ? 2 : 3, strokeOpacity: dark ? 0.7 : 0.8 }
}

// ── Toast notifications ────────────────────────────────────────────────────
const toast = ref({ visible: false, type: 'success', message: '' })
let _toastTimer = null

function showToast(message, type = 'success', duration = 3000) {
  if (_toastTimer) clearTimeout(_toastTimer)
  toast.value = { visible: true, type, message }
  _toastTimer = setTimeout(() => { toast.value.visible = false }, duration)
}

// ── Maintenance notification modal ─────────────────────────────────────────
const showNotifyModal = ref(false)
const notifyBadge = ref({ visible: false, message: '' })
let _badgeTimer = null

function onNotifySent(result) {
  showNotifyModal.value = false
  if (result.ok) {
    const total = result.total_sent || 0
    const msg = total > 0
      ? `${total} destinatário(s) notificado(s)`
      : 'Notificação enviada'
    if (_badgeTimer) clearTimeout(_badgeTimer)
    notifyBadge.value = { visible: true, message: msg }
    _badgeTimer = setTimeout(() => { notifyBadge.value.visible = false }, 8000)
    showToast(msg)
  } else {
    showToast(result.error || 'Erro ao enviar notificação', 'error')
  }
}

// ── Seleção e dados (composables sem provider) ─────────────────────────────
const {
  selectedItems,
  expandedSites,
  expandedCameraSites,
  toggleSiteExpansion,
  toggleSite: toggleSiteSelection,
  toggleCameraSiteExpansion,
  toggleCameraSite: toggleCameraSiteSelection,
  toggleItem: toggleItemSelection,
  selectAll: selectAllItems,
} = useMapSelection()
const { availableItems, sitesMap, foldersTree, loadInventoryItems: loadInventory, applyDisplayStatus } = useMapData()
const showInventoryPanel = ref(false)
// Flag de "já foi montado pelo menos uma vez" — usada para manter o painel
// no DOM (preservando estado interno) após a primeira abertura, sem pagar
// o custo do bundle no carregamento inicial da página.
const inventoryPanelMounted = ref(false)
watch(showInventoryPanel, (v) => {
  if (v) inventoryPanelMounted.value = true
})
const activeCategory = ref('devices')
const searchQuery = ref('')
const isFullscreen = ref(false)
const isInitialLoad = ref(true)

// ── Context Menu (botão direito) ─────────────────────────────────────────────
const ctxMenu = ref({ visible: false, x: 0, y: 0 })

function onViewerContextMenu(e) {
  ctxMenu.value = { visible: true, x: e.clientX, y: e.clientY }
}

function _hideCtxMenu() {
  ctxMenu.value.visible = false
}

function onCtxMenuAction(action) {
  _hideCtxMenu()
  if (action === 'inventory') showInventoryPanel.value = !showInventoryPanel.value
  else if (action === 'maintenance') toggleMaintenanceMode()
  else if (action === 'fullscreen') toggleFullscreen()
  else if (action === 'back') window.history.back()
}

function _globalKeydown(e) {
  if (e.key !== 'Escape') return
  _hideCtxMenu()
  // Fecha em cascata: modal mais específico primeiro, tela cheia por último
  if (showCableDetailModal.value)  { showCableDetailModal.value = false; return }
  if (showCableModal.value)        { showCableModal.value = false; return }
  if (showSiteModal.value)         { showSiteModal.value = false; return }
  if (maintenanceMode.value)       { exitMaintenanceMode(); return }
  if (showInventoryPanel.value)    { showInventoryPanel.value = false; return }
  if (isFullscreen.value)          { toggleFullscreen(); return }
}

// Modal de detalhes do site
const showSiteModal = ref(false)
const selectedSite = ref(null)

// Modal de detalhes do cabo
const showCableModal = ref(false)
const showCableDetailModal = ref(false)
const selectedCable = ref(null)

// Tooltip de níveis ópticos
const showCableTooltip = ref(false)
const hoveredCable = ref(null)
const tooltipPosition = ref({ x: 0, y: 0 })
let tooltipTimeout = null

// ── Estado em tempo real (EV-0014) ───────────────────────────────────────────
// WebSocket `/ws/dashboard/status/` é a fonte; o polling só entra como
// degradação quando o socket esgota as tentativas de reconexão.
const deviceStatusMap = ref(new Map()) // device_id (string) → 'online'|'offline'|'warning'|'unknown'
const lastStatusUpdate = ref(null)     // Date | null
let statusPollTimer = null
const STATUS_POLL_INTERVAL = 60_000   // só em modo degradado
const realtime = useRealtimeStatus({ autoConnect: false })

const STATUS_SEVERITY = { offline: 4, critical: 3, warning: 2, online: 1, unknown: 0 }

const statusSummary = computed(() => {
  const counts = { online: 0, warning: 0, critical: 0, offline: 0, unknown: 0 }
  availableItems.value.devices.forEach(d => {
    const k = d.status || 'unknown'
    counts[k] = (counts[k] || 0) + 1
  })
  const total = availableItems.value.devices.length
  return { ...counts, total }
})

const lastUpdateLabel = computed(() => {
  if (!lastStatusUpdate.value) return null
  const diffMs = Date.now() - lastStatusUpdate.value.getTime()
  const secs = Math.round(diffMs / 1000)
  if (secs < 60) return `${secs}s atrás`
  return `${Math.round(secs / 60)}min atrás`
})

const _normalizeAvailability = (avail) => availabilityToStatus(avail, 'unknown')

function _deriveCableStatus(cable) {
  const a = deviceStatusMap.value.get(String(cable.origin_device_id)) || 'unknown'
  const b = deviceStatusMap.value.get(String(cable.destination_device_id)) || 'unknown'
  if (a === 'unknown' && b === 'unknown') return cable.status
  const sevA = STATUS_SEVERITY[a] ?? 0
  const sevB = STATUS_SEVERITY[b] ?? 0
  return sevA >= sevB ? a : b
}

function applyDeviceStatuses(newMap) {
  deviceStatusMap.value = newMap
  lastStatusUpdate.value = new Date()

  // Só redesenha quando algum estado mudou de facto (evita iterar 200+
  // marcadores a cada mensagem sem motivo).
  let changed = false
  availableItems.value.devices.forEach(device => {
    const live = newMap.get(String(device.id))
    if (live && live !== device.status) {
      device.status = live
      changed = true
    }
  })
  // Recomputar o displayStatus agregado do site: a mudança de UM device
  // afeta a cor dos OUTROS devices offline do mesmo site.
  if (changed) applyDisplayStatus(availableItems.value.devices)

  availableItems.value.cables.forEach(cable => {
    if (cable.origin_device_id || cable.destination_device_id) {
      const next = _deriveCableStatus(cable)
      if (next !== cable.status) {
        cable.status = next
        changed = true
      }
    }
  })
  if (changed) updateMap()
}

function applyCableStatuses(cableMap) {
  let changed = false
  availableItems.value.cables.forEach(cable => {
    const live = cableMap.get(String(cable.id))
    if (live && live !== cable.status) {
      cable.status = live
      changed = true
    }
  })
  if (changed) {
    lastStatusUpdate.value = new Date()
    updateMap()
  }
}

// Primeira pintura (e modo degradado): leitura REST única do estado atual.
async function fetchAndApplyDeviceStatuses() {
  try {
    const res = await fetch('/api/v1/monitoring/hosts/status/', { credentials: 'include' })
    if (!res.ok) return
    const data = await res.json()
    const newMap = new Map()
    ;(data.hosts_status || []).forEach(host => {
      if (host.device_id) newMap.set(String(host.device_id), _normalizeAvailability(host.available))
    })
    applyDeviceStatuses(newMap)
  } catch (err) {
    console.warn('[CustomMapViewer] Erro ao ler estado inicial:', err)
  }
}

function startDegradedPolling() {
  if (statusPollTimer) return
  console.warn('[CustomMapViewer] WebSocket indisponível; polling de 60 s em modo degradado')
  statusPollTimer = setInterval(fetchAndApplyDeviceStatuses, STATUS_POLL_INTERVAL)
}

realtime.onHosts((_hosts, next) => applyDeviceStatuses(new Map([...deviceStatusMap.value, ...next])))
realtime.onCables((_cables, next) => applyCableStatuses(next))
watch(realtime.error, (err) => {
  if (err === 'Max reconnect attempts reached') startDegradedPolling()
})
watch(realtime.connected, (isConnected) => {
  if (isConnected && statusPollTimer) {
    clearInterval(statusPollTimer)
    statusPollTimer = null
  }
})

function startStatusPolling() {
  fetchAndApplyDeviceStatuses()
  realtime.connect()
}

function stopStatusPolling() {
  realtime.disconnect()
  if (statusPollTimer) {
    clearInterval(statusPollTimer)
    statusPollTimer = null
  }
}

const mapData = ref({
  id: null,
  name: 'Carregando...',
  category: 'backbone',
  description: ''
})

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

const toggleSite = (siteId, devices) => {
  toggleSiteSelection(siteId, devices)
  updateMap()
}

// Funções específicas para câmeras
const toggleCameraSite = (siteName, cameras) => {
  toggleCameraSiteSelection(siteName, cameras)
  updateMap()
}

// ── Marcadores (diff incremental por id) ────────────────────────────────────
const activeMarkers = new Map() // deviceId → IMarker

function updateMarkers() {
  if (!map.value) return
  const wanted = new Set(selectedItems.value.devices)

  activeMarkers.forEach((marker, id) => {
    if (!wanted.has(id)) {
      marker.remove()
      activeMarkers.delete(id)
    }
  })

  availableItems.value.devices
    .filter(device => wanted.has(device.id) && device.lat && device.lng)
    .forEach(device => {
      // displayStatus é derivado do agregado do site (offline com irmão online →
      // warning); fallback ao status puro se ainda não foi computado.
      const markerStatus = device.displayStatus || device.status
      const existing = activeMarkers.get(device.id)
      if (existing) {
        existing.setStyle({ color: deviceColor(markerStatus) })
        return
      }

      const lat = parseFloat(device.lat)
      const lng = parseFloat(device.lng)
      if (Number.isNaN(lat) || Number.isNaN(lng)) return
      if (!sitesMap.value.get(String(device.site))) return

      const marker = map.value.createMarker({
        position: { lat, lng },
        title: device.name,
        color: deviceColor(markerStatus),
        size: DEVICE_MARKER_SIZE,
      })
      marker.on('click', () => handleDeviceClick(device))
      activeMarkers.set(device.id, marker)
    })
}

function clearAllMarkers() {
  activeMarkers.forEach(marker => marker.remove())
  activeMarkers.clear()
}

// ── Cabos (diff incremental por id) ──────────────────────────────────────────
const activePolylines = new Map() // cableId → IPolyline
const highlightedCables = new Set()

function cablePath(cable) {
  return (cable.path_coordinates || [])
    .map(coord => ({ lat: parseFloat(coord.lat), lng: parseFloat(coord.lng) }))
    .filter(point => !Number.isNaN(point.lat) && !Number.isNaN(point.lng))
}

function updatePolylines() {
  if (!map.value) return
  const wanted = new Set(selectedItems.value.cables)
  const base = cableBaseStyle()

  activePolylines.forEach((polyline, id) => {
    if (!wanted.has(id)) {
      polyline.remove()
      activePolylines.delete(id)
      highlightedCables.delete(id)
    }
  })

  availableItems.value.cables
    .filter(cable => wanted.has(cable.id) && cable.path_coordinates?.length > 0)
    .forEach(cable => {
      const existing = activePolylines.get(cable.id)
      if (existing) {
        if (!highlightedCables.has(cable.id)) {
          existing.setStyle({ strokeColor: cableColor(cable.status), ...base })
        }
        return
      }

      const path = cablePath(cable)
      if (path.length < 2) return

      const polyline = map.value.createPolyline({
        path,
        strokeColor: cableColor(cable.status),
        ...base,
        clickable: true,
      })
      polyline.on('click', () => handleCableClick(cable))
      polyline.on('mouseover', (event) => handleCableHover(cable, event))
      polyline.on('mouseout', handleCableUnhover)
      activePolylines.set(cable.id, polyline)
    })
}

function clearAllPolylines() {
  activePolylines.forEach(polyline => polyline.remove())
  activePolylines.clear()
  highlightedCables.clear()
}

// Destaque pedido pelo painel lateral (hover no item)
const highlightCable = (cableId) => {
  const polyline = activePolylines.get(cableId)
  if (!polyline) return
  highlightedCables.add(cableId)
  polyline.setStyle({ strokeWeight: 5, strokeOpacity: 1, zIndex: 1000 })
}

const unhighlightCable = (cableId) => {
  const polyline = activePolylines.get(cableId)
  if (!polyline) return
  highlightedCables.delete(cableId)
  polyline.setStyle({ ...cableBaseStyle(), zIndex: 1 })
}

// Ajusta o mapa para mostrar todos os itens visíveis (markers + polylines)
const fitAllItemsBounds = () => {
  if (!map.value) return
  const points = []

  activeMarkers.forEach(marker => points.push(marker.getPosition()))

  const selectedCableIds = new Set(selectedItems.value.cables)
  availableItems.value.cables
    .filter(cable => selectedCableIds.has(cable.id) && cable.path_coordinates)
    .forEach(cable => points.push(...cablePath(cable)))

  if (points.length === 0) return
  map.value.fitBounds(points, { padding: 50, maxZoom: 15 })
}

// Função unificada para atualizar todo o mapa (markers + polylines)
const updateMap = () => {
  if (!map.value) return
  const wasInitialLoad = isInitialLoad.value

  updateMarkers()
  updatePolylines()
  isInitialLoad.value = false

  // Carga inicial: ajusta bounds se há itens; sem itens permanece na localização configurada.
  // Sem setTimeout: a factory só devolve o mapa quando o provider está pronto.
  if (wasInitialLoad) {
    const hasItems = selectedItems.value.devices.length > 0 || selectedItems.value.cables.length > 0
    if (hasItems) fitAllItemsBounds()
  }
}

const toggleItem = (itemId) => {
  toggleItemSelection(itemId, activeCategory.value)
  updateMap()
}

const selectAll = () => {
  const category = activeCategory.value
  selectAllItems(category, availableItems.value[category])
  updateMap()
  // Reenquadra mapa para mostrar todos os itens selecionados
  setTimeout(() => fitAllItemsBounds(), 150)
}

const clearAllOverlays = () => {
  clearAllMarkers()
  clearAllPolylines()
}

const focusOnItem = (item) => {
  if (!map.value) return

  // Para devices e cameras que têm lat/lng diretamente
  if (item.lat && item.lng) {
    map.value.setCenter({ lat: parseFloat(item.lat), lng: parseFloat(item.lng) })
    map.value.setZoom(15)
    return
  }

  // Para cabos que têm path_coordinates: centralizar no ponto médio
  if (item.path_coordinates && item.path_coordinates.length > 0) {
    const midIndex = Math.floor(item.path_coordinates.length / 2)
    const midPoint = item.path_coordinates[midIndex]

    if (midPoint && midPoint.lat && midPoint.lng) {
      map.value.setCenter({ lat: parseFloat(midPoint.lat), lng: parseFloat(midPoint.lng) })
      map.value.setZoom(13) // Zoom menor para ver mais da rota
    }
  }
}

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
  const el = document.querySelector('.custom-map-viewer')
  if (!el) return
  el.classList.toggle('fullscreen', isFullscreen.value)
  // ResizeObserver detecta a mudança de tamanho e chama map.resize()
}

const loadMapData = async () => {
  try {
    const mapId = route.params.mapId

    if (mapId === 'default') {
      // Mapa padrão: carregar tudo
      mapData.value = {
        id: 'default',
        name: 'Mapa Completo',
        category: route.params.category || 'backbone',
        description: 'Visualização completa de todos os equipamentos'
      }
    } else {
      // Carregar mapa customizado
      const response = await fetch(`/api/v1/maps/custom/${mapId}/`, {
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error(`Erro ao carregar mapa: ${response.status}`)
      }

      const data = await response.json()
      mapData.value = data.map
      selectedItems.value = data.selected_items || selectedItems.value
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
    await loadInventory()
  } catch (error) {
    console.error('[CustomMapViewer] Erro ao carregar inventário:', error)
  }
}

const destroyCurrentMap = () => {
  clearAllOverlays()
  if (map.value) {
    map.value.off('click', _onMaintMapClick)
    map.value.destroy()
    map.value = null
  }
  if (mapContainer.value) {
    mapContainer.value.innerHTML = ''
  }
}

// Handlers para clicks em markers e polylines
const handleDeviceClick = (device) => {
  const site = sitesMap.value.get(String(device.site || device.site_id))
  if (site) {
    selectedSite.value = site
    showSiteModal.value = true
  }
}

const handleCableClick = (cable) => {
  hoveredCable.value = cable
  showCableTooltip.value = true
}

const openCableDetailsFromTooltip = (cable) => {
  showCableTooltip.value = false
  selectedCable.value = cable
  showCableDetailModal.value = true
}

// Handlers para hover em cabos (tooltip) — `event` é o MapEvent comum (clientX/clientY)
const handleCableHover = (cable, event) => {
  if (tooltipTimeout) {
    clearTimeout(tooltipTimeout)
  }

  // Pequeno delay antes de mostrar tooltip
  tooltipTimeout = setTimeout(() => {
    hoveredCable.value = cable
    tooltipPosition.value = {
      x: event?.clientX || 0,
      y: event?.clientY || 0
    }
    showCableTooltip.value = true
  }, 300)
}

const handleCableUnhover = () => {
  if (tooltipTimeout) {
    clearTimeout(tooltipTimeout)
    tooltipTimeout = null
  }
  // Tooltip now has a close button — do not auto-close on mouse out
}

// ── Mapa: criação pelo provider configurado ──────────────────────────────────
const initMap = async () => {
  if (!mapContainer.value) return

  try {
    const config = await getMapConfig()
    providerName.value = config.mapProvider || 'google'

    const lat = parseFloat(config.mapDefaultLat)
    const lng = parseFloat(config.mapDefaultLng)
    const zoom = parseInt(config.mapDefaultZoom, 10)

    const created = await createMap(mapContainer.value, {
      center: Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng } : DEFAULT_CENTER,
      zoom: Number.isFinite(zoom) && zoom > 0 ? zoom : DEFAULT_ZOOM,
      mapTypeId: config.mapType || 'roadmap',
      theme: uiStore.theme === 'dark' ? 'dark' : 'light',
      controls: {
        mapType: true,
        streetView: config.enableStreetView !== false,
        fullscreen: config.enableFullscreen !== false,
        traffic: config.enableTraffic === true,
        scale: true,
      },
      minZoom: 3,
      maxZoom: 20,
    })

    map.value = created
    updateMap()
  } catch (error) {
    console.error('[CustomMapViewer] Erro ao inicializar mapa:', error)
    showToast('Erro ao carregar o mapa: ' + error.message, 'error', 5000)
  }
}

// Tema do utilizador: o provider re-estiliza o fundo (Google) e os cabos mudam de espessura
watch(() => uiStore.theme, (newTheme) => {
  if (!map.value) return
  map.value.setTheme(newTheme === 'dark' ? 'dark' : 'light')
  updatePolylines()
})

const saveMapItems = async () => {
  try {
    const mapId = route.params.mapId
    if (mapId === 'default') {
      showToast('Não é possível salvar o mapa padrão', 'warning')
      return
    }

    const response = await fetch(`/api/v1/maps/custom/${mapId}/items/`, {
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

    showToast('Itens salvos com sucesso!')
  } catch (error) {
    console.error('[CustomMapViewer] Erro ao salvar itens:', error)
    showToast('Erro ao salvar itens do mapa', 'error')
  }
}

// Observar mudanças nos items selecionados e atualizar mapa
watch(() => selectedItems.value.devices, () => {
  if (map.value) updateMap()
}, { deep: true })

watch(() => selectedItems.value.cables, () => {
  if (map.value) updateMap()
}, { deep: true })

// ── Maintenance Area (Fase 5.2) ─────────────────────────────────────────────
const maintenanceMode = ref(false)
const maintenanceVertices = ref([]) // [{ lat, lng }, ...]
const affectedCables = ref([])
const affectedDevices = ref([])
let _maintOverlay = null       // IPolyline (2 vértices) ou IPolygon (3+)
let _maintOverlayKind = null   // 'line' | 'polygon'
let _resizeObserver = null

// Observa mudanças no tamanho do container (nav toggle, fullscreen, etc.)
// e pede ao provider para recalcular o canvas.
function _initResizeObserver() {
  if (!mapContainer.value || typeof ResizeObserver === 'undefined') return
  if (_resizeObserver) { _resizeObserver.disconnect(); _resizeObserver = null }

  _resizeObserver = new ResizeObserver(() => {
    try {
      map.value?.resize()
    } catch (e) { /* best-effort: ignorado de propósito */ }
  })
  _resizeObserver.observe(mapContainer.value)
}

function _pointInPolygon(point, polygon) {
  const { lat: py, lng: px } = point
  let inside = false
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].lng, yi = polygon[i].lat
    const xj = polygon[j].lng, yj = polygon[j].lat
    const intersect = ((yi > py) !== (yj > py)) && (px < ((xj - xi) * (py - yi)) / (yj - yi) + xi)
    if (intersect) inside = !inside
  }
  return inside
}

function _runMaintenanceSpatialQuery() {
  const poly = maintenanceVertices.value
  if (poly.length < 3) return

  affectedCables.value = availableItems.value.cables.filter(cable => {
    if (!cable.path_coordinates?.length) return false
    return cable.path_coordinates.some(coord => {
      const lat = parseFloat(coord.lat ?? coord[1])
      const lng = parseFloat(coord.lng ?? coord[0])
      return !isNaN(lat) && !isNaN(lng) && _pointInPolygon({ lat, lng }, poly)
    })
  })

  affectedDevices.value = availableItems.value.devices.filter(device => {
    const lat = parseFloat(device.lat)
    const lng = parseFloat(device.lng)
    return !isNaN(lat) && !isNaN(lng) && _pointInPolygon({ lat, lng }, poly)
  })
}

function _clearMaintPolygonOverlay() {
  if (!_maintOverlay) return
  try { _maintOverlay.remove() } catch (e) { /* best-effort */ }
  _maintOverlay = null
  _maintOverlayKind = null
}

function _drawMaintPolygon() {
  const verts = maintenanceVertices.value
  if (!map.value || verts.length < 2) return
  const path = verts.map(v => ({ lat: v.lat, lng: v.lng }))
  const kind = verts.length === 2 ? 'line' : 'polygon'

  if (_maintOverlay && _maintOverlayKind === kind) {
    _maintOverlay.setPath(path)
    return
  }

  _clearMaintPolygonOverlay()
  _maintOverlay = kind === 'line'
    ? map.value.createPolyline({ path, strokeColor: MAINTENANCE_STYLE.strokeColor, strokeOpacity: MAINTENANCE_STYLE.strokeOpacity, strokeWeight: MAINTENANCE_STYLE.strokeWeight, clickable: false })
    : map.value.createPolygon({ path, ...MAINTENANCE_STYLE, clickable: false })
  _maintOverlayKind = kind
}

function _setCursor(style) {
  map.value?.setCursor(style || '')
}

function _onMaintMapClick(event) {
  if (!maintenanceMode.value) return
  if (!Number.isFinite(event?.lat) || !Number.isFinite(event?.lng)) return
  maintenanceVertices.value.push({ lat: event.lat, lng: event.lng })
  _drawMaintPolygon()
  if (maintenanceVertices.value.length >= 3) _runMaintenanceSpatialQuery()
}

function toggleMaintenanceMode() {
  if (maintenanceMode.value) exitMaintenanceMode()
  else enterMaintenanceMode()
}

function enterMaintenanceMode() {
  maintenanceMode.value = true
  maintenanceVertices.value = []
  affectedCables.value = []
  affectedDevices.value = []
  map.value?.on('click', _onMaintMapClick)
  _setCursor('crosshair')
}

function exitMaintenanceMode() {
  map.value?.off('click', _onMaintMapClick)
  _setCursor('')
  _clearMaintPolygonOverlay()
  maintenanceMode.value = false
  maintenanceVertices.value = []
  affectedCables.value = []
  affectedDevices.value = []
}

function clearMaintenanceArea() {
  _clearMaintPolygonOverlay()
  maintenanceVertices.value = []
  affectedCables.value = []
  affectedDevices.value = []
}

function exportMaintenanceCSV() {
  const rows = [['Tipo', 'Nome', 'Status', 'Site', 'Lat', 'Lng']]
  affectedCables.value.forEach(cable => {
    rows.push(['Cabo', cable.name || `Cabo #${cable.id}`, cable.status || '', '', '', ''])
  })
  affectedDevices.value.forEach(device => {
    rows.push(['Equipamento', device.name, device.status || '', device.site_name || '', device.lat || '', device.lng || ''])
  })
  const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `area_manutencao_${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
// ─────────────────────────────────────────────────────────────────────────────

// Função para abrir detalhes completos do cabo
const openCableFullDetails = (cable) => {
  showCableModal.value = false
  selectedCable.value = cable
  showCableDetailModal.value = true
}

// Função para salvar alterações do cabo
const handleCableSave = async () => {
  // TODO(EV-0012d): persistir no backend; hoje só recarrega o inventário
  showCableDetailModal.value = false
  await loadInventoryItems()
  updateMap()
}

onMounted(async () => {
  document.addEventListener('click', _hideCtxMenu)
  document.addEventListener('keydown', _globalKeydown)

  // 1–2. Inventário e dados do mapa em paralelo (tempo = max, não a soma)
  await Promise.all([loadInventoryItems(), loadMapData()])

  // 3. Se for mapa default, selecionar todos os items automaticamente
  if (route.params.mapId === 'default') {
    if (availableItems.value.devices.length > 0) {
      selectedItems.value.devices = availableItems.value.devices.map(d => d.id)
    }
    if (availableItems.value.cables.length > 0) {
      selectedItems.value.cables = availableItems.value.cables.map(c => c.id)
    }
  }

  // 4. Inicializar mapa (updateMap() corre no fim do init)
  await initMap()

  // 4b. Observar mudanças de tamanho do container (nav toggle, fullscreen)
  _initResizeObserver()

  // 5. Estado em tempo real (REST inicial + WebSocket)
  startStatusPolling()
})

onBeforeUnmount(() => {
  stopStatusPolling()

  if (maintenanceMode.value) {
    exitMaintenanceMode()
  }

  destroyCurrentMap()

  document.removeEventListener('click', _hideCtxMenu)
  document.removeEventListener('keydown', _globalKeydown)
  if (_resizeObserver) { _resizeObserver.disconnect(); _resizeObserver = null }
  if (tooltipTimeout) clearTimeout(tooltipTimeout)
  if (_toastTimer) clearTimeout(_toastTimer)
  if (_badgeTimer) clearTimeout(_badgeTimer)
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

/* Mobile: menu é overlay fixo, mapa ocupa tela toda */
@media (max-width: 768px) {
  .custom-map-viewer {
    margin-left: 0 !important;
  }
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

.custom-map-viewer.fullscreen {
  z-index: 10000;
  margin-left: 0 !important;
  left: 0 !important;
}

/* ── Status poll badge (Fase 5.1) ── */
.status-poll-badge {
  position: absolute;
  bottom: 80px;
  left: 16px;
  z-index: 900;
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(15, 23, 42, 0.82);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 5px 12px;
  font-size: 0.75rem;
  color: #cbd5e1;
  pointer-events: none;
}
.spb-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  animation: spb-pulse 2s ease-in-out infinite;
}
.spb-dot--ok      { background: #10b981; }
.spb-dot--warning { background: #f59e0b; }
.spb-online { color: #6ee7b7; font-weight: 600; }
.spb-offline { color: #fca5a5; font-weight: 600; }
.spb-time   { color: #64748b; }
@keyframes spb-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.5; }
}

/* ==========================================
   LIGHT THEME OVERRIDES
   ========================================== */
:root[data-theme="light"] .custom-map-viewer,
html:not(.dark)[data-theme="light"] .custom-map-viewer {
  background: var(--bg-primary);
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

.panel-tabs {
  display: flex;
  padding: 16px 16px 0 16px;
  gap: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  overflow-x: auto;
}

/* ==========================================
   MAPBOX MARKERS - Garantir visibilidade
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

.custom-map-viewer.fullscreen {
  z-index: 10000;
  margin-left: 0 !important;
  left: 0 !important;
}

/* ==========================================
   LIGHT THEME OVERRIDES
   ========================================== */
:root[data-theme="light"] .custom-map-viewer,
html:not(.dark)[data-theme="light"] .custom-map-viewer {
  background: var(--bg-primary);
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

/* ── Notify sent badge ───────────────────────────────────────────────────── */
.map-fit-btn {
  position: absolute;
  bottom: 80px;
  right: 12px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  background: var(--bg-card, #1e2433);
  color: var(--text-primary, #e2e8f0);
  border: 1px solid var(--border-primary, rgba(255,255,255,0.08));
  border-radius: 8px;
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  transition: background 0.15s, transform 0.1s;
}
.map-fit-btn:hover {
  background: var(--bg-hover, #2a3347);
  transform: translateY(-1px);
}
.map-fit-btn:active {
  transform: translateY(0);
}

.notify-sent-badge {
  position: absolute;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9400;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px 10px 12px;
  background: rgba(10, 60, 40, 0.96);
  border: 1px solid #10b981;
  border-radius: 10px;
  color: #ecfdf5;
  font-size: 0.82rem;
  font-weight: 600;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.45);
  white-space: nowrap;
  pointer-events: all;
}
.nsb-close {
  display: flex;
  align-items: center;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  padding: 0;
  margin-left: 4px;
  transition: color 0.15s;
}
.nsb-close:hover { color: #fff; }

/* ── Toast notification ──────────────────────────────────────────────────── */
.map-toast {
  position: absolute;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9500;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 20px 11px 14px;
  border-radius: 10px;
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.45);
  font-size: 0.82rem;
  font-weight: 600;
  white-space: nowrap;
  pointer-events: none;
}

.map-toast--success {
  background: rgba(10, 60, 40, 0.96);
  border: 1px solid #10b981;
  color: #ecfdf5;
}

.map-toast--error {
  background: rgba(80, 10, 10, 0.96);
  border: 1px solid #ef4444;
  color: #fff1f2;
}

.map-toast--warning {
  background: rgba(70, 45, 0, 0.96);
  border: 1px solid #f59e0b;
  color: #fffbeb;
}

.map-toast__icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.25s ease;
}

.toast-slide-enter-from,
.toast-slide-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(10px);
}
</style>
