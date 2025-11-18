<template>
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-medium text-gray-600 dark:text-gray-400 uppercase">
        {{ displayName }}
      </h3>
      <span class="text-2xl">{{ statusIcon }}</span>
    </div>
    
    <div class="space-y-2">
      <div class="flex items-center gap-2">
        <span
          :class="[
            'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
            statusClass
          ]"
        >
          {{ statusText }}
        </span>
      </div>
      
      <div v-if="data.version" class="text-sm text-gray-600 dark:text-gray-400">
        Version: <span class="font-mono">{{ data.version }}</span>
      </div>
      
      <div v-if="data.response_time_ms !== undefined" class="text-sm text-gray-600 dark:text-gray-400">
        Response: <span class="font-mono">{{ data.response_time_ms }}ms</span>
      </div>
      
      <div v-if="data.workers !== undefined" class="text-sm text-gray-600 dark:text-gray-400">
        Workers: <span class="font-mono">{{ data.workers }}</span>
      </div>
      
      <div v-if="data.active_tasks !== undefined" class="text-sm text-gray-600 dark:text-gray-400">
        Active Tasks: <span class="font-mono">{{ data.active_tasks }}</span>
      </div>
      
      <div v-if="data.connected_clients !== undefined" class="text-sm text-gray-600 dark:text-gray-400">
        Clients: <span class="font-mono">{{ data.connected_clients }}</span>
      </div>
      
      <div v-if="data.used_memory_human" class="text-sm text-gray-600 dark:text-gray-400">
        Memory: <span class="font-mono">{{ data.used_memory_human }}</span>
      </div>
      
      <div v-if="data.error" class="mt-2 text-xs text-red-600 dark:text-red-400 font-mono">
        {{ data.error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  name: {
    type: String,
    required: true,
  },
  data: {
    type: Object,
    required: true,
  },
});

const displayName = computed(() => {
  const names = {
    redis: 'Redis Cache',
    postgresql: 'PostgreSQL',
    zabbix: 'Zabbix',
    celery: 'Celery Workers',
  };
  return names[props.name] || props.name;
});

const statusIcon = computed(() => {
  const status = props.data.status;
  if (status === 'online') return '🟢';
  if (status === 'offline') return '🔴';
  if (status === 'not_configured') return '⚪';
  return '⚫';
});

const statusText = computed(() => {
  const status = props.data.status;
  if (status === 'online') return 'Online';
  if (status === 'offline') return 'Offline';
  if (status === 'not_configured') return 'Not Configured';
  return 'Unknown';
});

const statusClass = computed(() => {
  const status = props.data.status;
  if (status === 'online') {
    return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
  }
  if (status === 'offline') {
    return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
  }
  if (status === 'not_configured') {
    return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  }
  return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
});
</script>
