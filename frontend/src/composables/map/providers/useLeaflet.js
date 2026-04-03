/**
 * Composable para Leaflet (OpenStreetMap) - Lazy Loaded
 * Carrega a biblioteca Leaflet apenas quando necessário
 */

let L = null
let leafletLoaded = false

export async function loadLeaflet() {
  if (leafletLoaded && L) {
    return L
  }

  try {
    console.log('[useLeaflet] Carregando biblioteca Leaflet...')
    
    // Importação dinâmica da biblioteca E do CSS juntos
    const [leafletModule] = await Promise.all([
      import('leaflet'),
      import('leaflet/dist/leaflet.css')
    ])
    
    L = leafletModule.default
    
    leafletLoaded = true
    console.log('[useLeaflet] Leaflet carregado com sucesso!')
    console.log('[useLeaflet] Versão:', L.version)
    
    return L
  } catch (error) {
    console.error('[useLeaflet] Erro ao carregar Leaflet:', error)
    throw new Error('Falha ao carregar biblioteca Leaflet')
  }
}

export function isLeafletLoaded() {
  return leafletLoaded
}

export function getLeaflet() {
  if (!L) {
    throw new Error('Leaflet não foi carregado. Chame loadLeaflet() primeiro.')
  }
  return L
}
