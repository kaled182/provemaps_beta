<template>
  <div class="h-full flex flex-col gap-4">
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

    <!-- Fluxo para grupos com devices -->
    <div
      v-if="deleteDialog.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
    >
      <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-2xl p-6 border border-gray-200 dark:border-gray-700">
        <div class="flex items-start gap-3">
          <div class="flex-shrink-0 w-10 h-10 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center">
            <i class="fas fa-exclamation-triangle"></i>
          </div>
          <div class="flex-1">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
              {{ deleteDialog.devices.length }} devices encontrados
            </h3>
            <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">
              Migre ou remova os devices antes de excluir
              <span class="font-semibold">{{ deleteDialog.group?.name }}</span>.
            </p>
          </div>
        </div>

        <div class="mt-4 space-y-4">
          <div class="p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/40">
            <label class="flex items-start gap-3 cursor-pointer">
              <input
                v-model="deleteDialog.action"
                type="radio"
                value="migrate"
                class="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500"
                :disabled="!migrationTargets.length || deleteDialog.submitting"
              />
              <div>
                <p class="text-sm font-semibold text-gray-900 dark:text-white">Migrar devices para outro grupo</p>
                <p class="text-xs text-gray-600 dark:text-gray-300">
                  Todos os devices serão movidos antes de remover o grupo.
                </p>
              </div>
            </label>
            <select
              v-model="deleteDialog.targetGroupId"
              class="mt-3 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-900 dark:text-white px-3 py-2 disabled:opacity-60"
              :disabled="deleteDialog.action !== 'migrate' || !migrationTargets.length || deleteDialog.submitting"
            >
              <option v-for="target in migrationTargets" :key="target.id" :value="target.id">
                {{ target.name }}
              </option>
            </select>
            <p v-if="!migrationTargets.length" class="text-xs text-amber-600 mt-2">
              Não há outros grupos disponíveis para migração.
            </p>
          </div>

          <div class="p-3 rounded-xl border border-gray-200 dark:border-gray-700">
            <label class="flex items-start gap-3 cursor-pointer">
              <input
                v-model="deleteDialog.action"
                type="radio"
                value="remove"
                class="mt-1 h-4 w-4 text-red-600 focus:ring-red-500"
                :disabled="deleteDialog.submitting"
              />
              <div>
                <p class="text-sm font-semibold text-gray-900 dark:text-white">Remover devices do inventário</p>
                <p class="text-xs text-gray-600 dark:text-gray-300">
                  Os devices serão apagados definitivamente antes de excluir o grupo.
                </p>
              </div>
            </label>
          </div>

          <div class="bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
            <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span class="font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wide">Devices afetados</span>
              <span class="px-2 py-1 rounded bg-white/80 dark:bg-gray-800 text-gray-700 dark:text-gray-200">
                {{ deleteDialog.devices.length }}
              </span>
            </div>
            <ul class="mt-3 max-h-36 overflow-auto text-sm text-gray-700 dark:text-gray-200 space-y-1">
              <li
                v-for="device in deleteDialog.devices"
                :key="device.id"
                class="flex items-center gap-2"
              >
                <i class="fas fa-server text-gray-400"></i>
                <span class="font-medium">{{ device.name }}</span>
                <span v-if="device.site_name" class="text-xs text-gray-500">({{ device.site_name }})</span>
                <span v-if="device.primary_ip" class="text-xs text-gray-500">- {{ device.primary_ip }}</span>
              </li>
            </ul>
          </div>

          <div
            v-if="deleteDialog.error"
            class="text-sm text-red-600 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2"
          >
            {{ deleteDialog.error }}
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button
            @click="closeDeleteDialog"
            class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-sm"
            :disabled="deleteDialog.submitting"
          >
            Cancelar
          </button>
          <button
            @click="submitDeleteWithDevices"
            class="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white shadow-sm transition-colors text-sm disabled:opacity-60 disabled:cursor-not-allowed"
            :disabled="deleteDialog.submitting || (deleteDialog.action === 'migrate' && !deleteDialog.targetGroupId)"
          >
            {{ deleteDialog.submitting ? 'Processando...' : 'Confirmar e remover grupo' }}
          </button>
        </div>
      </div>
    </div>

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
const deleteDialog = ref(getEmptyDeleteDialog());
const groups = ref([]);
const availableDevices = ref([]);
const initialSelection = ref([]);
const searchQuery = ref('');
const errorMessage = ref('');

const filteredGroups = computed(() => {
  const q = searchQuery.value.toLowerCase().trim();
  return groups.value.filter((g) => !q || (g.name || '').toLowerCase().includes(q));
});

const migrationTargets = computed(() => {
  if (!deleteDialog.value.group) return [];
  return groups.value.filter((g) => g.id !== deleteDialog.value.group.id);
});

function getEmptyDeleteDialog() {
  return {
    open: false,
    submitting: false,
    error: '',
    group: null,
    devices: [],
    action: 'migrate',
    targetGroupId: null,
  };
}

const mapGroupFromApi = (g) => ({
  id: g.id,
  name: g.name,
  description: g.description,
  device_count: g.device_count ?? (g.devices ? g.devices.length : 0),
  device_ids: g.device_ids || (g.devices ? g.devices.map((d) => d.id) : []),
  devices: g.devices || [],
});

const mapDeviceFromApi = (d) => ({
  id: d.id,
  name: d.name,
  primary_ip: d.primary_ip,
  site_name: d.site_name || d.site || '',
  monitoring_group: d.monitoring_group || d.group || null,
  role: d.role || d.category || null,
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

const fetchDevicesByGroup = async (groupId) => {
  const data = await api.get(`/api/v1/devices/available-for-group/?group_id=${groupId}`);
  const list = Array.isArray(data) ? data : data.results || data.devices || [];
  return list
    .map(mapDeviceFromApi)
    .filter((d) => String(d.monitoring_group) === String(groupId));
};

const loadAvailableDevices = async (groupId = null) => {
  try {
    const query = groupId ? `?group_id=${groupId}` : '';
    const data = await api.get(`/api/v1/devices/available-for-group/${query}`);
    const list = Array.isArray(data) ? data : data.results || data.devices || [];
    availableDevices.value = list.map(mapDeviceFromApi);
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

const handleDelete = async (group) => {
  errorMessage.value = '';
  confirmDialog.value = { open: false, item: null };
  deleteDialog.value = getEmptyDeleteDialog();
  detailLoading.value = true;
  try {
    const devicesInGroup = await fetchDevicesByGroup(group.id);
    if (devicesInGroup.length === 0) {
      confirmDialog.value = { open: true, item: group };
      return;
    }
    const targets = groups.value.filter((g) => g.id !== group.id);
    deleteDialog.value = {
      ...getEmptyDeleteDialog(),
      open: true,
      group,
      devices: devicesInGroup,
      action: targets.length ? 'migrate' : 'remove',
      targetGroupId: targets[0]?.id || null,
    };
  } catch (error) {
    console.error('Erro ao verificar devices do grupo', error);
    errorMessage.value = error.message || 'Erro ao verificar devices do grupo.';
  } finally {
    detailLoading.value = false;
  }
};

const closeConfirm = () => {
  confirmDialog.value = { open: false, item: null };
};

const closeDeleteDialog = () => {
  deleteDialog.value = getEmptyDeleteDialog();
};

const deleteGroup = async (groupId) => {
  await api.delete(`/api/v1/device-groups/${groupId}/`);
  await fetchGroups();
};

const proceedDelete = async () => {
  const group = confirmDialog.value.item;
  if (!group) return;
  saving.value = true;
  errorMessage.value = '';
  try {
    await deleteGroup(group.id);
    await loadAvailableDevices(null);
    closeConfirm();
  } catch (error) {
    console.error('Erro ao remover grupo', error);
    errorMessage.value = error.message || 'Erro ao remover grupo.';
  } finally {
    saving.value = false;
  }
};

const submitDeleteWithDevices = async () => {
  if (!deleteDialog.value.group) return;
  deleteDialog.value.submitting = true;
  deleteDialog.value.error = '';
  try {
    const { action, targetGroupId, devices, group } = deleteDialog.value;
    if (action === 'migrate') {
      if (!targetGroupId) {
        deleteDialog.value.error = 'Selecione um grupo de destino.';
        return;
      }
      await Promise.all(
        devices.map((device) =>
          api.patch(`/api/v1/devices/${device.id}/`, {
            monitoring_group: targetGroupId,
          })
        )
      );
    } else {
      await Promise.all(
        devices.map((device) => api.delete(`/api/v1/devices/${device.id}/`))
      );
    }
    await deleteGroup(group.id);
    await loadAvailableDevices(null);
    closeDeleteDialog();
  } catch (error) {
    console.error('Erro ao remover grupo com devices', error);
    deleteDialog.value.error =
      error.message || 'Erro ao remover grupo e devices.';
  } finally {
    deleteDialog.value.submitting = false;
  }
};

onMounted(async () => {
  await fetchGroups();
});

defineExpose({
  openCreateModal,
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
