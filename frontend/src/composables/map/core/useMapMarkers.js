/**
 * Composable para gerenciamento de marcadores no mapa
 * Suporta Google Maps, Mapbox GL e Leaflet (OSM)
 */
import { ref } from 'vue'

export function useMapMarkers() {
  // Estado
  const activeMarkers = new Map() // { deviceId: markerInstance }
  
  /**
   * Cria um marcador compatível com o provedor atual
   */
  const createMarker = ({ lat, lng, title, icon, animation, mapInstance, provider, getActiveMapZoom, applyMapboxMarkerDimensions }) => {
    if (provider === 'google') {
      return new google.maps.Marker({
        position: { lat, lng },
        map: mapInstance,
        title,
        icon,
        animation
      })
    } else if (provider === 'mapbox') {
      // Verificar se mapboxgl está disponível
      if (typeof window === 'undefined' || !window.mapboxgl) {
        console.warn('[useMapMarkers] mapboxgl não está disponível ainda')
        return null
      }
      
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
      
      const marker = new window.mapboxgl.Marker(el)
        .setLngLat([lng, lat])
        .addTo(mapInstance)
      
      // Adicionar propriedades compatíveis
      marker._listeners = {}
      marker._status = icon?.statusKey || 'offline'
      marker.setMap = (map) => map ? marker.addTo(map) : marker.remove()
      marker.getPosition = () => ({ lat: () => lat, lng: () => lng })
      marker._applySize = (zoomOverride) => {
        if (!getActiveMapZoom || !applyMapboxMarkerDimensions) return
        const zoom = Number.isFinite(zoomOverride) ? zoomOverride : getActiveMapZoom()
        applyMapboxMarkerDimensions(marker, zoom)
      }
      marker.setIcon = (newIcon, applySize) => {
        if (newIcon?.fillColor) {
          el.style.backgroundColor = newIcon.fillColor
        }
        marker._status = newIcon?.statusKey || marker._status
        if (applySize) applySize()
      }
      
      return marker
    } else if (provider === 'osm') {
      // Criar ícone customizado para Leaflet
      const iconColor = icon?.fillColor || '#10b981'
      // eslint-disable-next-line no-undef
      const leafletIcon = L.divIcon({
        className: 'leaflet-custom-marker',
        html: `<div style="width: 30px; height: 30px; border-radius: 50%; background-color: ${iconColor}; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
      })
      
      // eslint-disable-next-line no-undef
      const marker = L.marker([lat, lng], { icon: leafletIcon, title })
        .addTo(mapInstance)
      
      // Adicionar propriedades compatíveis
      marker._listeners = {}
      marker.setMap = (map) => map ? marker.addTo(map) : marker.remove()
      marker.getPosition = () => ({ lat: () => lat, lng: () => lng })
      marker.setIcon = (newIcon) => {
        if (newIcon?.fillColor) {
          // eslint-disable-next-line no-undef
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
  
  /**
   * Adiciona listener de evento ao marcador (compatível com todos os provedores)
   */
  const addMarkerListener = (marker, event, callback, provider) => {
    if (provider === 'google') {
      marker.addListener(event, callback)
    } else if (provider === 'mapbox') {
      const eventMap = { click: 'click' }
      const mapboxEvent = eventMap[event] || event
      marker.getElement().addEventListener(mapboxEvent, callback)
      if (!marker._listeners[event]) marker._listeners[event] = []
      marker._listeners[event].push(callback)
    } else if (provider === 'osm') {
      const leafletEvent = event === 'click' ? 'click' : event
      marker.on(leafletEvent, callback)
      if (!marker._listeners[event]) marker._listeners[event] = []
      marker._listeners[event].push(callback)
    }
  }
  
  /**
   * Remove todos os listeners de um marcador
   */
  const clearMarkerListeners = (marker, provider) => {
    if (provider === 'google') {
      google.maps.event.clearInstanceListeners(marker)
    } else if (provider === 'mapbox') {
      if (marker._listeners) {
        Object.entries(marker._listeners).forEach(([event, callbacks]) => {
          callbacks.forEach(cb => marker.getElement().removeEventListener(event, cb))
        })
        marker._listeners = {}
      }
    } else if (provider === 'osm') {
      if (marker._listeners) {
        Object.entries(marker._listeners).forEach(([event, callbacks]) => {
          callbacks.forEach(cb => marker.off(event, cb))
        })
        marker._listeners = {}
      }
    }
  }
  
  /**
   * Obtém ícone do marcador baseado no status
   */
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
  
  /**
   * Atualiza marcadores no mapa usando diffing incremental
   */
  const updateMapMarkers = ({
    mapInstance,
    provider,
    selectedDeviceIds,
    availableDevices,
    sitesMap,
    isInitialLoad,
    animateItemId,
    onMarkerClick,
    updateMapboxMarkerSizes,
    getActiveMapZoom,
    applyMapboxMarkerDimensions,
    skipAutoFit = false
  }) => {
    if (!mapInstance) {
      console.warn('[useMapMarkers] Map instance não inicializado')
      return
    }
    
    console.log('[useMapMarkers] Atualizando markers com diffing')
    const currentDeviceIds = new Set(selectedDeviceIds)
    
    // 1. REMOVER markers de devices desmarcados
    activeMarkers.forEach((marker, id) => {
      if (!currentDeviceIds.has(id)) {
        console.log(`[useMapMarkers] Removendo marker do device ${id}`)
        clearMarkerListeners(marker, provider)
        marker.setMap(null)
        activeMarkers.delete(id)
      }
    })
    
    // 2. ADICIONAR/ATUALIZAR markers de devices selecionados
    const selectedDevices = availableDevices.filter(device => 
      currentDeviceIds.has(device.id) && device.lat && device.lng
    )
    
    console.log(`[useMapMarkers] ${selectedDevices.length} devices para processar`)
    
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
        console.error(`[useMapMarkers] Coordenadas inválidas para ${device.name}`)
        return
      }
      
      // Buscar site no mapa
      const actualSite = sitesMap.get(String(device.site))
      if (!actualSite) {
        console.warn(`[useMapMarkers] Site ${device.site} não encontrado para ${device.name}`)
        return
      }
      
      const shouldAnimate = isInitialLoad || (animateItemId && device.id === animateItemId)
      
      // Criar marker
      const marker = createMarker({
        lat,
        lng,
        title: device.name,
        icon: getMarkerIcon(device.status),
        animation: shouldAnimate && provider === 'google' ? google.maps.Animation.DROP : null,
        mapInstance,
        provider,
        getActiveMapZoom,
        applyMapboxMarkerDimensions
      })
      
      // Se marker não foi criado (ex: mapboxgl não disponível), pular
      if (!marker) {
        console.warn(`[useMapMarkers] Não foi possível criar marker para ${device.name}`)
        return
      }
      
      marker.siteData = actualSite
      
      // Adicionar listener de clique
      addMarkerListener(marker, 'click', () => {
        console.log('🔥 MARKER CLICADO! Device:', device.name, 'Site:', actualSite.name)
        onMarkerClick(device)
      }, provider)
      
      activeMarkers.set(device.id, marker)
    })

    // Atualizar tamanhos de markers Mapbox se necessário
    if (provider === 'mapbox' && updateMapboxMarkerSizes) {
      updateMapboxMarkerSizes()
    }
    
    console.log(`[useMapMarkers] ${activeMarkers.size} markers ativos após update`)
    
    // Ajustar bounds apenas na carga inicial (se não skipAutoFit)
    if (!skipAutoFit && isInitialLoad && activeMarkers.size > 0) {
      if (provider === 'google') {
        const bounds = new google.maps.LatLngBounds()
        activeMarkers.forEach(marker => bounds.extend(marker.getPosition()))
        mapInstance.fitBounds(bounds)
        
        if (activeMarkers.size === 1) {
          const listener = google.maps.event.addListener(mapInstance, 'idle', () => {
            if (mapInstance.getZoom() > 15) {
              mapInstance.setZoom(15)
            }
            google.maps.event.removeListener(listener)
          })
        }
      } else if (provider === 'mapbox') {
        if (window.mapboxgl) {
          const bounds = new window.mapboxgl.LngLatBounds()
          activeMarkers.forEach(marker => {
            if (typeof marker.getLngLat === 'function') {
              bounds.extend(marker.getLngLat())
            }
          })

          if (!bounds.isEmpty()) {
            mapInstance.fitBounds(bounds, { padding: 80, maxZoom: 15 })
          }
        }
      }
    }
    
    return activeMarkers.size
  }
  
  /**
   * Limpa todos os marcadores do mapa
   */
  const clearAllMarkers = (provider) => {
    activeMarkers.forEach((marker) => {
      clearMarkerListeners(marker, provider)
      marker.setMap(null)
    })
    activeMarkers.clear()
  }
  
  return {
    // Estado
    activeMarkers,
    
    // Funções
    createMarker,
    addMarkerListener,
    clearMarkerListeners,
    updateMapMarkers,
    getMarkerIcon,
    clearAllMarkers
  }
}
