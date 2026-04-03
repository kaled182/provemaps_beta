/**
 * Google Maps Loader - Carregamento centralizado da API do Google Maps
 * 
 * DEPRECATED: Este módulo está sendo substituído por mapLoader.js
 * que suporta múltiplos provedores (Google, Mapbox, OSM, Esri)
 * 
 * Este wrapper é mantido para compatibilidade com código existente.
 */

import { loadGoogleMaps as loadGoogleMapsNew, getMapConfig } from './mapLoader.js';

let loadingPromise = null;
let isLoaded = false;

/**
 * Obtém a API key do Google Maps do endpoint de configuração
 * @returns {Promise<string|null>}
 * @deprecated Use getMapConfig() from mapLoader.js instead
 */
export async function getGoogleMapsApiKey() {
  try {
    console.log('[GoogleMapsLoader] Fetching API key from /api/config/');
    const config = await getMapConfig();
    
    // Verificar se o provider configurado é Google Maps
    if (config.mapProvider && config.mapProvider !== 'google') {
      console.warn(`[GoogleMapsLoader] ⚠️ MAP_PROVIDER is ${config.mapProvider}, not google`);
      console.warn('[GoogleMapsLoader] ⚠️ Consider using mapLoader.loadConfiguredMapProvider() instead');
    }
    
    const apiKey = config.googleMapsApiKey;
    
    if (apiKey) {
      console.log('[GoogleMapsLoader] ✅ API key found from config endpoint');
      return apiKey;
    } else {
      console.error('[GoogleMapsLoader] ❌ No API key in config response');
      return null;
    }
  } catch (error) {
    console.error('[GoogleMapsLoader] Error fetching config:', error);
    return null;
  }
}

/**
 * Carrega o Google Maps JavaScript API
 * @returns {Promise<void>}
 * @deprecated Use loadConfiguredMapProvider() from mapLoader.js to respect configured provider
 */
export async function loadGoogleMaps() {
  console.log('[GoogleMapsLoader] loadGoogleMaps() called');
  
  // Verificar se o provider configurado é Google Maps
  try {
    const config = await getMapConfig();
    if (config.mapProvider && config.mapProvider !== 'google') {
      console.warn(`[GoogleMapsLoader] ⚠️ WARNING: MAP_PROVIDER is configured as '${config.mapProvider}'`);
      console.warn('[GoogleMapsLoader] ⚠️ But Google Maps is being loaded anyway (legacy code)');
      console.warn('[GoogleMapsLoader] ⚠️ Consider migrating to mapLoader.loadConfiguredMapProvider()');
    }
  } catch (err) {
    console.error('[GoogleMapsLoader] Failed to check map provider:', err);
  }
  
  console.log('[GoogleMapsLoader] isLoaded:', isLoaded);
  console.log('[GoogleMapsLoader] window.google?.maps:', !!window.google?.maps);
  
  // Se já está carregado, retorna imediatamente
  if (isLoaded && window.google?.maps) {
    console.log('[GoogleMapsLoader] Already loaded, returning immediately');
    return Promise.resolve();
  }

  // Se já está carregando, retorna a promise existente
  if (loadingPromise) {
    console.log('[GoogleMapsLoader] Already loading, returning existing promise');
    return loadingPromise;
  }

  console.log('[GoogleMapsLoader] Delegating to mapLoader.loadGoogleMaps()...');
  
  loadingPromise = loadGoogleMapsNew()
    .then(() => {
      isLoaded = true;
      console.log('[GoogleMapsLoader] ✅ Google Maps loaded via mapLoader');
      loadingPromise = null;
    })
    .catch((error) => {
      console.error('[GoogleMapsLoader] ❌ Failed to load Google Maps:', error);
      loadingPromise = null;
      isLoaded = false;
      throw error;
    });

  return loadingPromise;
}

/**
 * Verifica se o Google Maps está disponível
 * @returns {boolean}
 */
export function isGoogleMapsLoaded() {
  return isLoaded && window.google?.maps;
}

/**
 * Aguarda o Google Maps estar disponível (com timeout)
 * @param {number} timeout - Timeout em ms (padrão: 10000)
 * @returns {Promise<void>}
 */
export function waitForGoogleMaps(timeout = 10000) {
  if (isGoogleMapsLoaded()) {
    return Promise.resolve();
  }

  return Promise.race([
    loadGoogleMaps(),
    new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Google Maps load timeout')), timeout)
    )
  ]);
}
