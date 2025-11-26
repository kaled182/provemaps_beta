<template>
  <div class="h-full min-h-0 flex flex-col gap-3">
    <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-sm p-3 flex flex-col md:flex-row gap-3 items-center justify-between">
      <div class="relative w-full md:w-2/5 lg:w-1/3">
        <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
          <i class="fas fa-search"></i>
        </span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Buscar sites..."
          class="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-sm"
        />
      </div>

      <div class="flex items-center gap-2 w-full md:w-auto justify-end">
        <select
          v-model="typeFilter"
          class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer text-sm"
        >
          <option value="all">Todos os Tipos</option>
          <option value="pop">POP</option>
          <option value="datacenter">Data Center</option>
          <option value="customer">Cliente</option>
          <option value="hub">Hub</option>
        </select>

        <div class="flex bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
          <button
            @click="viewMode = 'grid'"
            :class="['p-2 rounded-md transition-all', viewMode === 'grid' ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm' : 'text-gray-400 hover:text-gray-600']"
          >
            <i class="fas fa-th-large"></i>
          </button>
          <button
            @click="viewMode = 'list'"
            :class="['p-2 rounded-md transition-all', viewMode === 'list' ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm' : 'text-gray-400 hover:text-gray-600']"
          >
            <i class="fas fa-list"></i>
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p class="text-gray-500 dark:text-gray-400">Carregando estrutura...</p>
      </div>
    </div>

    <div v-else class="flex-1 min-h-0 flex flex-col gap-3 overflow-auto inventory-scroll">
      <div v-if="errorMessage" class="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-800 px-4 py-3 rounded-lg">
        {{ errorMessage }}
      </div>

      <div v-if="viewMode === 'grid'" class="site-grid pb-12 pr-2">
        <SiteCard
          v-for="site in filteredSites"
          :key="site.id"
          :site="site"
          @edit="openEditModal"
          @delete="confirmDelete"
          @view="goToDetails"
        />

        <div v-if="filteredSites.length === 0" class="col-span-full flex flex-col items-center justify-center py-20 text-gray-400">
          <i class="fas fa-map-marker-alt text-5xl mb-4 opacity-20"></i>
          <p>Nenhum site encontrado com estes filtros.</p>
        </div>
      </div>

      <div v-else class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 flex-1 min-h-0 overflow-hidden flex flex-col">
        <div class="overflow-auto flex-1">
          <table class="w-full text-left border-collapse">
            <thead class="bg-gray-50 dark:bg-gray-700/50 sticky top-0 z-10">
              <tr>
                <th class="p-4 text-xs font-semibold text-gray-500 uppercase">Nome</th>
                <th class="p-4 text-xs font-semibold text-gray-500 uppercase">Tipo</th>
                <th class="p-4 text-xs font-semibold text-gray-500 uppercase">Endereço</th>
                <th class="p-4 text-xs font-semibold text-gray-500 uppercase text-center">Devices</th>
                <th class="p-4 text-xs font-semibold text-gray-500 uppercase text-right">Ações</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
              <tr v-for="site in filteredSites" :key="site.id" class="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                <td class="p-4 font-medium text-gray-900 dark:text-white">{{ site.name }}</td>
                <td class="p-4">
                  <span :class="getTypeClass(site.type)" class="px-2 py-1 rounded-full text-xs font-medium capitalize">
                    {{ site.type || 'Geral' }}
                  </span>
                </td>
                <td class="p-4 text-gray-500 dark:text-gray-400 text-sm">{{ site.address }}</td>
                <td class="p-4 text-center">
                  <span class="bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2 py-0.5 rounded text-xs font-bold">
                    {{ site.device_count || 0 }}
                  </span>
                </td>
                <td class="p-4 text-right space-x-2">
                  <button @click="goToDetails(site)" class="text-gray-600 dark:text-gray-300 hover:text-blue-700 dark:hover:text-blue-400 p-1">
                    <i class="fas fa-eye"></i>
                  </button>
                  <button @click="openEditModal(site)" class="text-blue-600 hover:text-blue-800 p-1">
                    <i class="fas fa-edit"></i>
                  </button>
                  <button @click="confirmDelete(site)" class="text-red-500 hover:text-red-700 p-1">
                    <i class="fas fa-trash-alt"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <SiteEditModal
      v-if="showModal"
      :show="showModal"
      :site="selectedSite"
      @close="showModal = false"
      @saved="handleSiteSaved"
    />

    <!-- Confirmação de remoção -->
    <div
      v-if="confirmDialog.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
    >
      <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-md p-6 border border-gray-200 dark:border-gray-700">
        <div class="flex items-start gap-3">
          <div class="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 text-red-600 flex items-center justify-center">
            <i class="fas fa-trash-alt"></i>
          </div>
          <div class="flex-1">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Remover site</h3>
            <p
              class="text-sm text-gray-600 dark:text-gray-300 mt-1"
              v-if="(confirmDialog.item?.device_count || 0) === 0"
            >
              Tem certeza que deseja remover <span class="font-semibold">{{ confirmDialog.item?.name }}</span>? Esta ação não pode ser desfeita.
            </p>
            <p
              class="text-sm text-yellow-700 dark:text-yellow-200 mt-1"
              v-else
            >
              Este site possui {{ confirmDialog.item?.device_count }} device(s). Remova ou migre os devices para outro site antes de apagar.
            </p>
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button
            @click="closeConfirm"
            class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-sm"
            :disabled="saving"
          >
            Cancelar
          </button>
          <template v-if="(confirmDialog.item?.device_count || 0) === 0">
            <button
              @click="proceedDelete"
              class="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white shadow-sm transition-colors text-sm disabled:opacity-60 disabled:cursor-not-allowed"
              :disabled="saving"
            >
              {{ saving ? 'Removendo...' : 'Remover' }}
            </button>
          </template>
          <template v-else>
            <button
              @click="goToDetails(confirmDialog.item)"
              class="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition-colors text-sm"
              :disabled="saving"
            >
              Ver detalhes / migrar
            </button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useApi } from '@/composables/useApi';
import SiteCard from './SiteCard.vue';
import SiteEditModal from './SiteEditModal.vue';

const loading = ref(false);
const saving = ref(false);
const errorMessage = ref('');
const searchQuery = ref('');
const typeFilter = ref('all');
const viewMode = ref('grid');
const showModal = ref(false);
const confirmDialog = ref({ open: false, item: null });
const selectedSite = ref(null);
const router = useRouter();
const api = useApi();

const sites = ref([]);

const mapFromApi = (payload) => {
  if (!payload) return {};
  const rawType = payload.type || payload.address_line2 || payload.category || '';
  return {
    id: payload.id,
    name: payload.name || payload.display_name || '',
    type: rawType ? rawType.toLowerCase() : '',
    address: payload.address || payload.address_line1 || '',
    address_line2: payload.address_line2,
    address_line3: payload.address_line3,
    city: payload.city,
    state: payload.state,
    zip_code: payload.zip_code,
    lat: payload.latitude,
    lng: payload.longitude,
    device_count: payload.device_count ?? 0,
    status: payload.status || 'active',
    slug: payload.slug,
  };
};

const mapToApi = (siteData) => {
  const toFixed6 = (value) => {
    if (value === null || value === undefined || value === '') return null;
    const num = Number(value);
    if (Number.isNaN(num)) return null;
    return Number(num.toFixed(6));
  };

  return {
    name: siteData.name,
    address: siteData.address || '',
    address_line2: siteData.type || siteData.address_line2 || '',
    address_line3: siteData.address_line3 || '',
    city: siteData.city || '',
    state: siteData.state || '',
    zip_code: siteData.zip_code || '',
    latitude: toFixed6(siteData.lat),
    longitude: toFixed6(siteData.lng),
  };
};

const filteredSites = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  return sites.value.filter((site) => {
    const name = (site.name || '').toLowerCase();
    const address = (site.address || '').toLowerCase();
    const matchSearch = !query || name.includes(query) || address.includes(query);
    const matchType = typeFilter.value === 'all' || site.type === typeFilter.value;
    return matchSearch && matchType;
  });
});

const openCreateModal = () => {
  selectedSite.value = null;
  showModal.value = true;
};

const openEditModal = (site) => {
  selectedSite.value = { ...site };
  showModal.value = true;
};

const fetchSites = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    let url = '/api/v1/sites/?page_size=200';
    const collection = [];
    while (url) {
      const data = await api.get(url);
      const pageItems = Array.isArray(data) ? data : data.results || [];
      collection.push(...pageItems);
      url = data.next || null;
    }
    sites.value = collection.map(mapFromApi);
  } catch (error) {
    console.error('Erro ao carregar sites', error);
    errorMessage.value = error.message || 'Erro ao carregar sites.';
  } finally {
    loading.value = false;
  }
};

const handleSiteSaved = async (siteData) => {
  saving.value = true;
  errorMessage.value = '';
  try {
    const payload = mapToApi(siteData);
    if (siteData.id) {
      await api.patch(`/api/v1/sites/${siteData.id}/`, payload);
    } else {
      await api.post('/api/v1/sites/', payload);
    }
    showModal.value = false;
    await fetchSites();
  } catch (error) {
    console.error('Erro ao salvar site', error);
    errorMessage.value = error.message || 'Erro ao salvar site.';
  } finally {
    saving.value = false;
  }
};

const confirmDelete = (site) => {
  confirmDialog.value = { open: true, item: site };
};

const closeConfirm = () => {
  confirmDialog.value = { open: false, item: null };
};

const proceedDelete = async () => {
  const site = confirmDialog.value.item;
  if (!site) return;
  if (site.device_count && Number(site.device_count) > 0) return;

  saving.value = true;
  errorMessage.value = '';
  try {
    await api.delete(`/api/v1/sites/${site.id}/`);
    await fetchSites();
    closeConfirm();
  } catch (error) {
    console.error('Erro ao remover site', error);
    errorMessage.value = error.message || 'Erro ao remover site.';
  } finally {
    saving.value = false;
  }
};

const goToDetails = (site) => {
  if (!site?.id) return;
  router.push({ name: 'inventory-detail', params: { id: site.id } });
};

const getTypeClass = (type) => {
  const map = {
    pop: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    datacenter: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    customer: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    hub: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  };
  return map[type] || 'bg-gray-100 text-gray-700';
};

const exportSites = () => {
  const headers = ['id', 'name', 'type', 'address', 'device_count', 'status', 'lat', 'lng'];
  const escapeCell = (value) => {
    if (value === null || value === undefined) return '';
    const str = String(value);
    return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
  };
  const rows = filteredSites.value.map((site) => headers.map((h) => escapeCell(site[h])));
  const csvContent = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'inventory_sites.csv';
  link.click();
  URL.revokeObjectURL(url);
};

onMounted(async () => {
  await fetchSites();
});

defineExpose({ openCreateModal, exportSites });
</script>

<style scoped>
.site-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

/* Scrollbar alinhada ao padrão do DeviceImport */
.inventory-scroll::-webkit-scrollbar {
  width: 6px;
}

.inventory-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.inventory-scroll::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.3);
  border-radius: 3px;
}

.inventory-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(156, 163, 175, 0.5);
}

.dark .inventory-scroll::-webkit-scrollbar-thumb {
  background: rgba(75, 85, 99, 0.3);
}

.dark .inventory-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(75, 85, 99, 0.5);
}

.inventory-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(156, 163, 175, 0.3) transparent;
}

.dark .inventory-scroll {
  scrollbar-color: rgba(75, 85, 99, 0.3) transparent;
}
</style>
