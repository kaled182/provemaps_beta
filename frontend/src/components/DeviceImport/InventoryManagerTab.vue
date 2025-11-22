<template>
  <div class="space-y-6">
    <div class="relative">
      <input 
        v-model="search"
        type="text" 
        placeholder="Filtrar dispositivos ou grupos..." 
        class="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
      >
      <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <i class="fas fa-search text-gray-400 dark:text-gray-500"></i>
      </div>
    </div>

    <div v-for="group in filteredGroups" :key="group.group_id" class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden shadow-sm">
      <div 
        @click="toggleGroup(group.group_id)"
        class="px-4 py-3 bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer flex justify-between items-center transition-colors"
      >
        <div class="flex items-center space-x-3">
          <i class="fas fa-layer-group text-indigo-500 dark:text-indigo-400"></i>
          <span class="font-semibold text-gray-800 dark:text-gray-100">{{ group.group_name }}</span>
          <span class="bg-indigo-100 dark:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300 text-xs font-medium px-2.5 py-0.5 rounded-full">
            {{ group.devices.length }}
          </span>
        </div>
        <i 
          class="fas fa-chevron-down transition-transform duration-200 text-gray-400 dark:text-gray-500"
          :class="{ 'transform rotate-180': !collapsedGroups.includes(group.group_id) }"
        ></i>
      </div>

      <div v-show="!collapsedGroups.includes(group.group_id)" class="border-t border-gray-200 dark:border-gray-700">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-700/30">
            <tr>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Nome / IP</th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Configuração de Avisos</th>
              <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Ações</th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-for="device in group.devices" :key="device.id" class="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
              <td class="px-6 py-4 whitespace-nowrap w-10">
                <div 
                  class="h-2.5 w-2.5 rounded-full" 
                  :class="{
                    'bg-green-500': device.status === 'online',
                    'bg-red-500': device.status === 'offline',
                    'bg-yellow-500': device.status === 'warning'
                  }"
                  :title="device.status"
                ></div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ device.name }}</div>
                <div class="text-sm text-gray-500 dark:text-gray-400">{{ device.ip }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center space-x-4">
                  <div 
                    class="flex items-center space-x-1 px-2 py-1 rounded"
                    :class="device.alerts.whatsapp ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-700' : 'text-gray-300 dark:text-gray-600 opacity-50'"
                  >
                    <i class="fab fa-whatsapp"></i>
                    <span class="text-xs hidden md:inline">Zap</span>
                  </div>
                  <div 
                    class="flex items-center space-x-1 px-2 py-1 rounded"
                    :class="device.alerts.email ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-700' : 'text-gray-300 dark:text-gray-600 opacity-50'"
                  >
                    <i class="far fa-envelope"></i>
                    <span class="text-xs hidden md:inline">Email</span>
                  </div>
                  <div 
                    class="flex items-center space-x-1 px-2 py-1 rounded"
                    :class="device.alerts.screen ? 'bg-orange-50 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 border border-orange-200 dark:border-orange-700' : 'text-gray-300 dark:text-gray-600 opacity-50'"
                  >
                    <i class="fas fa-desktop"></i>
                    <span class="text-xs hidden md:inline">Tela</span>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button 
                  @click="$emit('edit-device', device, false)" 
                  class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/30 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 px-3 py-1 rounded transition-colors"
                >
                  <i class="fas fa-cog mr-1"></i> Configurar
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="filteredGroups.length === 0" class="text-center py-12">
      <i class="fas fa-inbox text-gray-400 dark:text-gray-600 text-4xl mb-3"></i>
      <p class="text-gray-500 dark:text-gray-400">Nenhum dispositivo encontrado</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  data: {
    type: Array,
    required: true
  }
});

const emit = defineEmits(['edit-device']);

const search = ref('');
const collapsedGroups = ref([]); // IDs dos grupos fechados

const toggleGroup = (id) => {
  if (collapsedGroups.value.includes(id)) {
    collapsedGroups.value = collapsedGroups.value.filter(gId => gId !== id);
  } else {
    collapsedGroups.value.push(id);
  }
};

const filteredGroups = computed(() => {
  if (!search.value) return props.data;
  
  const term = search.value.toLowerCase();
  return props.data.map(group => {
    // Filtra dispositivos dentro do grupo
    const filteredDevices = group.devices.filter(d => 
      d.name.toLowerCase().includes(term) || 
      d.ip.includes(term)
    );
    
    // Se o nome do grupo der match, mostra tudo, senão mostra só os devices filtrados
    const groupMatch = group.group_name.toLowerCase().includes(term);
    
    if (groupMatch) return group;
    
    return {
      ...group,
      devices: filteredDevices
    };
  }).filter(g => g.devices.length > 0 || g.group_name.toLowerCase().includes(term));
});
</script>
