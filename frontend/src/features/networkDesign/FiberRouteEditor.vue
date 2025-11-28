<template>
  <div class="h-full flex flex-col relative">
    <div class="absolute top-4 left-4 z-[1000] bg-white dark:bg-gray-800 p-4 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 max-w-md">
      <div v-if="loading" class="flex items-center gap-2">
        <div class="animate-spin h-4 w-4 border-2 border-indigo-500 rounded-full border-t-transparent"></div>
        <span class="text-sm">Carregando cabo...</span>
      </div>
      <div v-else>
        <h3 class="font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <i class="fas fa-bezier-curve text-indigo-500"></i>
          {{ cable.name }}
        </h3>
        <div class="mt-2 flex items-center gap-2 text-xs text-gray-500">
          <span :class="{'text-green-600 font-bold': !!cable.site_a_name}">{{ cable.site_a_name || 'Origem Indefinida' }}</span>
          <i class="fas fa-arrow-right"></i>
          <span :class="{'text-indigo-600 font-bold': !!cable.site_b_name}">{{ cable.site_b_name || 'Destino Indefinido' }}</span>
        </div>
        <div v-if="pathStats" class="mt-2 text-xs text-gray-600 dark:text-gray-400">
          <i class="fas fa-route mr-1"></i> {{ pathStats.points }} pontos · {{ pathStats.distance }} km
        </div>
        <div class="mt-3 flex gap-2">
          <label class="px-3 py-1.5 rounded-lg text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-200 dark:border-gray-600 cursor-pointer">
            <input type="file" class="hidden" accept=".kml" @change="onKmlSelected" />
            <i class="fas fa-file-upload mr-1"></i> KML
          </label>
          <button @click="saveGeometry" :disabled="!canSave" class="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-colors shadow-sm">
            <i class="fas fa-save mr-1"></i> Salvar Traçado
          </button>
          <router-link :to="'/network/inventory'" class="px-3 py-1.5 rounded-lg text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600">
            Cancelar
          </router-link>
        </div>
      </div>
    </div>
    <UnifiedMapView
      ref="mapRef"
      :plugins="['drawing']"
      :plugin-options="pluginOptions"
      class="w-full h-full"
      @map-ready="onMapReady"
      @plugin-loaded="onPluginLoaded"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useApi } from '@/composables/useApi';
import UnifiedMapView from '@/components/Map/UnifiedMapView.vue';

const route = useRoute();
const api = useApi();
const id = route.params.id;

const loading = ref(true);
const cable = ref({});
const mapRef = ref(null);
const pathStats = ref(null);
const mapInstance = ref(null);
const drawingPlugin = ref(null);

const pluginOptions = {
  drawing: {
    onPathChange: (coords, distance) => {
      pathStats.value = {
        points: coords.length,
        distance: (distance / 1000).toFixed(2)
      };
    }
  }
};

const canSave = computed(() => {
  return pathStats.value && pathStats.value.points >= 2;
});

const getDrawing = () => drawingPlugin.value;

const onMapReady = (map) => {
  mapInstance.value = map;
  console.log('[FiberRouteEditor] Map ready', map);
};

const onPluginLoaded = async (pluginName, plugin) => {
  if (pluginName === 'drawing') {
    drawingPlugin.value = plugin;
    console.log('[FiberRouteEditor] Drawing plugin loaded', plugin);
    await loadCableData();
  }
};

const loadCableData = async () => {
  try {
    const data = await api.get(`/api/v1/fiber-cables/${id}/`);
    cable.value = data;
    console.log('[FiberRouteEditor] Cable data loaded', data);

    const drawing = getDrawing();
    if (!drawing) {
      console.warn('[FiberRouteEditor] Drawing plugin not available');
      return;
    }

    // Carregar path existente
    const path = Array.isArray(data.path_coordinates) ? data.path_coordinates : [];
    if (path.length >= 2) {
      console.log('[FiberRouteEditor] Loading existing path', path.length, 'points');
      drawing.setPath(path);
      drawing.fitBounds();
    } else {
      // Centralizar entre Site A e B
      const locA = data.site_a_location;
      const locB = data.site_b_location;
      if (locA && locB && mapInstance.value) {
        console.log('[FiberRouteEditor] Centering on sites', locA, locB);
        const bounds = new google.maps.LatLngBounds();
        bounds.extend(new google.maps.LatLng(locA.lat, locA.lng));
        bounds.extend(new google.maps.LatLng(locB.lat, locB.lng));
        mapInstance.value.fitBounds(bounds);
        
        // Desenhar linha guia tracejada
        new google.maps.Polyline({
          path: [locA, locB],
          map: mapInstance.value,
          strokeColor: '#9CA3AF',
          strokeOpacity: 0.6,
          strokeWeight: 2,
          geodesic: true,
          icons: [{
            icon: { path: 'M 0,-1 0,1', strokeOpacity: 1, scale: 2 },
            offset: '0',
            repeat: '20px'
          }]
        });
      }
    }
    
    // Iniciar modo desenho
    drawing.startDrawing();
  } catch (err) {
    console.error('[FiberRouteEditor] Erro ao carregar cabo', err);
    alert(err?.message || 'Erro ao carregar dados do cabo.');
  } finally {
    loading.value = false;
  }
};

const saveGeometry = async () => {
  try {
    const drawing = getDrawing();
    if (!drawing) {
      alert('Plugin de desenho não está disponível.');
      return;
    }
    
    const path = drawing.getPathCoordinates() || [];
    if (path.length < 2) {
      alert('É necessário desenhar pelo menos 2 pontos.');
      return;
    }
    
    console.log('[FiberRouteEditor] Saving path', path.length, 'points');
    const result = await api.post(`/api/v1/fiber-cables/${id}/update-path/`, { path });
    console.log('[FiberRouteEditor] Path saved', result);
    alert(`Traçado salvo com sucesso! ${result.points} pontos, ${result.length_km} km`);
  } catch (err) {
    console.error('[FiberRouteEditor] Erro ao salvar traçado', err);
    alert(err?.message || 'Erro ao salvar traçado.');
  }
};

const onKmlSelected = async (evt) => {
  const file = evt.target.files?.[0];
  if (!file) return;
  
  evt.target.value = ''; // Reset input
  
  try {
    console.log('[FiberRouteEditor] Importing KML', file.name);
    const formData = new FormData();
    formData.append('kml', file);
    
    const result = await api.postFormData(`/api/v1/fiber-cables/${id}/import-kml/`, formData);
    console.log('[FiberRouteEditor] KML imported', result);
    
    const drawing = getDrawing();
    if (drawing && result.path && result.path.length > 0) {
      drawing.clearPath();
      drawing.setPath(result.path);
      drawing.fitBounds();
      alert(`KML importado! ${result.points} pontos, ${result.length_km} km`);
    } else {
      alert('KML importado mas sem coordenadas válidas.');
    }
  } catch (err) {
    console.error('[FiberRouteEditor] Falha ao importar KML', err);
    alert(err?.message || 'Falha ao importar KML.');
  }
};
</script>

<style scoped>
</style>
