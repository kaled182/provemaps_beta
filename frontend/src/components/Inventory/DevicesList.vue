<template>
  <div class="h-full flex flex-col gap-6 relative">
    <!-- KPIs -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="kpi-card">
        <div>
          <p class="kpi-label">Total</p>
          <p class="kpi-value">{{ kpis.total }}</p>
        </div>
        <div class="kpi-icon bg-blue-50 text-blue-600 dark:bg-blue-900/20">
          <i class="fas fa-server"></i>
        </div>
      </div>

      <div class="kpi-card">
        <div>
          <p class="kpi-label">Online</p>
          <p class="kpi-value text-green-600 dark:text-green-400">{{ kpis.online }}</p>
        </div>
        <div class="kpi-icon bg-green-50 text-green-600 dark:bg-green-900/20">
          <i class="fas fa-check-circle"></i>
        </div>
      </div>

      <div class="kpi-card">
        <div>
          <p class="kpi-label">Offline</p>
          <p class="kpi-value text-red-600 dark:text-red-400">{{ kpis.offline }}</p>
        </div>
        <div class="kpi-icon bg-red-50 text-red-600 dark:bg-red-900/20">
          <i class="fas fa-exclamation-triangle"></i>
        </div>
      </div>

      <div class="kpi-card">
        <div>
          <p class="kpi-label">Sites</p>
          <p class="kpi-value text-gray-900 dark:text-white">{{ kpis.sites }}</p>
        </div>
        <div class="kpi-icon bg-purple-50 text-purple-600 dark:bg-purple-900/20">
          <i class="fas fa-map-marker-alt"></i>
        </div>
      </div>
    </div>

    <!-- Toolbar de filtros -->
    <div class="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col lg:flex-row gap-3 items-start lg:items-center justify-between">
      <div class="relative w-full lg:w-96">
        <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
        <input
          v-model="filters.search"
          type="text"
          placeholder="Buscar por nome, IP ou HostID..."
          class="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
        />
      </div>

      <div class="flex flex-wrap gap-2 w-full lg:w-auto justify-end items-center">
        <select v-model="filters.site" class="filter-select dark:bg-gray-900 dark:border-gray-700">
          <option value="">Todos os Sites</option>
          <option v-for="site in sitesOptions" :key="site" :value="site">{{ site }}</option>
        </select>

        <select v-model="filters.vendor" class="filter-select dark:bg-gray-900 dark:border-gray-700">
          <option value="">Todos os Fabricantes</option>
          <option v-for="vendor in vendorOptions" :key="vendor" :value="vendor">{{ vendor }}</option>
        </select>

        <select v-model="filters.status" class="filter-select dark:bg-gray-900 dark:border-gray-700">
          <option value="">Todos Status</option>
          <option value="online">Online</option>
          <option value="offline">Offline</option>
          <option value="unknown">Desconhecido</option>
        </select>

        <button
          class="px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-200 rounded-lg transition-colors flex items-center gap-2"
          title="Atualizar status Zabbix"
          :disabled="refreshing"
          @click="refreshStatuses"
        >
          <i :class="refreshing ? 'fas fa-sync-alt fa-spin' : 'fas fa-sync-alt'"></i>
          <span class="hidden sm:inline">Sincronizar</span>
        </button>

        <div class="relative">
          <button
            @click="showColumnsMenu = !showColumnsMenu"
            class="px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-200 rounded-lg transition-colors flex items-center gap-2"
          >
            <i class="fas fa-columns"></i>
            <span class="hidden sm:inline">Colunas</span>
          </button>
          <div
            v-if="showColumnsMenu"
            class="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-2 z-30"
          >
            <label
              v-for="col in columns"
              :key="col.key"
              class="flex items-center gap-2 px-2 py-1 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 rounded"
            >
              <input type="checkbox" v-model="col.visible" />
              <span>{{ col.label }}</span>
            </label>
          </div>
        </div>

        <button
          class="px-4 py-2 bg-gray-100 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-200 rounded-lg transition-colors"
          title="Limpar filtros"
          @click="clearFilters"
        >
          <i class="fas fa-filter"></i>
        </button>
      </div>
    </div>

    <!-- Tabela -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 flex-1 overflow-hidden flex flex-col">
      <div class="flex-1 overflow-auto inventory-scroll">
        <div v-if="loading" class="p-6 text-center text-gray-500 dark:text-gray-400">Carregando devices...</div>
        <div v-else-if="error" class="p-6 text-red-600 dark:text-red-300">{{ error }}</div>
        <div v-else-if="filteredDevices.length === 0" class="flex flex-col items-center justify-center py-12 text-gray-400">
          <i class="fas fa-search text-4xl mb-3 opacity-20"></i>
          <p>Nenhum dispositivo encontrado.</p>
        </div>
        <table v-else class="w-full text-left border-collapse">
          <thead class="bg-gray-50 dark:bg-gray-800 sticky top-0 z-20">
            <tr>
              <th class="th w-10 text-center">
                <input
                  type="checkbox"
                  :checked="isAllSelected"
                  @change="toggleSelectAll"
                  class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
              </th>
              <th v-if="isVisible('status')" class="th w-32">Status</th>
              <th v-if="isVisible('device')" class="th">Dispositivo</th>
              <th v-if="isVisible('ip')" class="th">Endereço IP</th>
              <th v-if="isVisible('site')" class="th">Site</th>
              <th v-if="isVisible('vendor')" class="th">Fabricante / Modelo</th>
              <th v-if="isVisible('hostid')" class="th text-right">HostID</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
            <tr v-for="device in filteredDevices" :key="device.id" class="group hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
              <td class="px-5 py-4 text-center align-middle">
                <input
                  type="checkbox"
                  :checked="selectedIds.has(device.id)"
                  @change="toggleSelection(device.id)"
                  class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
              </td>

              <td v-if="isVisible('status')" class="px-5 py-4 align-middle">
                <div class="flex items-center gap-2" :title="statusTooltip(device)">
                  <span :class="['status-dot', statusClass(device)]"></span>
                  <span class="text-xs text-gray-500 dark:text-gray-400 capitalize">{{ displayStatus(device) }}</span>
                </div>
              </td>

              <td v-if="isVisible('device')" class="px-5 py-4 align-middle">
                <div class="flex items-center gap-3">
                  <div class="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-300">
                    <i :class="roleIcon(device)"></i>
                  </div>
                  <div>
                    <div class="font-bold text-gray-900 dark:text-white text-sm">{{ device.name }}</div>
                    <div class="text-xs text-indigo-500 dark:text-indigo-300" v-if="device.group_name">
                      {{ device.group_name }}
                    </div>
                  </div>
                </div>
              </td>

              <td v-if="isVisible('ip')" class="px-5 py-4 align-middle">
                <button
                  @click="copyToClipboard(device.primary_ip || device.ip)"
                  class="flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors group/ip"
                >
                  <span class="font-mono text-sm text-gray-700 dark:text-gray-200">{{ device.primary_ip || device.ip || '—' }}</span>
                  <i class="fas fa-copy text-xs text-gray-300 group-hover/ip:text-indigo-500 transition-colors"></i>
                </button>
              </td>

              <td v-if="isVisible('site')" class="px-5 py-4 align-middle">
                <div class="flex flex-col">
                  <span class="text-sm font-medium text-gray-700 dark:text-gray-200">{{ siteLabel(device) || '—' }}</span>
                </div>
              </td>

              <td v-if="isVisible('vendor')" class="px-5 py-4 align-middle">
                <div class="text-sm text-gray-700 dark:text-gray-300">{{ device.vendor || '—' }}</div>
                <div class="text-xs text-gray-500">{{ device.model || '—' }}</div>
              </td>

              <td v-if="isVisible('hostid')" class="px-5 py-4 text-right text-sm text-gray-600 dark:text-gray-300 align-middle">
                {{ device.zabbix_hostid || '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="border-t border-gray-200 dark:border-gray-700 px-6 py-3 bg-gray-50 dark:bg-gray-700/30 flex justify-between items-center text-xs text-gray-500">
        <span>Mostrando {{ filteredDevices.length }} de {{ devices.length }} registros</span>
      </div>
    </div>

    <transition
      enter-active-class="transform ease-out duration-300 transition"
      enter-from-class="translate-y-full opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-full opacity-0"
    >
      <div
        v-if="selectedIds.size > 0"
        class="fixed bottom-6 left-1/2 -translate-x-1/2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-2xl rounded-full px-6 py-3 flex items-center gap-4 z-40"
      >
        <span class="text-sm font-medium text-gray-600 dark:text-gray-300 border-r border-gray-200 dark:border-gray-700 pr-4">
          <span class="text-indigo-600 dark:text-indigo-400 font-bold">{{ selectedIds.size }}</span> selecionados
        </span>
        <div class="flex gap-2">
          <button @click="openGroupModal" class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full text-gray-600 dark:text-gray-300" title="Mover para grupo">
            <i class="fas fa-layer-group"></i>
          </button>
          <button @click="openStatusModal" class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full text-gray-600 dark:text-gray-300" title="Modo manutenção">
            <i class="fas fa-tools"></i>
          </button>
        </div>
        <button @click="clearSelection" class="ml-2 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 underline">
          Cancelar
        </button>
      </div>
    </transition>

    <transition
      enter-active-class="transform ease-out duration-300 transition"
      enter-from-class="translate-y-full opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-full opacity-0"
    >
      <div
        v-if="selectedIds.size > 0"
        class="fixed bottom-6 left-1/2 -translate-x-1/2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-2xl rounded-full px-6 py-3 flex items-center gap-4 z-40"
      >
        <span class="text-sm font-medium text-gray-600 dark:text-gray-300 border-r border-gray-200 dark:border-gray-700 pr-4">
          <span class="text-indigo-600 dark:text-indigo-400 font-bold">{{ selectedIds.size }}</span> selecionados
        </span>
        <div class="flex gap-2">
          <button @click="openGroupModal" class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full text-gray-600 dark:text-gray-300" title="Mover para grupo">
            <i class="fas fa-layer-group"></i>
          </button>
          <button @click="openStatusModal" class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full text-gray-600 dark:text-gray-300" title="Modo manutenção">
            <i class="fas fa-tools"></i>
          </button>
          <div class="w-px h-4 bg-gray-300 dark:bg-gray-600 my-auto"></div>
          <button @click="confirmBulkDelete" class="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-full text-red-600 dark:text-red-400" title="Excluir">
            <i class="fas fa-trash-alt"></i>
          </button>
        </div>
        <button @click="clearSelection" class="ml-2 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 underline">
          Cancelar
        </button>
      </div>
    </transition>

    <!-- Modal de Grupo -->
    <div v-if="modals.group" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-md overflow-hidden border border-gray-200 dark:border-gray-700">
        <div class="p-6 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
          <h3 class="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <i class="fas fa-layer-group text-indigo-500"></i> Alterar Grupo
          </h3>
          <button @click="modals.group = false" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="p-6">
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Selecione o novo grupo para os <span class="font-bold text-gray-900 dark:text-white">{{ selectedIds.size }}</span> dispositivos selecionados.
          </p>
          <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Novo Grupo</label>
          <div class="relative">
            <select v-model="forms.groupTarget" class="w-full appearance-none bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="" disabled>Selecione um grupo...</option>
              <option v-for="group in availableGroups" :key="group.id" :value="group.id">{{ group.name }}</option>
            </select>
            <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-500">
              <i class="fas fa-chevron-down text-xs"></i>
            </div>
          </div>
        </div>
        <div class="p-4 bg-gray-50 dark:bg-gray-700/50 flex justify-end gap-3">
          <button @click="modals.group = false" class="px-4 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg font-medium text-sm">Cancelar</button>
          <button
            @click="saveBulkGroup"
            :disabled="!forms.groupTarget"
            class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium text-sm shadow-sm flex items-center gap-2"
          >
            <i class="fas fa-save"></i> Salvar Mudanças
          </button>
        </div>
      </div>
    </div>

    <!-- Modal de Status / Manutenção -->
    <div v-if="modals.status" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-md overflow-hidden border border-gray-200 dark:border-gray-700">
        <div class="p-6 border-b border-gray-100 dark:border-gray-700">
          <h3 class="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <i class="fas fa-tools text-orange-500"></i> Gestão de Status
          </h3>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Dispositivos: {{ selectedIds.size }} selecionados
          </p>
        </div>
        <div class="p-6 space-y-4">
          <div class="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg border border-blue-100 dark:border-blue-800 flex gap-3">
            <i class="fas fa-info-circle text-blue-500 mt-0.5"></i>
            <p class="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">
              O status <b>Online/Offline</b> é gerido automaticamente pelo Zabbix/SNMP. Use esta opção para definir janelas de manutenção.
            </p>
          </div>
          <div class="space-y-3">
            <label class="flex items-center p-3 border border-gray-200 dark:border-gray-700 rounded-xl cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors" :class="{'ring-2 ring-green-500 border-transparent': forms.statusTarget === 'active'}">
              <input type="radio" v-model="forms.statusTarget" value="active" class="w-4 h-4 text-green-600 focus:ring-green-500 border-gray-300 dark:border-gray-600" />
              <div class="ml-3">
                <span class="block text-sm font-bold text-gray-900 dark:text-white">Ativo (Monitorado)</span>
                <span class="block text-xs text-gray-500">Alertas habilitados.</span>
              </div>
            </label>
            <label class="flex items-center p-3 border border-gray-200 dark:border-gray-700 rounded-xl cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors" :class="{'ring-2 ring-orange-500 border-transparent': forms.statusTarget === 'maintenance'}">
              <input type="radio" v-model="forms.statusTarget" value="maintenance" class="w-4 h-4 text-orange-600 focus:ring-orange-500 border-gray-300 dark:border-gray-600" />
              <div class="ml-3">
                <span class="block text-sm font-bold text-gray-900 dark:text-white">Em Manutenção</span>
                <span class="block text-xs text-gray-500">Silencia alertas temporariamente.</span>
              </div>
            </label>
          </div>
        </div>
        <div class="p-4 bg-gray-50 dark:bg-gray-700/50 flex justify-end gap-3">
          <button @click="modals.status = false" class="px-4 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg font-medium text-sm">Cancelar</button>
          <button
            @click="saveBulkStatus"
            class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium text-sm shadow-sm flex items-center gap-2"
          >
            <i class="fas fa-check"></i> Confirmar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useApi } from '@/composables/useApi';

const api = useApi();
const devices = ref([]);
const sitesCount = ref(0);
const statusMap = ref({});
const selectedIds = ref(new Set());
const columns = ref([
  { key: 'status', label: 'Status', visible: true },
  { key: 'device', label: 'Dispositivo', visible: true },
  { key: 'ip', label: 'Endereço IP', visible: true },
  { key: 'site', label: 'Site', visible: true },
  { key: 'vendor', label: 'Fabricante / Modelo', visible: true },
  { key: 'hostid', label: 'HostID', visible: true },
]);
const showColumnsMenu = ref(false);
const refreshing = ref(false);
const loading = ref(false);
const error = ref('');
const modals = reactive({ group: false, status: false });
const forms = reactive({ groupTarget: '', statusTarget: 'active' });
const availableGroups = ref([]);

const filters = ref({
  search: '',
  site: '',
  vendor: '',
  status: '',
});

const normalizeStatus = (device) => {
  const mapStatus = statusMap.value[String(device.id)];
  if (mapStatus) return mapStatus;
  const raw = (device.status || device.zabbix_status || device.availability || '').toString().toLowerCase();
  if (['1', 'up', 'online', 'true'].includes(raw)) return 'online';
  if (['0', '2', 'down', 'offline', 'false', 'critical'].includes(raw)) return 'offline';
  return 'unknown';
};

const siteLabel = (d) => d.site_name || d.site_display_name || (d.site ? `Site ${d.site}` : '');

const kpis = computed(() => {
  const total = devices.value.length;
  let online = 0;
  let offline = 0;
  devices.value.forEach((d) => {
    const status = normalizeStatus(d);
    if (status === 'online') online += 1;
    else if (status === 'offline') offline += 1;
  });
  return {
    total,
    online,
    offline,
    sites: sitesCount.value,
  };
});

const sitesOptions = computed(() =>
  [...new Set(devices.value.map((d) => siteLabel(d)).filter(Boolean))].sort()
);

const vendorOptions = computed(() =>
  [...new Set(devices.value.map((d) => d.vendor).filter(Boolean))].sort()
);

const filteredDevices = computed(() => {
  const q = filters.value.search.trim().toLowerCase();
  return devices.value.filter((d) => {
    const status = normalizeStatus(d);
    const matchSearch =
      !q ||
      (d.name || '').toLowerCase().includes(q) ||
      (d.site_name || '').toLowerCase().includes(q) ||
      (d.primary_ip || d.ip || '').toLowerCase().includes(q) ||
      (d.zabbix_hostid || '').toString().includes(q);
    const matchSite = !filters.value.site || d.site_name === filters.value.site;
    const matchVendor = !filters.value.vendor || d.vendor === filters.value.vendor;
    const matchStatus = !filters.value.status || status === filters.value.status;
    return matchSearch && matchSite && matchVendor && matchStatus;
  });
});

const roleIcon = (device) => {
  const role = device.role || device.category;
  const map = {
    router: 'fas fa-route text-orange-500',
    switch: 'fas fa-random text-blue-500',
    olt: 'fas fa-network-wired text-green-500',
    radio: 'fas fa-broadcast-tower text-cyan-500',
    backbone: 'fas fa-project-diagram text-indigo-500',
  };
  return map[role] || 'fas fa-server text-gray-400';
};

const statusClass = (device) => {
  const status = normalizeStatus(device);
  if (status === 'online') return 'bg-green-400 ring-4 ring-green-200 dark:ring-green-700/60 animate-pulse-slow';
  if (status === 'offline') return 'bg-red-500 ring-4 ring-red-200 dark:ring-red-700/60';
  return 'bg-gray-300 ring-4 ring-gray-200 dark:ring-gray-700/60';
};

const displayStatus = (device) => {
  const status = normalizeStatus(device);
  if (status === 'online') return 'online';
  if (status === 'offline') return 'offline';
  return 'desconhecido';
};

const statusTooltip = (device) => {
  const parts = [];
  if (device.status_text) parts.push(device.status_text);
  if (device.last_update) parts.push(`Última atualização: ${device.last_update}`);
  return parts.join(' • ') || 'Sem detalhes de status';
};

const copyToClipboard = async (text) => {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
  } catch (err) {
    console.error('Falha ao copiar IP', err);
  }
};

const clearFilters = () => {
  filters.value = { search: '', site: '', vendor: '', status: '' };
};

const clearSelection = () => {
  selectedIds.value = new Set();
};

const isAllSelected = computed(() => {
  return filteredDevices.value.length > 0 && selectedIds.value.size === filteredDevices.value.length;
});

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedIds.value = new Set();
  } else {
    selectedIds.value = new Set(filteredDevices.value.map((d) => d.id));
  }
};

const toggleSelection = (id) => {
  const next = new Set(selectedIds.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selectedIds.value = next;
};

const isVisible = (key) => columns.value.find((c) => c.key === key)?.visible;

const fetchDevices = async () => {
  loading.value = true;
  error.value = '';
  try {
    const data = await api.get('/api/v1/devices/');
    const list = Array.isArray(data) ? data : data.results || data.devices || [];
    devices.value = list;
    await fetchStatuses(list);
  } catch (err) {
    console.error('Erro ao carregar devices', err);
    error.value = err.message || 'Erro ao carregar devices.';
  } finally {
    loading.value = false;
  }
};

const fetchStatuses = async (list) => {
  if (!list || !list.length) return;
  const ids = list.map((d) => d.id).filter(Boolean);
  if (!ids.length) return;
  try {
    const data = await api.get(`/api/v1/inventory/devices/zabbix-status/?device_ids=${ids.join(',')}`);
    const statuses = data?.statuses || {};
    statusMap.value = statuses;
  } catch (err) {
    console.warn('Não foi possível carregar status dos devices', err);
  }
};

const refreshStatuses = async () => {
  refreshing.value = true;
  await fetchStatuses(devices.value);
  refreshing.value = false;
};

const confirmBulkDelete = async () => {
  // Função desativada (remoção via UI bloqueada conforme pedido)
  return;
};

const openGroupModal = async () => {
  forms.groupTarget = '';
  await fetchGroups();
  modals.group = true;
};

const openStatusModal = () => {
  forms.statusTarget = 'active';
  modals.status = true;
};

const saveBulkGroup = async () => {
  if (!forms.groupTarget || !selectedIds.value.size) return;
  const ids = Array.from(selectedIds.value);
  try {
    await Promise.all(
      ids.map((id) => api.patch(`/api/v1/devices/${id}/`, { monitoring_group: forms.groupTarget }))
    );
    await fetchDevices();
    modals.group = false;
    clearSelection();
  } catch (err) {
    console.error('Falha ao mover devices', err);
    alert(err.message || 'Erro ao mover devices');
  }
};

const saveBulkStatus = async () => {
  if (!selectedIds.value.size) return;
  const ids = Array.from(selectedIds.value);
  const maintenance = forms.statusTarget === 'maintenance';
  try {
    await Promise.all(
      ids.map((id) =>
        api.patch(`/api/v1/devices/${id}/`, {
          enable_screen_alert: !maintenance,
          enable_whatsapp_alert: !maintenance,
          enable_email_alert: !maintenance,
        })
      )
    );
    await fetchDevices();
    modals.status = false;
    clearSelection();
  } catch (err) {
    console.error('Falha ao atualizar status', err);
    alert(err.message || 'Erro ao alterar status');
  }
};

const fetchGroups = async () => {
  try {
    const data = await api.get('/api/v1/device-groups/?page_size=200');
    const list = Array.isArray(data) ? data : data.results || [];
    availableGroups.value = list.map((g) => ({ id: g.id, name: g.name }));
  } catch (err) {
    console.warn('Não foi possível carregar grupos', err);
    availableGroups.value = [];
  }
};

const fetchSitesCount = async () => {
  try {
    const data = await api.get('/api/v1/sites/?page_size=1');
    sitesCount.value = Number(data?.count || 0);
  } catch (err) {
    console.warn('Não foi possível carregar contagem de sites', err);
    sitesCount.value = 0;
  }
};

onMounted(async () => {
  await Promise.all([fetchDevices(), fetchSitesCount(), fetchGroups()]);
});
</script>

<style scoped>
.kpi-card {
  @apply bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm flex items-center justify-between;
}
.kpi-label {
  @apply text-xs font-semibold text-gray-500 uppercase tracking-wide;
}
.kpi-value {
  @apply text-2xl font-bold text-gray-900 dark:text-white;
}
.kpi-icon {
  @apply p-3 rounded-lg;
}
.filter-select {
  @apply px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none;
}
.th {
  @apply px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider;
}
.status-dot {
  @apply h-3 w-3 rounded-full inline-block;
}
.animate-pulse-slow {
  animation: pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .5; }
}

/* Scrollbar padrão (mesmo estilo usado em DeviceImport) */
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
