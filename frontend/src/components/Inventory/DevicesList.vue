<template>
  <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 h-full flex flex-col">
    <div class="p-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Devices</h2>
        <span class="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
          {{ filtered.length }}
        </span>
      </div>
      <input
        v-model="search"
        type="text"
        placeholder="Buscar device, site, IP..."
        class="w-72 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
      />
    </div>

    <div class="flex-1 overflow-auto">
      <div v-if="loading" class="p-6 text-center text-gray-500 dark:text-gray-400">Carregando devices...</div>
      <div v-else-if="error" class="p-6 text-red-600 dark:text-red-300">{{ error }}</div>
      <div v-else-if="filtered.length === 0" class="p-6 text-center text-gray-500 dark:text-gray-400">Nenhum device encontrado.</div>

      <table v-else class="min-w-full text-sm">
        <thead class="bg-gray-50 dark:bg-gray-800/60 text-xs uppercase text-gray-500 dark:text-gray-300">
          <tr>
            <th class="text-left px-4 py-2">Nome</th>
            <th class="text-left px-4 py-2">Site</th>
            <th class="text-left px-4 py-2">Vendor</th>
            <th class="text-left px-4 py-2">Modelo</th>
            <th class="text-left px-4 py-2">IP</th>
            <th class="text-left px-4 py-2">HostID</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
          <tr v-for="device in filtered" :key="device.id" class="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition">
            <td class="px-4 py-2 font-medium text-gray-900 dark:text-white">{{ device.name }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ device.site_name || device.site }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ device.vendor || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ device.model || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ device.primary_ip || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ device.zabbix_hostid || '—' }}</td>
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
const devices = ref([]);
const search = ref('');

const filtered = computed(() => {
  const q = search.value.toLowerCase().trim();
  return devices.value.filter((d) => {
    const name = (d.name || '').toLowerCase();
    const site = (d.site_name || '').toLowerCase();
    const ip = (d.primary_ip || '').toLowerCase();
    return !q || name.includes(q) || site.includes(q) || ip.includes(q);
  });
});

const fetchDevices = async () => {
  loading.value = true;
  error.value = '';
  try {
    const data = await api.get('/api/v1/devices/');
    devices.value = Array.isArray(data) ? data : data.results || [];
  } catch (err) {
    console.error('Erro ao carregar devices', err);
    error.value = err.message || 'Erro ao carregar devices.';
  } finally {
    loading.value = false;
  }
};

onMounted(fetchDevices);
</script>
