<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div class="bg-white dark:bg-gray-800 w-[95vw] h-[85vh] rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 flex flex-col">
      <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h3 class="font-semibold text-gray-900 dark:text-white text-sm">
          Traçado do Cabo
          <span v-if="cableName" class="ml-2 text-gray-500">{{ cableName }}</span>
          <span v-if="pointCount" class="ml-2 text-xs text-gray-400">{{ pointCount }} pontos · {{ distanceKm.toFixed(2) }} km</span>
        </h3>
        <div class="flex items-center gap-2">
          <label class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded cursor-pointer">
            <input type="file" accept=".kml,.kmz" class="hidden" @change="onKmlSelected" />
            <i class="fas fa-file-upload mr-1"></i> Importar KML
          </label>
          <button @click="clearPath" class="px-3 py-1 text-xs bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded">
            Limpar
          </button>
          <button @click="savePath" class="px-3 py-1 text-xs bg-indigo-600 hover:bg-indigo-700 text-white rounded">
            <i class="fas fa-save mr-1"></i> Salvar Traçado
          </button>
          <button @click="$emit('close')" class="px-3 py-1 text-xs bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded">
            Fechar
          </button>
        </div>
      </div>
      <div class="flex-1 relative">
        <MapCanvas class="w-full h-full" :controls="{ streetView: false, mapType: false }" @ready="onMapReady" />
        <p class="absolute bottom-3 left-3 text-xs bg-white/90 dark:bg-gray-900/80 text-gray-700 dark:text-gray-200 rounded px-2 py-1 pointer-events-none">
          Clique no mapa para adicionar vértices; arraste para mover; botão direito num vértice remove.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * CableMapModal — editar o traçado de um cabo no mapa.
 * EV-0012d: `MapCanvas` + `useRouteDrawing` em vez da `UnifiedMapView` Google-only.
 * O traçado atual do cabo é carregado ao abrir (antes começava-se do zero).
 */
import { ref, onBeforeUnmount, watch } from 'vue';
import MapCanvas from '@/components/Map/MapCanvas.vue';
import { createRouteDrawing } from '@/composables/useRouteDrawing';
import { useApi } from '@/composables/useApi';

const props = defineProps({
  show: { type: Boolean, default: false },
  cableId: { type: [String, Number], required: true },
  cableName: { type: String, default: '' },
});
const emit = defineEmits(['close', 'saved']);

const api = useApi();
const pointCount = ref(0);
const distanceKm = ref(0);
let drawing = null;

const onPathChange = (path, meters) => {
  pointCount.value = path.length;
  distanceKm.value = meters / 1000;
};

const onMapReady = async (map) => {
  drawing?.destroy();
  drawing = createRouteDrawing(map, { onPathChange });
  await loadCurrentPath();
  drawing.start();
};

const loadCurrentPath = async () => {
  try {
    const cable = await api.get(`/api/v1/inventory/fiber-cables/${props.cableId}/`);
    const path = cable?.path || cable?.path_coordinates || [];
    if (drawing && path.length) {
      drawing.setPath(path);
      drawing.fitBounds();
    }
  } catch (err) {
    console.error('[CableMapModal] Falha ao carregar traçado atual', err);
  }
};

const clearPath = () => drawing?.clear();

const savePath = async () => {
  try {
    const path = drawing?.getPath() || [];
    await api.post(`/api/v1/fiber-cables/${props.cableId}/update-path/`, { path });
    emit('saved', { cable_id: props.cableId, points: path.length });
    alert('Traçado salvo com sucesso.');
  } catch (err) {
    console.error('Falha ao salvar traçado', err);
    alert(err?.message || 'Falha ao salvar traçado.');
  }
};

const onKmlSelected = async (evt) => {
  const file = evt.target.files?.[0];
  if (!file) return;
  try {
    const form = new FormData();
    form.append('kml', file);
    const resp = await fetch(`/api/v1/fiber-cables/${props.cableId}/import-kml/`, {
      method: 'POST',
      body: form,
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' },
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`HTTP ${resp.status} ${resp.statusText}: ${txt.slice(0, 200)}`);
    }
    const json = await resp.json();
    const points = json?.points || 0;
    if (drawing) {
      drawing.setPath(json?.path || []);
      drawing.fitBounds();
    }
    alert(`KML importado. Pontos: ${points}.`);
  } catch (err) {
    console.error('Falha ao importar KML', err);
    alert(err?.message || 'Falha ao importar KML.');
  } finally {
    evt.target.value = '';
  }
};

const teardown = () => {
  drawing?.destroy();
  drawing = null;
  pointCount.value = 0;
  distanceKm.value = 0;
};

watch(() => props.show, (open) => {
  if (!open) teardown(); // o MapCanvas desmonta com o v-if e destrói o mapa
});

onBeforeUnmount(teardown);
</script>
