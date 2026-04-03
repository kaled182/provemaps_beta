<template>
  <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 h-full flex flex-col">
    <div class="p-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between gap-4 flex-wrap">
      <div class="flex items-center gap-3">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Ports</h2>
        <span class="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
          {{ filtered.length }}
        </span>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <input
          v-model="search"
          type="text"
          placeholder="Buscar porta, device..."
          class="w-72 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
        />
        <select
          v-model="deviceFilter"
          class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Todos os equipamentos</option>
          <option v-for="d in deviceOptions" :key="d.id" :value="d.id">
            {{ d.name }}
          </option>
        </select>
      </div>
    </div>

    <div class="flex-1 overflow-auto">
      <div v-if="loading" class="p-6 text-center text-gray-500 dark:text-gray-400">Carregando portas...</div>
      <div v-else-if="error" class="p-6 text-red-600 dark:text-red-300">{{ error }}</div>
      <div v-else-if="filtered.length === 0" class="p-6 text-center text-gray-500 dark:text-gray-400">Nenhuma porta encontrada.</div>

      <table v-else class="min-w-full text-sm">
        <thead class="bg-gray-50 dark:bg-gray-800/60 text-xs uppercase text-gray-500 dark:text-gray-300">
          <tr>
            <th class="text-left px-4 py-2">Nome</th>
            <th class="text-left px-4 py-2">Device</th>
            <th class="text-left px-4 py-2">Site</th>
            <th class="text-left px-4 py-2">Zabbix Key</th>
            <th class="text-left px-4 py-2">InterfaceID</th>
            <th class="text-left px-4 py-2">ItemID</th>
            <th class="text-left px-4 py-2">Traffic In</th>
            <th class="text-left px-4 py-2">Traffic Out</th>
            <th class="text-left px-4 py-2">Power Keys</th>
            <th class="text-left px-4 py-2">Notas</th>
            <th class="text-left px-4 py-2">Ações</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
          <tr v-for="port in filtered" :key="port.id" class="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition">
            <td class="px-4 py-2 font-medium text-gray-900 dark:text-white">{{ port.name }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ port.device_name || port.device }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ port.site_name || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ port.zabbix_item_key || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ port.zabbix_interfaceid || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ port.zabbix_itemid || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ port.zabbix_item_id_traffic_in || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ port.zabbix_item_id_traffic_out || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">
              <div class="flex flex-col text-xs text-gray-600 dark:text-gray-400">
                <span class="truncate">RX: {{ port.rx_power_item_key || '—' }}</span>
                <span class="truncate">TX: {{ port.tx_power_item_key || '—' }}</span>
              </div>
            </td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ port.notes || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">
              <button
                @click="openEdit(port)"
                class="inline-flex items-center justify-center h-8 w-8 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-500 hover:text-blue-600 hover:border-blue-400 transition"
                title="Editar porta"
              >
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-2.586-9.586a2 2 0 112.828 2.828L11 15l-4 1 1-4 8.414-8.414z"/></svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showEditModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div class="w-full max-w-xl bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-xl overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
          <div>
            <h3 class="text-base font-semibold text-gray-900 dark:text-white">Editar Porta</h3>
            <p class="text-xs text-gray-500 dark:text-gray-400">Ajuste chaves e observações do monitoramento.</p>
          </div>
          <button @click="closeEdit" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="p-6 space-y-4">
          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <label class="text-xs font-semibold text-gray-600 dark:text-gray-300">Porta</label>
              <div class="mt-1 text-sm text-gray-900 dark:text-gray-200">{{ editForm.name }}</div>
            </div>
            <div>
              <label class="text-xs font-semibold text-gray-600 dark:text-gray-300">Device</label>
              <div class="mt-1 text-sm text-gray-900 dark:text-gray-200">{{ editForm.device_name }}</div>
            </div>
          </div>
          <div>
            <label class="text-xs font-semibold text-gray-600 dark:text-gray-300">Zabbix Key</label>
            <input
              v-model="editForm.zabbix_item_key"
              type="text"
              class="mt-1 w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white text-sm outline-none"
              placeholder="ifOperStatus..."
            />
          </div>
          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <label class="text-xs font-semibold text-gray-600 dark:text-gray-300">RX Power Key</label>
              <input
                v-model="editForm.rx_power_item_key"
                type="text"
                class="mt-1 w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white text-sm outline-none"
                placeholder="rxPowerKey..."
              />
            </div>
            <div>
              <label class="text-xs font-semibold text-gray-600 dark:text-gray-300">TX Power Key</label>
              <input
                v-model="editForm.tx_power_item_key"
                type="text"
                class="mt-1 w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white text-sm outline-none"
                placeholder="txPowerKey..."
              />
            </div>
          </div>
          <div>
            <label class="text-xs font-semibold text-gray-600 dark:text-gray-300">Notas</label>
            <textarea
              v-model="editForm.notes"
              rows="3"
              class="mt-1 w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white text-sm outline-none resize-none"
              placeholder="Observações sobre esta porta"
            ></textarea>
          </div>
        </div>
        <div class="px-6 py-4 border-t border-gray-100 dark:border-gray-700 flex items-center justify-end gap-3">
          <button @click="closeEdit" class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">Cancelar</button>
          <button @click="saveEdit" class="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg">
            Salvar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useApi } from '@/composables/useApi';

const api = useApi();
const loading = ref(false);
const error = ref('');
const ports = ref([]);
const search = ref('');
const deviceOptions = ref([]);
const deviceFilter = ref('');
const showEditModal = ref(false);
const editForm = ref({
  id: null,
  name: '',
  device_name: '',
  zabbix_item_key: '',
  rx_power_item_key: '',
  tx_power_item_key: '',
  notes: '',
});

const filtered = computed(() => {
  const q = search.value.toLowerCase().trim();
  return ports.value.filter((p) => {
    const name = (p.name || '').toLowerCase();
    const device = (p.device_name || '').toLowerCase();
    const site = (p.site_name || '').toLowerCase();
    const matchesQuery = !q || name.includes(q) || device.includes(q) || site.includes(q);
    const matchesDevice = !deviceFilter.value || String(p.device) === String(deviceFilter.value);
    return matchesQuery && matchesDevice;
  });
});

const fetchPorts = async () => {
  loading.value = true;
  error.value = '';
  const accumulated = [];
  let nextUrl = '/api/v1/ports/';

  try {
    while (nextUrl) {
      const data = await api.get(nextUrl);
      const page = Array.isArray(data) ? data : data.results || [];
      accumulated.push(...page);
      const nxt = data.next;
      if (nxt) {
        // normaliza para caminho relativo (DRF retorna URL absoluta)
        const parsed = new URL(nxt, window.location.origin);
        nextUrl = `${parsed.pathname}${parsed.search}`;
      } else {
        nextUrl = '';
      }
    }
    ports.value = accumulated;
  } catch (err) {
    console.error('Erro ao carregar portas', err);
    error.value = err.message || 'Erro ao carregar portas.';
  } finally {
    loading.value = false;
  }
};

const fetchDeviceOptions = async () => {
  try {
    const data = await api.get('/api/v1/devices/');
    const list = Array.isArray(data) ? data : data.results || [];
    deviceOptions.value = list.map((d) => ({ id: d.id, name: d.name }));
  } catch (err) {
    console.error('Erro ao carregar devices para filtro', err);
  }
};

onMounted(async () => {
  await Promise.all([fetchPorts(), fetchDeviceOptions()]);
});

const openEdit = (port) => {
  editForm.value = {
    id: port.id,
    name: port.name || '',
    device_name: port.device_name || port.device || '',
    zabbix_item_key: port.zabbix_item_key || '',
    rx_power_item_key: port.rx_power_item_key || '',
    tx_power_item_key: port.tx_power_item_key || '',
    notes: port.notes || '',
  };
  showEditModal.value = true;
};

const closeEdit = () => {
  showEditModal.value = false;
};

const saveEdit = async () => {
  if (!editForm.value.id) return;
  try {
    await api.patch(`/api/v1/ports/${editForm.value.id}/`, {
      zabbix_item_key: editForm.value.zabbix_item_key,
      rx_power_item_key: editForm.value.rx_power_item_key,
      tx_power_item_key: editForm.value.tx_power_item_key,
      notes: editForm.value.notes,
    });
    showEditModal.value = false;
    await fetchPorts();
  } catch (err) {
    console.error('Erro ao salvar porta', err);
  }
};
</script>
