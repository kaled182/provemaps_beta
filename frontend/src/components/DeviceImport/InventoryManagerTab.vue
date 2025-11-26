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

    <!-- Container único com scroll - EXATAMENTE como Sincronização -->
    <div class="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md max-h-[600px] overflow-y-auto">
      <ul class="divide-y divide-gray-200 dark:divide-gray-700">
        <li v-for="group in filteredGroups" :key="group.group_id" class="group-container">
          
          <!-- Cabeçalho do Grupo -->
          <div 
            @click="toggleGroup(group.group_id)"
            class="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <div class="flex items-center">
              <i 
                class="fas fa-chevron-right text-gray-400 dark:text-gray-500 mr-3 transition-transform duration-200"
                :class="{ 'rotate-90': !collapsedGroups.includes(group.group_id) }"
              ></i>
              <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ group.group_name }}</span>
              <span class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-200">
                {{ group.devices.length }}
              </span>
            </div>
            <i 
              class="fas fa-chevron-down transition-transform duration-200 text-gray-400 dark:text-gray-500"
              :class="{ 'transform rotate-180': !collapsedGroups.includes(group.group_id) }"
            ></i>
          </div>

          <!-- Tabela de Dispositivos -->
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
                <div class="flex items-center space-x-2">
                  <!-- Status Zabbix -->
                  <div 
                    class="h-2.5 w-2.5 rounded-full" 
                    :class="{
                      'bg-green-500': getDeviceStatus(device.id) === 'online',
                      'bg-red-500': getDeviceStatus(device.id) === 'offline',
                      'bg-yellow-500': getDeviceStatus(device.id) === 'disabled',
                      'bg-gray-400': getDeviceStatus(device.id) === 'unknown'
                    }"
                    :title="getStatusLabel(getDeviceStatus(device.id))"
                  ></div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ device.name }}</div>
                <div class="text-sm text-gray-500 dark:text-gray-400">
                  {{ device.primary_ip || '(sem IP)' }}
                </div>
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
                <div class="flex items-center justify-end space-x-2">
                  <button 
                    v-if="device.zabbix_hostid"
                    @click="$emit('view-interfaces', device)" 
                    class="text-blue-600 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300 bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/50 px-3 py-1 rounded transition-colors"
                    title="Ver interfaces do dispositivo"
                  >
                    <i class="fas fa-network-wired mr-1"></i> Interfaces
                  </button>
                  <button 
                    @click="$emit('edit-device', device, false)" 
                    class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/30 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 px-3 py-1 rounded transition-colors"
                    title="Configurar dispositivo"
                  >
                    <i class="fas fa-cog mr-1"></i> Configurar
                  </button>
                  <button 
                    @click="$emit('delete-device', device)" 
                    class="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300 bg-red-50 dark:bg-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/50 px-3 py-1 rounded transition-colors"
                    title="Excluir dispositivo"
                  >
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </li>

    <!-- Empty state -->
    <li v-if="filteredGroups.length === 0" class="text-center py-12">
      <i class="fas fa-inbox text-gray-400 dark:text-gray-600 text-4xl mb-3"></i>
      <p class="text-gray-500 dark:text-gray-400">Nenhum dispositivo encontrado</p>
    </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useApi } from '@/composables/useApi';

const props = defineProps({
  data: {
    type: Array,
    required: true
  }
});

const emit = defineEmits(['edit-device', 'delete-device', 'view-interfaces']);

const api = useApi();
const search = ref('');
const collapsedGroups = ref([]); // IDs dos grupos fechados

// Estado para ping status - usando objeto reativo ao invés de Map
const pingStatus = ref({});

// Estado para status Zabbix
const zabbixStatus = ref({});

// Helper functions para acessar ping status
const getPingStatus = (deviceId) => {
  return pingStatus.value[deviceId]?.status || null;
};

const getPingLatency = (deviceId) => {
  const latency = pingStatus.value[deviceId]?.latency;
  return latency ? latency.toFixed(0) : 0;
};

const getStatusLabel = (status) => {
  const labels = {
    online: 'Online (Zabbix)',
    offline: 'Offline (Zabbix)',
    disabled: 'Desabilitado no Zabbix',
    unknown: 'Status Desconhecido'
  };
  return labels[status] || 'Desconhecido';
};

const getDeviceStatus = (deviceId) => {
  return zabbixStatus.value[deviceId] || 'unknown';
};

// Função para buscar status do Zabbix em batch
const fetchZabbixStatus = async () => {
  const allDeviceIds = [];
  
  // Coletar todos os device IDs
  props.data.forEach(group => {
    group.devices.forEach(device => {
      allDeviceIds.push(device.id);
    });
  });
  
  if (allDeviceIds.length === 0) return;
  
  try {
    const response = await api.get(`/api/v1/inventory/devices/zabbix-status/?device_ids=${allDeviceIds.join(',')}`);
    
    if (response.statuses) {
      zabbixStatus.value = response.statuses;
    }
  } catch (error) {
    console.error('Erro ao buscar status Zabbix:', error);
  }
};

// Lifecycle - buscar status Zabbix
onMounted(() => {
  fetchZabbixStatus();
});

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

<style scoped>
/* Custom scrollbar - IDÊNTICO à aba Sincronização */
.max-h-\[600px\]::-webkit-scrollbar {
  width: 6px;
}

.max-h-\[600px\]::-webkit-scrollbar-track {
  background: transparent;
}

.max-h-\[600px\]::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.3);
  border-radius: 3px;
}

.max-h-\[600px\]::-webkit-scrollbar-thumb:hover {
  background: rgba(156, 163, 175, 0.5);
}

/* Dark mode scrollbar */
.dark .max-h-\[600px\]::-webkit-scrollbar-thumb {
  background: rgba(75, 85, 99, 0.3);
}

.dark .max-h-\[600px\]::-webkit-scrollbar-thumb:hover {
  background: rgba(75, 85, 99, 0.5);
}

/* Firefox scrollbar */
.max-h-\[600px\] {
  scrollbar-width: thin;
  scrollbar-color: rgba(156, 163, 175, 0.3) transparent;
}

.dark .max-h-\[600px\] {
  scrollbar-color: rgba(75, 85, 99, 0.3) transparent;
}
</style>
