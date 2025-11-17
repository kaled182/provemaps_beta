/**
 * useMapService - Composable unificado para gerenciar Google Maps
 * 
 * Arquitetura modular que permite diferentes contextos (monitoring, network design, etc.)
 * carregarem apenas as ferramentas necessárias através de plugins.
 * 
 * @example
 * // Monitoring context
 * const { initMap, loadPlugin } = useMapService({ mode: 'monitoring' });
 * await loadPlugin('segments'); // Carrega polylines de fibra
 * await loadPlugin('devices');  // Carrega markers de devices
 * 
 * @example
 * // Network Design context
 * const { initMap, loadPlugin } = useMapService({ mode: 'design' });
 * await loadPlugin('drawing');     // Ferramentas de desenho
 * await loadPlugin('contextMenu'); // Menu de contexto
 */

import { ref, computed, shallowRef } from 'vue';
import { waitForGoogleMaps } from '@/utils/googleMapsLoader';

// Registry de plugins disponíveis
const pluginRegistry = new Map();

/**
 * Registra um plugin no registry global
 * @param {string} name - Nome do plugin
 * @param {Function} factory - Função factory que retorna o plugin
 */
export function registerMapPlugin(name, factory) {
  if (pluginRegistry.has(name)) {
    console.warn(`[MapService] Plugin "${name}" already registered, overwriting`);
  }
  pluginRegistry.set(name, factory);
}

/**
 * Composable principal do serviço de mapas
 * @param {Object} options - Opções de configuração
 * @param {string} options.mode - Modo de operação ('monitoring', 'design', 'analysis')
 * @param {Object} options.center - Coordenadas iniciais { lat, lng }
 * @param {number} options.zoom - Zoom inicial
 * @param {string} options.mapTypeId - Tipo do mapa ('roadmap', 'terrain', 'satellite')
 * @returns {Object} API do serviço de mapas
 */
export function useMapService(options = {}) {
  const {
    mode = 'monitoring',
    center = { lat: -15.7801, lng: -47.9292 },
    zoom = 12,
    mapTypeId = 'roadmap'
  } = options;

  // Estado reativo
  const mapInstance = shallowRef(null);
  const googleApi = shallowRef(null);
  const isReady = ref(false);
  const isLoading = ref(false);
  const error = ref(null);
  const loadedPlugins = ref(new Map());

  /**
   * Inicializa o Google Maps
   * @param {HTMLElement|string} container - Container do mapa ou seletor
   * @param {Object} mapOptions - Opções adicionais do Google Maps
   * @returns {Promise<google.maps.Map>}
   */
  async function initMap(container, mapOptions = {}) {
    if (mapInstance.value) {
      console.warn('[MapService] Map already initialized');
      return mapInstance.value;
    }

    isLoading.value = true;
    error.value = null;

    try {
      // Aguarda Google Maps API estar disponível
      await waitForGoogleMaps();
      googleApi.value = window.google;

      const element = typeof container === 'string' 
        ? document.querySelector(container)
        : container;

      if (!element) {
        throw new Error(`Map container not found: ${container}`);
      }

      // Cria instância do mapa
      const finalOptions = {
        center,
        zoom,
        mapTypeId,
        ...mapOptions
      };

      mapInstance.value = new window.google.maps.Map(element, finalOptions);
      isReady.value = true;

      console.log(`[MapService] Map initialized in ${mode} mode`);
      return mapInstance.value;
    } catch (err) {
      error.value = err.message;
      console.error('[MapService] Failed to initialize map:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * Carrega e inicializa um plugin
   * @param {string} pluginName - Nome do plugin registrado
   * @param {Object} pluginOptions - Opções específicas do plugin
   * @returns {Promise<Object>} Instância do plugin
   */
  async function loadPlugin(pluginName, pluginOptions = {}) {
    if (!isReady.value) {
      throw new Error('[MapService] Map not initialized. Call initMap() first');
    }

    if (loadedPlugins.value.has(pluginName)) {
      console.warn(`[MapService] Plugin "${pluginName}" already loaded`);
      return loadedPlugins.value.get(pluginName);
    }

    const factory = pluginRegistry.get(pluginName);
    if (!factory) {
      throw new Error(`[MapService] Plugin "${pluginName}" not found. Available: ${Array.from(pluginRegistry.keys()).join(', ')}`);
    }

    try {
      console.log(`[MapService] Loading plugin: ${pluginName}`);
      const pluginContext = {
        map: mapInstance.value,
        google: googleApi.value,
        mode
      };

      const plugin = await factory(pluginContext, pluginOptions);
      loadedPlugins.value.set(pluginName, plugin);

      console.log(`[MapService] Plugin "${pluginName}" loaded successfully`);
      return plugin;
    } catch (err) {
      console.error(`[MapService] Failed to load plugin "${pluginName}":`, err);
      throw err;
    }
  }

  /**
   * Remove um plugin carregado
   * @param {string} pluginName - Nome do plugin
   */
  async function unloadPlugin(pluginName) {
    const plugin = loadedPlugins.value.get(pluginName);
    if (!plugin) {
      return;
    }

    // Chama cleanup se disponível
    if (typeof plugin.cleanup === 'function') {
      await plugin.cleanup();
    }

    loadedPlugins.value.delete(pluginName);
    console.log(`[MapService] Plugin "${pluginName}" unloaded`);
  }

  /**
   * Obtém um plugin carregado
   * @param {string} pluginName - Nome do plugin
   * @returns {Object|undefined}
   */
  function getPlugin(pluginName) {
    return loadedPlugins.value.get(pluginName);
  }

  /**
   * Limpa todos os recursos do mapa
   */
  async function cleanup() {
    // Limpa todos os plugins
    for (const [name] of loadedPlugins.value) {
      await unloadPlugin(name);
    }

    mapInstance.value = null;
    googleApi.value = null;
    isReady.value = false;
    error.value = null;
  }

  return {
    // Estado
    map: computed(() => mapInstance.value),
    google: computed(() => googleApi.value),
    isReady: computed(() => isReady.value),
    isLoading: computed(() => isLoading.value),
    error: computed(() => error.value),
    mode,

    // Métodos
    initMap,
    loadPlugin,
    unloadPlugin,
    getPlugin,
    cleanup
  };
}

/**
 * Hook para obter API key do Google Maps
 * @returns {string}
 */
export function useGoogleMapsApiKey() {
  const runtimeKey = typeof document !== 'undefined'
    ? document.querySelector('meta[name="google-maps-api-key"]')?.getAttribute('content')
    : '';
  
  return runtimeKey || import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';
}
