<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div class="bg-white dark:bg-gray-800 w-[95vw] h-[85vh] rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 flex flex-col">
      <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h3 class="font-semibold text-gray-900 dark:text-white text-sm">
          Traçado do Cabo
          <span v-if="cableName" class="ml-2 text-gray-500">{{ cableName }}</span>
        </h3>
        <div class="flex items-center gap-2">
          <label class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded cursor-pointer">
            <input type="file" accept=".kml" class="hidden" @change="onKmlSelected" />
            <i class="fas fa-file-upload mr-1"></i> Importar KML
          </label>
          <button @click="savePath" class="px-3 py-1 text-xs bg-indigo-600 hover:bg-indigo-700 text-white rounded">
            <i class="fas fa-save mr-1"></i> Salvar Traçado
          </button>
          <button @click="$emit('close')" class="px-3 py-1 text-xs bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded">
            Fechar
          </button>
        </div>
      </div>
      <div class="flex-1">
        <UnifiedMapView
          ref="mapRef"
          :plugins="['drawing']"
          :center="center"
          :zoom="zoom"
          class="w-full h-full"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
import UnifiedMapView from '@/components/Map/UnifiedMapView.vue';
import { useApi } from '@/composables/useApi';

const props = defineProps({
  show: { type: Boolean, default: false },
  cableId: { type: [String, Number], required: true },
  cableName: { type: String, default: '' },
});
const emit = defineEmits(['close', 'saved']);

const api = useApi();
const mapRef = ref(null);
const center = ref({ lat: -15.78, lng: -47.93 });
const zoom = ref(12);
const currentPath = ref([]);

const getDrawingPlugin = () => {
  const inst = mapRef.value;
  if (!inst || typeof inst.getPlugin !== 'function') return null;
  return inst.getPlugin('drawing');
};

const savePath = async () => {
  try {
    const plugin = getDrawingPlugin();
    const path = plugin?.getPath?.() || currentPath.value || [];
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
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`HTTP ${resp.status} ${resp.statusText}: ${txt.slice(0, 200)}`);
    }
    const json = await resp.json();
    const points = json?.points || 0;
    // If map plugin supports setting path, draw it
    const plugin = getDrawingPlugin();
    if (plugin && typeof plugin.setPath === 'function') {
      plugin.setPath(json?.path || []);
    }
    currentPath.value = json?.path || [];
    alert(`KML importado. Pontos: ${points}.`);
  } catch (err) {
    console.error('Falha ao importar KML', err);
    alert(err?.message || 'Falha ao importar KML.');
  }
};

watch(() => props.show, (open) => {
  if (open) {
    // Optionally center map based on cable sites in future
    setTimeout(() => {
      const plugin = getDrawingPlugin();
      plugin?.startDrawing?.();
    }, 100);
  }
});

onMounted(() => {
  // No-op; UnifiedMapView loads itself with Google Maps key
});
</script>

<style scoped>
</style>