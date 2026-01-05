<template>
  <div class="space-y-6">
    <div class="relative">
      <input 
        v-model="search"
        type="text" 
        placeholder="Filtrar dispositivos ou grupos..." 
        class="w-full pl-10 pr-4 py-2 app-input"
      >
      <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <i class="fas fa-search app-text-tertiary"></i>
      </div>
    </div>

    <!-- Container único com scroll - EXATAMENTE como Sincronização -->
    <div class="app-surface overflow-hidden sm:rounded-md max-h-[600px] overflow-y-auto">
      <ul class="divide-y app-divide">
        <li v-for="group in filteredGroups" :key="group.group_id" class="group-container">
          
          <!-- Cabeçalho do Grupo -->
          <div 
            @click="toggleGroup(group.group_id)"
            class="app-surface-muted px-4 py-3 flex items-center justify-between cursor-pointer app-row transition-colors"
          >
            <div class="flex items-center">
              <i 
                class="fas fa-chevron-right app-text-tertiary mr-3 transition-transform duration-200"
                :class="{ 'rotate-90': !collapsedGroups.includes(group.group_id) }"
              ></i>
              <span class="text-sm font-bold app-text-primary">{{ group.group_name }}</span>
              <span class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium app-chip">
                {{ group.devices.length }}
              </span>
            </div>
            <i 
              class="fas fa-chevron-down transition-transform duration-200 app-text-tertiary"
              :class="{ 'transform rotate-180': !collapsedGroups.includes(group.group_id) }"
            ></i>
          </div>

          <!-- Tabela de Dispositivos -->
          <div v-show="!collapsedGroups.includes(group.group_id)" class="border-t app-divider">
        <table class="min-w-full divide-y app-divide">
          <thead class="app-surface-muted">
            <tr>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase tracking-wider">Status</th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase tracking-wider">Nome / IP</th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase tracking-wider">Configuração de Avisos</th>
              <th scope="col" class="px-6 py-3 text-right text-xs font-medium app-text-tertiary uppercase tracking-wider">Ações</th>
            </tr>
          </thead>
          <tbody class="app-surface divide-y app-divide">
            <tr v-for="device in group.devices" :key="device.id" class="app-row transition-colors">
              <td class="px-6 py-4 whitespace-nowrap w-10">
                <div class="flex items-center space-x-2">
                  <!-- Status Zabbix -->
                  <div 
                    class="h-2.5 w-2.5 rounded-full" 
                    :style="getStatusDotStyle(getDeviceStatus(device.id))"
                    :title="getStatusLabel(getDeviceStatus(device.id))"
                  ></div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium app-text-primary">{{ device.name }}</div>
                <div class="text-sm app-text-tertiary">
                  {{ device.primary_ip || '(sem IP)' }}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center space-x-4">
                  <div 
                    class="flex items-center space-x-1"
                    :class="device.alerts.whatsapp ? 'app-badge app-badge-success' : 'app-badge app-badge-muted opacity-50'"
                  >
                    <i class="fab fa-whatsapp"></i>
                    <span class="text-xs hidden md:inline">Zap</span>
                  </div>
                  <div 
                    class="flex items-center space-x-1"
                    :class="device.alerts.email ? 'app-badge app-badge-info' : 'app-badge app-badge-muted opacity-50'"
                  >
                    <i class="far fa-envelope"></i>
                    <span class="text-xs hidden md:inline">Email</span>
                  </div>
                  <div 
                    class="flex items-center space-x-1"
                    :class="device.alerts.screen ? 'app-badge app-badge-warning' : 'app-badge app-badge-muted opacity-50'"
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
                    class="px-3 py-1 rounded transition-colors app-btn"
                    title="Ver interfaces do dispositivo"
                  >
                    <i class="fas fa-network-wired mr-1"></i> Interfaces
                  </button>
                  <button 
                    @click="$emit('edit-device', device, false)" 
                    class="px-3 py-1 rounded transition-colors app-btn-primary"
                    title="Configurar dispositivo"
                  >
                    <i class="fas fa-cog mr-1"></i> Configurar
                  </button>
                  <button 
                    @click="$emit('delete-device', device)" 
                    class="px-3 py-1 rounded transition-colors app-btn-danger"
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
      <i class="fas fa-inbox app-text-tertiary text-4xl mb-3"></i>
      <p class="app-text-tertiary">Nenhum dispositivo encontrado</p>
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

const getStatusDotStyle = (status) => {
  const colors = {
    online: 'var(--status-online)',
    offline: 'var(--status-offline)',
    disabled: 'var(--status-warning)',
    unknown: 'var(--status-unknown)'
  };
  return { backgroundColor: colors[status] || colors.unknown };
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
