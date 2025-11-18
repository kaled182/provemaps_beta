/**
 * Google Maps Loader - Carregamento centralizado da API do Google Maps
 * 
 * Garante que a API seja carregada apenas uma vez e compartilhada
 * entre todas as páginas/componentes que precisam usar mapas.
 * 
 * Resolve o problema de navegação de páginas sem maps (Zabbix Lookup)
 * para páginas com maps (Network Design, Monitoring) onde o script
 * não estava disponível.
 */

let loadingPromise = null;
let isLoaded = false;

/**
 * Obtém a API key do Google Maps do endpoint de configuração
 * @returns {Promise<string|null>}
 */
export async function getGoogleMapsApiKey() {
  try {
    console.log('[GoogleMapsLoader] Fetching API key from /api/config/');
    const response = await fetch('/api/config/', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      console.error('[GoogleMapsLoader] Failed to fetch config:', response.status);
      return null;
    }
    
    const config = await response.json();
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
 */
export async function loadGoogleMaps() {
  console.log('[GoogleMapsLoader] loadGoogleMaps() called');
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

  console.log('[GoogleMapsLoader] Starting new load...');

  // Inicia novo carregamento
  loadingPromise = new Promise(async (resolve, reject) => {
    // Verifica se já existe script
    const existingScript = document.querySelector('script[data-google-maps]');
    if (existingScript) {
      console.log('[GoogleMapsLoader] Found existing script tag');
      if (window.google?.maps) {
        console.log('[GoogleMapsLoader] Google Maps already available');
        isLoaded = true;
        resolve();
        return;
      }
      
      console.log('[GoogleMapsLoader] Script exists but API not ready, waiting for load event');
      existingScript.addEventListener('load', () => {
        console.log('[GoogleMapsLoader] Existing script loaded');
        isLoaded = true;
        resolve();
      }, { once: true });
      
      existingScript.addEventListener('error', (err) => {
        console.error('[GoogleMapsLoader] Existing script failed to load');
        loadingPromise = null;
        reject(new Error('Failed to load Google Maps API'));
      }, { once: true });
      
      return;
    }

    // Obtém API key com retry
    console.log('[GoogleMapsLoader] Fetching API key...');
    const apiKey = await getGoogleMapsApiKey();
    console.log('[GoogleMapsLoader] API key found:', !!apiKey);
    
    if (!apiKey) {
      loadingPromise = null;
      reject(new Error('Google Maps API key not found'));
      return;
    }

    // Cria novo script
    console.log('[GoogleMapsLoader] Creating new script tag');
    const script = document.createElement('script');
    const params = new URLSearchParams({
      key: apiKey,
      libraries: 'geometry,places,marker'
    });
    
    script.src = `https://maps.googleapis.com/maps/api/js?${params.toString()}`;
    script.async = true;
    script.defer = true;
    script.dataset.googleMaps = 'true';
    
    script.addEventListener('load', () => {
      isLoaded = true;
      console.log('[GoogleMapsLoader] ✅ New script loaded successfully');
      console.log('[GoogleMapsLoader] window.google.maps available:', !!window.google?.maps);
      resolve();
    }, { once: true });
    
    script.addEventListener('error', () => {
      console.error('[GoogleMapsLoader] ❌ Failed to load script');
      loadingPromise = null;
      reject(new Error('Failed to load Google Maps API'));
    }, { once: true });
    
    console.log('[GoogleMapsLoader] Appending script to head');
    document.head.appendChild(script);
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
