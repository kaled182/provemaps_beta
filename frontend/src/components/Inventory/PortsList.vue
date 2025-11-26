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
            <th class="text-left px-4 py-2">RX Power Key</th>
            <th class="text-left px-4 py-2">TX Power Key</th>
            <th class="text-left px-4 py-2">Notas</th>
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
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ port.rx_power_item_key || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ port.tx_power_item_key || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ port.notes || '—' }}</td>
          </tr>
        </tbody>
      </table>
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
</script>
