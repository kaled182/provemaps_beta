<template>
  <div class="h-full flex flex-col gap-4">
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3 bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
      <div>
        <h2 class="text-lg font-bold text-gray-900 dark:text-white">Grupos de Dispositivos</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400">Gerencie agrupamentos lógicos para relatórios e acesso</p>
      </div>
      <button
        @click="openCreateModal"
        class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-md transition-colors flex items-center gap-2"
      >
        <i class="fas fa-plus"></i> Novo Grupo
      </button>
    </div>

    <div class="flex items-center justify-between bg-white dark:bg-gray-800 p-3 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
      <div class="relative w-full md:w-80">
        <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Buscar grupo..."
          class="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
        />
      </div>
      <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 ml-3">
        <span class="px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200">Total: {{ groups.length }}</span>
      </div>
    </div>

    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
    </div>

    <div v-else-if="errorMessage" class="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-800 px-4 py-3 rounded-lg">
      {{ errorMessage }}
    </div>

    <div v-else-if="filteredGroups.length === 0" class="flex-1 flex flex-col items-center justify-center text-gray-400">
      <i class="fas fa-layer-group text-6xl mb-4 opacity-20"></i>
      <p>Nenhum grupo criado.</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 overflow-auto pb-12 inventory-scroll">
      <DeviceGroupCard
        v-for="group in filteredGroups"
        :key="group.id"
        :group="group"
        @edit="openEditModal"
        @delete="handleDelete"
      />
    </div>

    <DeviceGroupEditModal
      v-if="showModal"
      :show="showModal"
      :group="selectedGroup"
      :all-devices="availableDevices"
      :initial-selected-ids="initialSelection"
      :saving="saving"
      @close="showModal = false"
      @save="handleSave"
    />

    <!-- Confirmação de remoção de grupo -->
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
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Remover grupo</h3>
            <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">
              Tem certeza que deseja remover <span class="font-semibold">{{ confirmDialog.item?.name }}</span>? Esta ação não pode ser desfeita.
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
          <button
            @click="proceedDelete"
            class="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white shadow-sm transition-colors text-sm disabled:opacity-60 disabled:cursor-not-allowed"
            :disabled="saving"
          >
            {{ saving ? 'Removendo...' : 'Remover' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useApi } from '@/composables/useApi';
import DeviceGroupCard from './DeviceGroupCard.vue';
import DeviceGroupEditModal from './DeviceGroupEditModal.vue';

const api = useApi();

const loading = ref(false);
const saving = ref(false);
const detailLoading = ref(false);
const showModal = ref(false);
const selectedGroup = ref(null);
const confirmDialog = ref({ open: false, item: null });
const groups = ref([]);
const availableDevices = ref([]);
const initialSelection = ref([]);
const searchQuery = ref('');
const errorMessage = ref('');

const filteredGroups = computed(() => {
  const q = searchQuery.value.toLowerCase().trim();
  return groups.value.filter((g) => !q || (g.name || '').toLowerCase().includes(q));
});

const mapGroupFromApi = (g) => ({
  id: g.id,
  name: g.name,
  description: g.description,
  device_count: g.device_count ?? (g.devices ? g.devices.length : 0),
  device_ids: g.device_ids || (g.devices ? g.devices.map((d) => d.id) : []),
  devices: g.devices || [],
});

const fetchGroups = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    let url = '/api/v1/device-groups/?page_size=200';
    const collection = [];
    while (url) {
      const data = await api.get(url);
      const pageItems = Array.isArray(data) ? data : data.results || [];
      collection.push(...pageItems);
      url = data.next || null;
    }
    groups.value = collection.map(mapGroupFromApi);
  } catch (error) {
    console.error('Erro ao carregar grupos', error);
    errorMessage.value = error.message || 'Erro ao carregar grupos.';
  } finally {
    loading.value = false;
  }
};

const fetchGroupDetail = async (id) => {
  const data = await api.get(`/api/v1/device-groups/${id}/`);
  return mapGroupFromApi(data);
};

const loadAvailableDevices = async (groupId = null) => {
  try {
    const query = groupId ? `?group_id=${groupId}` : '';
    const data = await api.get(`/api/v1/devices/available-for-group/${query}`);
    const list = Array.isArray(data) ? data : data.results || data.devices || [];
    availableDevices.value = list.map((d) => ({
      id: d.id,
      name: d.name,
      primary_ip: d.primary_ip,
      site_name: d.site_name || d.site || '',
      monitoring_group: d.monitoring_group || d.group || null,
      role: d.role || d.category || null,
    }));
  } catch (error) {
    console.error('Erro ao carregar devices disponíveis', error);
    availableDevices.value = [];
  }
};

const openCreateModal = () => {
  selectedGroup.value = null;
  initialSelection.value = [];
  loadAvailableDevices(null).then(() => {
    showModal.value = true;
  });
};

const openEditModal = async (group) => {
  detailLoading.value = true;
  errorMessage.value = '';
  try {
    await loadAvailableDevices(group.id);
    const fullGroup = await fetchGroupDetail(group.id);
    selectedGroup.value = fullGroup;
    initialSelection.value = availableDevices.value
      .filter((d) => String(d.monitoring_group) === String(group.id))
      .map((d) => d.id);
    showModal.value = true;
  } catch (error) {
    console.error('Erro ao carregar grupo', error);
    errorMessage.value = error.message || 'Erro ao carregar grupo.';
  } finally {
    detailLoading.value = false;
  }
};

const handleSave = async (groupData) => {
  saving.value = true;
  errorMessage.value = '';
  try {
    const targetId = groupData.id;
    const newIds = new Set(groupData.device_ids || []);
    const oldIds = new Set(initialSelection.value || []);

    const toAssign = Array.from(newIds).filter((id) => !oldIds.has(id));
    const toUnassign = Array.from(oldIds).filter((id) => !newIds.has(id));

    // Atualiza devices adicionados
    await Promise.all(
      toAssign.map((id) =>
        api.patch(`/api/v1/devices/${id}/`, { monitoring_group: targetId })
      )
    );
    // Remove devices que saíram
    await Promise.all(
      toUnassign.map((id) =>
        api.patch(`/api/v1/devices/${id}/`, { monitoring_group: null })
      )
    );

    // Apenas atualização de nome/descrição se disponível (viewset é read-only; se backend permitir, descomente)
    // await api.put(`/api/v1/device-groups/${targetId}/`, { name: groupData.name, description: groupData.description });

    showModal.value = false;
    await fetchGroups();
    await loadAvailableDevices(null);
  } catch (error) {
    console.error('Erro ao salvar grupo', error);
    errorMessage.value = error.message || 'Erro ao salvar grupo.';
  } finally {
    saving.value = false;
  }
};

const handleDelete = (group) => {
  confirmDialog.value = { open: true, item: group };
};

const closeConfirm = () => {
  confirmDialog.value = { open: false, item: null };
};

const proceedDelete = async () => {
  const group = confirmDialog.value.item;
  if (!group) return;
  saving.value = true;
  errorMessage.value = '';
  try {
    await api.delete(`/api/v1/device-groups/${group.id}/`);
    await fetchGroups();
    closeConfirm();
  } catch (error) {
    console.error('Erro ao remover grupo', error);
    errorMessage.value = error.message || 'Erro ao remover grupo.';
  } finally {
    saving.value = false;
  }
};

onMounted(async () => {
  await fetchGroups();
});
</script>

<style scoped>
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
