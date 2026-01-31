/**
 * Map Styles Utility
 * 
 * Centralized map styling configuration that removes grid lines
 * and applies light/dark themes to Google Maps.
 */

/**
 * Get Google Maps styles based on theme
 * Removes grid lines and applies color scheme
 * @param {string} theme - 'light', 'dark', or 'auto'
 * @param {string|null} systemTheme - System theme preference when theme is 'auto'
 * @returns {Array} Google Maps styles array
 */
export function getMapStyles(theme = 'light', systemTheme = null) {
  // Resolve auto theme to light or dark
  const effectiveTheme = theme === 'auto' 
    ? (systemTheme || 'light') 
    : theme

  if (effectiveTheme === 'dark') {
    return getDarkMapStyles()
  } else {
    return getLightMapStyles()
  }
}

/**
 * Light theme map styles
 * Clean appearance with subtle colors, no grid lines
 */
function getLightMapStyles() {
  return [
    // CRITICAL: Remove ALL border strokes (quadrantes/grid lines)
    {
      featureType: 'all',
      elementType: 'geometry.stroke',
      stylers: [{ visibility: 'off' }]
    },
    // Remove ALL administrative borders (country, state, city, etc.)
    {
      featureType: 'administrative',
      elementType: 'geometry.stroke',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'administrative',
      elementType: 'geometry',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'administrative.country',
      elementType: 'geometry.stroke',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'administrative.province',
      elementType: 'geometry.stroke',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'administrative.locality',
      elementType: 'geometry.stroke',
      stylers: [{ visibility: 'off' }]
    },
    // Hide all labels on administrative boundaries
    {
      featureType: 'administrative',
      elementType: 'labels',
      stylers: [{ visibility: 'simplified' }]
    },
    // Base map - PALETA OFICIAL GOOGLE MAPS 2024+ (tons frios)
    {
      elementType: 'geometry',
      stylers: [{ color: '#F1F3F4' }]  // Cinza Google "Cloud" oficial (mais frio)
    },
    {
      elementType: 'labels.text.fill',
      stylers: [{ color: '#70757A' }]  // Cinza médio oficial para textos
    },
    {
      elementType: 'labels.text.stroke',
      stylers: [{ color: '#FFFFFF', weight: 3 }]  // Branco puro
    },
    // Landscape - cinza frio oficial
    {
      featureType: 'landscape',
      elementType: 'geometry',
      stylers: [{ color: '#F1F3F4' }]  // Cinza Cloud (tom frio)
    },
    {
      featureType: 'landscape.natural',
      elementType: 'geometry',
      stylers: [{ color: '#D2EBD8' }]  // Verde menta suave (oficial)
    },
    {
      featureType: 'landscape.natural.terrain',
      elementType: 'geometry',
      stylers: [{ color: '#F1F3F4' }]  // Cinza Cloud
    },
    // Roads - branco puro para contraste
    {
      featureType: 'road',
      elementType: 'geometry',
      stylers: [{ color: '#FFFFFF' }]  // Branco puro (oficial)
    },
    {
      featureType: 'road',
      elementType: 'geometry.stroke',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'road.highway',
      elementType: 'geometry.fill',
      stylers: [{ color: '#FEE191' }]  // Amarelo suave oficial (nova paleta)
    },
    {
      featureType: 'road.highway',
      elementType: 'geometry.stroke',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'road.arterial',
      elementType: 'geometry',
      stylers: [{ color: '#FFFFFF' }]  // Branco puro
    },
    {
      featureType: 'road.local',
      elementType: 'geometry',
      stylers: [{ color: '#FFFFFF' }]  // Branco puro
    },
    {
      featureType: 'road',
      elementType: 'labels.text.fill',
      stylers: [{ color: '#70757A' }]  // Cinza médio
    },
    {
      featureType: 'road',
      elementType: 'labels.text.stroke',
      stylers: [{ color: '#FFFFFF', weight: 2 }]
    },
    // Water - azul vibrante moderno (EXATO da nova versão)
    {
      featureType: 'water',
      elementType: 'geometry',
      stylers: [{ color: '#AADAFF' }]  // Azul exato da nova versão Google Maps
    },
    {
      featureType: 'water',
      elementType: 'labels.text.fill',
      stylers: [{ color: '#4A90C7' }]  // Azul escuro para texto
    },
    {
      featureType: 'water',
      elementType: 'labels.text.stroke',
      stylers: [{ color: '#FFFFFF', weight: 2 }]
    },
    // POI - verde menta suave
    {
      featureType: 'poi',
      elementType: 'geometry',
      stylers: [{ color: '#D2EBD8' }]  // Verde menta suave
    },
    {
      featureType: 'poi.park',
      elementType: 'geometry',
      stylers: [{ color: '#D2EBD8' }]  // Verde menta suave (oficial)
    },
    {
      featureType: 'poi.park',
      elementType: 'labels.text.fill',
      stylers: [{ color: '#5A7D5A' }]  // Verde escuro
    },
    {
      featureType: 'poi.business',
      elementType: 'geometry',
      stylers: [{ color: '#F1F3F4' }]  // Cinza Cloud
    },
    {
      featureType: 'poi.medical',
      elementType: 'geometry',
      stylers: [{ color: '#FFCDD2' }]
    },
    {
      featureType: 'poi.school',
      elementType: 'geometry',
      stylers: [{ color: '#FFF9C4' }]
    },
    // Transit
    {
      featureType: 'transit',
      elementType: 'geometry',
      stylers: [{ color: '#F1F3F4' }]  // Cinza Cloud
    },
    {
      featureType: 'transit.line',
      elementType: 'geometry',
      stylers: [{ color: '#E0E0E0' }]
    },
    {
      featureType: 'transit.station',
      elementType: 'geometry',
      stylers: [{ color: '#E0E0E0' }]
    },
    // Hide minor administrative borders completely
    {
      featureType: 'administrative.locality',
      elementType: 'geometry',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'administrative.neighborhood',
      elementType: 'geometry',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'administrative.land_parcel',
      elementType: 'geometry',
      stylers: [{ visibility: 'off' }]
    }
  ]
}

/**
 * Dark theme map styles
 * Official Google "Night" mode appearance
 */
function getDarkMapStyles() {
  return [
    // CRÍTICO: Remover grades/quadrantes
    {
      featureType: 'all',
      elementType: 'geometry.stroke',
      stylers: [{ visibility: 'off' }]
    },
    // Remove ALL administrative borders (country, state, city, etc.)
    {
      featureType: 'administrative',
      elementType: 'geometry.stroke',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'administrative',
      elementType: 'geometry',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'administrative.country',
      elementType: 'geometry.stroke',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'administrative.province',
      elementType: 'geometry.stroke',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'administrative.locality',
      elementType: 'geometry.stroke',
      stylers: [{ visibility: 'off' }]
    },
    // Fundo Geral (Landscape) - Azul noite oficial
    {
      featureType: 'landscape',
      elementType: 'geometry',
      stylers: [{ color: '#242f3e' }]  // Azul noite oficial Google
    },
    // Água (Deep Blue)
    {
      featureType: 'water',
      elementType: 'geometry',
      stylers: [{ color: '#17263c' }]  // Azul profundo
    },
    {
      featureType: 'water',
      elementType: 'labels.text.fill',
      stylers: [{ color: '#515c6d' }]
    },
    {
      featureType: 'water',
      elementType: 'labels.text.stroke',
      stylers: [{ color: '#17263c' }]
    },
    // Textos e Rótulos
    {
      elementType: 'labels.text.fill',
      stylers: [{ color: '#d59563' }]  // Tom pêssego/laranja suave para legibilidade
    },
    {
      elementType: 'labels.text.stroke',
      stylers: [{ color: '#242f3e' }]  // Fundo escuro
    },
    // Rodovias (Highways)
    {
      featureType: 'road.highway',
      elementType: 'geometry',
      stylers: [{ color: '#746855' }]  // Tom acastanhado
    },
    {
      featureType: 'road.highway',
      elementType: 'geometry.stroke',
      stylers: [{ color: '#1f2835' }]  // Borda escura
    },
    // Estradas Arteriais e Locais
    {
      featureType: 'road',
      elementType: 'geometry',
      stylers: [{ color: '#38414e' }]  // Cinza azulado
    },
    {
      featureType: 'road',
      elementType: 'geometry.stroke',
      stylers: [{ color: '#212a37' }]
    },
    {
      featureType: 'road',
      elementType: 'labels.text.fill',
      stylers: [{ color: '#9ca5b3' }]  // Cinza claro para textos de rua
    },
    // Pontos de Interesse (POI)
    {
      featureType: 'poi',
      elementType: 'geometry',
      stylers: [{ color: '#283d54' }]  // Azul escuro
    },
    {
      featureType: 'poi',
      elementType: 'labels.text.fill',
      stylers: [{ color: '#d59563' }]
    },
    // Parques
    {
      featureType: 'poi.park',
      elementType: 'geometry',
      stylers: [{ color: '#263c3f' }]  // Verde escuro
    },
    {
      featureType: 'poi.park',
      elementType: 'labels.text.fill',
      stylers: [{ color: '#6b9a76' }]  // Verde suave para textos
    },
    // Transit
    {
      featureType: 'transit',
      elementType: 'geometry',
      stylers: [{ color: '#2f3948' }]
    },
    {
      featureType: 'transit.station',
      elementType: 'labels.text.fill',
      stylers: [{ color: '#d59563' }]
    },
    // Hide minor administrative borders
    {
      featureType: 'administrative.locality',
      elementType: 'geometry',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'administrative.neighborhood',
      elementType: 'geometry',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'administrative.land_parcel',
      elementType: 'geometry',
      stylers: [{ visibility: 'off' }]
    }
  ]
}

/**
 * Get current system theme preference
 * @returns {'light'|'dark'} System theme
 */
export function getSystemTheme() {
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return 'light'
}

/**
 * Watch for system theme changes
 * @param {Function} callback - Called when system theme changes
 * @returns {Function} Cleanup function to remove listener
 */
export function watchSystemTheme(callback) {
  if (typeof window === 'undefined' || !window.matchMedia) {
    return () => {} // No-op cleanup
  }

  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  
  const listener = (e) => {
    callback(e.matches ? 'dark' : 'light')
  }

  // Modern browsers
  if (mediaQuery.addEventListener) {
    mediaQuery.addEventListener('change', listener)
    return () => mediaQuery.removeEventListener('change', listener)
  }
  
  // Legacy browsers
  mediaQuery.addListener(listener)
  return () => mediaQuery.removeListener(listener)
}
