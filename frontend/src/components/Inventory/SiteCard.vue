<template>
  <div
    class="group bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 flex flex-col overflow-hidden cursor-pointer h-full border-l-4"
    :class="statusBorderClass"
  >
    <div :class="['h-1.5 w-full', statusColor]"></div>

    <div class="p-5 flex-1 flex flex-col">
      <div class="flex justify-between items-start mb-3">
        <div class="flex items-center gap-3">
          <div :class="['w-10 h-10 rounded-lg flex items-center justify-center text-lg', iconBgColor]">
            <i :class="['fas', iconClass]"></i>
          </div>
          <div>
            <h3 class="text-base font-bold text-gray-900 dark:text-white leading-tight group-hover:text-blue-600 transition-colors">
              {{ site.name }}
            </h3>
            <span class="text-xs text-gray-400 uppercase font-semibold tracking-wider">{{ site.type }}</span>
          </div>
        </div>
        <span
          class="text-xs px-2 py-1 rounded-full font-semibold"
          :class="statusBadgeClass"
        >
          {{ site.status || 'N/D' }}
        </span>
        <div class="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
          <button
            @click.stop="$emit('edit', site)"
            class="p-1.5 text-gray-400 hover:text-blue-600 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors"
            title="Editar"
          >
            <i class="fas fa-pencil-alt"></i>
          </button>
          <button
            @click.stop="$emit('delete', site)"
            class="p-1.5 text-gray-400 hover:text-red-600 rounded-md hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors"
            title="Remover"
          >
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>

      <div class="mt-2 space-y-2 flex-1">
        <div class="flex items-start gap-2 text-sm text-gray-500 dark:text-gray-400 min-h-[40px]">
          <i class="fas fa-map-marker-alt mt-1 text-gray-300"></i>
          <span class="line-clamp-2">{{ site.address || 'Sem endereço definido' }}</span>
        </div>
      </div>

      <div class="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 flex justify-between items-center">
        <div class="flex items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-300">
          <i class="fas fa-server text-gray-400"></i>
          {{ site.device_count }} <span class="text-xs font-normal text-gray-400">Devices</span>
        </div>
        <button
          @click.stop="$emit('view', site)"
          class="text-xs font-medium text-blue-600 hover:underline"
        >
          Ver Detalhes
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  site: { type: Object, required: true },
});

const statusColors = {
  active: 'green',
  maintenance: 'orange',
  inactive: 'red',
  down: 'red',
  planning: 'blue',
};

const statusColor = computed(() => {
  return props.site.status === 'active' ? 'bg-green-500' : 'bg-gray-300';
});

const statusBorderClass = computed(() => {
  const color = statusColors[props.site.status?.toLowerCase()] || 'gray';
  return `border-${color}-500 dark:border-${color}-500`;
});

const statusBadgeClass = computed(() => {
  const color = statusColors[props.site.status?.toLowerCase()] || 'gray';
  return `bg-${color}-100 text-${color}-700 dark:bg-${color}-900/30 dark:text-${color}-300`;
});

const iconClass = computed(() => {
  switch (props.site.type) {
    case 'datacenter':
      return 'fa-database';
    case 'pop':
      return 'fa-network-wired';
    case 'customer':
      return 'fa-building';
    default:
      return 'fa-map-pin';
  }
});

const iconBgColor = computed(() => {
  switch (props.site.type) {
    case 'datacenter':
      return 'bg-purple-100 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400';
    case 'pop':
      return 'bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400';
    case 'customer':
      return 'bg-green-100 text-green-600 dark:bg-green-900/20 dark:text-green-400';
    default:
      return 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';
  }
});
</script>
