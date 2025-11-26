<template>
  <div
    class="group bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-500 shadow-sm hover:shadow-md transition-all duration-200 flex flex-col h-full cursor-pointer relative overflow-hidden"
  >
    <div class="h-1.5 w-full bg-gradient-to-r from-blue-500 to-indigo-600 opacity-80"></div>

    <div class="p-5 flex-1 flex flex-col">
      <div class="flex justify-between items-start mb-3">
        <div class="p-2.5 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded-lg">
          <i class="fas fa-layer-group text-lg"></i>
        </div>

        <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            @click.stop="$emit('edit', group)"
            class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md transition-colors"
          >
            <i class="fas fa-pencil-alt"></i>
          </button>
          <button
            @click.stop="$emit('delete', group)"
            class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors"
          >
            <i class="fas fa-trash-alt"></i>
          </button>
        </div>
      </div>

      <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-1 truncate">{{ group.name }}</h3>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4 line-clamp-2 min-h-[2.5rem]">
        {{ group.description || 'Sem descrição definida.' }}
      </p>

      <div class="mt-auto pt-4 border-t border-gray-100 dark:border-gray-700">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Membros</span>
          <span class="text-xs font-bold bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded-full">
            {{ group.device_count || 0 }}
          </span>
        </div>

        <div class="flex -space-x-2 overflow-hidden py-1">
          <template v-if="(group.device_count || 0) > 0">
            <div
              v-for="i in Math.min(group.device_count, 4)"
              :key="i"
              class="inline-block h-6 w-6 rounded-full ring-2 ring-white dark:ring-gray-800 bg-gray-200 dark:bg-gray-600 flex items-center justify-center text-[10px] text-gray-500 font-bold"
            >
              <i class="fas fa-server"></i>
            </div>
            <div
              v-if="group.device_count > 4"
              class="inline-block h-6 w-6 rounded-full ring-2 ring-white dark:ring-gray-800 bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-[9px] text-gray-500 font-bold"
            >
              +{{ group.device_count - 4 }}
            </div>
          </template>
          <span v-else class="text-xs text-gray-400 italic">Nenhum dispositivo</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ group: { type: Object, required: true } });
defineEmits(['edit', 'delete']);
</script>
