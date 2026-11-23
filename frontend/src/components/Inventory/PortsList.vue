<template>
  <div class="bg-surface rounded-xl shadow-sm border border-neutral-200 h-full flex flex-col">
    <div class="px-3 py-2 border-b border-neutral-100 flex items-center justify-between gap-3 flex-wrap">
      <div class="flex items-center gap-3">
        <h2 class="text-base font-semibold text-neutral-900">Portas</h2>
        <span class="text-xs px-2 py-1 rounded-full bg-neutral-100 text-neutral-600">
          {{ filtered.length }}
        </span>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <input
          v-model="search"
          type="text"
          placeholder="Buscar porta, device..."
          class="w-72 px-3 py-2 rounded-lg border border-neutral-300 bg-neutral-50 text-neutral-900 focus:ring-2 focus:ring-blue-500 focus:border-info outline-none"
        />
        <select
          v-model="deviceFilter"
          class="px-3 py-2 rounded-lg border border-neutral-300 bg-surface text-neutral-900 focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Todos os equipamentos</option>
          <option v-for="d in deviceOptions" :key="d.id" :value="d.id">
            {{ d.name }}
          </option>
        </select>
      </div>
    </div>

    <div class="flex-1 overflow-auto">
      <div v-if="loading" class="p-6 text-center text-neutral-500">Carregando portas...</div>
      <div v-else-if="error" class="p-6 text-danger">{{ error }}</div>
      <div v-else-if="filtered.length === 0" class="p-6 text-center text-neutral-500">Nenhuma porta encontrada.</div>

      <table v-else class="min-w-full text-sm">
        <thead class="bg-neutral-50 text-xs uppercase text-neutral-500">
          <tr>
            <th class="text-left px-3 py-2 whitespace-nowrap">Nome</th>
            <th class="text-left px-3 py-2 whitespace-nowrap">Dispositivo</th>
            <th class="text-left px-3 py-2 whitespace-nowrap">Site</th>
            <th class="text-left px-3 py-2 whitespace-nowrap">Chave Zabbix</th>
            <th class="text-left px-3 py-2 whitespace-nowrap">Interface ID</th>
            <th class="text-left px-3 py-2 whitespace-nowrap">Item ID</th>
            <th class="text-left px-3 py-2 whitespace-nowrap">Tráfego entrada</th>
            <th class="text-left px-3 py-2 whitespace-nowrap">Tráfego saída</th>
            <th class="text-left px-3 py-2 whitespace-nowrap">Chaves de potência</th>
            <th class="text-left px-3 py-2 whitespace-nowrap">Notas</th>
            <th class="text-left px-3 py-2 whitespace-nowrap">Ações</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          <tr v-for="port in filtered" :key="port.id" class="hover:bg-neutral-50 transition">
            <td class="px-3 py-1.5 font-medium text-neutral-900">{{ port.name }}</td>
            <td class="px-3 py-1.5 text-neutral-700">{{ port.device_name || port.device }}</td>
            <td class="px-3 py-1.5 text-neutral-700">{{ port.site_name || '—' }}</td>
            <td class="px-3 py-1.5 text-neutral-700 font-mono text-xs tabular-nums whitespace-nowrap">{{ port.zabbix_item_key || '—' }}</td>
            <td class="px-3 py-1.5 text-neutral-700 font-mono text-xs tabular-nums whitespace-nowrap">{{ port.zabbix_interfaceid || '—' }}</td>
            <td class="px-3 py-1.5 text-neutral-700 font-mono text-xs tabular-nums whitespace-nowrap">{{ port.zabbix_itemid || '—' }}</td>
            <td class="px-3 py-1.5 text-neutral-700 font-mono text-xs tabular-nums whitespace-nowrap">{{ port.zabbix_item_id_traffic_in || '—' }}</td>
            <td class="px-3 py-1.5 text-neutral-700 font-mono text-xs tabular-nums whitespace-nowrap">{{ port.zabbix_item_id_traffic_out || '—' }}</td>
            <td class="px-3 py-1.5 text-neutral-700">
              <div class="flex flex-col text-xs text-neutral-600">
                <span class="truncate">RX: {{ port.rx_power_item_key || '—' }}</span>
                <span class="truncate">TX: {{ port.tx_power_item_key || '—' }}</span>
              </div>
            </td>
            <td class="px-3 py-1.5 text-neutral-700">{{ port.notes || '—' }}</td>
            <td class="px-3 py-1.5 text-neutral-700">
              <button
                @click="openEdit(port)"
                class="inline-flex items-center justify-center h-8 w-8 rounded-lg border border-neutral-200 text-neutral-500 hover:text-info hover:border-info transition"
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
      <div class="w-full max-w-xl bg-surface rounded-2xl border border-neutral-200 shadow-xl overflow-hidden">
        <div class="px-6 py-4 border-b border-neutral-100 flex items-center justify-between">
          <div>
            <h3 class="text-base font-semibold text-neutral-900">Editar Porta</h3>
            <p class="text-xs text-neutral-500">Ajuste chaves e observações do monitoramento.</p>
          </div>
          <button @click="closeEdit" class="text-neutral-400 hover:text-neutral-600">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="p-6 space-y-4">
          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <label class="text-xs font-semibold text-neutral-600">Porta</label>
              <div class="mt-1 text-sm text-neutral-900">{{ editForm.name }}</div>
            </div>
            <div>
              <label class="text-xs font-semibold text-neutral-600">Device</label>
              <div class="mt-1 text-sm text-neutral-900">{{ editForm.device_name }}</div>
            </div>
          </div>
          <div>
            <label class="text-xs font-semibold text-neutral-600">Zabbix Key</label>
            <input
              v-model="editForm.zabbix_item_key"
              type="text"
              class="mt-1 w-full px-3 py-2 rounded-lg border border-neutral-300 bg-neutral-50 text-neutral-900 text-sm outline-none"
              placeholder="ifOperStatus..."
            />
          </div>
          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <label class="text-xs font-semibold text-neutral-600">RX Power Key</label>
              <input
                v-model="editForm.rx_power_item_key"
                type="text"
                class="mt-1 w-full px-3 py-2 rounded-lg border border-neutral-300 bg-neutral-50 text-neutral-900 text-sm outline-none"
                placeholder="rxPowerKey..."
              />
            </div>
            <div>
              <label class="text-xs font-semibold text-neutral-600">TX Power Key</label>
              <input
                v-model="editForm.tx_power_item_key"
                type="text"
                class="mt-1 w-full px-3 py-2 rounded-lg border border-neutral-300 bg-neutral-50 text-neutral-900 text-sm outline-none"
                placeholder="txPowerKey..."
              />
            </div>
          </div>
          <div>
            <label class="text-xs font-semibold text-neutral-600">Notas</label>
            <textarea
              v-model="editForm.notes"
              rows="3"
              class="mt-1 w-full px-3 py-2 rounded-lg border border-neutral-300 bg-neutral-50 text-neutral-900 text-sm outline-none resize-none"
              placeholder="Observações sobre esta porta"
            ></textarea>
          </div>
        </div>
        <div class="px-6 py-4 border-t border-neutral-100 flex items-center justify-end gap-3">
          <button @click="closeEdit" class="px-4 py-2 text-sm text-neutral-600 hover:bg-neutral-100 rounded-lg">Cancelar</button>
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
