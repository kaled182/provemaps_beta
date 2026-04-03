/**
 * UnifiedMapView - Componente unificado de mapa com sistema de plugins
 * 
 * Usa useMapService para carregar apenas as ferramentas necessárias
 * baseado no contexto (monitoring, design, etc.)
 */

<template>
  <div class="unified-map-container">
    <div ref="mapContainer" class="map-canvas"></div>
    
    <!-- Slot for custom controls -->
    <slot name="controls"></slot>
    
    <!-- Loading state -->
    <div v-if="isLoading" class="map-loading">
      <div class="spinner"></div>
      <p>Carregando mapa...</p>
    </div>
    
    <!-- Error state -->
    <div v-if="error" class="map-error">
      <p>{{ error }}</p>
      <button @click="retryInit">Tentar novamente</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useMapService, useGoogleMapsApiKey } from '@/composables/useMapService';
import '@/composables/mapPlugins'; // Registra plugins

const props = defineProps({
  /**
   * Modo de operação do mapa
   * 'monitoring' - Visualização de segmentos e devices
   * 'design' - Network design com ferramentas de desenho
   * 'analysis' - Análise de rede
   */
  mode: {
    type: String,
    default: 'monitoring',
    validator: (value) => ['monitoring', 'design', 'analysis'].includes(value)
  },
  
  /**
   * Plugins a serem carregados
   * Ex: ['segments', 'devices'] ou ['drawing', 'contextMenu']
   */
  plugins: {
    type: Array,
    default: () => []
  },
  
  /**
   * Opções do mapa
   */
  mapOptions: {
    type: Object,
    default: () => ({})
  },
  
  /**
   * Opções específicas por plugin
   * Ex: { segments: { onSegmentClick: fn }, devices: { enableClustering: true } }
   */
  pluginOptions: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits([
  'map-ready',
  'plugin-loaded',
  'error'
]);

// State
const mapContainer = ref(null);
const loadedPluginInstances = ref({});

// Map service
const apiKey = useGoogleMapsApiKey();
const {
  map,
  isReady,
  isLoading,
  error,
  initMap,
  loadPlugin,
  unloadPlugin,
  cleanup: cleanupMap
} = useMapService({
  mode: props.mode,
  center: props.mapOptions.center || { lat: -15.7801, lng: -47.9292 },
  zoom: props.mapOptions.zoom || 12,
  mapTypeId: props.mapOptions.mapTypeId || 'roadmap'
});

/**
 * Inicializa o mapa e carrega plugins
 */
async function initialize() {
  try {
    // Inicializa mapa
    await initMap(mapContainer.value, props.mapOptions);
    emit('map-ready', map.value);

    // Carrega plugins solicitados
    await loadPlugins();
  } catch (err) {
    console.error('[UnifiedMapView] Initialization failed:', err);
    emit('error', err);
  }
}

/**
 * Carrega todos os plugins especificados
 */
async function loadPlugins() {
  for (const pluginName of props.plugins) {
    try {
      const options = props.pluginOptions[pluginName] || {};
      const plugin = await loadPlugin(pluginName, options);
      loadedPluginInstances.value[pluginName] = plugin;
      emit('plugin-loaded', pluginName, plugin);
    } catch (err) {
      console.error(`[UnifiedMapView] Failed to load plugin "${pluginName}":`, err);
    }
  }
}

/**
 * Retorna instância de um plugin carregado
 * @param {string} pluginName - Nome do plugin
 * @returns {Object|undefined}
 */
function getPlugin(pluginName) {
  return loadedPluginInstances.value[pluginName];
}

/**
 * Tenta reinicializar em caso de erro
 */
async function retryInit() {
  await initialize();
}

// Lifecycle
onMounted(() => {
  initialize();
});

onUnmounted(() => {
  cleanupMap();
});

// Watch para mudanças nos plugins
watch(() => props.plugins, async (newPlugins, oldPlugins) => {
  if (!isReady.value) return;

  // Remove plugins que não estão mais na lista
  for (const pluginName of oldPlugins || []) {
    if (!newPlugins.includes(pluginName)) {
      await unloadPlugin(pluginName);
      delete loadedPluginInstances.value[pluginName];
    }
  }

  // Adiciona novos plugins
  for (const pluginName of newPlugins) {
    if (!oldPlugins?.includes(pluginName)) {
      const options = props.pluginOptions[pluginName] || {};
      const plugin = await loadPlugin(pluginName, options);
      loadedPluginInstances.value[pluginName] = plugin;
      emit('plugin-loaded', pluginName, plugin);
    }
  }
});

// Expose API
defineExpose({
  map,
  getPlugin,
  loadedPlugins: loadedPluginInstances
});
</script>

<style scoped>
.unified-map-container {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.map-canvas {
  width: 100%;
  height: 100%;
}

.map-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  background: rgba(255, 255, 255, 0.95);
  padding: 24px 32px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 16px;
  border: 4px solid #e5e7eb;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.map-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  background: #fef2f2;
  color: #991b1b;
  padding: 24px 32px;
  border-radius: 8px;
  border: 1px solid #fecaca;
}

.map-error button {
  margin-top: 12px;
  padding: 8px 16px;
  background: #dc2626;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.map-error button:hover {
  background: #b91c1c;
}
</style>
