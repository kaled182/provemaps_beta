<template>
  <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 h-full flex flex-col">
    <div class="p-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Fiber Cables</h2>
        <span class="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
          {{ filtered.length }}
        </span>
      </div>
      <input
        v-model="search"
        type="text"
        placeholder="Buscar cabo..."
        class="w-72 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
      />
    </div>

    <div class="flex-1 overflow-auto">
      <div v-if="loading" class="p-6 text-center text-gray-500 dark:text-gray-400">Carregando cabos...</div>
      <div v-else-if="error" class="p-6 text-red-600 dark:text-red-300">{{ error }}</div>
      <div v-else-if="filtered.length === 0" class="p-6 text-center text-gray-500 dark:text-gray-400">Nenhum cabo encontrado.</div>

      <table v-else class="min-w-full text-sm">
        <thead class="bg-gray-50 dark:bg-gray-800/60 text-xs uppercase text-gray-500 dark:text-gray-300">
          <tr>
            <th class="text-left px-4 py-2">Nome</th>
            <th class="text-left px-4 py-2">Origem</th>
            <th class="text-left px-4 py-2">Destino</th>
            <th class="text-left px-4 py-2">Comprimento (km)</th>
            <th class="text-left px-4 py-2">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
          <tr v-for="cable in filtered" :key="cable.id" class="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition">
            <td class="px-4 py-2 font-medium text-gray-900 dark:text-white">{{ cable.name }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ cable.origin_site_name || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ cable.destination_site_name || '—' }}</td>
            <td class="px-4 py-2 text-gray-700 dark:text-gray-300">{{ cable.length_km ?? '—' }}</td>
            <td class="px-4 py-2">
              <span class="px-2 py-1 rounded-full text-xs font-semibold"
                :class="cable.status === 'up' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'">
                {{ cable.status || 'N/D' }}
              </span>
            </td>
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
const cables = ref([]);
const search = ref('');

const filtered = computed(() => {
  const q = search.value.toLowerCase().trim();
  return cables.value.filter((c) => {
    const name = (c.name || '').toLowerCase();
    const origin = (c.origin_site_name || '').toLowerCase();
    const dest = (c.destination_site_name || '').toLowerCase();
    return !q || name.includes(q) || origin.includes(q) || dest.includes(q);
  });
});

const fetchCables = async () => {
  loading.value = true;
  error.value = '';
  try {
    const data = await api.get('/api/v1/fiber-cables/');
    cables.value = Array.isArray(data) ? data : data.results || [];
  } catch (err) {
    console.error('Erro ao carregar cabos', err);
    error.value = err.message || 'Erro ao carregar cabos.';
  } finally {
    loading.value = false;
  }
};

onMounted(fetchCables);
</script>
