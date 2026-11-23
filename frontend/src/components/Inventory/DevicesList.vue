<template>
  <div class="h-full flex flex-col gap-3 relative">
    <!-- KPIs -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-2">
      <div class="kpi-card">
        <div>
          <p class="kpi-label">Total</p>
          <p class="kpi-value">{{ kpis.total }}</p>
        </div>
        <div class="kpi-icon bg-info/10 text-info">
          <i class="fas fa-server"></i>
        </div>
      </div>

      <div class="kpi-card">
        <div>
          <p class="kpi-label">Online</p>
          <p class="kpi-value text-success">{{ kpis.online }}</p>
        </div>
        <div class="kpi-icon bg-success/10 text-success">
          <i class="fas fa-check-circle"></i>
        </div>
      </div>

      <div class="kpi-card">
        <div>
          <p class="kpi-label">Offline</p>
          <p class="kpi-value text-danger">{{ kpis.offline }}</p>
        </div>
        <div class="kpi-icon bg-danger/10 text-danger">
          <i class="fas fa-exclamation-triangle"></i>
        </div>
      </div>

      <div class="kpi-card">
        <div>
          <p class="kpi-label">Sites</p>
          <p class="kpi-value text-neutral-900">{{ kpis.sites }}</p>
        </div>
        <div class="kpi-icon bg-primary-50 text-primary-600">
          <i class="fas fa-map-marker-alt"></i>
        </div>
      </div>
    </div>

    <!-- Toolbar de filtros -->
    <div class="bg-surface px-3 py-2 rounded-lg border border-neutral-200 flex flex-col lg:flex-row gap-3 items-start lg:items-center justify-between">
      <div class="relative w-full lg:w-96">
        <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"></i>
        <input
          v-model="filters.search"
          type="text"
          placeholder="Buscar por nome, IP ou HostID..."
          class="w-full pl-10 pr-4 py-2 rounded-lg border border-neutral-300 bg-neutral-50 text-neutral-900 focus:ring-2 focus:ring-primary-500 outline-none"
        />
      </div>

      <div class="flex flex-wrap gap-2 w-full lg:w-auto justify-end items-center">
        <select v-model="filters.site" class="filter-select">
          <option value="">Todos os Sites</option>
          <option v-for="site in sitesOptions" :key="site" :value="site">{{ site }}</option>
        </select>

        <select v-model="filters.vendor" class="filter-select">
          <option value="">Todos os Fabricantes</option>
          <option v-for="vendor in vendorOptions" :key="vendor" :value="vendor">{{ vendor }}</option>
        </select>

        <select v-model="filters.status" class="filter-select">
          <option value="">Todos Status</option>
          <option value="online">Online</option>
          <option value="offline">Offline</option>
          <option value="unknown">Desconhecido</option>
        </select>

        <button
          class="px-3 py-2 bg-surface border border-neutral-300 hover:bg-neutral-100 text-neutral-600 rounded-lg transition-colors flex items-center gap-2"
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
            class="px-3 py-2 bg-surface border border-neutral-300 hover:bg-neutral-100 text-neutral-600 rounded-lg transition-colors flex items-center gap-2"
          >
            <i class="fas fa-columns"></i>
            <span class="hidden sm:inline">Colunas</span>
          </button>
          <div
            v-if="showColumnsMenu"
            class="absolute right-0 mt-2 w-48 bg-surface border border-neutral-200 rounded-lg shadow-lg p-2 z-30"
          >
            <label
              v-for="col in columns"
              :key="col.key"
              class="flex items-center gap-2 px-2 py-1 text-sm text-neutral-700 hover:bg-neutral-50 rounded"
            >
              <input type="checkbox" v-model="col.visible" />
              <span>{{ col.label }}</span>
            </label>
          </div>
        </div>

        <button
          class="px-4 py-2 bg-neutral-100 border border-neutral-300 hover:bg-neutral-200 text-neutral-600 rounded-lg transition-colors"
          title="Limpar filtros"
          @click="clearFilters"
        >
          <i class="fas fa-filter"></i>
        </button>
      </div>
    </div>

    <!-- Tabela -->
    <div class="bg-surface rounded-xl shadow-sm border border-neutral-200 flex-1 overflow-hidden flex flex-col">
      <div class="flex-1 overflow-auto inventory-scroll">
        <div v-if="loading" class="p-6 text-center text-neutral-500">Carregando devices...</div>
        <div v-else-if="error" class="p-6 text-danger">{{ error }}</div>
        <div v-else-if="filteredDevices.length === 0" class="flex flex-col items-center justify-center py-12 text-neutral-400">
          <i class="fas fa-search text-4xl mb-3 opacity-20"></i>
          <p>Nenhum dispositivo encontrado.</p>
        </div>
        <table v-else class="w-full text-left border-collapse">
          <thead class="bg-neutral-50 sticky top-0 z-20">
            <tr>
              <th class="th w-10 text-center">
                <input
                  type="checkbox"
                  :checked="isAllSelected"
                  @change="toggleSelectAll"
                  class="rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
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
          <tbody class="divide-y divide-neutral-100">
            <tr v-for="device in filteredDevices" :key="device.id" class="group hover:bg-neutral-50 transition-colors">
              <td class="px-3 py-1.5 text-center align-middle">
                <input
                  type="checkbox"
                  :checked="selectedIds.has(device.id)"
                  @change="toggleSelection(device.id)"
                  class="rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
                />
              </td>

              <td v-if="isVisible('status')" class="px-3 py-1.5 align-middle">
                <div class="flex items-center gap-2" :title="statusTooltip(device)">
                  <span :class="['status-dot', statusClass(device)]"></span>
                  <span class="text-xs text-neutral-500 capitalize">{{ displayStatus(device) }}</span>
                </div>
              </td>

              <td v-if="isVisible('device')" class="px-3 py-1.5 align-middle">
                <div class="flex items-center gap-2 whitespace-nowrap">
                  <i :class="[roleIcon(device), 'w-4 text-center text-neutral-500']"></i>
                  <span class="font-semibold text-neutral-900 text-sm">{{ device.name }}</span>
                  <span v-if="device.group_name" class="text-xs text-primary-600 truncate">{{ device.group_name }}</span>
                </div>
              </td>

              <td v-if="isVisible('ip')" class="px-3 py-1.5 align-middle">
                <button
                  @click="copyToClipboard(device.primary_ip || device.ip)"
                  class="flex items-center gap-2 px-1.5 py-0.5 rounded hover:bg-neutral-100 transition-colors group/ip"
                >
                  <span class="font-mono text-sm tabular-nums text-neutral-700">{{ device.primary_ip || device.ip || '—' }}</span>
                  <i class="fas fa-copy text-xs text-neutral-300 group-hover/ip:text-primary-500 transition-colors"></i>
                </button>
              </td>

              <td v-if="isVisible('site')" class="px-3 py-1.5 align-middle">
                <div class="flex flex-col">
                  <span class="text-sm font-medium text-neutral-700">{{ siteLabel(device) || '—' }}</span>
                </div>
              </td>

              <td v-if="isVisible('vendor')" class="px-3 py-1.5 align-middle">
                <span class="text-sm text-neutral-700 whitespace-nowrap">{{ device.vendor || '—' }}</span>
                <span class="text-xs text-neutral-500 whitespace-nowrap"> · {{ device.model || '—' }}</span>
              </td>

              <td v-if="isVisible('hostid')" class="px-3 py-1.5 text-right text-sm text-neutral-600 align-middle font-mono tabular-nums">
                {{ device.zabbix_hostid || '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="border-t border-neutral-200 px-6 py-3 bg-neutral-50 flex justify-between items-center text-xs text-neutral-500">
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
        class="fixed bottom-6 left-1/2 -translate-x-1/2 bg-surface border border-neutral-200 shadow-2xl rounded-full px-6 py-3 flex items-center gap-4 z-40"
      >
        <span class="text-sm font-medium text-neutral-600 border-r border-neutral-200 pr-4">
          <span class="text-primary-600 font-bold">{{ selectedIds.size }}</span> selecionados
        </span>
        <div class="flex gap-2">
          <button @click="openGroupModal" class="p-2 hover:bg-neutral-100 rounded-full text-neutral-600" title="Mover para grupo">
            <i class="fas fa-layer-group"></i>
          </button>
          <button @click="openStatusModal" class="p-2 hover:bg-neutral-100 rounded-full text-neutral-600" title="Modo manutenção">
            <i class="fas fa-tools"></i>
          </button>
          <div class="w-px h-4 bg-neutral-300 my-auto"></div>
          <button @click="confirmBulkDelete" class="p-2 hover:bg-danger/10 rounded-full text-danger" title="Excluir">
            <i class="fas fa-trash-alt"></i>
          </button>
        </div>
        <button @click="clearSelection" class="ml-2 text-xs text-neutral-400 hover:text-neutral-600 underline">
          Cancelar
        </button>
      </div>
    </transition>

    <!-- Modal de Grupo -->
    <div v-if="modals.group" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div class="bg-surface rounded-2xl shadow-xl w-full max-w-md overflow-hidden border border-neutral-200">
        <div class="p-6 border-b border-neutral-100 flex justify-between items-center">
          <h3 class="text-lg font-bold text-neutral-900 flex items-center gap-2">
            <i class="fas fa-layer-group text-primary-500"></i> Alterar Grupo
          </h3>
          <button @click="modals.group = false" class="text-neutral-400 hover:text-neutral-600">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="p-6">
          <p class="text-sm text-neutral-500 mb-4">
            Selecione o novo grupo para os <span class="font-bold text-neutral-900">{{ selectedIds.size }}</span> dispositivos selecionados.
          </p>
          <label class="block text-xs font-bold text-neutral-500 uppercase mb-2">Novo Grupo</label>
          <div class="relative">
            <select v-model="forms.groupTarget" class="w-full appearance-none bg-neutral-50 border border-neutral-300 text-neutral-900 rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-primary-500">
              <option value="" disabled>Selecione um grupo...</option>
              <option v-for="group in availableGroups" :key="group.id" :value="group.id">{{ group.name }}</option>
            </select>
            <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-neutral-500">
              <i class="fas fa-chevron-down text-xs"></i>
            </div>
          </div>
        </div>
        <div class="p-4 bg-neutral-50 flex justify-end gap-3">
          <button @click="modals.group = false" class="px-4 py-2 text-neutral-600 hover:bg-neutral-200 rounded-lg font-medium text-sm">Cancelar</button>
          <button
            @click="saveBulkGroup"
            :disabled="!forms.groupTarget"
            class="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium text-sm shadow-sm flex items-center gap-2"
          >
            <i class="fas fa-save"></i> Salvar Mudanças
          </button>
        </div>
      </div>
    </div>

    <!-- Modal de Status / Manutenção -->
    <div v-if="modals.status" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div class="bg-surface rounded-2xl shadow-xl w-full max-w-md overflow-hidden border border-neutral-200">
        <div class="p-6 border-b border-neutral-100">
          <h3 class="text-lg font-bold text-neutral-900 flex items-center gap-2">
            <i class="fas fa-tools text-warning"></i> Gestão de Status
          </h3>
          <p class="text-xs text-neutral-500 mt-1">
            Dispositivos: {{ selectedIds.size }} selecionados
          </p>
        </div>
        <div class="p-6 space-y-4">
          <div class="bg-info/10 p-3 rounded-lg border border-blue-100 flex gap-3">
            <i class="fas fa-info-circle text-info mt-0.5"></i>
            <p class="text-xs text-info leading-relaxed">
              O status <b>Online/Offline</b> é gerido automaticamente pelo Zabbix/SNMP. Use esta opção para definir janelas de manutenção.
            </p>
          </div>
          <div class="space-y-3">
            <label class="flex items-center p-3 border border-neutral-200 rounded-xl cursor-pointer hover:bg-neutral-50 transition-colors" :class="{'ring-2 ring-green-500 border-transparent': forms.statusTarget === 'active'}">
              <input type="radio" v-model="forms.statusTarget" value="active" class="w-4 h-4 text-success focus:ring-green-500 border-neutral-300" />
              <div class="ml-3">
                <span class="block text-sm font-bold text-neutral-900">Ativo (Monitorado)</span>
                <span class="block text-xs text-neutral-500">Alertas habilitados.</span>
              </div>
            </label>
            <label class="flex items-center p-3 border border-neutral-200 rounded-xl cursor-pointer hover:bg-neutral-50 transition-colors" :class="{'ring-2 ring-orange-500 border-transparent': forms.statusTarget === 'maintenance'}">
              <input type="radio" v-model="forms.statusTarget" value="maintenance" class="w-4 h-4 text-warning focus:ring-orange-500 border-neutral-300" />
              <div class="ml-3">
                <span class="block text-sm font-bold text-neutral-900">Em Manutenção</span>
                <span class="block text-xs text-neutral-500">Silencia alertas temporariamente.</span>
              </div>
            </label>
          </div>
        </div>
        <div class="p-4 bg-neutral-50 flex justify-end gap-3">
          <button @click="modals.status = false" class="px-4 py-2 text-neutral-600 hover:bg-neutral-200 rounded-lg font-medium text-sm">Cancelar</button>
          <button
            @click="saveBulkStatus"
            class="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium text-sm shadow-sm flex items-center gap-2"
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
  @apply bg-surface px-3 py-2 rounded-lg border border-neutral-200 flex items-center justify-between;
}
.kpi-label {
  @apply text-xs font-semibold text-neutral-500 uppercase tracking-wide;
}
.kpi-value {
  @apply text-xl font-semibold text-neutral-900 font-mono tabular-nums;
}
.kpi-icon {
  @apply p-2 rounded-md;
}
.filter-select {
  @apply px-3 py-2 rounded-lg border border-neutral-300 bg-surface text-sm text-neutral-900 focus:ring-2 focus:ring-primary-500 outline-none;
}
.th {
  @apply px-3 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wider;
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
