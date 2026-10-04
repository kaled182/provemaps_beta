<template>
  <div class="flex h-screen overflow-hidden relative bg-gray-50 dark:bg-gray-900">
    
    <!-- Área do Mapa -->
    <div class="flex-1 relative bg-gray-100 dark:bg-gray-800 z-0">
      
      <MapCanvas class="w-full h-full" :controls="{ streetView: false }" @ready="onMapReady">
        <MapPopup v-if="map && popup" :map="map" :position="popup.position">
          <div class="p-2 text-sm">
            <p class="font-bold">{{ popup.title }}</p>
            <p v-if="popup.text" class="text-xs opacity-80">{{ popup.text }}</p>
          </div>
        </MapPopup>
      </MapCanvas>

      <div v-if="mode === 'edit'" class="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 text-xs bg-white/90 dark:bg-gray-800/90 text-gray-700 dark:text-gray-200 rounded-full px-3 py-1 shadow">
        {{ drawnPointCount }} vértices · {{ drawnDistanceKm.toFixed(2) }} km — clique para adicionar, arraste para mover, botão direito remove
      </div>
      
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
/**
 * FiberRouteEditor — ver e editar o traçado de um cabo.
 * EV-0012d: `MapCanvas` + `useRouteDrawing` + `MapPopup` em vez da
 * `UnifiedMapView`/`google.maps`. Em modo «Editar Traçado» os vértices são
 * arrastáveis e o salvar envia o caminho novo (antes mantinha sempre o antigo).
 */
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRoute } from 'vue-router';
import { useApi } from '@/composables/useApi';
import MapCanvas from '@/components/Map/MapCanvas.vue';
import MapPopup from '@/components/Map/MapPopup.vue';
import { createRouteDrawing, normalizePoint } from '@/composables/useRouteDrawing';
import EditorSidebar from './components/EditorSidebar.vue';

const route = useRoute();
const api = useApi();

const cableId = computed(() => route.params.id);

// ==================== State Management ====================
const cable = ref(null);
const mode = ref('read');
const isSaving = ref(false);
const map = ref(null);          // IMap (shallow por natureza: só se atribui)
const popup = ref(null);        // { position, title, text }
const drawnPointCount = ref(0);
const drawnDistanceKm = ref(0);

const notification = reactive({
  show: false,
  title: '',
  message: '',
  type: 'info',
  confirmAction: null
});

// ==================== Objetos do mapa (IMap) ====================
let routePolyline = null;
let startMarker = null;
let endMarker = null;
let drawing = null;

// ==================== Lifecycle ====================
onMounted(async () => {
  await loadCable();
});

onBeforeUnmount(() => {
  stopEditing();
  clearMapObjects();
});

// ==================== Data Loading ====================
const cablePath = () => (cable.value?.path || []).map(normalizePoint).filter(Boolean);

const loadCable = async () => {
  try {
    const response = await api.get(`/api/v1/inventory/fiber-cables/${cableId.value}/`);
    cable.value = response;
    if (map.value) {
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
const onMapReady = (created) => {
  map.value = created;
  if (cable.value) {
    renderCableOnMap();
  }
};

// ==================== Rendering ====================
const renderCableOnMap = () => {
  const coords = cablePath();
  if (!map.value || !coords.length) return;

  clearMapObjects();

  routePolyline = map.value.createPolyline({
    path: coords,
    strokeColor: '#2563EB',
    strokeOpacity: 0.8,
    strokeWeight: 3,
    clickable: false,
  });

  startMarker = map.value.createMarker({
    position: coords[0],
    markerType: 'origin',
    title: cable.value.name || 'Início',
  });
  startMarker.on('click', () => {
    popup.value = { position: coords[0], title: cable.value.name || 'Cabo', text: 'Início do traçado' };
  });

  if (coords.length > 1) {
    const last = coords[coords.length - 1];
    endMarker = map.value.createMarker({ position: last, markerType: 'destination', title: 'Fim' });
    endMarker.on('click', () => {
      const km = cable.value.calculated_length_km;
      popup.value = { position: last, title: 'Fim do Traçado', text: Number.isFinite(km) ? `${km.toFixed(2)} km` : '' };
    });
  }

  map.value.fitBounds(coords, { padding: 50, maxZoom: 16 });
};

const clearMapObjects = () => {
  routePolyline?.remove();
  routePolyline = null;
  startMarker?.remove();
  startMarker = null;
  endMarker?.remove();
  endMarker = null;
  popup.value = null;
};

// ==================== Mode Control ====================
const startEditing = () => {
  if (!map.value) return;
  clearMapObjects();
  drawing = createRouteDrawing(map.value, {
    onPathChange: (path, meters) => {
      drawnPointCount.value = path.length;
      drawnDistanceKm.value = meters / 1000;
    },
  });
  drawing.setPath(cablePath());
  drawing.start();
};

const stopEditing = () => {
  drawing?.destroy();
  drawing = null;
  drawnPointCount.value = 0;
  drawnDistanceKm.value = 0;
};

const setMode = (newMode) => {
  if (newMode === mode.value) return;
  mode.value = newMode;
  if (newMode === 'edit') {
    startEditing();
  } else {
    stopEditing();
    renderCableOnMap();
  }
};

// ==================== Save/Cancel ====================
const saveCable = async (updatedData = {}) => {
  isSaving.value = true;

  try {
    // Em edição, o traçado desenhado substitui o antigo (GeoJSON [lng, lat])
    const path = drawing
      ? drawing.getPath().map(({ lat, lng }) => [lng, lat])
      : cable.value.path;
    const payload = { ...updatedData, path };

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

    setMode('read');
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
