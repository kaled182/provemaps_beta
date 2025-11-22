<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
    <header class="mb-8 flex flex-col md:flex-row md:items-center md:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Gestão de Dispositivos</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Sincronize com o Zabbix e configure alertas operacionais.</p>
      </div>
      <div class="mt-4 md:mt-0 flex space-x-3">
        <button 
          @click="refreshData" 
          class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          <i class="fas fa-sync-alt mr-2" :class="{ 'fa-spin': loading }"></i>
          Recarregar Dados
        </button>
      </div>
    </header>

    <div class="bg-white dark:bg-gray-800 rounded-lg shadow mb-6">
      <div class="border-b border-gray-200 dark:border-gray-700">
        <nav class="-mb-px flex" aria-label="Tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="currentTab = tab.id"
            :class="[
              currentTab === tab.id
                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600',
              'w-1/2 py-4 px-1 text-center border-b-2 font-medium text-sm transition-colors duration-200'
            ]"
          >
            <i :class="[tab.icon, 'mr-2']"></i>
            {{ tab.name }}
            <span v-if="tab.count" class="ml-2 py-0.5 px-2.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
              {{ tab.count }}
            </span>
          </button>
        </nav>
      </div>

      <div class="p-6 min-h-[400px]">
        <div v-if="loading" class="flex justify-center items-center h-64">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 dark:border-indigo-400"></div>
        </div>

        <div v-else>
          <keep-alive>
            <component 
              :is="currentTabComponent" 
              :data="tabData"
              @edit-device="openEditModal"
              @trigger-sync="handleSync"
            />
          </keep-alive>
        </div>
      </div>
    </div>

    <DeviceEditModal
      v-if="showModal"
      :device="selectedDevice"
      :devices="selectedDevices"
      :is-new="isEditingNewDevice"
      :available-groups="availableGroups"
      @close="closeModal"
      @save="saveDeviceChanges"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import InventoryManagerTab from './InventoryManagerTab.vue';
import ImportPreviewTab from './ImportPreviewTab.vue';
import DeviceEditModal from './DeviceEditModal.vue';

// Estado
const loading = ref(false);
const currentTab = ref('inventory');
const showModal = ref(false);
const selectedDevice = ref(null);
const selectedDevices = ref([]); // Array para importação em lote
const isEditingNewDevice = ref(false); // Diferencia se é um device novo (pré) ou existente (pós)

// Mock de Dados (Substituir pela sua chamada de API depois)
const inventoryData = ref([]);
const previewData = ref([]);

// Grupos disponíveis para seleção (virá da API futuramente)
const availableGroups = ref([
  'Backbone',
  'Distribuição',
  'Acesso GPON',
  'Clientes Corporativos',
  'Servidores',
  'Network Devices'
]);

const tabs = computed(() => [
  { 
    id: 'inventory', 
    name: 'Inventário Atual (Pós)', 
    icon: 'fas fa-server', 
    count: inventoryData.value.reduce((acc, g) => acc + g.devices.length, 0) 
  },
  { 
    id: 'preview', 
    name: 'Sincronização (Pré)', 
    icon: 'fas fa-file-import', 
    count: previewData.value.length 
  }
]);

const currentTabComponent = computed(() => {
  return currentTab.value === 'inventory' ? InventoryManagerTab : ImportPreviewTab;
});

const tabData = computed(() => {
  return currentTab.value === 'inventory' ? inventoryData.value : previewData.value;
});

// Ações
const refreshData = async () => {
  loading.value = true;
  
  try {
    // TODO: Substituir por chamadas reais de API
    // const [inventoryResp, previewResp] = await Promise.all([
    //   fetch('/api/devices/grouped/'),
    //   fetch('/api/zabbix/preview/')
    // ]);
    
    // Simulação de API Call
    await new Promise(resolve => setTimeout(resolve, 800));
    
    // Dados já agrupados (Pós-Importação)
    inventoryData.value = [
      {
        group_id: 1,
        group_name: 'Backbone Principal',
        devices: [
          { 
            id: 101, 
            name: 'Router-Core-01', 
            ip: '10.0.0.1', 
            status: 'online',
            alerts: { whatsapp: true, email: false, screen: true } 
          },
          { 
            id: 102, 
            name: 'Switch-Agg-01', 
            ip: '10.0.0.2', 
            status: 'online',
            alerts: { whatsapp: false, email: true, screen: true } 
          }
        ]
      },
      {
        group_id: 2,
        group_name: 'Distribuição Norte',
        devices: [
          { 
            id: 201, 
            name: 'OLT-Huawei-01', 
            ip: '10.0.10.1', 
            status: 'online',
            alerts: { whatsapp: true, email: true, screen: true } 
          }
        ]
      }
    ];

    // Dados "Flat" vindos do Zabbix (Pré-Importação)
    previewData.value = [
      { 
        id: 'zbx_999', 
        name: 'Novo-Router-X', 
        ip: '192.168.1.50', 
        status: 'new', 
        group_suggestion: 'Sem Grupo' 
      },
      { 
        id: '101', 
        name: 'Router-Core-01', 
        ip: '10.0.0.1', 
        status: 'changed', 
        changes: ['Nome alterado no Zabbix'] 
      }
    ];
  } catch (error) {
    console.error('Erro ao carregar dados:', error);
  } finally {
    loading.value = false;
  }
};

const openEditModal = (device, isNew = false) => {
  selectedDevice.value = JSON.parse(JSON.stringify(device)); // Deep copy
  isEditingNewDevice.value = isNew;
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
  selectedDevice.value = null;
  selectedDevices.value = [];
};

// Função auxiliar: Mapeia grupo do Zabbix para nossos grupos (lógica inteligente)
const matchGroup = (zabbixGroupName) => {
  if (!zabbixGroupName) return 'Acesso GPON'; // Default
  
  const groupLower = zabbixGroupName.toLowerCase();
  
  // Regras específicas de mapeamento
  if (groupLower.includes('server') || groupLower.includes('servidor')) return 'Servidores';
  if (groupLower.includes('network') || groupLower.includes('rede')) return 'Network Devices';
  if (groupLower.includes('switch') || groupLower.includes('router') || groupLower.includes('backbone')) return 'Backbone';
  if (groupLower.includes('distribuição') || groupLower.includes('distribution')) return 'Distribuição';
  if (groupLower.includes('gpon') || groupLower.includes('olt') || groupLower.includes('onu')) return 'Acesso GPON';
  if (groupLower.includes('corporativo') || groupLower.includes('cliente')) return 'Clientes Corporativos';
  
  // Tenta encontrar correspondência parcial (case-insensitive)
  const match = availableGroups.value.find(g => 
    groupLower.includes(g.toLowerCase()) || g.toLowerCase().includes(groupLower)
  );
  
  return match || 'Acesso GPON'; // Default se não achar
};

const saveDeviceChanges = async (payload) => {
  console.log('Salvando dispositivo(s):', payload);
  
  try {
    if (payload.mode === 'batch') {
      // Importação em lote
      console.log(`Importando ${payload.devices.length} dispositivos em lote:`, payload.devices);
      
      // TODO: Implementar chamada de API batch
      // const response = await fetch('/api/devices/batch-import/', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ devices: payload.devices })
      // });
      
      alert(`${payload.devices.length} dispositivos importados com sucesso!`);
    } else {
      // Importação/edição single (compatibilidade)
      console.log('Salvando dispositivo único:', payload);
      
      // TODO: Implementar chamada de API
      // const response = await fetch(`/api/devices/${payload.id}/`, {
      //   method: 'PATCH',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(payload)
      // });
      
      alert('Dispositivo salvo com sucesso!');
    }
    
    closeModal();
    await refreshData(); // Atualiza a lista
  } catch (error) {
    console.error('Erro ao salvar dispositivo:', error);
    alert('Erro ao salvar. Veja o console para detalhes.');
  }
};

const handleSync = (selectedItems) => {
  console.log('Importando/Sincronizando itens:', selectedItems);
  
  if (!Array.isArray(selectedItems) || selectedItems.length === 0) {
    alert('Selecione ao menos um dispositivo para importar.');
    return;
  }
  
  // Normaliza os dados para o formato esperado pelo modal
  const normalizedDevices = selectedItems.map(deviceData => ({
    ...deviceData,
    name: deviceData.name,
    ip: deviceData.ip || deviceData.ip_address,
    ip_address: deviceData.ip || deviceData.ip_address,
    mac: deviceData.mac || '',
    zabbix_id: deviceData.zabbix_id,
    group: matchGroup(deviceData.group_name),
    category: 'backbone',
    alerts: {
      screen: true,
      whatsapp: false,
      email: false
    }
  }));
  
  if (normalizedDevices.length === 1) {
    // Modo SINGLE: Usa selectedDevice (compatibilidade)
    selectedDevice.value = normalizedDevices[0];
    selectedDevices.value = []; // Limpa array
  } else {
    // Modo BATCH: Usa selectedDevices array
    selectedDevices.value = normalizedDevices;
    selectedDevice.value = null; // Limpa single
  }
  
  isEditingNewDevice.value = true;
  showModal.value = true;
};

onMounted(() => {
  refreshData();
});
</script>
