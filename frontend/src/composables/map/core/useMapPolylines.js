/**
 * Composable para gerenciamento de polylines (cabos) no mapa
 * Suporta Google Maps, Mapbox GL e Leaflet (OSM)
 */
export function useMapPolylines() {
  // Estado
  const activePolylines = new Map() // { cableId: polylineInstance }
  
  /**
   * Cria uma polyline compatível com o provedor atual
   */
  const createPolyline = ({ path, strokeColor, strokeOpacity, strokeWeight, mapInstance, provider }) => {
    if (provider === 'google') {
      return new google.maps.Polyline({
        path,
        geodesic: true,
        strokeColor,
        strokeOpacity,
        strokeWeight,
        map: mapInstance
      })
    } else if (provider === 'mapbox') {
      // Mapbox usa layers e sources
      const sourceId = `polyline-${Date.now()}-${Math.random()}`
      const layerId = `layer-${sourceId}`
      
      mapInstance.addSource(sourceId, {
        type: 'geojson',
        data: {
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: path.map(p => [p.lng, p.lat])
          }
        }
      })
      
      mapInstance.addLayer({
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
            if (mapInstance.getLayer(layerId)) {
              mapInstance.removeLayer(layerId)
            }
            if (mapInstance.getSource(sourceId)) {
              mapInstance.removeSource(sourceId)
            }
          }
        },
        setOptions: ({ strokeColor: color, strokeOpacity: opacity, strokeWeight: weight }) => {
          if (mapInstance.getLayer(layerId)) {
            if (color) mapInstance.setPaintProperty(layerId, 'line-color', color)
            if (opacity !== undefined) mapInstance.setPaintProperty(layerId, 'line-opacity', opacity)
            if (weight) mapInstance.setPaintProperty(layerId, 'line-width', weight)
          }
        },
        addListener: (event, callback) => {
          if (event === 'click') {
            mapInstance.on('click', layerId, callback)
            if (!polylineObj._listeners[event]) polylineObj._listeners[event] = []
            polylineObj._listeners[event].push(callback)
          }
        }
      }

      return polylineObj
    } else if (provider === 'osm') {
      const latlngs = path.map(p => [p.lat, p.lng])
      // eslint-disable-next-line no-undef
      const polyline = L.polyline(latlngs, {
        color: strokeColor,
        opacity: strokeOpacity,
        weight: strokeWeight
      }).addTo(mapInstance)
      
      polyline._listeners = {}
      polyline.setMap = (map) => map ? polyline.addTo(map) : polyline.remove()
      
      return polyline
    }
  }
  
  /**
   * Adiciona listener de evento à polyline (compatível com todos os provedores)
   */
  const addPolylineListener = (polyline, event, callback, provider, mapInstance) => {
    if (provider === 'google') {
      polyline.addListener(event, callback)
    } else if (provider === 'mapbox') {
      if (polyline.layerId) {
        // Mapear eventos para Mapbox
        const mapboxEvent = event === 'click' ? 'click' : 
                           event === 'mouseover' ? 'mouseenter' : 
                           event === 'mouseout' ? 'mouseleave' : event
        
        mapInstance.on(mapboxEvent, polyline.layerId, callback)
        if (!polyline._listeners[event]) polyline._listeners[event] = []
        polyline._listeners[event].push({ event: mapboxEvent, callback })
      }
    } else if (provider === 'osm') {
      const leafletEvent = event === 'click' ? 'click' : 
                          event === 'mouseover' ? 'mouseover' : 
                          event === 'mouseout' ? 'mouseout' : event
      polyline.on(leafletEvent, callback)
      if (!polyline._listeners[event]) polyline._listeners[event] = []
      polyline._listeners[event].push(callback)
    }
  }
  
  /**
   * Remove todos os listeners de uma polyline
   */
  const clearPolylineListeners = (polyline, provider, mapInstance) => {
    if (provider === 'google') {
      google.maps.event.clearInstanceListeners(polyline)
    } else if (provider === 'mapbox') {
      if (polyline._listeners && polyline.layerId) {
        Object.entries(polyline._listeners).forEach(([event, listeners]) => {
          listeners.forEach(item => {
            const mapboxEvent = item.event || event
            const callback = item.callback || item
            mapInstance.off(mapboxEvent, polyline.layerId, callback)
          })
        })
        polyline._listeners = {}
      }
    } else if (provider === 'osm') {
      if (polyline._listeners) {
        Object.entries(polyline._listeners).forEach(([event, callbacks]) => {
          callbacks.forEach(cb => polyline.off(event, cb))
        })
        polyline._listeners = {}
      }
    }
  }
  
  /**
   * Atualiza polylines de cabos no mapa usando diffing incremental
   */
  const updateCablePolylines = ({
    mapInstance,
    provider,
    selectedCableIds,
    availableCables,
    isDarkMode,
    onPolylineClick,
    onPolylineHover,
    onPolylineUnhover
  }) => {
    if (!mapInstance) {
      console.warn('[useMapPolylines] Map instance não inicializado')
      return
    }
    
    console.log('[useMapPolylines] Atualizando polylines com diffing')
    const currentCableIds = new Set(selectedCableIds)
    
    // Detectar tema ativo para ajustar espessura da linha
    const strokeWeight = isDarkMode ? 2 : 3
    const strokeOpacity = isDarkMode ? 0.7 : 0.8
    
    // 1. REMOVER polylines de cabos desmarcados
    activePolylines.forEach((polyline, id) => {
      if (!currentCableIds.has(id)) {
        console.log(`[useMapPolylines] Removendo polyline do cabo ${id}`)
        clearPolylineListeners(polyline, provider, mapInstance)
        if (typeof polyline.setMap === 'function') {
          polyline.setMap(null)
        } else if (provider === 'mapbox') {
          if (polyline.layerId && mapInstance.getLayer(polyline.layerId)) {
            mapInstance.removeLayer(polyline.layerId)
          }
          if (polyline.sourceId && mapInstance.getSource(polyline.sourceId)) {
            mapInstance.removeSource(polyline.sourceId)
          }
        }
        activePolylines.delete(id)
      }
    })
    
    // 2. ADICIONAR/ATUALIZAR polylines de cabos selecionados
    const selectedCables = availableCables.filter(cable => 
      currentCableIds.has(cable.id) && cable.path_coordinates && cable.path_coordinates.length > 0
    )
    
    console.log(`[useMapPolylines] ${selectedCables.length} cabos para processar`)
    
    const statusColors = {
      // API cable.status values
      up: '#10b981',
      down: '#ef4444',
      degraded: '#f59e0b',
      // Aliases used by legacy/optical status
      online: '#10b981',
      offline: '#ef4444',
      warning: '#f59e0b',
      critical: '#dc2626',
      unknown: '#6b7280'
    }
    
    selectedCables.forEach((cable) => {
      // Se já existe, atualizar cor E espessura baseado no tema
      if (activePolylines.has(cable.id)) {
        const existingPolyline = activePolylines.get(cable.id)
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
        console.warn(`[useMapPolylines] Cabo ${cable.name} sem coordenadas suficientes`)
        return
      }
      
      // Criar polyline
      const polyline = createPolyline({
        path: validPath,
        strokeColor: statusColors[cable.status] || statusColors.unknown,
        strokeOpacity: strokeOpacity,
        strokeWeight: strokeWeight,
        mapInstance,
        provider
      })
      
      polyline.cableData = cable
      
      // Adicionar listener de clique
      if (onPolylineClick) {
        addPolylineListener(polyline, 'click', () => {
          onPolylineClick(cable)
        }, provider, mapInstance)
      }
      
      // Adicionar listeners de hover para tooltip
      if (onPolylineHover) {
        addPolylineListener(polyline, 'mouseover', (event) => {
          console.log('[useMapPolylines] Cable hover:', cable.label)
          onPolylineHover(cable, event)
          // Destacar visualmente no hover
          if (typeof polyline.setOptions === 'function') {
            polyline.setOptions({ 
              strokeWeight: strokeWeight + 2,
              strokeOpacity: 1
            })
          } else if (provider === 'mapbox' && mapInstance.getLayer(polyline.layerId)) {
            // Mapbox usa setPaintProperty
            mapInstance.setPaintProperty(polyline.layerId, 'line-width', strokeWeight + 2)
            mapInstance.setPaintProperty(polyline.layerId, 'line-opacity', 1)
          }
        }, provider, mapInstance)
      }
      
      if (onPolylineUnhover) {
        addPolylineListener(polyline, 'mouseout', () => {
          console.log('[useMapPolylines] Cable unhover')
          onPolylineUnhover()
          // Restaurar estilo original
          if (typeof polyline.setOptions === 'function') {
            polyline.setOptions({ 
              strokeWeight: strokeWeight,
              strokeOpacity: strokeOpacity
            })
          } else if (provider === 'mapbox' && mapInstance.getLayer(polyline.layerId)) {
            // Mapbox usa setPaintProperty
            mapInstance.setPaintProperty(polyline.layerId, 'line-width', strokeWeight)
            mapInstance.setPaintProperty(polyline.layerId, 'line-opacity', strokeOpacity)
          }
        }, provider, mapInstance)
      }
      
      activePolylines.set(cable.id, polyline)
    })
    
    console.log(`[useMapPolylines] ${activePolylines.size} polylines ativas`)
    
    return activePolylines.size
  }
  
  /**
   * Destaca um cabo quando o mouse passa sobre o item no painel
   */
  const highlightCable = (cableId, isDarkMode) => {
    const polyline = activePolylines.get(cableId)
    if (!polyline) return
    
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
  
  /**
   * Remove destaque do cabo
   */
  const unhighlightCable = (cableId) => {
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
  
  /**
   * Limpa todas as polylines do mapa
   */
  const clearAllPolylines = (provider, mapInstance) => {
    activePolylines.forEach((polyline) => {
      clearPolylineListeners(polyline, provider, mapInstance)
      if (typeof polyline.setMap === 'function') {
        polyline.setMap(null)
      } else if (provider === 'mapbox') {
        if (polyline.layerId && mapInstance.getLayer(polyline.layerId)) {
          mapInstance.removeLayer(polyline.layerId)
        }
        if (polyline.sourceId && mapInstance.getSource(polyline.sourceId)) {
          mapInstance.removeSource(polyline.sourceId)
        }
      }
    })
    activePolylines.clear()
  }
  
  return {
    // Estado
    activePolylines,
    
    // Funções
    createPolyline,
    addPolylineListener,
    clearPolylineListeners,
    updateCablePolylines,
    highlightCable,
    unhighlightCable,
    clearAllPolylines
  }
}
