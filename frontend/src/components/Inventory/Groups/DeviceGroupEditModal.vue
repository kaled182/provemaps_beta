<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
    <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-4xl flex flex-col max-h-[90vh] overflow-hidden border border-gray-200 dark:border-gray-700">
      <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center bg-gray-50/50 dark:bg-gray-800">
        <div>
          <h3 class="text-xl font-bold text-gray-900 dark:text-white">
            {{ isEditing ? 'Editar Grupo' : 'Novo Grupo de Dispositivos' }}
          </h3>
          <p class="text-sm text-gray-500 dark:text-gray-400">Organize seus equipamentos logicamente</p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors">
          <i class="fas fa-times text-xl"></i>
        </button>
      </div>

      <div class="flex flex-col md:flex-row flex-1 overflow-hidden">
        <div class="w-full md:w-1/3 p-6 border-b md:border-b-0 md:border-r border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 overflow-y-auto">
          <div class="space-y-5">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Nome do Grupo</label>
              <input
                v-model="form.name"
                type="text"
                class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:ring-2 focus:ring-indigo-500 outline-none transition-shadow"
                placeholder="Ex: Switches Core"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Descrição</label>
              <textarea
                v-model="form.description"
                rows="4"
                class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:ring-2 focus:ring-indigo-500 outline-none resize-none text-sm"
                placeholder="Finalidade deste grupo..."
              ></textarea>
            </div>

            <div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-100 dark:border-blue-800">
              <div class="flex items-start gap-3">
                <i class="fas fa-info-circle text-blue-500 mt-0.5"></i>
                <p class="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">
                  Grupos facilitam a aplicação de regras de monitoramento em massa e filtros nos mapas.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div class="w-full md:w-2/3 p-6 flex flex-col h-[500px] md:h-auto">
          <h4 class="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3 flex justify-between items-center">
            Gerenciar Membros
            <span class="text-xs font-normal text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded-md">
              {{ selectedDevices.length }} selecionados
            </span>
          </h4>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
            <div class="relative">
              <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Buscar dispositivos..."
                class="w-full pl-9 pr-4 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
            <select
              v-model="siteFilter"
              class="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm text-gray-700 dark:text-gray-200 focus:ring-2 focus:ring-indigo-500 outline-none"
            >
              <option value="all">Todos os sites</option>
              <option v-for="opt in siteOptions" :key="opt" :value="opt">{{ opt }}</option>
            </select>
          </div>

          <div class="flex flex-1 gap-4 min-h-0">
            <div class="flex-1 flex flex-col border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <div class="bg-gray-50 dark:bg-gray-700/50 px-3 py-2 border-b border-gray-200 dark:border-gray-700 text-xs font-semibold text-gray-500">
                Disponíveis
              </div>
              <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
                <div
                  v-for="device in filteredAvailable"
                  :key="device.id"
                  @click="toggleDevice(device)"
                  class="flex items-center gap-2 p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer group transition-colors"
                >
                  <div class="mr-1 text-gray-400 text-lg">
                    <i :class="getDeviceIcon(device.role)"></i>
                  </div>
                  <div class="w-4 h-4 rounded border border-gray-300 dark:border-gray-500 flex items-center justify-center bg-white dark:bg-gray-800 group-hover:border-indigo-500"></div>
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-700 dark:text-gray-200 truncate">{{ device.name }}</div>
                    <div class="text-xs text-gray-400 truncate">
                      {{ device.primary_ip || device.ip || 'Sem IP' }} • {{ device.site_name || 'Sem Site' }}
                    </div>
                  </div>
                  <i class="fas fa-plus text-gray-300 group-hover:text-indigo-500"></i>
                </div>
                <div v-if="filteredAvailable.length === 0" class="text-center py-8 text-gray-400 text-xs">
                  Nada encontrado.
                </div>
              </div>
            </div>

            <div class="flex flex-col justify-center gap-2 px-2 text-gray-300">
              <button
                @click.stop="addAllFiltered"
                class="p-2 bg-gray-100 dark:bg-gray-700 hover:bg-indigo-100 dark:hover:bg-indigo-900/30 text-gray-500 hover:text-indigo-600 rounded-lg transition-colors"
                title="Adicionar todos visíveis"
              >
                <i class="fas fa-angle-double-right"></i>
              </button>
              <button
                @click.stop="removeAll"
                class="p-2 bg-gray-100 dark:bg-gray-700 hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-500 hover:text-red-600 rounded-lg transition-colors"
                title="Remover todos"
              >
                <i class="fas fa-angle-double-left"></i>
              </button>
            </div>

            <div class="flex-1 flex flex-col border border-indigo-100 dark:border-gray-600 ring-1 ring-indigo-500/20 rounded-lg overflow-hidden bg-indigo-50/30 dark:bg-indigo-900/10">
              <div class="bg-indigo-50 dark:bg-gray-700/50 px-3 py-2 border-b border-indigo-100 dark:border-gray-600 text-xs font-semibold text-indigo-600 dark:text-indigo-300">
                No Grupo
              </div>
              <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
                <div
                  v-for="device in selectedDevices"
                  :key="device.id"
                  @click="toggleDevice(device)"
                  class="flex items-center gap-2 p-2 rounded-md bg-white dark:bg-gray-800 shadow-sm border border-indigo-100 dark:border-gray-600 cursor-pointer hover:border-red-300 dark:hover:border-red-500 group transition-all"
                >
                  <div class="w-4 h-4 rounded bg-indigo-500 flex items-center justify-center text-white text-[10px] group-hover:bg-red-500 transition-colors">
                    <i class="fas fa-check group-hover:hidden"></i>
                    <i class="fas fa-times hidden group-hover:block"></i>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-900 dark:text-white truncate">{{ device.name }}</div>
                    <div class="text-xs text-gray-400 truncate">{{ device.site_name || 'Sem Site' }}</div>
                  </div>
                </div>
                <div v-if="selectedDevices.length === 0" class="text-center py-8 text-gray-400 text-xs italic">
                  Clique nos itens à esquerda para adicionar.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="px-6 py-4 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-3 bg-white dark:bg-gray-800">
        <button
          @click="$emit('close')"
          class="px-4 py-2 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
        >
          Cancelar
        </button>
        <button
          @click="save"
          class="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg shadow-lg shadow-indigo-500/30 transition-all transform active:scale-95 flex items-center gap-2"
          :disabled="saving"
        >
          <i class="fas fa-save"></i> {{ saving ? 'Salvando...' : 'Salvar Grupo' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  show: Boolean,
  group: Object,
  allDevices: { type: Array, default: () => [] },
  initialSelectedIds: { type: Array, default: () => [] },
  saving: Boolean,
});

const emit = defineEmits(['close', 'save']);

const form = ref({ name: '', description: '' });
const selectedIds = ref(new Set());
const searchQuery = ref('');
const siteFilter = ref('all');

const isEditing = computed(() => !!props.group);

const siteOptions = computed(() => {
  const set = new Set();
  props.allDevices.forEach((d) => {
    if (d.site_name) set.add(d.site_name);
  });
  return Array.from(set).sort();
});

const getDeviceIcon = (role) => {
  const map = {
    router: 'fas fa-router text-orange-500',
    switch: 'fas fa-random text-blue-500',
    olt: 'fas fa-network-wired text-green-500',
    server: 'fas fa-server text-purple-500',
    firewall: 'fas fa-shield-alt text-red-500',
    radio: 'fas fa-broadcast-tower text-cyan-500',
    default: 'fas fa-box text-gray-400',
  };
  return map[role?.toLowerCase()] || map.default;
};

const filteredAvailable = computed(() => {
  const query = searchQuery.value.toLowerCase();
  return props.allDevices
    .filter((d) => {
      const notSelected = !selectedIds.value.has(d.id);
      const matchesSearch =
        d.name.toLowerCase().includes(query) ||
        (d.primary_ip && d.primary_ip.toLowerCase().includes(query)) ||
        (d.ip && d.ip.toLowerCase().includes(query));
      const matchesSite = siteFilter.value === 'all' || d.site_name === siteFilter.value;
      // Se o device já pertence a outro grupo (monitoring_group), só mostra se for o próprio grupo atual
      const belongsToOtherGroup =
        d.monitoring_group && String(d.monitoring_group) !== String(props.group?.id || '');
      return notSelected && matchesSearch && matchesSite && !belongsToOtherGroup;
    })
    .slice(0, 80);
});

const selectedDevices = computed(() => props.allDevices.filter((d) => selectedIds.value.has(d.id)));

const toggleDevice = (device) => {
  if (selectedIds.value.has(device.id)) {
    selectedIds.value.delete(device.id);
  } else {
    selectedIds.value.add(device.id);
  }
};

const addAllFiltered = () => {
  filteredAvailable.value.forEach((d) => selectedIds.value.add(d.id));
};

const removeAll = () => {
  selectedIds.value.clear();
};

const save = () => {
  if (!form.value.name) return alert('Nome obrigatório');
  emit('save', {
    ...form.value,
    id: props.group?.id,
    device_ids: Array.from(selectedIds.value),
  });
};

watch(
  () => props.group,
  (newGroup) => {
    if (newGroup) {
      form.value = { name: newGroup.name, description: newGroup.description };
      const ids =
        props.initialSelectedIds && props.initialSelectedIds.length
          ? props.initialSelectedIds
          : newGroup.devices
          ? newGroup.devices.map((d) => d.id)
          : newGroup.device_ids || [];
      selectedIds.value = new Set(ids);
    } else {
      form.value = { name: '', description: '' };
      selectedIds.value = new Set();
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(156, 163, 175, 0.3);
  border-radius: 20px;
}
</style>
