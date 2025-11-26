<template>
  <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 h-full flex flex-col">
    <div class="p-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Device Groups</h2>
        <span class="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
          {{ filtered.length }}
        </span>
      </div>
      <input
        v-model="search"
        type="text"
        placeholder="Buscar grupo..."
        class="w-64 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
      />
    </div>

    <div class="flex-1 overflow-auto">
      <div v-if="loading" class="p-6 text-center text-gray-500 dark:text-gray-400">Carregando grupos...</div>
      <div v-else-if="error" class="p-6 text-red-600 dark:text-red-300">{{ error }}</div>
      <div v-else-if="filtered.length === 0" class="p-6 text-center text-gray-500 dark:text-gray-400">Nenhum grupo encontrado.</div>
      <ul v-else class="divide-y divide-gray-100 dark:divide-gray-700">
        <li v-for="group in filtered" :key="group.id" class="px-4 py-3 flex items-center justify-between">
          <span class="text-gray-900 dark:text-white font-medium">{{ group.name }}</span>
          <span class="text-xs text-gray-500 dark:text-gray-400">ID: {{ group.id }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useApi } from '@/composables/useApi';

const api = useApi();
const loading = ref(false);
const error = ref('');
const groups = ref([]);
const search = ref('');

const filtered = computed(() => {
  const q = search.value.toLowerCase().trim();
  return groups.value.filter((g) => !q || (g.name || '').toLowerCase().includes(q));
});

const fetchGroups = async () => {
  loading.value = true;
  error.value = '';
  try {
    const data = await api.get('/api/v1/device-groups/');
    groups.value = Array.isArray(data) ? data : data.results || [];
  } catch (err) {
    console.error('Erro ao carregar device groups', err);
    error.value = err.message || 'Erro ao carregar device groups.';
  } finally {
    loading.value = false;
  }
};

onMounted(fetchGroups);
</script>
