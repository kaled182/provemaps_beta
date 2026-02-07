/**
 * Composable para Mapbox - Lazy Loaded
 * Carrega a biblioteca Mapbox apenas quando necessário
 */

let mapboxgl = null
let mapboxLoaded = false

export async function loadMapbox() {
  if (mapboxLoaded && mapboxgl) {
    return mapboxgl
  }

  try {
    console.log('[useMapbox] Carregando biblioteca Mapbox...')
    
    // Importação dinâmica da biblioteca E do CSS juntos
    const [mapboxModule] = await Promise.all([
      import('mapbox-gl'),
      import('mapbox-gl/dist/mapbox-gl.css')
    ])
    
    mapboxgl = mapboxModule.default
    
    mapboxLoaded = true
    console.log('[useMapbox] Mapbox carregado com sucesso!')
    console.log('[useMapbox] Versão:', mapboxgl.version)
    
    return mapboxgl
  } catch (error) {
    console.error('[useMapbox] Erro ao carregar Mapbox:', error)
    throw new Error('Falha ao carregar biblioteca Mapbox')
  }
}

export function isMapboxLoaded() {
  return mapboxLoaded
}

export function getMapbox() {
  if (!mapboxgl) {
    throw new Error('Mapbox não foi carregado. Chame loadMapbox() primeiro.')
  }
  return mapboxgl
}
