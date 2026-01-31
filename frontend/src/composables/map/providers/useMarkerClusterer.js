/**
 * Composable para MarkerClusterer - Lazy Loaded
 * Carrega a biblioteca apenas quando clustering está ativado
 */

let MarkerClusterer = null
let clustererLoaded = false

export async function loadMarkerClusterer() {
  if (clustererLoaded && MarkerClusterer) {
    return MarkerClusterer
  }

  try {
    console.log('[useMarkerClusterer] Carregando biblioteca MarkerClusterer...')
    
    // Importação dinâmica da biblioteca
    const module = await import('@googlemaps/markerclusterer')
    MarkerClusterer = module.MarkerClusterer
    
    clustererLoaded = true
    console.log('[useMarkerClusterer] MarkerClusterer carregado com sucesso!')
    
    return MarkerClusterer
  } catch (error) {
    console.error('[useMarkerClusterer] Erro ao carregar MarkerClusterer:', error)
    throw new Error('Falha ao carregar biblioteca MarkerClusterer')
  }
}

export function isMarkerClustererLoaded() {
  return clustererLoaded
}

export function getMarkerClusterer() {
  if (!MarkerClusterer) {
    throw new Error('MarkerClusterer não foi carregado. Chame loadMarkerClusterer() primeiro.')
  }
  return MarkerClusterer
}
