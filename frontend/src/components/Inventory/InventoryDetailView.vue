<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
    <div class="flex items-center justify-between mb-6">
      <nav class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
        <button @click="goBack" class="hover:text-blue-600">Inventário</button>
        <span>/</span>
        <span class="text-gray-800 dark:text-gray-200">{{ site.name || 'Site' }}</span>
      </nav>
      <div class="flex items-center gap-3">
        <button
          @click="handleEdit"
          class="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          <i class="fas fa-edit"></i>
          Editar
        </button>
        <p class="text-xs text-gray-500 dark:text-gray-400">Site ID: {{ route.params.id }}</p>
      </div>
    </div>

    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div v-if="loading" class="flex items-center justify-center py-12">
        <div class="text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p class="text-gray-500 dark:text-gray-400">Carregando site...</p>
        </div>
      </div>

      <div v-else class="space-y-6">
        <div v-if="errorMessage" class="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-800 px-4 py-3 rounded-lg">
          {{ errorMessage }}
        </div>

        <div class="flex items-start justify-between">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400 uppercase font-semibold">Inventário de Rede</p>
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ site.name || 'Site' }}</h1>
            <div class="mt-2 flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
              <span :class="['px-2 py-1 rounded-full text-xs font-semibold capitalize', typeBadge]">
                {{ site.type || 'Geral' }}
              </span>
              <span class="px-2 py-1 rounded-full text-xs font-semibold bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200">
                Status: {{ site.status || 'N/D' }}
              </span>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="border border-gray-100 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-800/50">
            <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">Endereço</p>
            <p class="text-gray-800 dark:text-gray-200">{{ site.address || 'Não informado' }}</p>
          </div>
          <div class="border border-gray-100 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-800/50">
            <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">Coordenadas</p>
            <p class="text-gray-800 dark:text-gray-200">
              {{ site.lat || '—' }}, {{ site.lng || '—' }}
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-800/40 flex items-center justify-between">
            <div>
              <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">Racks</p>
              <p class="text-lg font-bold text-gray-900 dark:text-white">—</p>
              <p class="text-xs text-gray-500 dark:text-gray-400">Sincronize quando o endpoint estiver disponível.</p>
            </div>
            <button class="px-3 py-2 text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 transition">
              Adicionar Rack
            </button>
          </div>
          <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-800/40 flex items-center justify-between">
            <div>
              <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">Dispositivos</p>
              <p class="text-lg font-bold text-gray-900 dark:text-white">{{ site.device_count || 0 }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400">Integre com o endpoint de devices do site.</p>
            </div>
            <button @click="goToDevices" class="px-3 py-2 text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 transition">
              Ver Devices
            </button>
          </div>
          <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-800/40 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                </svg>
              </div>
              <div>
                <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">Câmeras</p>
                <p class="text-lg font-bold text-gray-900 dark:text-white">{{ site.camera_count || 0 }}</p>
              </div>
            </div>
            <button @click="goToCameras" class="px-3 py-2 text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 transition">
              Ver Câmeras
            </button>
          </div>
        </div>

        <div class="bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <div class="flex items-center justify-between mb-3">
            <div>
              <p class="text-sm font-semibold text-gray-700 dark:text-gray-200">Dispositivos</p>
              <p class="text-xs text-gray-500 dark:text-gray-400">Lista de devices associados ao site</p>
            </div>
            <div class="flex items-center gap-2">
              <button
                @click="fetchDevices"
                class="px-3 py-2 text-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
              >
                Recarregar
              </button>
            </div>
          </div>

          <div v-if="devicesLoading" class="py-8 text-center text-gray-500 dark:text-gray-400">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3"></div>
            Carregando dispositivos...
          </div>

          <div v-else-if="devicesError" class="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-800 px-4 py-3 rounded-lg">
            {{ devicesError }}
          </div>

          <div v-else-if="devices.length === 0" class="py-6 text-center text-gray-500 dark:text-gray-400">
            Nenhum dispositivo encontrado para este site.
          </div>

          <div v-else class="overflow-x-auto">
            <table class="min-w-full border-collapse">
              <thead class="bg-gray-100 dark:bg-gray-800/60 text-xs uppercase text-gray-500 dark:text-gray-300">
                <tr>
                  <th class="text-left px-3 py-2">Nome</th>
                  <th class="text-left px-3 py-2">Vendor</th>
                  <th class="text-left px-3 py-2">Modelo</th>
                  <th class="text-left px-3 py-2">IP</th>
              <th class="text-left px-3 py-2">HostID</th>
              <th class="text-right px-3 py-2">Ações</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700 text-sm">
            <tr v-for="device in devices" :key="device.id" class="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition">
              <td class="px-3 py-2 font-medium text-gray-900 dark:text-white">{{ device.name }}</td>
              <td class="px-3 py-2 text-gray-700 dark:text-gray-300">{{ device.vendor || '—' }}</td>
              <td class="px-3 py-2 text-gray-700 dark:text-gray-300">{{ device.model || '—' }}</td>
              <td class="px-3 py-2 text-gray-700 dark:text-gray-300">{{ device.primary_ip || '—' }}</td>
              <td class="px-3 py-2 text-gray-700 dark:text-gray-300">{{ device.zabbix_hostid || '—' }}</td>
              <td class="px-3 py-2 text-right">
                <button
                  @click="openMigration(device)"
                  class="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-colors"
                  title="Migrar dispositivo para outro site"
                >
                  <i class="fas fa-random"></i>
                  Migrar
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
      </div>
    </div>

  <SiteEditModal
    :show="showEdit"
    :site="site"
    @close="showEdit = false"
    @saved="saveEdit"
  />

  <!-- Modal de Migração (placeholder visual) -->
  <div
    v-if="showMigrate"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
  >
    <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-lg p-6 border border-gray-200 dark:border-gray-700">
      <div class="flex items-start gap-3">
        <div class="flex-shrink-0 w-10 h-10 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
          <i class="fas fa-random"></i>
        </div>
        <div class="flex-1">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Migrar dispositivo</h3>
          <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">
            Selecione o site de destino para mover <span class="font-semibold">{{ migrateDevice?.name }}</span>.
          </p>
          <div class="mt-4 space-y-2">
            <label class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Destino</label>
            <select
              v-model="destinationSite"
              class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              :disabled="sitesLoading || migrationSaving"
            >
              <option v-if="sitesLoading" disabled>Carregando sites...</option>
              <option
                v-for="opt in sitesOptions"
                :key="opt.id"
                :value="opt.id"
              >
                {{ opt.name }}
              </option>
            </select>
          </div>
          <p v-if="migrationError" class="mt-3 text-sm text-red-600 dark:text-red-300">
            {{ migrationError }}
          </p>
        </div>
      </div>

      <div class="flex justify-end gap-3 mt-6">
        <button
          @click="closeMigration"
          class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-sm"
          :disabled="migrationSaving"
        >
          Fechar
        </button>
        <button
          @click="submitMigration"
          class="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition-colors text-sm disabled:opacity-60 disabled:cursor-not-allowed"
          :disabled="migrationSaving || sitesLoading || !destinationSite"
        >
          {{ migrationSaving ? 'Migrando...' : 'Migrar' }}
        </button>
      </div>
    </div>
  </div>
</div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useApi } from '@/composables/useApi';
import SiteEditModal from './SiteEditModal.vue';

const route = useRoute();
const router = useRouter();
const api = useApi();

const loading = ref(false);
const errorMessage = ref('');
const site = ref({});
const showEdit = ref(false);
const showMigrate = ref(false);
const migrateDevice = ref(null);
const migrationError = ref('');
const migrationSaving = ref(false);
const sitesOptions = ref([]);
const sitesLoading = ref(false);
const destinationSite = ref(null);
const devices = ref([]);
const devicesLoading = ref(false);
const devicesError = ref('');
const mapFromApi = (payload) => {
  if (!payload) return {};
  return {
    id: payload.id,
    name: payload.name || payload.display_name || '',
    type: payload.type || payload.address_line2 || payload.category || '',
    address: payload.address || payload.address_line1 || '',
    address_line2: payload.address_line2,
    address_line3: payload.address_line3,
    city: payload.city,
    state: payload.state,
    zip_code: payload.zip_code,
    lat: payload.latitude,
    lng: payload.longitude,
    device_count: payload.device_count ?? 0,
    camera_count: payload.camera_count ?? 0,
    status: payload.status || 'active',
    slug: payload.slug,
  };
};

const typeBadge = computed(() => {
  const type = site.value.type;
  const map = {
    pop: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    datacenter: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    customer: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    hub: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  };
  return map[type] || 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200';
});

const fetchSite = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const data = await api.get(`/api/v1/sites/${route.params.id}/`);
    site.value = mapFromApi(data);
  } catch (error) {
    console.error('Erro ao carregar site', error);
    errorMessage.value = error.message || 'Erro ao carregar site.';
  } finally {
    loading.value = false;
  }
};

const fetchSitesOptions = async () => {
  sitesLoading.value = true;
  migrationError.value = '';
  try {
    let url = '/api/v1/sites/?page_size=200';
    const collection = [];
    while (url) {
      const data = await api.get(url);
      const pageItems = Array.isArray(data) ? data : data.results || [];
      collection.push(...pageItems);
      url = data.next || null;
    }
    const mapped = collection
      .map((item) => ({ id: item.id, name: item.name || item.display_name || `Site ${item.id}` }))
      .filter((opt) => String(opt.id) !== String(route.params.id));
    sitesOptions.value = mapped;
    destinationSite.value = mapped[0]?.id || null;
  } catch (error) {
    console.error('Erro ao carregar sites para migração', error);
    migrationError.value = error.message || 'Erro ao carregar sites disponíveis.';
  } finally {
    sitesLoading.value = false;
  }
};

const goBack = () => {
  router.push({ name: 'inventory' });
};

const goToDevices = () => {
  router.push({ name: 'inventory-devices' });
};

const goToCameras = () => {
  const siteName = site.value.name || site.value.display_name;
  if (siteName) {
    router.push({ name: 'video', query: { tab: 'cameras', search: siteName } });
  } else {
    router.push({ name: 'video', query: { tab: 'cameras' } });
  }
};

const handleEdit = () => {
  showEdit.value = true;
};

const saveEdit = async (siteData) => {
  try {
    const toFixed6 = (value) => {
      if (value === null || value === undefined || value === '') return null;
      const num = Number(value);
      if (Number.isNaN(num)) return null;
      return Number(num.toFixed(6));
    };

    await api.patch(`/api/v1/sites/${route.params.id}/`, {
      name: siteData.name,
      address: siteData.address || '',
      address_line2: siteData.address_line2 || '',
      address_line3: siteData.address_line3 || '',
      city: siteData.city || '',
      state: siteData.state || '',
      zip_code: siteData.zip_code || '',
      latitude: toFixed6(siteData.lat),
      longitude: toFixed6(siteData.lng),
    });
    showEdit.value = false;
    await fetchSite();
    await fetchDevices();
  } catch (error) {
    console.error('Erro ao salvar site', error);
    errorMessage.value = error.message || 'Erro ao salvar site.';
  }
};

const fetchDevices = async () => {
  devicesLoading.value = true;
  devicesError.value = '';
  try {
    const payload = await api.get(`/api/v1/sites/${route.params.id}/devices/`);
    const collection = Array.isArray(payload?.devices) ? payload.devices : [];
    devices.value = collection.map((d) => ({
      id: d.id,
      name: d.name,
      vendor: d.vendor,
      model: d.model,
      primary_ip: d.primary_ip,
      zabbix_hostid: d.zabbix_hostid,
    }));
    // Atualiza contador se backend retornar device_count
    if (typeof payload?.device_count === 'number') {
      site.value = { ...site.value, device_count: payload.device_count };
    }
  } catch (error) {
    console.error('Erro ao carregar devices', error);
    devicesError.value = error.message || 'Erro ao carregar devices.';
  } finally {
    devicesLoading.value = false;
  }
};

const openMigration = (device) => {
  migrateDevice.value = device;
  showMigrate.value = true;
  if (!sitesOptions.value.length) {
    fetchSitesOptions();
  } else {
    destinationSite.value = sitesOptions.value[0]?.id || null;
  }
};

const closeMigration = () => {
  showMigrate.value = false;
  migrateDevice.value = null;
  migrationError.value = '';
  destinationSite.value = null;
};

const submitMigration = async () => {
  if (!migrateDevice.value || !destinationSite.value) return;
  migrationSaving.value = true;
  migrationError.value = '';
  try {
    await api.patch(`/api/v1/devices/${migrateDevice.value.id}/`, {
      site: destinationSite.value,
    });
    closeMigration();
    await fetchDevices();
    await fetchSite();
  } catch (error) {
    console.error('Erro ao migrar device', error);
    migrationError.value = error.message || 'Erro ao migrar device.';
  } finally {
    migrationSaving.value = false;
  }
};

onMounted(async () => {
  await fetchSite();
  await fetchDevices();
  // Pré-carrega sites destino para o modal de migração
  fetchSitesOptions();
});
</script>
