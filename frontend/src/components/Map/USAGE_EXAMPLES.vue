/**
 * EXEMPLOS DE USO - UnifiedMapView com Plugins
 * 
 * Demonstra como usar o componente unificado de mapa em diferentes contextos
 */

// ============================================================================
// EXEMPLO 1: Monitoring/Dashboard - Visualização de Segmentos e Devices
// ============================================================================

<template>
  <div class="monitoring-view">
    <UnifiedMapView
      ref="mapRef"
      mode="monitoring"
      :plugins="['segments', 'devices']"
      :plugin-options="pluginOptions"
      :map-options="mapOptions"
      @map-ready="onMapReady"
      @plugin-loaded="onPluginLoaded"
    >
      <!-- Custom controls -->
      <template #controls>
        <div class="map-controls">
          <button @click="refreshData">🔄 Atualizar</button>
          <button @click="fitAllSegments">🎯 Ajustar Zoom</button>
        </div>
      </template>
    </UnifiedMapView>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useDashboardStore } from '@/stores/dashboard';
import { useInventoryStore } from '@/stores/inventory';
import UnifiedMapView from '@/components/Map/UnifiedMapView.vue';

const dashboardStore = useDashboardStore();
const inventoryStore = useInventoryStore();
const mapRef = ref(null);

// Opções do mapa
const mapOptions = {
  center: { lat: -15.7801, lng: -47.9292 },
  zoom: 12,
  mapTypeId: 'roadmap'
};

// Opções específicas dos plugins
const pluginOptions = {
  // Plugin de segmentos
  segments: {
    onSegmentClick: (segment, event) => {
      console.log('Segmento clicado:', segment);
      // Abre modal ou sidebar com detalhes
      dashboardStore.selectSegment(segment.id);
    },
    onSegmentHover: (segment, event, isHover) => {
      if (isHover) {
        // Mostra tooltip com sinal
        showSignalTooltip(segment, event);
      } else {
        hideSignalTooltip();
      }
    }
  },
  
  // Plugin de devices
  devices: {
    enableClustering: true, // Agrupa markers próximos
    onDeviceClick: (device, marker) => {
      console.log('Device clicado:', device);
      // Foca no device e mostra detalhes
      dashboardStore.selectDevice(device.id);
    },
    customIcon: (device) => {
      // Ícone customizado baseado no tipo de device
      return {
        url: `/icons/${device.type}.png`,
        scaledSize: { width: 32, height: 32 }
      };
    }
  }
};

// Quando o mapa está pronto
function onMapReady(map) {
  console.log('Mapa pronto!', map);
  loadInitialData();
}

// Quando um plugin é carregado
function onPluginLoaded(pluginName, plugin) {
  console.log(`Plugin "${pluginName}" carregado`, plugin);
  
  if (pluginName === 'segments') {
    loadSegments();
  } else if (pluginName === 'devices') {
    loadDevices();
  }
}

// Carrega dados iniciais
async function loadInitialData() {
  await Promise.all([
    loadSegments(),
    loadDevices()
  ]);
}

// Carrega segmentos de fibra
async function loadSegments() {
  const segmentsPlugin = mapRef.value?.getPlugin('segments');
  if (!segmentsPlugin) return;

  const segments = await inventoryStore.fetchSegments();
  segmentsPlugin.drawSegments(segments);
}

// Carrega devices/sites
async function loadDevices() {
  const devicesPlugin = mapRef.value?.getPlugin('devices');
  if (!devicesPlugin) return;

  const devices = await inventoryStore.fetchDevices();
  devicesPlugin.drawDevices(devices);
}

// Atualiza dados
async function refreshData() {
  await loadInitialData();
}

// Ajusta zoom para mostrar todos os segmentos
function fitAllSegments() {
  const segmentsPlugin = mapRef.value?.getPlugin('segments');
  segmentsPlugin?.fitBounds();
}

// Tooltips de sinal
function showSignalTooltip(segment, event) {
  // Implementar lógica de tooltip
}

function hideSignalTooltip() {
  // Esconder tooltip
}
</script>

// ============================================================================
// EXEMPLO 2: Network Design - Ferramentas de Desenho
// ============================================================================

<template>
  <div class="network-design-view">
    <UnifiedMapView
      ref="mapRef"
      mode="design"
      :plugins="['drawing', 'contextMenu', 'segments']"
      :plugin-options="pluginOptions"
      :map-options="mapOptions"
      @map-ready="onMapReady"
      @plugin-loaded="onPluginLoaded"
    >
      <template #controls>
        <div class="design-controls">
          <button @click="startDrawing" :disabled="isDrawing">✏️ Desenhar</button>
          <button @click="stopDrawing" :disabled="!isDrawing">⏸️ Parar</button>
          <button @click="clearPath">🗑️ Limpar</button>
          <button @click="savePath" :disabled="!hasPath">💾 Salvar</button>
          <div class="distance-display">
            📏 {{ distanceKm.toFixed(3) }} km
          </div>
        </div>
      </template>
    </UnifiedMapView>

    <!-- Painel de pontos da rota -->
    <div v-if="pathPoints.length > 0" class="route-points-panel">
      <h3>Pontos da Rota ({{ pathPoints.length }})</h3>
      <ul>
        <li v-for="(point, index) in pathPoints" :key="index">
          {{ index + 1 }}. Lat: {{ point.lat.toFixed(6) }}, Lng: {{ point.lng.toFixed(6) }}
          <button @click="removePoint(index)">❌</button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import UnifiedMapView from '@/components/Map/UnifiedMapView.vue';
import { useFiberStore } from '@/stores/fiber';

const fiberStore = useFiberStore();
const mapRef = ref(null);
const pathPoints = ref([]);
const distanceKm = ref(0);
const isDrawing = ref(false);

// Opções do mapa - terreno é melhor para rotas
const mapOptions = {
  center: { lat: -16.6869, lng: -49.2648 },
  zoom: 6,
  mapTypeId: 'terrain'
};

// Opções dos plugins
const pluginOptions = {
  // Plugin de desenho
  drawing: {
    editable: true,
    onPathChange: (coordinates, distance) => {
      pathPoints.value = coordinates;
      distanceKm.value = distance / 1000;
    },
    onMarkerAdded: (index, position) => {
      console.log('Ponto adicionado:', index, position);
    },
    onMarkerMoved: (index, position) => {
      console.log('Ponto movido:', index, position);
    }
  },
  
  // Plugin de menu de contexto
  contextMenu: {
    menuItems: [
      {
        id: 'save-cable',
        label: '💾 Salvar Cabo',
        action: ({ latLng }) => {
          savePath();
        }
      },
      {
        id: 'load-cable',
        label: '📂 Carregar Cabo',
        action: ({ latLng }) => {
          openLoadDialog();
        }
      },
      { separator: true },
      {
        id: 'import-kml',
        label: '📥 Importar KML',
        action: ({ latLng }) => {
          openKmlImport();
        }
      },
      {
        id: 'clear',
        label: '🗑️ Limpar Tudo',
        action: ({ latLng }) => {
          clearPath();
        }
      }
    ],
    onItemClick: (itemId, data) => {
      console.log('Menu item clicked:', itemId, data);
    }
  },
  
  // Plugin de segmentos - para visualizar cabos existentes
  segments: {
    onSegmentClick: (segment, event) => {
      // Carregar cabo para edição
      loadCableForEdit(segment.id);
    }
  }
};

const hasPath = computed(() => pathPoints.value.length > 0);

function onMapReady(map) {
  console.log('Mapa de design pronto');
  loadExistingCables();
}

function onPluginLoaded(pluginName, plugin) {
  console.log(`Plugin "${pluginName}" carregado`);
}

// Controles de desenho
function startDrawing() {
  const drawingPlugin = mapRef.value?.getPlugin('drawing');
  drawingPlugin?.startDrawing();
  isDrawing.value = true;
}

function stopDrawing() {
  const drawingPlugin = mapRef.value?.getPlugin('drawing');
  drawingPlugin?.stopDrawing();
  isDrawing.value = false;
}

function clearPath() {
  const drawingPlugin = mapRef.value?.getPlugin('drawing');
  drawingPlugin?.clearPath();
  pathPoints.value = [];
  distanceKm.value = 0;
}

function removePoint(index) {
  const drawingPlugin = mapRef.value?.getPlugin('drawing');
  drawingPlugin?.removePoint(index);
}

async function savePath() {
  if (!hasPath.value) return;

  const drawingPlugin = mapRef.value?.getPlugin('drawing');
  const coordinates = drawingPlugin?.getPathCoordinates();
  
  // Salva no backend
  await fiberStore.saveCable({
    name: 'Novo Cabo',
    path: coordinates,
    length_km: distanceKm.value
  });
  
  alert('Cabo salvo com sucesso!');
}

async function loadExistingCables() {
  const segmentsPlugin = mapRef.value?.getPlugin('segments');
  if (!segmentsPlugin) return;

  const cables = await fiberStore.fetchCables();
  segmentsPlugin.drawSegments(cables);
}

async function loadCableForEdit(cableId) {
  const cable = await fiberStore.fetchCable(cableId);
  const drawingPlugin = mapRef.value?.getPlugin('drawing');
  
  drawingPlugin?.setPath(cable.path);
  drawingPlugin?.fitBounds();
}

function openLoadDialog() {
  // Abrir modal de seleção de cabo
}

function openKmlImport() {
  // Abrir modal de importação KML
}
</script>

// ============================================================================
// EXEMPLO 3: Análise de Rede - Combinando múltiplos plugins
// ============================================================================

<template>
  <div class="network-analysis-view">
    <UnifiedMapView
      ref="mapRef"
      mode="analysis"
      :plugins="activePlugins"
      :plugin-options="pluginOptions"
      :map-options="mapOptions"
      @map-ready="onMapReady"
    >
      <template #controls>
        <div class="analysis-controls">
          <label>
            <input type="checkbox" v-model="showSegments" />
            Segmentos de Fibra
          </label>
          <label>
            <input type="checkbox" v-model="showDevices" />
            Devices
          </label>
          <label>
            <input type="checkbox" v-model="enableDrawing" />
            Ferramentas de Desenho
          </label>
        </div>
      </template>
    </UnifiedMapView>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import UnifiedMapView from '@/components/Map/UnifiedMapView.vue';

const mapRef = ref(null);
const showSegments = ref(true);
const showDevices = ref(true);
const enableDrawing = ref(false);

// Plugins ativos baseados nas checkboxes
const activePlugins = computed(() => {
  const plugins = [];
  if (showSegments.value) plugins.push('segments');
  if (showDevices.value) plugins.push('devices');
  if (enableDrawing.value) plugins.push('drawing', 'contextMenu');
  return plugins;
});

const mapOptions = { zoom: 10 };
const pluginOptions = {
  segments: { /* ... */ },
  devices: { /* ... */ },
  drawing: { /* ... */ }
};

function onMapReady() {
  console.log('Análise pronta');
}
</script>

<style scoped>
.map-controls,
.design-controls,
.analysis-controls {
  position: absolute;
  top: 16px;
  left: 16px;
  background: white;
  padding: 12px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  z-index: 1000;
  display: flex;
  gap: 8px;
  align-items: center;
}

button {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: white;
  cursor: pointer;
  font-size: 14px;
}

button:hover {
  background: #1d4ed8;
}

button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.distance-display {
  padding: 8px 12px;
  background: #f3f4f6;
  border-radius: 6px;
  font-weight: 600;
  color: #374151;
}

.route-points-panel {
  position: absolute;
  right: 16px;
  top: 16px;
  background: white;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  max-height: 400px;
  overflow-y: auto;
  width: 300px;
}

.route-points-panel h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #111827;
}

.route-points-panel ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.route-points-panel li {
  padding: 8px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.route-points-panel li button {
  padding: 4px 8px;
  font-size: 12px;
  background: #ef4444;
}
</style>
