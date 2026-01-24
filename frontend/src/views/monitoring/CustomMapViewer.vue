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
              <span class="badge">{{ getSelectedCount(category.key) }}</span>
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
              <div 
                v-for="item in filteredItems" 
                :key="item.id"
                class="item-row"
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
                    {{ item.status }}
                  </span>
                  <button @click="focusOnItem(item)" class="btn-focus">
                    <i class="fas fa-crosshairs"></i>
                  </button>
                </div>
              </div>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { loadGoogleMaps } from '@/utils/googleMapsLoader'
import { useUiStore } from '@/stores/ui'
import SiteDetailsModal from '@/components/SiteDetailsModal.vue'

const route = useRoute()
const { get, post } = useApi()
const uiStore = useUiStore()

const mapContainer = ref(null)
const googleMap = ref(null)
const markers = ref([])
const cablePolylines = ref([])
const allOverlays = ref([]) // Tracking de TODAS as overlays
const showInventoryPanel = ref(false)
const activeCategory = ref('devices')
const searchQuery = ref('')
const isFullscreen = ref(false)
const isInitialLoad = ref(true) // Flag para controlar animação inicial

// Modal de detalhes do site
const showSiteModal = ref(false)
const selectedSite = ref(null)

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

const inventoryCategories = [
  { key: 'devices', label: 'Sites', icon: 'fas fa-map-marker-alt' },
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

const getSelectedCount = (category) => {
  return selectedItems.value[category]?.length || 0
}

const isItemSelected = (itemId) => {
  return selectedItems.value[activeCategory.value]?.includes(itemId)
}

// Função unificada para atualizar todo o mapa (markers + polylines)
const updateMap = (animateItemId = null) => {
  if (!googleMap.value) {
    console.warn('[CustomMapViewer] Google Map não inicializado ainda')
    return
  }
  
  console.log('[CustomMapViewer] updateMap chamado - limpando tudo e redesenhando')
  // LIMPAR TUDO PRIMEIRO
  clearAllOverlays()
  // Agora criar novas overlays (passando qual item animar)
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

// Função para limpar COMPLETAMENTE todas as overlays do mapa
const clearAllOverlays = () => {
  console.log('[CustomMapViewer] Limpando TODAS as overlays antigas')
  console.log('[CustomMapViewer] Total overlays rastreadas:', allOverlays.value.length)
  
  // Limpar todas as overlays rastreadas
  allOverlays.value.forEach((overlay, idx) => {
    try {
      if (overlay.infoWindow) {
        overlay.infoWindow.close()
        overlay.infoWindow = null
      }
      google.maps.event.clearInstanceListeners(overlay)
      if (typeof overlay.setVisible === 'function') {
        overlay.setVisible(false)
      }
      overlay.setMap(null)
      console.log(`[CustomMapViewer] Overlay ${idx + 1} removida`)
    } catch (e) {
      console.error(`[CustomMapViewer] Erro ao remover overlay ${idx + 1}:`, e)
    }
  })
  
  allOverlays.value = []
  markers.value = []
  cablePolylines.value = []
  console.log('[CustomMapViewer] Todas as overlays removidas')
}

const focusOnItem = (item) => {
  if (item.lat && item.lng && googleMap.value) {
    googleMap.value.setCenter({ lat: item.lat, lng: item.lng })
    googleMap.value.setZoom(15)
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
    
    // 1. Carregar Sites com devices
    const sitesResponse = await fetch('/api/v1/sites/?page_size=500', {
      credentials: 'include'
    })
    
    if (!sitesResponse.ok) {
      throw new Error(`Erro ao carregar sites: ${sitesResponse.status}`)
    }
    
    const sitesData = await sitesResponse.json()
    const sites = Array.isArray(sitesData) ? sitesData : (sitesData.results || [])
    console.log(`[CustomMapViewer] ${sites.length} sites carregados`)
    
    // 2. Carregar hosts do dashboard (dispositivos com status)
    const hostsResponse = await fetch('/maps_view/api/dashboard/data/', {
      credentials: 'include'
    })
    
    if (!hostsResponse.ok) {
      throw new Error(`Erro ao carregar hosts: ${hostsResponse.status}`)
    }
    
    const hostsData = await hostsResponse.json()
    const hostsArray = hostsData.hosts_status || hostsData.hosts || []
    console.log(`[CustomMapViewer] ${hostsArray.length} hosts carregados`)
    
    // 3. Criar mapa de hosts por ID para lookup rápido
    const hostsMap = new Map()
    hostsArray.forEach(host => {
      if (host.id) {
        hostsMap.set(String(host.id), host)
      }
    })
    
    // 4. Processar sites e criar devices com localização
    const devicesWithLocation = []
    
    sites.forEach(site => {
      if (!site) return
      
      const lat = parseFloat(site.latitude)
      const lng = parseFloat(site.longitude)
      
      // Só adicionar se tiver coordenadas válidas
      if (isNaN(lat) || isNaN(lng)) return
      
      // Pegar status do host se existir
      const host = hostsMap.get(String(site.id))
      
      devicesWithLocation.push({
        id: site.id,
        name: site.name || site.display_name || `Site ${site.id}`,
        type: site.type || 'site',
        lat: lat,
        lng: lng,
        status: host?.status || 'unknown',
        ip: host?.ip || host?.primary_ip || site.ip_address,
        location: site.city || site.location || 'N/A',
        site_id: site.id,
        device_count: site.device_count || site.devices_count || 0
      })
    })
    
    availableItems.value.devices = devicesWithLocation
    console.log(`[CustomMapViewer] ${devicesWithLocation.length} devices com localização processados`)
    
    // 5. Carregar cabos de fibra com rotas
    try {
      const cablesResponse = await fetch('/api/v1/fiber-cables/', {
        credentials: 'include'
      })
      
      if (cablesResponse.ok) {
        const cablesData = await cablesResponse.json()
        const cables = Array.isArray(cablesData) ? cablesData : (cablesData.results || [])
        
        console.log('[CustomMapViewer] Raw cables data:', cables.slice(0, 2))
        
        availableItems.value.cables = cables.map(cable => {
          const pathCoords = cable.path_coordinates || []
          console.log(`[CustomMapViewer] Cabo ${cable.name}:`, {
            id: cable.id,
            has_path: !!cable.path_coordinates,
            path_length: pathCoords.length,
            first_coord: pathCoords[0]
          })
          
          return {
            id: cable.id,
            name: cable.name,
            status: cable.status || 'unknown',
            description: cable.description || '',
            path_coordinates: pathCoords,
            site_a_name: cable.site_a_name,
            site_b_name: cable.site_b_name,
            length_km: cable.length_km
          }
        })
        
        console.log(`[CustomMapViewer] ${availableItems.value.cables.length} cabos carregados`)
      }
    } catch (error) {
      console.warn('[CustomMapViewer] Erro ao carregar cabos:', error)
      availableItems.value.cables = []
    }
    
    // 6. Cameras e Racks (placeholders por enquanto)
    availableItems.value.cameras = []
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

const initMap = async () => {
  if (!mapContainer.value) {
    console.warn('[CustomMapViewer] Container do mapa não encontrado')
    return
  }
  
  try {
    // Carregar Google Maps API se necessário
    console.log('[CustomMapViewer] Iniciando carregamento do Google Maps...')
    await loadGoogleMaps()
    
    if (!window.google?.maps) {
      throw new Error('Google Maps API não carregou corretamente')
    }
    
    console.log('[CustomMapViewer] Google Maps API disponível, criando mapa...')
    console.log('[CustomMapViewer] Tema atual:', uiStore.theme)
    
    const defaultCenter = { lat: -15.8267, lng: -47.9218 } // Brasília
    
    googleMap.value = new google.maps.Map(mapContainer.value, {
      center: defaultCenter,
      zoom: 12,
      mapTypeId: 'roadmap',
      styles: getMapStyles(uiStore.theme),
      mapTypeControl: true,
      streetViewControl: true,
      fullscreenControl: true,
      zoomControl: true
    })
    
    console.log('[CustomMapViewer] Mapa criado com sucesso - Tipo:', googleMap.value.getMapTypeId())
    console.log('[CustomMapViewer] Mapa zoom:', googleMap.value.getZoom())
    console.log('[CustomMapViewer] Mapa center:', googleMap.value.getCenter().toString())
    
    // Atualizar mapa completo após criar
    updateMap()
  } catch (error) {
    console.error('[CustomMapViewer] Erro ao inicializar mapa:', error)
  }
}

const updateCablePolylines = () => {
  if (!googleMap.value) {
    console.warn('[CustomMapViewer] Google Map não inicializado ainda')
    return
  }
  
  console.log('[CustomMapViewer] updateCablePolylines chamado')
  console.log('[CustomMapViewer] Total cabos disponíveis:', availableItems.value.cables.length)
  console.log('[CustomMapViewer] Total cabos selecionados:', selectedItems.value.cables.length)
  
  // Adicionar polylines dos cabos selecionados
  const selectedCables = availableItems.value.cables.filter(cable => 
    selectedItems.value.cables.includes(cable.id) && cable.path_coordinates && cable.path_coordinates.length > 0
  )
  
  console.log(`[CustomMapViewer] ${selectedCables.length} cabos filtrados para desenhar polylines`)
  
  selectedCables.forEach((cable, index) => {
    console.log(`[CustomMapViewer] Desenhando cabo ${index + 1}:`, {
      name: cable.name,
      points: cable.path_coordinates.length,
      status: cable.status
    })
    
    // Converter coordenadas para formato Google Maps
    const path = cable.path_coordinates.map(coord => ({
      lat: parseFloat(coord.lat),
      lng: parseFloat(coord.lng)
    }))
    
    // Validar coordenadas
    const validPath = path.filter(point => !isNaN(point.lat) && !isNaN(point.lng))
    
    if (validPath.length < 2) {
      console.warn(`[CustomMapViewer] Cabo ${cable.name} não tem coordenadas suficientes (${validPath.length}))`)
      return
    }
    
    // Cor baseada no status
    const statusColors = {
      up: '#10b981',
      down: '#ef4444',
      degraded: '#f59e0b',
      unknown: '#6b7280'
    }
    
    const polyline = new google.maps.Polyline({
      path: validPath,
      geodesic: true,
      strokeColor: statusColors[cable.status] || statusColors.unknown,
      strokeOpacity: 0.8,
      strokeWeight: 3,
      map: googleMap.value
    })
    
    // InfoWindow para o cabo
    const infoContent = `
      <div style="color: #000; padding: 12px; max-width: 250px;">
        <h3 style="margin: 0 0 8px 0; font-size: 16px; font-weight: 700;">${cable.name}</h3>
        <div style="font-size: 14px; line-height: 1.6;">
          <p style="margin: 4px 0;"><strong>De:</strong> ${cable.site_a_name || 'N/A'}</p>
          <p style="margin: 4px 0;"><strong>Para:</strong> ${cable.site_b_name || 'N/A'}</p>
          <p style="margin: 4px 0;"><strong>Status:</strong> <span style="color: ${statusColors[cable.status] || statusColors.unknown}; font-weight: 700;">${cable.status || 'N/A'}</span></p>
          <p style="margin: 4px 0;"><strong>Comprimento:</strong> ${cable.length_km ? cable.length_km + ' km' : 'N/A'}</p>
          <p style="margin: 4px 0;"><strong>Pontos:</strong> ${validPath.length}</p>
        </div>
      </div>
    `
    
    const infoWindow = new google.maps.InfoWindow({
      content: infoContent
    })
    
    // Anexar InfoWindow ao polyline ANTES de adicionar listener
    polyline.infoWindow = infoWindow
    
    polyline.addListener('click', (event) => {
      // Fechar outras info windows
      cablePolylines.value.forEach(p => {
        if (p.infoWindow) p.infoWindow.close()
      })
      markers.value.forEach(m => {
        if (m.infoWindow) m.infoWindow.close()
      })
      
      infoWindow.setPosition(event.latLng)
      infoWindow.open(googleMap.value)
    })
    
    cablePolylines.value.push(polyline)
    allOverlays.value.push(polyline) // Registrar para limpeza global
  })
  
  console.log(`[CustomMapViewer] ${cablePolylines.value.length} polylines desenhadas no mapa`)
}

const updateMapMarkers = (animateItemId = null) => {
  if (!googleMap.value) {
    console.warn('[CustomMapViewer] Google Map não inicializado ainda')
    return
  }
  
  console.log('[CustomMapViewer] updateMapMarkers chamado')
  console.log('[CustomMapViewer] Item para animar:', animateItemId)
  console.log('[CustomMapViewer] É carregamento inicial?', isInitialLoad.value)
  console.log('[CustomMapViewer] Total devices disponíveis:', availableItems.value.devices.length)
  console.log('[CustomMapViewer] Total devices selecionados:', selectedItems.value.devices.length)
  
  // Adicionar markers dos dispositivos selecionados
  const selectedDevices = availableItems.value.devices.filter(device => 
    selectedItems.value.devices.includes(device.id) && device.lat && device.lng
  )
  
  console.log(`[CustomMapViewer] ${selectedDevices.length} devices filtrados para criar markers`)
  
  if (selectedDevices.length === 0) {
    console.warn('[CustomMapViewer] Nenhum device selecionado com lat/lng válidos!')
    console.log('[CustomMapViewer] Devices disponíveis:', availableItems.value.devices.slice(0, 3))
    console.log('[CustomMapViewer] IDs selecionados:', selectedItems.value.devices.slice(0, 5))
  }
  
  selectedDevices.forEach((device, index) => {
    const lat = parseFloat(device.lat)
    const lng = parseFloat(device.lng)
    
    console.log(`[CustomMapViewer] Criando marker ${index + 1}:`, {
      name: device.name,
      lat: lat,
      lng: lng,
      status: device.status,
      latValid: !isNaN(lat),
      lngValid: !isNaN(lng)
    })
    
    // Validar coordenadas
    if (isNaN(lat) || isNaN(lng)) {
      console.error(`[CustomMapViewer] Coordenadas inválidas para ${device.name}`)
      return
    }
    
    const position = { lat: lat, lng: lng }
    
    console.log(`[CustomMapViewer] Posição do marker ${index + 1}:`, position)
    console.log(`[CustomMapViewer] Mapa existe?`, !!googleMap.value)
    
    // Determinar se deve animar este marker
    // Anima se: 1) é carregamento inicial OU 2) é o item específico sendo marcado
    const shouldAnimate = isInitialLoad.value || (animateItemId && device.id === animateItemId)
    
    const marker = new google.maps.Marker({
      position: position,
      map: googleMap.value,
      title: device.name,
      icon: getMarkerIcon(device.status),
      animation: shouldAnimate ? google.maps.Animation.DROP : null
    })
    
    console.log(`[CustomMapViewer] Marker ${index + 1} criado:`, {
      position: marker.getPosition(),
      map: !!marker.getMap(),
      visible: marker.getVisible(),
      animated: shouldAnimate
    })
    
    // Armazenar dados do site no marker para usar no modal
    marker.siteData = device
    
    marker.addListener('click', () => {
      // Abrir modal de detalhes do site
      selectedSite.value = marker.siteData
      showSiteModal.value = true
      console.log('[CustomMapViewer] Abrindo modal para site:', marker.siteData.name)
    })
    
    markers.value.push(marker)
    allOverlays.value.push(marker) // Registrar para limpeza global
  })
  
  // Se houver markers, ajustar bounds do mapa
  if (markers.value.length > 0) {
    console.log(`[CustomMapViewer] Ajustando bounds para ${markers.value.length} markers`)
    
    const bounds = new google.maps.LatLngBounds()
    markers.value.forEach(marker => {
      const pos = marker.getPosition()
      console.log(`[CustomMapViewer] Adicionando posição ao bounds:`, { lat: pos.lat(), lng: pos.lng() })
      bounds.extend(pos)
    })
    
    console.log(`[CustomMapViewer] Bounds calculados:`, {
      ne: { lat: bounds.getNorthEast().lat(), lng: bounds.getNorthEast().lng() },
      sw: { lat: bounds.getSouthWest().lat(), lng: bounds.getSouthWest().lng() }
    })
    
    googleMap.value.fitBounds(bounds)
    
    console.log(`[CustomMapViewer] fitBounds aplicado`)
    
    // Se for apenas um marker, não dar zoom muito próximo
    if (markers.value.length === 1) {
      const listener = google.maps.event.addListener(googleMap.value, 'idle', () => {
        if (googleMap.value.getZoom() > 15) {
          googleMap.value.setZoom(15)
        }
        google.maps.event.removeListener(listener)
      })
    }
    
    console.log(`[CustomMapViewer] Markers configurados e visíveis no mapa`)
  } else {
    console.warn('[CustomMapViewer] Nenhum marker para exibir!')
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

// Função para obter estilos do mapa baseado no tema
const getMapStyles = (theme) => {
  if (theme === 'light') {
    // Estilo claro: mantém as cores padrão do Google Maps com ajustes sutis
    return [
      { elementType: 'geometry', stylers: [{ color: '#f5f5f5' }] },
      { elementType: 'labels.text.fill', stylers: [{ color: '#616161' }] },
      { elementType: 'labels.text.stroke', stylers: [{ color: '#f5f5f5' }] },
      { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#ffffff' }] },
      { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#e5e5e5' }] },
      { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#757575' }] },
      { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#c9e6f7' }] },
      { featureType: 'water', elementType: 'labels.text.fill', stylers: [{ color: '#4e91c7' }] },
      { featureType: 'poi', elementType: 'geometry', stylers: [{ color: '#eeeeee' }] },
      { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#e5f4e3' }] }
    ]
  } else {
    // Estilo escuro
    return [
      { elementType: 'geometry', stylers: [{ color: '#1d2c4d' }] },
      { elementType: 'labels.text.fill', stylers: [{ color: '#8ec3b9' }] },
      { elementType: 'labels.text.stroke', stylers: [{ color: '#1a3646' }] },
      { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#38414e' }] },
      { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#212a37' }] },
      { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#9ca5b3' }] },
      { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0e1626' }] },
      { featureType: 'water', elementType: 'labels.text.fill', stylers: [{ color: '#4e6d70' }] }
    ]
  }
}

const getMarkerIcon = (status) => {
  const colors = {
    online: '#10b981',
    warning: '#f59e0b',
    critical: '#ef4444',
    offline: '#6b7280'
  }
  
  return {
    path: google.maps.SymbolPath.CIRCLE,
    fillColor: colors[status] || colors.offline,
    fillOpacity: 0.9,
    strokeColor: '#fff',
    strokeWeight: 2,
    scale: 8
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

// Observar mudanças no tema e atualizar estilos do mapa
watch(() => uiStore.theme, (newTheme) => {
  if (googleMap.value) {
    console.log('[CustomMapViewer] Tema alterado para:', newTheme)
    googleMap.value.setOptions({
      styles: getMapStyles(newTheme)
    })
    console.log('[CustomMapViewer] Estilos do mapa atualizados')
  }
})

// Observar mudanças nos items selecionados e atualizar mapa
watch(() => selectedItems.value.devices, () => {
  if (googleMap.value) {
    console.log('[CustomMapViewer] Devices selecionados alterados')
    updateMapMarkers()
  }
}, { deep: true })

watch(() => selectedItems.value.cables, () => {
  if (googleMap.value) {
    console.log('[CustomMapViewer] Cabos selecionados alterados')
    updateCablePolylines()
  }
}, { deep: true })

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
  
  // 4. Inicializar Google Maps
  await initMap()
  
  // 5. Marcar que o carregamento inicial foi concluído
  // Aguardar um pouco para garantir que a animação inicial aconteceu
  setTimeout(() => {
    isInitialLoad.value = false
    console.log('[CustomMapViewer] Carregamento inicial concluído - animações desativadas')
  }, 2000)
  
  console.log('[CustomMapViewer] Inicialização completa')
})

onBeforeUnmount(() => {
  window.removeEventListener('google-maps-loaded', initMap)
})
</script>

<style scoped>
.custom-map-viewer {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #1a1d2e;
  display: flex;
  flex-direction: column;
  /* Ajustar margem baseado no estado do menu */
  margin-left: var(--nav-menu-width, 72px);
  transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
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
}

.item-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.item-name {
  color: #fff;
  font-size: 14px;
}

.item-info {
  display: flex;
  align-items: center;
  gap: 8px;
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
</style>
