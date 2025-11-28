<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
    <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
      <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-800">
        <div>
          <h3 class="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <i class="fas fa-bezier-curve text-indigo-500"></i>
            {{ isEditing ? 'Editar Cabo Óptico' : 'Lançamento de Novo Cabo' }}
          </h3>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Defina a rota física e as características da fibra.</p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors">
          <i class="fas fa-times text-xl"></i>
        </button>
      </div>

      <div class="p-6 overflow-y-auto space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nome do Cabo (ID)</label>
            <input
              v-model="form.name"
              type="text"
              class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:ring-2 focus:ring-indigo-500 outline-none transition-shadow"
              placeholder="Ex: CB-BKB-GANDRA-01"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Tipo de Rede</label>
            <select v-model="form.type" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 outline-none">
              <option value="backbone">Backbone (Primário)</option>
              <option value="distribution">Distribuição (Secundário)</option>
              <option value="drop">Drop (Acesso)</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Status Operacional</label>
            <select v-model="form.status" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 outline-none">
              <option value="active">Ativo (Iluminado)</option>
              <option value="planned">Planejado / Em Projeto</option>
              <option value="dark">Fibra Apagada (Dark Fiber)</option>
              <option value="cut">Rompido (Crítico)</option>
            </select>
          </div>
        </div>

        <div v-if="!hasExistingRoute" class="p-4 rounded-xl border border-dashed border-indigo-300 dark:border-indigo-700 bg-indigo-50/60 dark:bg-indigo-900/10">
          <h4 class="text-xs font-bold text-indigo-800 dark:text-indigo-300 uppercase mb-2 flex items-center gap-2">
            <i class="fas fa-file-import"></i> Importar Rota via KML
          </h4>
          <p class="text-xs text-gray-600 dark:text-gray-400 mb-2">Use o arquivo KML para desenhar o caminho do cabo (mesmo formato usado em NetworkDesign).</p>
          <label class="flex flex-col items-start gap-2 cursor-pointer">
            <input
              type="file"
              accept=".kml"
              @change="onFileSelected"
              class="text-sm text-gray-700 dark:text-gray-200"
            />
            <span class="text-xs text-gray-500 dark:text-gray-400">
              {{ form.kmlFile ? form.kmlFile.name : 'Selecione o arquivo KML...' }}
            </span>
          </label>
          <div v-if="!form.kmlFile && !isEditing" class="mt-2 text-xs text-red-500 flex items-center gap-1">
            <i class="fas fa-exclamation-circle"></i> O arquivo KML é obrigatório para lançar um novo cabo.
          </div>
        </div>

        <div class="bg-indigo-50 dark:bg-indigo-900/10 p-4 rounded-xl border border-indigo-100 dark:border-indigo-800/30">
          <h4 class="text-xs font-bold text-indigo-800 dark:text-indigo-300 uppercase mb-3 flex items-center gap-2">
            <i class="fas fa-route"></i> Definição de Rota
          </h4>

          <div class="mb-3 flex items-center gap-2">
            <label class="inline-flex items-center gap-2 text-xs text-gray-700 dark:text-gray-200 cursor-pointer">
              <input type="checkbox" v-model="form.single_port" class="text-indigo-600 focus:ring-indigo-500 rounded" />
              Monitorar apenas origem (sem SNMP no destino)
            </label>
          </div>

          <div class="flex flex-col md:flex-row items-center gap-3">
            <div class="flex-1 w-full">
              <label class="block text-xs text-gray-500 mb-1 font-medium">Origem (Site A)</label>
              <select v-model="form.site_a" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm outline-none">
                <option value="" disabled>Selecione...</option>
                <option v-for="site in availableSites" :key="site.id" :value="site.id">{{ site.name }}</option>
              </select>
            </div>

            <div class="text-indigo-400 dark:text-indigo-600 mt-4">
              <i class="fas fa-exchange-alt text-xl"></i>
            </div>

            <div class="flex-1 w-full">
              <label class="block text-xs text-gray-500 mb-1 font-medium">Destino (Site B)</label>
              <select v-model="form.site_b" :disabled="form.single_port" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm outline-none disabled:opacity-50">
                <option value="" disabled>Selecione...</option>
                <option v-for="site in availableSites" :key="site.id" :value="site.id">{{ site.name }}</option>
              </select>
            </div>
          </div>

          <div v-if="!form.single_port && form.site_a && form.site_a === form.site_b" class="mt-2 text-xs text-red-500 flex items-center gap-1">
            <i class="fas fa-exclamation-circle"></i> Origem e destino não podem ser o mesmo local.
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="md:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Dispositivo Origem</label>
              <select v-model="form.device_a" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 outline-none">
                <option value="">Selecione...</option>
                <option v-for="dev in devicesA" :key="dev.id" :value="dev.id">{{ dev.name }}</option>
              </select>
              <p class="text-[10px] text-gray-500 mt-1">Site A: {{ form.site_a || '—' }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Dispositivo Destino</label>
              <select v-model="form.device_b" :disabled="form.single_port" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 outline-none disabled:opacity-50">
                <option value="">Selecione...</option>
                <option v-for="dev in devicesB" :key="dev.id" :value="dev.id">{{ dev.name }}</option>
              </select>
              <p class="text-[10px] text-gray-500 mt-1">Site B: {{ form.site_b || '—' }}</p>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Porta Origem</label>
            <select v-model="form.port_a" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 outline-none">
              <option value="">Selecione...</option>
              <option v-for="p in portsA" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
            <p v-if="loadingPortsA" class="text-[10px] text-gray-400 mt-1">Carregando portas...</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Porta Destino</label>
            <select v-model="form.port_b" :disabled="form.single_port" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 outline-none disabled:opacity-50">
              <option value="">Selecione...</option>
              <option v-for="p in portsB" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
            <p v-if="loadingPortsB" class="text-[10px] text-gray-400 mt-1">Carregando portas...</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Capacidade (FO)</label>
            <select v-model="form.fiber_count" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 outline-none font-mono">
              <option :value="6">06 FO</option>
              <option :value="12">12 FO</option>
              <option :value="24">24 FO</option>
              <option :value="36">36 FO</option>
              <option :value="48">48 FO</option>
              <option :value="72">72 FO</option>
              <option :value="144">144 FO</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Metragem (m)</label>
            <div class="relative">
              <input
                v-model.number="form.length"
                type="number"
                min="0"
                readonly
                class="w-full pl-3 pr-8 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-800 font-mono"
                :class="form.length > 0 ? 'text-gray-900 dark:text-white font-bold' : 'text-gray-500'"
                placeholder="0"
              />
              <span class="absolute right-3 top-2 text-xs text-gray-400 font-bold">m</span>
            </div>
            <p v-if="form.kmlFile && form.length === 0" class="text-[10px] text-orange-500 mt-1 flex items-center gap-1">
              <i class="fas fa-exclamation-triangle"></i>
              KML processado mas comprimento = 0. Verifique o arquivo.
            </p>
          </div>

          <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2 border border-gray-200 dark:border-gray-600 flex flex-col justify-center items-center">
            <span class="text-[10px] text-gray-500 uppercase font-bold">Perda Estimada</span>
            <div class="flex items-baseline gap-1">
              <span class="text-lg font-bold text-gray-700 dark:text-gray-200">{{ estimatedLoss }}</span>
              <span class="text-xs text-gray-400">dB</span>
            </div>
            <span class="text-[9px] text-gray-400">@ 1310nm (0.35dB/km)</span>
          </div>
        </div>

        <div v-if="kmlError" class="text-xs text-red-500 flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg p-2">
          <i class="fas fa-exclamation-triangle"></i>
          <span>{{ kmlError }}</span>
        </div>
      </div>

      <div class="px-6 py-4 bg-gray-50 dark:bg-gray-700/30 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-3">
        <button @click="$emit('close')" class="px-4 py-2 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors">Cancelar</button>
        <button
          @click="save"
          :disabled="!isValid || saving"
          class="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg shadow-sm flex items-center gap-2 font-medium transition-all"
        >
          <i class="fas fa-save" :class="{ 'fa-spin': saving }"></i> Salvar Cabo
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';

const props = defineProps({
  show: Boolean,
  cable: Object,
  sites: { type: Array, default: () => [] },
  saving: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'saved']);

const form = ref({
  id: null,
  name: '',
  type: 'backbone',
  status: 'planned',
  site_a: '',
  site_b: '',
  device_a: '',
  device_b: '',
  port_a: '',
  port_b: '',
  fiber_count: 12,
  length: 0,
  kmlFile: null,
  kmlName: '',
  single_port: false,
});

const kmlError = ref('');
const devicesA = ref([]);
const devicesB = ref([]);
const loadingDevicesA = ref(false);
const loadingDevicesB = ref(false);
const portsA = ref([]);
const portsB = ref([]);
const loadingPortsA = ref(false);
const loadingPortsB = ref(false);
const isInitializing = ref(false); // Flag para evitar resets durante carga inicial

const availableSites = computed(() => props.sites || []);
const isEditing = computed(() => !!(props.cable && props.cable.id));

// Esconde import KML quando já existe rota (comprimento > 0 ou path com 2+ pontos)
const hasExistingRoute = computed(() => {
  if (!isEditing.value) return false;
  const len = Number(form.value.length || 0);
  const path = ((props.cable && (props.cable.path || props.cable.path_coordinates)) || []);
  return len > 0 || (Array.isArray(path) && path.length >= 2);
});

const isValid = computed(() => {
  const baseOk = (
    form.value.name &&
    form.value.site_a &&
    form.value.length > 0 &&
    (isEditing.value ? true : !!form.value.kmlFile) &&
    (isEditing.value ? true : !!form.value.device_a) &&
    (isEditing.value ? true : !!form.value.port_a)
  );
  if (form.value.single_port) {
    return !!baseOk;
  }
  return (
    !!baseOk &&
    form.value.site_b &&
    form.value.site_a !== form.value.site_b &&
    (isEditing.value ? true : !!form.value.device_b) &&
    (isEditing.value ? true : !!form.value.port_b)
  );
});

const estimatedLoss = computed(() => {
  if (!form.value.length) return '0.00';
  const lossPerKm = 0.35;
  const km = form.value.length / 1000;
  const spliceLoss = 0.2;
  return ((km * lossPerKm) + spliceLoss).toFixed(2);
});

watch(
  () => props.cable,
  async (newCable) => {
    isInitializing.value = true; // Desabilita watches reativos durante inicialização
    
    if (newCable) {
      // Mapear dados da fibra incluindo IDs enriquecidos do backend
      form.value = {
        id: newCable.id || null,
        name: newCable.name || '',
        type: newCable.type || 'backbone',
        status: newCable.status || 'planned',
        // Sites (usar origin_site_id/destination_site_id se disponíveis)
        site_a: newCable.origin_site_id || newCable.site_a || '',
        site_b: newCable.destination_site_id || newCable.site_b || '',
        // Devices (usar origin_device_id/destination_device_id do backend)
        device_a: newCable.origin_device_id || newCable.device_a || '',
        device_b: newCable.destination_device_id || newCable.device_b || '',
        // Portas (origin_port/destination_port já são IDs)
        port_a: newCable.origin_port || newCable.port_a || '',
        port_b: newCable.destination_port || newCable.port_b || '',
        fiber_count: newCable.fiber_count || 12,
        length: newCable.length_km ? Math.round(newCable.length_km * 1000) : (newCable.length || 0),
        kmlFile: null,
        kmlName: '',
        single_port: !!newCable.single_port,
      };
      kmlError.value = '';

      console.debug('[FiberEditModal] Form inicializado', {
        site_a: form.value.site_a,
        site_b: form.value.site_b,
        device_a: form.value.device_a,
        device_b: form.value.device_b,
        port_a: form.value.port_a,
        port_b: form.value.port_b,
      });

      // Carregar devices e portas para os sites selecionados
      if (form.value.site_a) {
        await fetchDevices(form.value.site_a, 'a');
      }
      if (form.value.site_b) {
        await fetchDevices(form.value.site_b, 'b');
      }
      // Após devices carregados, carregar portas
      if (form.value.device_a) {
        await fetchPorts(form.value.device_a, 'a');
      }
      if (form.value.device_b) {
        await fetchPorts(form.value.device_b, 'b');
      }
      
      console.debug('[FiberEditModal] Cascading data carregado', {
        devicesA: devicesA.value.length,
        devicesB: devicesB.value.length,
        portsA: portsA.value.length,
        portsB: portsB.value.length,
      });
    } else {
      form.value = {
        id: null,
        name: '',
        type: 'backbone',
        status: 'planned',
        site_a: '',
        site_b: '',
        device_a: '',
        device_b: '',
        port_a: '',
        port_b: '',
        fiber_count: 48,
        length: 0,
        kmlFile: null,
        kmlName: '',
        single_port: false,
      };
      kmlError.value = '';
    }
    
    // Reativa watches após inicialização completa
    setTimeout(() => {
      isInitializing.value = false;
    }, 100);
  },
  { immediate: true }
);

const onFileSelected = (event) => {
  const file = event.target?.files?.[0];
  if (file) {
    form.value.kmlFile = file;
    form.value.kmlName = file.name;
    kmlError.value = '';
    parseKmlAndSetLength(file);
  }
};

const parseKmlAndSetLength = async (file) => {
  try {
    const text = await file.text();
    console.debug('[FiberEditModal] KML text length:', text.length);

    // Tenta múltiplos formatos de coordenadas
    let coords = [];

    // 1) Formato padrão <coordinates> em LineString/Multigeometry
    const coordsTag = extractCoordinatesFromTag(text);
    if (coordsTag.length) {
      coords = coordsTag;
      console.debug('[FiberEditModal] Coordenadas via <coordinates>:', coords.length);
    }

    // 2) Formato Google KML <gx:coord> (lon lat alt)
    if (!coords.length) {
      const gxCoords = extractCoordinatesFromGxCoord(text);
      if (gxCoords.length) {
        coords = gxCoords;
        console.debug('[FiberEditModal] Coordenadas via <gx:coord>:', coords.length);
      }
    }

    // 3) Fallback: tentar detectar pares lon,lat separados por espaço/linha
    if (!coords.length) {
      const generic = extractCoordinatesGeneric(text);
      if (generic.length) {
        coords = generic;
        console.debug('[FiberEditModal] Coordenadas via fallback genérico:', coords.length);
      }
    }

    if (!coords.length || coords.length < 2) {
      kmlError.value = 'Não foi possível encontrar coordenadas válidas no KML.';
      console.warn('[FiberEditModal] Nenhuma coordenada válida encontrada no KML');
      return;
    }

    const totalMeters = computePolylineLength(coords);
    console.debug('[FiberEditModal] Comprimento calculado:', totalMeters, 'metros');

    form.value.length = Math.round(totalMeters);
    console.debug('[FiberEditModal] form.length atualizado para:', form.value.length);
  } catch (err) {
    console.error('[FiberEditModal] Erro ao processar KML', err);
    kmlError.value = 'Erro ao processar o arquivo KML.';
  }
};

const extractCoordinatesFromTag = (kmlText) => {
  const coords = [];
  const regex = /<coordinates>([\s\S]*?)<\/coordinates>/gi;
  let match;
  while ((match = regex.exec(kmlText)) !== null) {
    const coordsText = match[1].trim();
    console.debug('[FiberEditModal] Coordenadas raw <coordinates>:', coordsText.substring(0, 200));
    const points = coordsText
      .replace(/\s+/g, ' ')
      .trim()
      .split(' ')
      .filter(Boolean);
    points.forEach((pair, idx) => {
      // Formato comum: lon,lat[,alt]
      const parts = pair.split(',');
      const lon = Number(parts[0]);
      const lat = Number(parts[1]);
      if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
        coords.push([lat, lon]);
      } else {
        console.warn(`[FiberEditModal] Coordenada inválida <coordinates> #${idx}:`, pair);
      }
    });
  }
  return coords;
};

const extractCoordinatesFromGxCoord = (kmlText) => {
  const coords = [];
  const regex = /<gx:coord>([\s\S]*?)<\/gx:coord>/gi;
  let match;
  while ((match = regex.exec(kmlText)) !== null) {
    const body = match[1].trim().split(/\s+/).filter(Boolean);
    // Formato: lon lat alt
    const lon = Number(body[0]);
    const lat = Number(body[1]);
    if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
      coords.push([lat, lon]);
    }
  }
  return coords;
};

const extractCoordinatesGeneric = (kmlText) => {
  const coords = [];
  // Tenta capturar pares numéricos padrão (lon,lat) ignorando altitude
  const regex = /(-?\d+\.\d+),\s*(-?\d+\.\d+)(?:,\s*-?\d+\.\d+)?/g;
  let match;
  while ((match = regex.exec(kmlText)) !== null) {
    const lon = Number(match[1]);
    const lat = Number(match[2]);
    if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
      coords.push([lat, lon]);
    }
  }
  return coords;
};

const computePolylineLength = (coords) => {
  let total = 0;
  for (let i = 1; i < coords.length; i += 1) {
    total += haversineDistance(coords[i - 1], coords[i]);
  }
  return total;
};

const haversineDistance = ([lat1, lon1], [lat2, lon2]) => {
  const toRad = (d) => (d * Math.PI) / 180;
  const R = 6371000; // meters
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

const save = () => {
  if (!isValid.value) return;
  emit('saved', { ...form.value });
};

watch(
  () => form.value.site_a,
  async (siteId) => {
    if (isInitializing.value) return; // Ignora durante inicialização
    
    form.value.device_a = '';
    form.value.port_a = '';
    portsA.value = [];
    if (siteId) {
      await fetchDevices(siteId, 'a');
    } else {
      devicesA.value = [];
    }
  }
);

watch(
  () => form.value.site_b,
  async (siteId) => {
    if (isInitializing.value || form.value.single_port) return; // Ignora durante inicialização ou modo single-port
    
    form.value.device_b = '';
    form.value.port_b = '';
    portsB.value = [];
    if (siteId) {
      await fetchDevices(siteId, 'b');
    } else {
      devicesB.value = [];
    }
  }
);

watch(
  () => form.value.device_a,
  async (deviceId) => {
    if (isInitializing.value) return; // Ignora durante inicialização
    
    const desired = form.value.port_a;
    portsA.value = [];
    form.value.port_a = '';
    if (deviceId) {
      await fetchPorts(deviceId, 'a');
      // restaura seleção se existir na lista
      const exists = portsA.value.some((p) => `${p.id}` === `${desired}`);
      if (exists) {
        form.value.port_a = desired;
      }
    }
  }
);

watch(
  () => form.value.device_b,
  async (deviceId) => {
    if (isInitializing.value || form.value.single_port) return; // Ignora durante inicialização ou modo single-port
    
    const desired = form.value.port_b;
    portsB.value = [];
    form.value.port_b = '';
    if (deviceId) {
      await fetchPorts(deviceId, 'b');
      const exists = portsB.value.some((p) => `${p.id}` === `${desired}`);
      if (exists) {
        form.value.port_b = desired;
      }
    }
  }
);

const devicesCache = ref(null);

const fetchDevices = async (siteId, target) => {
  const loadingFlag = target === 'a' ? loadingDevicesA : loadingDevicesB;
  const targetList = target === 'a' ? devicesA : devicesB;
  loadingFlag.value = true;
  try {
    // Lista todos devices e filtramos por site (endpoint oficial de opções)
    if (!devicesCache.value) {
      const resp = await fetch('/api/v1/inventory/devices/select-options/', {
        credentials: 'same-origin',
        headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      });
      if (!resp.ok) {
        console.error('Falha ao buscar devices (select-options)', resp.status, resp.statusText);
        devicesCache.value = [];
      } else {
        const json = await resp.json();
        // payload: { devices: [{id, name, site_id, site}] }
        devicesCache.value = json.devices || [];
      }
    }
    const filtered = (devicesCache.value || []).filter((d) => `${d.site_id}` === `${siteId}`);
    targetList.value = filtered.map((d) => ({ id: d.id, name: d.name }));
  } catch (err) {
    console.error('Erro ao carregar devices do site', siteId, err);
    targetList.value = [];
  } finally {
    loadingFlag.value = false;
  }
};

const fetchPorts = async (deviceId, target) => {
  const loadingFlag = target === 'a' ? loadingPortsA : loadingPortsB;
  const targetList = target === 'a' ? portsA : portsB;
  loadingFlag.value = true;
  try {
    // Usar novo endpoint REST com filtro por device
    const resp = await fetch(`/api/v1/ports/?device=${deviceId}&page_size=500`, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    });
    if (!resp.ok) {
      console.error('Falha ao buscar portas do device', deviceId, resp.status, resp.statusText);
      targetList.value = [];
    } else {
      const json = await resp.json();
      // DRF retorna {count, results}
      const ports = json.results || [];
      targetList.value = ports.map((p) => ({ 
        id: p.id, 
        name: p.name,
        device_id: p.device_id,
        site_id: p.site_id
      }));
      console.debug('[FiberCables] portas carregadas', deviceId, target, targetList.value.length);
    }
  } catch (err) {
    console.error('Erro ao carregar portas do device', deviceId, err);
    targetList.value = [];
  } finally {
    loadingFlag.value = false;
  }
};
</script>
