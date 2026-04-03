/**
 * Map Provider Factory & Registry
 * 
 * Gerencia providers de mapas e fornece instâncias baseadas na configuração
 * Singleton pattern para garantir apenas uma instância ativa
 */

import { GoogleMapsProvider } from './GoogleMapsProvider.js';
import { MapboxProvider } from './MapboxProvider.js';

/**
 * Registry global de providers
 */
const providers = {
  google: GoogleMapsProvider,
  mapbox: MapboxProvider,
  // Expansível: osm, esri, etc.
};

/**
 * Provider instance cache
 */
let currentProvider = null;
let currentProviderName = null;
let configCache = null;

/**
 * Busca configuração do backend
 */
async function fetchMapConfig() {
  if (configCache) {
    return configCache;
  }

  try {
    const response = await fetch('/api/config/');
    if (!response.ok) {
      throw new Error(`Config API returned ${response.status}`);
    }
    configCache = await response.json();
    console.log('[MapProviderFactory] Config loaded:', configCache.mapProvider);
    return configCache;
  } catch (error) {
    console.error('[MapProviderFactory] Failed to load config:', error);
    throw error;
  }
}

/**
 * Limpa o cache de configuração
 */
export function clearConfigCache() {
  configCache = null;
  console.log('[MapProviderFactory] Config cache cleared');
}

/**
 * Retorna o provider configurado
 * @param {boolean} forceReload - Força recarregar o provider
 * @returns {Promise<IMapProvider>}
 */
export async function getMapProvider(forceReload = false) {
  const config = await fetchMapConfig();
  const providerName = config.mapProvider || 'google';

  // Se já existe provider e é o mesmo tipo, reutilizar
  if (!forceReload && currentProvider && currentProviderName === providerName) {
    console.log(`[MapProviderFactory] Reusing existing ${providerName} provider`);
    return currentProvider;
  }

  // Verificar se o provider existe
  const ProviderClass = providers[providerName];
  if (!ProviderClass) {
    console.error(`[MapProviderFactory] Unknown provider: ${providerName}`);
    throw new Error(`Map provider '${providerName}' not supported`);
  }

  // Criar nova instância
  console.log(`[MapProviderFactory] Creating new ${providerName} provider`);
  currentProvider = new ProviderClass();
  currentProviderName = providerName;

  // Carregar dependências
  try {
    await currentProvider.load(config);
    console.log(`[MapProviderFactory] ✅ ${providerName} provider ready`);
  } catch (error) {
    console.error(`[MapProviderFactory] ❌ Failed to load ${providerName} provider:`, error);
    currentProvider = null;
    currentProviderName = null;
    throw error;
  }

  return currentProvider;
}

/**
 * Retorna o nome do provider atual
 * @returns {Promise<string>}
 */
export async function getCurrentProviderName() {
  const config = await fetchMapConfig();
  return config.mapProvider || 'google';
}

/**
 * Cria uma instância de mapa usando o provider configurado
 * @param {HTMLElement} container - Container DOM
 * @param {Object} options - Opções do mapa
 * @returns {Promise<IMap>}
 */
export async function createMap(container, options) {
  const provider = await getMapProvider();
  
  if (!provider.isLoaded()) {
    throw new Error(`Provider ${provider.getName()} not loaded`);
  }

  console.log(`[MapProviderFactory] Creating map with ${provider.getName()} provider`);
  const map = provider.createMap(container, options);
  
  return map;
}

/**
 * Registra um novo provider customizado
 * @param {string} name - Nome do provider
 * @param {Class} ProviderClass - Classe que implementa IMapProvider
 */
export function registerProvider(name, ProviderClass) {
  providers[name] = ProviderClass;
  console.log(`[MapProviderFactory] Registered custom provider: ${name}`);
}

/**
 * Lista providers disponíveis
 * @returns {string[]}
 */
export function listProviders() {
  return Object.keys(providers);
}

/**
 * Força recarregamento do provider
 */
export function reloadProvider() {
  currentProvider = null;
  currentProviderName = null;
  clearConfigCache();
  console.log('[MapProviderFactory] Provider cache cleared, will reload on next getMapProvider()');
}

// Export para acesso direto quando necessário
export { GoogleMapsProvider, MapboxProvider };
