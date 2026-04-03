<template>
  <div class="flex h-screen overflow-hidden relative bg-gray-50 dark:bg-gray-900">
    
    <!-- Área do Mapa -->
    <div class="flex-1 relative bg-gray-100 dark:bg-gray-800 z-0">
      
      <UnifiedMapView
        ref="mapRef"
        :plugins="['drawing']"
        :plugin-options="pluginOptions"
        class="w-full h-full"
        @map-ready="onMapReady"
        @plugin-loaded="onPluginLoaded"
      />
      
      <!-- Toolbar Flutuante -->
      <div class="absolute top-4 left-1/2 -translate-x-1/2 z-10 bg-white dark:bg-gray-800 rounded-full shadow-lg p-1.5 flex items-center gap-1 border border-gray-200 dark:border-gray-600">
        
        <button 
          @click="setMode('read')"
          class="px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2 transition-colors"
          :class="mode === 'read' ? 'bg-gray-800 dark:bg-gray-700 text-white shadow-md' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
        >
          <i class="fas fa-lock"></i> Visualizar
        </button>

        <button 
          @click="setMode('edit')"
          class="px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2 transition-colors"
          :class="mode === 'edit' ? 'bg-indigo-600 dark:bg-indigo-500 text-white shadow-md' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
        >
          <i class="fas fa-pen"></i> Editar Traçado
        </button>

        <div class="w-px h-4 bg-gray-300 dark:bg-gray-600 mx-1"></div>

        <label class="p-2 rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer" title="Importar KML">
          <input type="file" class="hidden" accept=".kml" @change="onKmlSelected" />
          <i class="fas fa-file-upload"></i>
        </label>
      </div>
    </div>

    <!-- Sidebar Direita -->
    <EditorSidebar 
      :cable="cable"
      :mode="mode"
      :saving="isSaving"
      @toggle-mode="setMode"
      @save="saveCable"
      @cancel="cancelEdit"
      @update-basic-info="updateBasicInfo"
    />

    <!-- Notificação Toast -->
    <transition name="slide-up">
      <div 
        v-if="notification.show" 
        class="fixed bottom-6 right-6 z-50 max-w-md bg-white dark:bg-gray-800 rounded-lg shadow-2xl border-l-4 p-4"
        :class="{
          'border-blue-500': notification.type === 'info',
          'border-green-500': notification.type === 'success',
          'border-yellow-500': notification.type === 'warning',
          'border-red-500': notification.type === 'error',
        }"
      >
        <div class="flex items-start gap-3">
          <i class="text-2xl" :class="{
            'fas fa-info-circle text-blue-500': notification.type === 'info',
            'fas fa-check-circle text-green-500': notification.type === 'success',
            'fas fa-exclamation-triangle text-yellow-500': notification.type === 'warning',
            'fas fa-times-circle text-red-500': notification.type === 'error',
          }"></i>
          <div class="flex-1">
            <h4 class="font-bold text-gray-900 dark:text-white text-sm">{{ notification.title }}</h4>
            <p class="text-xs text-gray-600 dark:text-gray-300 mt-1 whitespace-pre-line">{{ notification.message }}</p>
            
            <div v-if="notification.confirmAction" class="flex gap-2 mt-3">
              <button @click="confirmNotification" class="px-3 py-1.5 bg-red-500 text-white text-xs font-bold rounded hover:bg-red-600">
                Confirmar
              </button>
              <button @click="closeNotification" class="px-3 py-1.5 bg-gray-200 text-gray-700 text-xs font-bold rounded hover:bg-gray-300">
                Cancelar
              </button>
            </div>
            
            <button v-else @click="closeNotification" class="mt-2 text-xs text-indigo-600 hover:underline">
              Fechar
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import { useApi } from '@/composables/useApi';
import UnifiedMapView from '@/components/Map/UnifiedMapView.vue';
import EditorSidebar from './components/EditorSidebar.vue';

const route = useRoute();
const api = useApi();

const cableId = computed(() => route.params.id);

// ==================== State Management ====================
const cable = ref(null);
const mode = ref('read');
const isSaving = ref(false);
const mapRef = ref(null);
const drawingPlugin = ref(null);

const notification = reactive({
  show: false,
  title: '',
  message: '',
  type: 'info',
  confirmAction: null
});

const pluginOptions = {
  drawing: {
    drawingMode: null,
    drawingControl: false
  }
};

// ==================== Google Maps Objects ====================
let mapInstance = null;
let originalPolyline = null;
let startMarker = null;
let endMarker = null;

// ==================== Lifecycle ====================
onMounted(async () => {
  console.log('[FiberRouteEditor] Mounted — Simple Version (No CEOs/Fusion/Split)');
  await loadCable();
});

// ==================== Data Loading ====================
const loadCable = async () => {
  try {
    console.log(`[FiberRouteEditor] Loading cable ${cableId.value}`);
    const response = await api.get(`/api/v1/inventory/fiber-cables/${cableId.value}/`);
    cable.value = response;
    
    console.log('[FiberRouteEditor] Cable loaded:', cable.value);
    
    if (mapInstance) {
      await nextTick();
      renderCableOnMap();
    }
  } catch (err) {
    console.error('[FiberRouteEditor] Error loading cable:', err);
    showNotification(
      'Erro ao Carregar Cabo',
      err?.response?.data?.detail || err?.message || 'Erro desconhecido.',
      'error'
    );
  }
};

// ==================== Map Events ====================
const onMapReady = (map) => {
  console.log('[FiberRouteEditor] Map ready');
  mapInstance = map;
  
  if (cable.value) {
    renderCableOnMap();
  }
};

const onPluginLoaded = ({ pluginName, plugin }) => {
  if (pluginName === 'drawing') {
    console.log('[FiberRouteEditor] Drawing plugin loaded');
    drawingPlugin.value = plugin;
  }
};

// ==================== Rendering ====================
const renderCableOnMap = () => {
  if (!mapInstance || !cable.value?.path) {
    console.warn('[FiberRouteEditor] Cannot render: missing map or cable path');
    return;
  }

  clearMapObjects();

  const coords = cable.value.path.map(p => ({ lat: p[1], lng: p[0] }));
  
  // Draw polyline
  originalPolyline = new google.maps.Polyline({
    path: coords,
    geodesic: true,
    strokeColor: '#2563EB',
    strokeOpacity: 0.8,
    strokeWeight: 3,
    map: mapInstance
  });

  // Start marker
  if (coords.length > 0) {
    startMarker = new google.maps.Marker({
      position: coords[0],
      map: mapInstance,
      title: cable.value.name || 'Início',
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 8,
        fillColor: '#10B981',
        fillOpacity: 1,
        strokeColor: '#FFFFFF',
        strokeWeight: 2
      }
    });

    const startInfo = new google.maps.InfoWindow({
      content: `<div class="p-2">
        <p class="font-bold text-sm">${cable.value.name || 'Cabo'}</p>
        <p class="text-xs text-gray-600">Início do traçado</p>
      </div>`
    });

    startMarker.addListener('click', () => {
      startInfo.open(mapInstance, startMarker);
    });
  }

  // End marker
  if (coords.length > 1) {
    const lastCoord = coords[coords.length - 1];
    endMarker = new google.maps.Marker({
      position: lastCoord,
      map: mapInstance,
      title: 'Fim',
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 8,
        fillColor: '#EF4444',
        fillOpacity: 1,
        strokeColor: '#FFFFFF',
        strokeWeight: 2
      }
    });

    const endInfo = new google.maps.InfoWindow({
      content: `<div class="p-2">
        <p class="font-bold text-sm">Fim do Traçado</p>
        <p class="text-xs text-gray-600">${cable.value.calculated_length_km?.toFixed(2)} km</p>
      </div>`
    });

    endMarker.addListener('click', () => {
      endInfo.open(mapInstance, endMarker);
    });
  }

  // Fit bounds
  if (coords.length > 0) {
    const bounds = new google.maps.LatLngBounds();
    coords.forEach(coord => bounds.extend(coord));
    mapInstance.fitBounds(bounds);
  }

  console.log('[FiberRouteEditor] Cable rendered on map');
};

const clearMapObjects = () => {
  if (originalPolyline) {
    originalPolyline.setMap(null);
    originalPolyline = null;
  }
  if (startMarker) {
    startMarker.setMap(null);
    startMarker = null;
  }
  if (endMarker) {
    endMarker.setMap(null);
    endMarker = null;
  }
};

// ==================== Mode Control ====================
const setMode = (newMode) => {
  mode.value = newMode;
  console.log('[FiberRouteEditor] Mode changed:', newMode);
  
  if (newMode === 'edit' && drawingPlugin.value) {
    drawingPlugin.value.setDrawingMode(google.maps.drawing.OverlayType.POLYLINE);
  } else if (drawingPlugin.value) {
    drawingPlugin.value.setDrawingMode(null);
  }
};

// ==================== Save/Cancel ====================
const saveCable = async (updatedData) => {
  isSaving.value = true;
  
  try {
    const payload = {
      ...updatedData,
      path: cable.value.path // Mantém path existente por enquanto
    };
    
    console.log('[FiberRouteEditor] Saving cable:', payload);
    
    const response = await api.patch(
      `/api/v1/inventory/fiber-cables/${cableId.value}/`,
      payload
    );
    
    cable.value = response;
    
    showNotification(
      'Cabo Salvo!',
      'Alterações salvas com sucesso.',
      'success'
    );
    
    setMode('read');
  } catch (err) {
    console.error('[FiberRouteEditor] Error saving cable:', err);
    showNotification(
      'Erro ao Salvar',
      err?.response?.data?.detail || err?.message || 'Erro desconhecido.',
      'error'
    );
  } finally {
    isSaving.value = false;
  }
};

const cancelEdit = () => {
  setMode('read');
  loadCable(); // Reload para descartar mudanças
};

const updateBasicInfo = (updatedInfo) => {
  Object.assign(cable.value, updatedInfo);
};

// ==================== KML Import ====================
const onKmlSelected = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('kml_file', file);

  try {
    console.log('[FiberRouteEditor] Uploading KML...');
    const response = await api.post(
      `/api/v1/inventory/fiber-cables/${cableId.value}/import-kml/`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' }
      }
    );

    showNotification(
      'KML Importado!',
      `Traçado atualizado com ${response.coordinates_count} coordenadas.`,
      'success'
    );

    await loadCable();
  } catch (err) {
    console.error('[FiberRouteEditor] Error importing KML:', err);
    showNotification(
      'Erro ao Importar KML',
      err?.response?.data?.detail || err?.message || 'Erro desconhecido.',
      'error'
    );
  }

  event.target.value = '';
};

// ==================== Notifications ====================
const showNotification = (title, message, type = 'info', confirmAction = null) => {
  notification.title = title;
  notification.message = message;
  notification.type = type;
  notification.confirmAction = confirmAction;
  notification.show = true;

  if (!confirmAction) {
    setTimeout(closeNotification, 5000);
  }
};

const closeNotification = () => {
  notification.show = false;
  notification.confirmAction = null;
};

const confirmNotification = () => {
  if (notification.confirmAction) {
    notification.confirmAction();
  }
  closeNotification();
};
</script>

<style scoped>
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from {
  transform: translateY(100%);
  opacity: 0;
}

.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
