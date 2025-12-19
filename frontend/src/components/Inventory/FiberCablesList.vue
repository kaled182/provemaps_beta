<template>
  <div class="h-full flex flex-col gap-6">
    <!-- KPIs -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="kpi-card">
        <p class="kpi-label">Total de Cabos</p>
        <p class="kpi-value">{{ cables.length }}</p>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">Extensão Total</p>
        <p class="kpi-value text-indigo-600 dark:text-indigo-400">
          {{ totalKm }} <span class="text-sm text-gray-400 font-normal">km</span>
        </p>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">Cabos Saturados (&gt;80%)</p>
        <p class="kpi-value text-orange-600 dark:text-orange-400">{{ saturatedCables }}</p>
      </div>
      <div class="kpi-card flex items-center justify-between">
        <div>
          <p class="kpi-label">Ocupação Média</p>
          <p class="kpi-value text-blue-600 dark:text-blue-400">{{ averageOccupancy }}%</p>
        </div>
        <i class="fas fa-fiber-core text-blue-300 dark:text-blue-700"></i>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col lg:flex-row gap-4 items-center justify-between">
      <div class="relative w-full lg:w-96">
        <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
        <input
          v-model="search"
          type="text"
          placeholder="Buscar cabo, site ou código..."
          class="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
        />
      </div>

      <div class="flex flex-wrap gap-3 w-full lg:w-auto">
        <select v-model="filterStatus" class="filter-select">
          <option value="">Todos Status</option>
          <option value="up">Ativos</option>
          <option value="planned">Planejados</option>
          <option value="down">Rompidos</option>
          <option value="degraded">Degradados</option>
        </select>

        <select v-model="filterType" class="filter-select">
          <option value="">Todos os Tipos</option>
          <option value="backbone">Backbone</option>
          <option value="drop">Drop</option>
        </select>

        <label class="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200 cursor-pointer">
          <input type="checkbox" v-model="onlySaturated" class="text-indigo-600 focus:ring-indigo-500 rounded" />
          Cabos saturados
        </label>

        <button
          @click="openCreateModal"
          class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-sm transition-colors flex items-center gap-2 text-sm font-medium whitespace-nowrap"
        >
          <i class="fas fa-plus"></i> Novo Cabo
        </button>
      </div>
    </div>

    <!-- Table -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 flex-1 overflow-hidden flex flex-col">
      <div class="overflow-auto flex-1">
        <div v-if="loading" class="p-6 text-center text-gray-500 dark:text-gray-400">Carregando cabos...</div>
        <div v-else-if="error" class="p-6 text-red-600 dark:text-red-300">{{ error }}</div>
        <div v-else-if="filteredCables.length === 0" class="p-6 text-center text-gray-500 dark:text-gray-400">Nenhum cabo encontrado.</div>

        <table v-else class="w-full text-left border-collapse">
          <thead class="bg-gray-50 dark:bg-gray-700/50 sticky top-0 z-10">
            <tr>
              <th class="th w-2"></th>
              <th class="th">Identificação</th>
              <th class="th">Rota (Origem <i class="fas fa-long-arrow-alt-right mx-1"></i> Destino)</th>
              <th class="th w-48">Ocupação</th>
              <th class="th text-right">Metragem</th>
              <th class="th text-right">Ações</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
            <tr v-for="cable in filteredCables" :key="cable.id" class="group hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
              <td class="px-0 py-4 relative">
                <div :class="['absolute left-0 top-4 bottom-4 w-1 rounded-r-md', statusColor(cable.status)]"></div>
              </td>

              <td class="px-6 py-4">
                <div class="flex items-center gap-3">
                  <div class="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
                    <i :class="cable.type === 'drop' ? 'fas fa-level-down-alt' : 'fas fa-project-diagram'"></i>
                  </div>
                  <div>
                    <div class="font-bold text-gray-900 dark:text-white text-sm">{{ cable.name }}</div>
                    <div class="text-xs text-gray-500">
                      {{ cable.type || 'Backbone' }} • {{ cable.fiber_count || '?' }} FO
                    </div>
                  </div>
                </div>
              </td>

              <td class="px-6 py-4">
                <div v-if="cable.site_a_name || cable.site_b_name" class="flex items-center gap-2 text-sm">
                  <span class="pill blue" :title="cable.site_a_name">{{ cable.site_a_name }}</span>
                  <i class="fas fa-arrow-right text-gray-300 text-xs"></i>
                  <span class="pill indigo" :title="cable.site_b_name">{{ cable.site_b_name }}</span>
                </div>
                
                <div v-else class="flex items-center gap-2">
                  <span class="text-xs text-gray-400 italic flex items-center gap-1">
                    <i class="fas fa-unlink text-xs"></i>
                    Não conectado
                  </span>
                  <button 
                    @click="openConnectionModal(cable)"
                    class="text-xs bg-gray-100 dark:bg-gray-700 hover:bg-purple-50 dark:hover:bg-purple-900/20 text-purple-600 dark:text-purple-400 px-2 py-1 rounded border border-gray-200 dark:border-gray-600 hover:border-purple-300 transition-all font-medium"
                    title="Conectar cabo a sites"
                  >
                    <i class="fas fa-link mr-1"></i> Conectar
                  </button>
                </div>
              </td>

              <td class="px-6 py-4">
                <CapacityBar :used="cable.used_strands" :total="cable.fiber_count || 1" />
              </td>

              <td class="px-6 py-4 text-right">
                <span class="font-mono text-sm text-gray-700 dark:text-gray-300">{{ formatLength(cable.length) }}</span>
              </td>

              <td class="px-6 py-4 text-right space-x-2">
                <button 
                  @click="openStructureModal(cable)" 
                  class="text-gray-400 hover:text-purple-600 p-1" 
                  title="Ver estrutura física"
                >
                  <i class="fas fa-bullseye"></i>
                </button>
                <button @click="goToRouteEditor(cable)" class="text-gray-400 hover:text-blue-600 p-1" title="Ver no mapa">
                  <i class="fas fa-map-marked-alt"></i>
                </button>
                <button @click="handleEdit(cable)" class="text-gray-400 hover:text-indigo-600 p-1" title="Editar">
                  <i class="fas fa-edit"></i>
                </button>
                <button @click="handleDelete(cable)" class="text-gray-400 hover:text-red-600 p-1" title="Apagar cabo">
                  <i class="fas fa-trash-alt"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FiberCreateModal
    :show="showModal"
    :cable="selectedCable"
    @close="showModal = false"
    @saved="handleSaveCable"
  />

  <FiberConnectionModal
    :show="showConnectionModal"
    :cable="selectedConnectionCable"
    :sites="allSites"
    @close="showConnectionModal = false"
    @connected="handleCableConnected"
  />

  <CableStructureModal
    :show="showStructureModal"
    :cable-id="structureCableId"
    @close="showStructureModal = false"
    @fiber-selected="handleFiberSelected"
    @fusion-requested="handleFusionRequested"
    @port-connection-requested="handlePortConnectionRequested"
  />

  <CableMapModal
    :show="showMapModal"
    :cable-id="mapCableId"
    :cable-name="mapCableName"
    @close="showMapModal = false"
    @saved="handleMapSaved"
  />
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useApi, getCsrfToken } from '@/composables/useApi';
import CapacityBar from './Fiber/CapacityBar.vue';
import FiberCreateModal from './Fiber/FiberCreateModal.vue';
import FiberConnectionModal from './Fiber/FiberConnectionModal.vue';
import CableStructureModal from './Fibers/CableStructureModal.vue';
import CableMapModal from './Fibers/CableMapModal.vue';
import { useRouter } from 'vue-router';
import { mapFiberDetailToForm } from './Fiber/mapFiberDetail';

const api = useApi();
const router = useRouter();
const cables = ref([]);
const loading = ref(false);
const error = ref('');
const search = ref('');
const filterStatus = ref('');
const filterType = ref('');
const onlySaturated = ref(false);
const showModal = ref(false);
const selectedCable = ref(null);
const allSites = ref([]);
const saving = ref(false);
const sitesError = ref('');

// Structure Modal State
const showStructureModal = ref(false);
const structureCableId = ref(null);

// Connection Modal State
const showConnectionModal = ref(false);
const selectedConnectionCable = ref(null);

// Map Modal State
const showMapModal = ref(false);
const mapCableId = ref(null);
const mapCableName = ref('');

const statusColor = (status) => {
  switch (status) {
    case 'up':
      return 'bg-green-500';
    case 'planned':
      return 'bg-blue-400';
    case 'down':
      return 'bg-red-600';
    case 'degraded':
      return 'bg-orange-500';
    default:
      return 'bg-gray-300';
  }
};

const mappedCables = computed(() =>
  cables.value.map((c) => ({
    id: c.id,
    name: c.name,
    // Use new site_a_name/site_b_name fields from serializer
    site_a_name: c.site_a_name || null,
    site_b_name: c.site_b_name || null,
    site_a: c.site_a,
    site_b: c.site_b,
    origin_port_id: c.origin_port_id || c.origin_port,
    destination_port_id: c.destination_port_id || c.destination_port,
    origin_port: c.origin_port,
    destination_port: c.destination_port,
    length: c.length_km ? Number(c.length_km) * 1000 : c.length || 0,
    status: c.status || 'unknown',
    type: c.type || 'backbone',
    fiber_count: c.fiber_count || c.capacity || c.strands || 0,
    used_strands: c.used_strands || c.used || 0,
    // Connection state
    is_connected: c.is_connected || false,
    connection_status: c.connection_status || 'floating',
  }))
);

const filteredCables = computed(() => {
  const q = search.value.toLowerCase().trim();
  return mappedCables.value.filter((c) => {
    const matchSearch =
      !q ||
      c.name.toLowerCase().includes(q) ||
      (c.site_a_name || '').toLowerCase().includes(q) ||
      (c.site_b_name || '').toLowerCase().includes(q);
    const matchStatus = !filterStatus.value || c.status === filterStatus.value;
    const matchType = !filterType.value || c.type === filterType.value;
    const occupancy =
      c.fiber_count > 0 ? (c.used_strands / c.fiber_count) * 100 : 0;
    const matchSaturated = !onlySaturated.value || occupancy >= 80;
    return matchSearch && matchStatus && matchType && matchSaturated;
  });
});

const totalKm = computed(() => {
  const meters = mappedCables.value.reduce((acc, curr) => acc + (curr.length || 0), 0);
  return (meters / 1000).toFixed(2);
});

const saturatedCables = computed(() =>
  mappedCables.value.filter(
    (c) => c.fiber_count > 0 && (c.used_strands / c.fiber_count) >= 0.8
  ).length
);

const averageOccupancy = computed(() => {
  const values = mappedCables.value
    .filter((c) => c.fiber_count > 0)
    .map((c) => (c.used_strands / c.fiber_count) * 100);
  if (!values.length) return 0;
  return Math.round(values.reduce((a, b) => a + b, 0) / values.length);
});

const formatLength = (meters) => {
  if (!meters) return '-';
  if (meters >= 1000) return `${(meters / 1000).toFixed(2)} km`;
  return `${meters} m`;
};

const openCreateModal = () => {
  selectedCable.value = null;
  ensureSitesFromCables();
  showModal.value = true;
};

const fetchCables = async () => {
  loading.value = true;
  error.value = '';
  try {
    const data = await api.get('/api/v1/fiber-cables/');
    cables.value = Array.isArray(data) ? data : data.results || [];
  } catch (err) {
    console.error('Erro ao carregar cabos', err);
    error.value = err.message || 'Erro ao carregar cabos.';
  } finally {
    loading.value = false;
  }
};

const fetchSites = async () => {
  sitesError.value = '';

  const loadAll = async (baseUrl) => {
    let url = `${baseUrl}?page_size=500`;
    const collected = [];
    while (url) {
      const response = await fetch(url, { credentials: 'same-origin' });
      console.log('[FiberCables] Fetching sites', { url, status: response.status, redirected: response.redirected, finalUrl: response.url });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status} ${response.statusText} ao buscar sites (${url}). Conteúdo: ${text.slice(0, 200)}`);
      }
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        const text = await response.text();
        throw new Error(`Resposta não-JSON ao buscar sites (${url}). content-type=${contentType}. Conteúdo: ${text.slice(0, 200)}`);
      }
      const data = await response.json();
      const results = Array.isArray(data) ? data : data.results || [];
      results.forEach((s) => {
        collected.push({
          id: s.id,
          name: s.display_name || s.name || s.title || `Site ${s.id}`,
        });
      });
      url = data.next || null;
    }
    return collected;
  };

  const tryEndpoints = async () => {
    const endpoints = ['/api/v1/sites/', '/api/v1/inventory/sites/'];
    let lastError = null;
    for (const ep of endpoints) {
      try {
        const sites = await loadAll(ep);
        if (sites.length) return sites;
      } catch (err) {
        lastError = err;
        console.warn(`Falha ao carregar sites em ${ep}:`, err);
      }
    }
    if (lastError) throw lastError;
    return [];
  };

  try {
    const sites = await tryEndpoints();
    allSites.value = dedupeSites(sites);
    console.log('[FiberCables] Sites carregados via API:', allSites.value.length);
    if (!allSites.value.length) {
      sitesError.value = 'Nenhum site retornado pela API.';
      ensureSitesFromCables();
    }
  } catch (err) {
    console.error('Erro ao carregar sites', err);
    sitesError.value = err?.message || 'Erro ao carregar sites.';
    ensureSitesFromCables();
  }
};

const dedupeSites = (sites) => {
  const map = new Map();
  sites.forEach((s) => {
    if (!map.has(s.id)) {
      map.set(s.id, s);
    }
  });
  return Array.from(map.values());
};

const ensureSitesFromCables = () => {
  if (allSites.value.length) return;
  const names = new Set();
  mappedCables.value.forEach((c) => {
    if (c.site_a_name) names.add(c.site_a_name);
    if (c.site_b_name) names.add(c.site_b_name);
  });
  if (names.size) {
    allSites.value = Array.from(names).map((name) => ({
      id: name,
      name,
    }));
    console.warn('[FiberCables] Sites populados a partir dos cabos carregados (fallback):', allSites.value);
  }
};

// Cache de devices e portas para resolver port_id -> device_id/porta
const deviceOptionsCache = ref(null);
const portsCache = ref({});

const loadDeviceOptions = async () => {
  if (deviceOptionsCache.value) return deviceOptionsCache.value;
  const resp = await fetch('/api/v1/inventory/devices/select-options/', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!resp.ok) {
    throw new Error(`Falha ao carregar devices: ${resp.status}`);
  }
  const json = await resp.json();
  deviceOptionsCache.value = json.devices || [];
  console.debug('[FiberCables] device options cache', deviceOptionsCache.value?.length);
  return deviceOptionsCache.value;
};

const fetchPortsForDevice = async (deviceId) => {
  if (portsCache.value[deviceId]) return portsCache.value[deviceId];
  const endpoints = [
    `/api/v1/inventory/devices/${deviceId}/ports/?page_size=500`,
    `/api/v1/inventory/ports/?device=${deviceId}&page_size=500`,
    `/api/v1/ports/?device=${deviceId}&page_size=500`,
  ];
  for (const ep of endpoints) {
    try {
      const resp = await fetch(ep, {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      if (!resp.ok) {
        const txt = await resp.text().catch(() => '');
        console.warn('[FiberCables] portas device falha', deviceId, ep, resp.status, resp.statusText, txt.slice(0, 120));
        continue;
      }
      const ct = resp.headers.get('content-type') || '';
      if (!ct.includes('application/json')) {
        const txt = await resp.text().catch(() => '');
        console.warn('[FiberCables] portas device não-JSON', deviceId, ep, ct, txt.slice(0, 120));
        continue;
      }
      const json = await resp.json();
      const portsRaw = Array.isArray(json) ? json : json.results || json.ports || [];
      const ports = Array.isArray(portsRaw) ? portsRaw : [];
      portsCache.value[deviceId] = ports;
      console.debug('[FiberCables] portas carregadas', deviceId, ports.length);
      return ports;
    } catch (err) {
      console.warn('[FiberCables] erro portas device', deviceId, ep, err);
    }
  }
  return [];
};

const resolvePortById = async (portId) => {
  if (!portId) return null;
  const devices = await loadDeviceOptions();
  for (const dev of devices) {
    const ports = await fetchPortsForDevice(dev.id);
    const match = ports.find((p) => `${p.id}` === `${portId}`);
    if (match) {
      return {
        device_id: dev.id,
        device_name: dev.name,
        site_id: dev.site_id,
        port_id: match.id,
        port_name: match.name,
      };
    }
  }
  return null;
};

const fetchPortInfo = async (portId) => resolvePortById(portId);

const handleSaveCable = async (payload) => {
  if (!payload) return;
  saving.value = true;
  try {
    if (payload.id) {
      // Edição: atualizar apenas campos técnicos permitidos
      const body = {
        name: payload.name || '',
          status: payload.status || 'unknown'
      };
      await api.put(`/api/v1/fiber-cables/${payload.id}/`, body);
    } else {
      // Criação: novo cabo flutuante (Inventory First)
      const body = {
        name: payload.name || '',
        profile: payload.profile_id,
          status: payload.status || 'unknown'
      };
      await api.post('/api/v1/fiber-cables/', body);
    }
    await fetchCables();
    showModal.value = false;
  } catch (err) {
    console.error('Erro ao salvar cabo', err);
    alert(err?.message || 'Erro ao salvar cabo.');
  } finally {
    saving.value = false;
  }
};

// Connection Modal Handlers
const openConnectionModal = (cable) => {
  selectedConnectionCable.value = cable;
  showConnectionModal.value = true;
};

const handleCableConnected = async (payload) => {
  try {
    // POST /fiber-cables/{id}/connect/
    await api.post(`/api/v1/fiber-cables/${payload.cable_id}/connect/`, {
      site_a: payload.site_a,
      site_b: payload.site_b,
    });
    
    // Atualizar lista
    await fetchCables();
    showConnectionModal.value = false;
    
    // Feedback positivo
    alert('Cabo conectado com sucesso! Agora você pode desenhar a rota no mapa ou importar KML.');
  } catch (err) {
    console.error('Erro ao conectar cabo', err);
    alert(err?.message || 'Erro ao conectar cabo.');
  }
};

onMounted(fetchCables);
onMounted(fetchSites);

// Sempre que abrir o modal, garante uma lista mínima
watch(showModal, (open) => {
  if (open) {
    ensureSitesFromCables();
    if (!allSites.value.length || allSites.value.length <= 3) {
      fetchSites();
    }
  }
});

// Carrega detalhes quando editar
const findSiteIdByName = (name) => {
  if (!name) return '';
  const match = allSites.value.find(
    (s) => (s.name || '').toLowerCase() === name.toLowerCase()
  );
  return match ? match.id : '';
};

const mapStatusForModal = (status) => {
  if (!status) return 'planned';
  const s = `${status}`.toLowerCase();
  if (['up', 'ativo', 'active', 'iluminado'].includes(s)) return 'active';
  if (['planned', 'em projeto', 'planejado', 'planned/em projeto'].includes(s)) return 'planned';
  if (['cut', 'rompido'].includes(s)) return 'cut';
  if (['dark', 'apagado'].includes(s)) return 'dark';
  return 'planned';
};

// Structure Modal Handlers
const openStructureModal = (cable) => {
  structureCableId.value = cable.id;
  showStructureModal.value = true;
};

const openMapModal = (cable) => {
  mapCableId.value = cable.id;
  mapCableName.value = cable.name;
  showMapModal.value = true;
};

const goToRouteEditor = (cable) => {
  router.push({ name: 'FiberRouteEditor', params: { id: cable.id } });
};

const handleMapSaved = async () => {
  await fetchCables();
  showMapModal.value = false;
};

const handleFiberSelected = (fiber) => {
  console.log('Fibra selecionada:', fiber);
  // TODO: Pode ser usado para destacar a fibra ou armazenar para fusão/conexão
};

const handleFusionRequested = (fiber) => {
  console.log('Fusão solicitada para fibra:', fiber);
  // TODO: Abrir modal de fusão (Fase 3)
  alert(`Fusão de fibra será implementada na Fase 3\nFibra: ${fiber.number} (${fiber.color})`);
};

const handlePortConnectionRequested = (fiber) => {
  console.log('Conexão a porta solicitada para fibra:', fiber);
  // TODO: Abrir modal de conexão a porta (Fase 3)
  alert(`Conexão de fibra a porta será implementada na Fase 3\nFibra: ${fiber.number} (${fiber.color})`);
};

const handleEdit = async (cable) => {
  try {
    saving.value = true;
    if (!allSites.value.length) {
      try {
        await fetchSites();
      } catch (err) {
        console.warn('Falha ao carregar sites antes de editar, usando fallback', err);
        ensureSitesFromCables();
      }
    }

    // Busca detalhes completos do endpoint enriquecido
    let freshCable = null;
    try {
      freshCable = await api.get(`/api/v1/fiber-cables/${cable.id}/`);
      console.debug('[FiberCables] Detalhe fibra com campos enriquecidos', freshCable);
    } catch (err) {
      console.error('Falha ao obter detalhe do cabo', err);
      throw new Error(`Não foi possível carregar os detalhes do cabo: ${err.message}`);
    }

    // Mapear para formato do modal (device_a, site_a, port_a, etc.)
    const merged = mapFiberDetailToForm({
      cable: freshCable,
      detail: null, // Não precisamos mais do objeto detail separado
      sites: allSites.value,
      originPortInfo: null,
      destPortInfo: null,
    });

    // Log para depuração visual no navegador
    console.debug('[FiberCables] Mapeado para modal', merged);

    selectedCable.value = merged;
    showModal.value = true;
  } catch (err) {
    console.error('Erro ao carregar detalhes do cabo', err);
    alert(err?.message || 'Erro ao carregar cabo.');
  } finally {
    saving.value = false;
  }
};

const handleDelete = async (cable) => {
  try {
    const ok = confirm(`Apagar o cabo "${cable.name}"? Esta ação é permanente.`);
    if (!ok) return;
    await api.delete(`/api/v1/fiber-cables/${cable.id}/`);
    await fetchCables();
    alert('Cabo apagado com sucesso.');
  } catch (err) {
    console.error('Erro ao apagar cabo', err);
    alert(err?.message || 'Erro ao apagar cabo.');
  }
};
</script>

<style scoped>
.kpi-card {
  @apply bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm;
}
.kpi-label {
  @apply text-xs font-semibold text-gray-500 uppercase tracking-wide;
}
.kpi-value {
  @apply text-2xl font-bold text-gray-900 dark:text-white;
}
.th {
  @apply px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider;
}
.filter-select {
  @apply px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none;
}
.pill {
  @apply px-2 py-1 rounded text-sm font-medium truncate max-w-[140px];
}
.pill.blue {
  @apply bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300;
}
.pill.indigo {
  @apply bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300;
}
</style>
