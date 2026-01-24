<template>
  <div class="h-full min-h-0 flex flex-col gap-3">
  <div class="app-surface rounded-xl p-3 flex flex-col md:flex-row gap-3 items-center justify-between">
      <div class="relative w-full md:w-2/5 lg:w-1/3">
        <span class="absolute left-3 top-1/2 -translate-y-1/2 app-text-tertiary">
          <i class="fas fa-search"></i>
        </span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Buscar sites..."
          class="w-full pl-9 pr-3 py-2 rounded-lg outline-none transition-all text-sm app-input"
        />
      </div>

      <div class="flex items-center gap-2 w-full md:w-auto justify-end">
        <select
          v-model="typeFilter"
          class="px-3 py-2 rounded-lg outline-none cursor-pointer text-sm app-input"
        >
          <option value="all">Todos os Tipos</option>
          <option value="pop">POP</option>
          <option value="datacenter">Data Center</option>
          <option value="customer">Cliente</option>
          <option value="hub">Hub</option>
        </select>

        <div class="flex app-surface-muted p-1 rounded-lg">
          <button
            @click="viewMode = 'grid'"
            :class="['p-2 rounded-md transition-all app-text-tertiary', viewMode === 'grid' ? 'app-surface app-text-primary shadow-sm' : 'app-text-tertiary']"
          >
            <i class="fas fa-th-large"></i>
          </button>
          <button
            @click="viewMode = 'list'"
            :class="['p-2 rounded-md transition-all app-text-tertiary', viewMode === 'list' ? 'app-surface app-text-primary shadow-sm' : 'app-text-tertiary']"
          >
            <i class="fas fa-list"></i>
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4 app-spinner"></div>
        <p class="app-text-tertiary">Carregando estrutura...</p>
      </div>
    </div>

    <div v-else class="flex-1 min-h-0 flex flex-col gap-3 overflow-auto inventory-scroll">
      <div v-if="errorMessage" class="px-4 py-3 rounded-lg app-text-secondary" style="background: var(--danger-soft-bg); border: 1px solid var(--accent-danger); color: var(--accent-danger);">
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

        <div v-if="filteredSites.length === 0" class="col-span-full flex flex-col items-center justify-center py-20 app-text-tertiary">
          <i class="fas fa-map-marker-alt text-5xl mb-4 opacity-20"></i>
          <p>Nenhum site encontrado com estes filtros.</p>
        </div>
      </div>

      <div v-else class="app-surface rounded-xl flex-1 min-h-0 overflow-hidden flex flex-col">
        <div class="overflow-auto flex-1">
          <table class="w-full text-left border-collapse">
            <thead class="app-surface-muted sticky top-0 z-10">
              <tr>
                <th class="p-4 text-xs font-semibold app-text-tertiary uppercase">Nome</th>
                <th class="p-4 text-xs font-semibold app-text-tertiary uppercase">Tipo</th>
                <th class="p-4 text-xs font-semibold app-text-tertiary uppercase">Endereço</th>
                <th class="p-4 text-xs font-semibold app-text-tertiary uppercase text-center">Devices</th>
                <th class="p-4 text-xs font-semibold app-text-tertiary uppercase text-center">Câmeras</th>
                <th class="p-4 text-xs font-semibold app-text-tertiary uppercase text-right">Ações</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
              <tr v-for="site in filteredSites" :key="site.id" class="transition-colors app-row">
                <td class="p-4 font-medium app-text-primary">{{ site.name }}</td>
                <td class="p-4">
                  <span :class="getTypeClass(site.type)" class="px-2 py-1 rounded-full text-xs font-medium capitalize">
                    {{ site.type || 'Geral' }}
                  </span>
                </td>
                <td class="p-4 app-text-tertiary text-sm">{{ site.address }}</td>
                <td class="p-4 text-center">
                  <span class="app-chip px-2 py-0.5 rounded text-xs font-bold">
                    {{ site.device_count || 0 }}
                  </span>
                </td>
                <td class="p-4 text-center">
                  <div class="inline-flex items-center gap-1.5">
                    <svg v-if="(site.camera_count || 0) > 0" class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                    </svg>
                    <span class="app-chip px-2 py-0.5 rounded text-xs font-bold" :class="(site.camera_count || 0) > 0 ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : ''">
                      {{ site.camera_count || 0 }}
                    </span>
                  </div>
                </td>
                <td class="p-4 text-right space-x-2">
                  <button @click="goToDetails(site)" class="app-text-secondary hover:text-[var(--accent-info)] p-1">
                    <i class="fas fa-eye"></i>
                  </button>
                  <button @click="openEditModal(site)" class="app-text-secondary hover:text-[var(--accent-info)] p-1">
                    <i class="fas fa-edit"></i>
                  </button>
                  <button @click="confirmDelete(site)" class="app-text-secondary hover:text-[var(--accent-danger)] p-1">
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
      <div class="app-surface rounded-2xl w-full max-w-md p-6">
        <div class="flex items-start gap-3">
          <div class="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center" style="background: var(--danger-soft-bg); color: var(--accent-danger);">
            <i class="fas fa-trash-alt"></i>
          </div>
          <div class="flex-1">
            <h3 class="text-lg font-semibold app-text-primary">Remover site</h3>
            <p
              class="text-sm app-text-secondary mt-1"
              v-if="(confirmDialog.item?.device_count || 0) === 0"
            >
              Tem certeza que deseja remover <span class="font-semibold">{{ confirmDialog.item?.name }}</span>? Esta ação não pode ser desfeita.
            </p>
            <p
              class="text-sm mt-1" style="color: var(--status-warning);"
              v-else
            >
              Este site possui {{ confirmDialog.item?.device_count }} device(s). Remova ou migre os devices para outro site antes de apagar.
            </p>
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button
            @click="closeConfirm"
            class="px-4 py-2 rounded-lg transition-colors text-sm app-btn"
            :disabled="saving"
          >
            Cancelar
          </button>
          <template v-if="(confirmDialog.item?.device_count || 0) === 0">
            <button
              @click="proceedDelete"
              class="px-4 py-2 rounded-lg shadow-sm transition-colors text-sm disabled:opacity-60 disabled:cursor-not-allowed"
              style="background: var(--accent-danger); border: 1px solid var(--accent-danger); color: #ffffff;"
              :disabled="saving"
            >
              {{ saving ? 'Removendo...' : 'Remover' }}
            </button>
          </template>
          <template v-else>
            <button
              @click="goToDetails(confirmDialog.item)"
              class="px-4 py-2 rounded-lg shadow-sm transition-colors text-sm app-btn-primary"
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
    camera_count: payload.camera_count ?? 0,
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
