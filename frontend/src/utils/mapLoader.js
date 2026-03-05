/**
 * Map Loader - Carregamento centralizado de provedores de mapas
 * 
 * Suporta múltiplos provedores: Google Maps, Mapbox, OpenStreetMap, Esri
 * Carrega o provedor configurado no banco de dados via /api/config/
 */

let configCache = null;
let configPromise = null;
let googleMapsPromise = null;
let mapboxPromise = null;

/**
 * Obtém a configuração de mapas do backend
 * @returns {Promise<Object>}
 */
export async function getMapConfig() {
  // Se já tem cache, retorna imediatamente
  if (configCache) {
    console.log('[MapLoader] 📦 Using cached config');
    return configCache;
  }

  // Se já está carregando, retorna a promise existente
  if (configPromise) {
    console.log('[MapLoader] ⏳ Config already loading, waiting...');
    return configPromise;
  }

  console.log('[MapLoader] 🌍 Fetching map config from /api/config/');

  configPromise = fetch('/api/config/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const config = await response.json();
      
      // Validar que temos o provider
      if (!config.mapProvider) {
        console.warn('[MapLoader] ⚠️ No mapProvider in config, defaulting to google');
        config.mapProvider = 'google';
      }

      console.log(`[MapLoader] ✅ Config loaded: provider=${config.mapProvider}`);
      configCache = config;
      return config;
    })
    .catch((error) => {
      console.error('[MapLoader] ❌ Failed to load config:', error);
      configPromise = null;
      throw error;
    });

  return configPromise;
}

/**
 * Carrega o Google Maps JavaScript API
 * @returns {Promise<void>}
 */
export async function loadGoogleMaps() {
  console.log('[MapLoader] 🗺️ loadGoogleMaps() called');

  // Se já está carregado, retorna
  if (window.google?.maps) {
    console.log('[MapLoader] ✅ Google Maps already loaded');
    return;
  }

  // Se já está carregando, aguarda
  if (googleMapsPromise) {
    console.log('[MapLoader] ⏳ Google Maps already loading...');
    return googleMapsPromise;
  }

  // Busca a configuração
  const config = await getMapConfig();

  if (!config.googleMapsApiKey) {
    throw new Error('Google Maps API key not configured');
  }

  console.log('[MapLoader] 📡 Loading Google Maps script...');

  googleMapsPromise = new Promise((resolve, reject) => {
    // Verifica se já existe script
    const existingScript = document.querySelector('script[src*="maps.googleapis.com"]');
    if (existingScript) {
      if (window.google?.maps) {
        console.log('[MapLoader] ✅ Script exists and loaded');
        resolve();
        return;
      }
      
      // Script existe mas API não está pronta
      existingScript.addEventListener('load', () => {
        console.log('[MapLoader] ✅ Existing script loaded');
        resolve();
      });
      existingScript.addEventListener('error', () => {
        console.error('[MapLoader] ❌ Existing script failed');
        reject(new Error('Google Maps script load failed'));
      });
      return;
    }

    // Criar novo script
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${config.googleMapsApiKey}&libraries=places,drawing,geometry&language=${config.mapLanguage || 'pt-BR'}`;
    script.async = true;
    script.defer = true;

    script.onload = () => {
      console.log('[MapLoader] ✅ Google Maps script loaded successfully');
      resolve();
    };

    script.onerror = () => {
      console.error('[MapLoader] ❌ Failed to load Google Maps script');
      googleMapsPromise = null;
      reject(new Error('Google Maps script load failed'));
    };

    document.head.appendChild(script);
  });

  return googleMapsPromise;
}

/**
 * Carrega o Mapbox GL JS
 * @returns {Promise<void>}
 */
export async function loadMapbox() {
  console.log('[MapLoader] 🗺️ loadMapbox() called');

  // Se já está carregado, retorna
  if (window.mapboxgl) {
    console.log('[MapLoader] ✅ Mapbox already loaded');
    return;
  }

  // Se já está carregando, aguarda
  if (mapboxPromise) {
    console.log('[MapLoader] ⏳ Mapbox already loading...');
    return mapboxPromise;
  }

  // Busca a configuração
  const config = await getMapConfig();

  if (!config.mapboxToken) {
    throw new Error('Mapbox token not configured');
  }

  console.log('[MapLoader] 📡 Loading Mapbox GL JS...');

  mapboxPromise = new Promise((resolve, reject) => {
    // Carregar CSS primeiro
    if (!document.querySelector('link[href*="mapbox-gl.css"]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = 'https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.css';
      document.head.appendChild(link);
    }

    // Verificar se já existe script
    const existingScript = document.querySelector('script[src*="mapbox-gl.js"]');
    if (existingScript) {
      if (window.mapboxgl) {
        window.mapboxgl.accessToken = config.mapboxToken;
        console.log('[MapLoader] ✅ Mapbox exists and loaded');
        resolve();
        return;
      }

      existingScript.addEventListener('load', () => {
        window.mapboxgl.accessToken = config.mapboxToken;
        console.log('[MapLoader] ✅ Existing Mapbox script loaded');
        resolve();
      });
      existingScript.addEventListener('error', () => {
        console.error('[MapLoader] ❌ Existing Mapbox script failed');
        reject(new Error('Mapbox script load failed'));
      });
      return;
    }

    // Criar novo script
    const script = document.createElement('script');
    script.src = 'https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js';
    script.async = true;

    script.onload = () => {
      window.mapboxgl.accessToken = config.mapboxToken;
      console.log('[MapLoader] ✅ Mapbox GL JS loaded successfully');
      resolve();
    };

    script.onerror = () => {
      console.error('[MapLoader] ❌ Failed to load Mapbox script');
      mapboxPromise = null;
      reject(new Error('Mapbox script load failed'));
    };

    document.head.appendChild(script);
  });

  return mapboxPromise;
}

/**
 * Carrega o provedor de mapa configurado
 * @returns {Promise<{provider: string, config: Object}>}
 */
export async function loadConfiguredMapProvider() {
  console.log('[MapLoader] 🚀 Loading configured map provider...');

  const config = await getMapConfig();
  const provider = config.mapProvider || 'google';

  console.log(`[MapLoader] 🎯 Configured provider: ${provider}`);

  switch (provider) {
    case 'google':
      await loadGoogleMaps();
      break;
    
    case 'mapbox':
      await loadMapbox();
      break;
    
    case 'osm':
      // OpenStreetMap/Leaflet não requer carregamento de script
      console.log('[MapLoader] 🍃 OpenStreetMap selected (Leaflet)');
      break;
    
    case 'esri':
      console.log('[MapLoader] 🌐 Esri selected');
      // Esri pode ser carregado via módulos AMD ou CDN
      break;
    
    default:
      console.warn(`[MapLoader] ⚠️ Unknown provider: ${provider}, defaulting to google`);
      await loadGoogleMaps();
  }

  console.log(`[MapLoader] ✅ Provider loaded: ${provider}`);

  return {
    provider,
    config
  };
}

/**
 * Limpa o cache de configuração (útil para testes ou recarregamento)
 */
export function clearConfigCache() {
  console.log('[MapLoader] 🗑️ Clearing config cache');
  configCache = null;
  configPromise = null;
}

/**
 * Para compatibilidade com código existente que usa googleMapsLoader.js
 * @deprecated Use loadConfiguredMapProvider() instead
 */
export async function loadGoogleMapsLegacy() {
  console.warn('[MapLoader] ⚠️ Using legacy loadGoogleMaps - consider migrating to loadConfiguredMapProvider()');
  
  const config = await getMapConfig();
  
  // Se não for google, avisar mas ainda carregar (para compatibilidade)
  if (config.mapProvider !== 'google') {
    console.warn(`[MapLoader] ⚠️ Map provider is ${config.mapProvider}, but legacy code requested Google Maps`);
  }
  
  return loadGoogleMaps();
}
