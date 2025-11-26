<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
    <header class="mb-8 flex flex-col md:flex-row md:items-center md:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Gestão de Dispositivos</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Sincronize com o Zabbix e configure alertas operacionais.</p>
      </div>
      <div class="mt-4 md:mt-0 flex space-x-3">
        <button 
          @click="showImportRulesModal = true"
          class="inline-flex items-center px-4 py-2 border border-indigo-300 dark:border-indigo-600 rounded-md shadow-sm text-sm font-medium text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/30 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          <i class="fas fa-robot mr-2"></i>
          Configurar Regras
        </button>
        <button 
          @click="handleExportCSV"
          class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
        >
          <i class="fas fa-file-csv mr-2"></i>
          Exportar CSV
        </button>
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

      <div class="p-6">
        <div v-if="loading">
          <SkeletonLoader type="table" :rows="8" />
        </div>

        <div v-else>
          <keep-alive>
            <component 
              :is="currentTabComponent" 
              :data="tabData"
              :loading="loading"
              :available-groups="availableGroups"
              :available-sites="availableSites"
              @edit-device="openEditModal"
              @delete-device="handleDeleteDevice"
              @view-interfaces="openInterfacesModal"
              @trigger-sync="handleSync"
              @refresh-data="refreshData"
            />
          </keep-alive>
        </div>
      </div>
    </div>

    <!-- Confirm Delete Dialog -->
    <ConfirmDialog
      v-model:show="showDeleteConfirm"
      type="danger"
      title="Confirmar Exclusão"
      :message="deleteConfirmMessage"
      confirm-text="Excluir"
      cancel-text="Cancelar"
      @confirm="confirmDelete"
      @cancel="cancelDelete"
    />

    <DeviceEditModal
      v-if="showModal"
      :device="selectedDevice"
      :devices="selectedDevices"
      :is-new="isEditingNewDevice"
      :available-groups="availableGroups"
      :available-sites="availableSites"
      @close="closeModal"
      @save="saveDeviceChanges"
    />

    <!-- Interfaces Modal (Standalone) -->
    <div v-if="showInterfacesModal" class="fixed inset-0 z-[60] overflow-y-auto flex items-center justify-center">
      <div class="fixed inset-0 bg-black bg-opacity-60" @click="showInterfacesModal = false"></div>
      <div class="bg-white dark:bg-gray-800 w-full max-w-3xl rounded-lg shadow-2xl relative z-[70] flex flex-col m-4 max-h-[80vh]">
        <div class="p-4 border-b dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-900 rounded-t-lg">
          <div>
            <h3 class="font-bold text-gray-800 dark:text-white flex items-center">
              <i class="fas fa-network-wired text-blue-500 mr-2"></i>
              Interfaces do Dispositivo
            </h3>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {{ selectedInterfaceDevice?.name || '' }}
            </p>
          </div>
          <button @click="showInterfacesModal = false" class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">
            <i class="fas fa-times text-xl"></i>
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-4">
          <!-- Loading state -->
          <div v-if="loadingInterfaces" class="flex flex-col items-center justify-center py-12">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
            <p class="text-sm text-gray-600 dark:text-gray-300">Carregando interfaces...</p>
          </div>

          <!-- Empty state -->
          <div v-else-if="!interfacesData || interfacesData.length === 0" class="flex flex-col items-center justify-center py-12">
            <i class="fas fa-inbox text-gray-300 dark:text-gray-600 text-5xl mb-4"></i>
            <p class="text-gray-600 dark:text-gray-300 font-medium">Nenhuma interface encontrada</p>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">Este dispositivo não possui interfaces cadastradas.</p>
          </div>

          <!-- Interfaces list -->
          <div v-else class="space-y-3">
            <div 
              v-for="(iface, index) in interfacesData" 
              :key="index"
              class="border dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-750 hover:shadow-md transition-shadow"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="flex items-center">
                    <i class="fas fa-ethernet text-blue-500 mr-2"></i>
                    <h4 class="font-medium text-gray-800 dark:text-white">{{ iface.name }}</h4>
                    <span 
                      v-if="iface.status === 'up'" 
                      class="ml-2 px-2 py-0.5 text-xs bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 rounded-full"
                    >
                      <i class="fas fa-check-circle mr-1"></i>UP
                    </span>
                    <span 
                      v-else 
                      class="ml-2 px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-full"
                    >
                      <i class="fas fa-times-circle mr-1"></i>DOWN
                    </span>
                  </div>
                  <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">{{ iface.description || 'Sem descrição' }}</p>
                  
                  <!-- Signal levels -->
                  <div v-if="iface.rx_power || iface.tx_power" class="mt-3 grid grid-cols-2 gap-3">
                    <div v-if="iface.rx_power" class="bg-blue-50 dark:bg-blue-900/20 p-2 rounded">
                      <p class="text-xs text-gray-500 dark:text-gray-400">RX Power</p>
                      <p class="text-sm font-medium text-gray-800 dark:text-white">
                        {{ iface.rx_power }} dBm
                      </p>
                    </div>
                    <div v-if="iface.tx_power" class="bg-green-50 dark:bg-green-900/20 p-2 rounded">
                      <p class="text-xs text-gray-500 dark:text-gray-400">TX Power</p>
                      <p class="text-sm font-medium text-gray-800 dark:text-white">
                        {{ iface.tx_power }} dBm
                      </p>
                    </div>
                  </div>

                  <!-- Bandwidth -->
                  <div v-if="iface.speed" class="mt-2">
                    <p class="text-xs text-gray-500 dark:text-gray-400">
                      <i class="fas fa-tachometer-alt mr-1"></i>
                      Velocidade: <span class="font-medium text-gray-700 dark:text-gray-300">{{ iface.speed }}</span>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="p-4 border-t dark:border-gray-700 bg-white dark:bg-gray-800 rounded-b-lg flex justify-end">
          <button @click="showInterfacesModal = false" class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors">
            <i class="fas fa-times mr-2"></i>Fechar
          </button>
        </div>
      </div>
    </div>

    <!-- Import Rules Modal -->
    <ImportRulesModal v-model="showImportRulesModal" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import InventoryManagerTab from './InventoryManagerTab.vue';
import ImportPreviewTab from './ImportPreviewTab.vue';
import DeviceEditModal from './DeviceEditModal.vue';
import ImportRulesModal from './ImportRulesModal.vue';
import SkeletonLoader from '@/components/Common/SkeletonLoader.vue';
import ConfirmDialog from '@/components/Common/ConfirmDialog.vue';
import { useApi } from '@/composables/useApi';
import { useNotification } from '@/composables/useNotification';
import { validateDevices } from '@/utils/validators';
import { exportInventoryToCSV, exportZabbixPreviewToCSV } from '@/utils/csvExporter';

// Composables
const api = useApi();
const { success, error: notifyError } = useNotification();

// Estado
const loading = ref(false);
const currentTab = ref('inventory');
const showModal = ref(false);
const selectedDevice = ref(null);
const selectedDevices = ref([]);
const isEditingNewDevice = ref(false);
const showImportRulesModal = ref(false);

// Delete confirmation
const showDeleteConfirm = ref(false);
const deviceToDelete = ref(null);
const deleteConfirmMessage = computed(() => {
  if (!deviceToDelete.value) return '';
  return `Tem certeza que deseja excluir o dispositivo "${deviceToDelete.value.name}"? Esta ação não pode ser desfeita.`;
});

// Dados das abas
const inventoryData = ref([]);
const previewData = ref([]);
const availableGroups = ref([]);
const availableSites = ref([]);

// Interfaces Modal state
const showInterfacesModal = ref(false);
const selectedInterfaceDevice = ref(null);
const interfacesData = ref([]);
const loadingInterfaces = ref(false);

// Configuração das abas
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
    // 1. Buscar inventário agrupado (Pós-Importação)
    const grouped = await api.get('/api/v1/inventory/devices/grouped/');
    inventoryData.value = grouped;
    
    // Extrai grupos únicos (incluindo vazios) + complementa com todos do backend
    const uniqueGroups = new Set();
    grouped.forEach(group => {
      if (group.group_name && group.group_name !== 'Sem Grupo Definido') {
        uniqueGroups.add(group.group_name);
      }
    });
    // Busca lista completa de DeviceGroups para garantir que o dropdown tenha TODOS
    try {
      const allGroupsResponse = await api.get('/api/v1/device-groups/');
      const rawGroups = Array.isArray(allGroupsResponse)
        ? allGroupsResponse
        : (allGroupsResponse.results || allGroupsResponse.data || []);
      const allGroupNames = rawGroups
        .map(g => g && (g.name || g.group_name))
        .filter(Boolean);
      allGroupNames.forEach(name => uniqueGroups.add(name));
    } catch (groupErr) {
      console.warn('[DeviceImport] Erro ao buscar lista completa de grupos:', groupErr);
    }
    availableGroups.value = Array.from(uniqueGroups).sort((a, b) => a.localeCompare(b, 'pt-BR'));
    
    // 2. Buscar sites disponíveis
    try {
      const sitesResponse = await api.get('/api/v1/inventory/sites/');
      availableSites.value = sitesResponse.sites || [];
    } catch (sitesError) {
      console.warn('Erro ao buscar sites:', sitesError);
      availableSites.value = [];
    }
    
    // 3. Buscar preview do Zabbix (Pré-Importação) agrupado por hostgroups
    try {
      const response = await api.get('/api/v1/inventory/zabbix/lookup/hosts/grouped/');
      const zabbixGroups = response.data || [];
      
      // Marca quais já foram importados
      const importedIPs = new Set();
      const importedZabbixIds = new Set();
      
      grouped.forEach(group => {
        group.devices?.forEach(device => {
          if (device.primary_ip) importedIPs.add(device.primary_ip);
          if (device.zabbix_hostid) importedZabbixIds.add(device.zabbix_hostid);
        });
      });
      
      // Marca hosts importados em cada grupo
      previewData.value = zabbixGroups.map(group => ({
        ...group,
        hosts: group.hosts.map(host => ({
          ...host,
          is_imported: importedIPs.has(host.ip) || importedZabbixIds.has(host.zabbix_id)
        }))
      }));
    } catch (zabbixError) {
      console.warn('Erro ao buscar preview Zabbix:', zabbixError);
      notifyError('Aviso', 'Não foi possível carregar dispositivos do Zabbix.');
      previewData.value = [];
    }
    
  } catch (error) {
    console.error('Erro ao carregar dados:', error);
    notifyError('Erro ao Carregar', error.message || 'Não foi possível conectar ao servidor.');
  } finally {
    loading.value = false;
  }
};

const openEditModal = async (device, isNew = false) => {
  // Se for device existente, buscar dados atualizados do servidor
  if (!isNew && device?.id) {
    try {
      console.log('[DeviceImportManager] Fetching fresh device data for id:', device.id);
      const freshData = await api.get(`/api/v1/devices/${device.id}/`);
      selectedDevice.value = JSON.parse(JSON.stringify(freshData)); // Deep copy dos dados atualizados
      console.log('[DeviceImportManager] Fresh data loaded:', freshData);
    } catch (error) {
      console.warn('[DeviceImportManager] Error fetching fresh device data, using cached:', error);
      // Fallback: usa dados cached se fetch falhar
      selectedDevice.value = JSON.parse(JSON.stringify(device));
    }
  } else {
    // Para novos devices, usa dados passados como estão
    selectedDevice.value = JSON.parse(JSON.stringify(device)); // Deep copy
  }
  
  isEditingNewDevice.value = isNew;
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
  selectedDevice.value = null;
  selectedDevices.value = [];
};

// Mapeia grupo do Zabbix para grupos conhecidos
const matchGroup = (zabbixGroupName) => {
  if (!zabbixGroupName) return null;
  
  const groupLower = zabbixGroupName.toLowerCase();
  
  const mappings = {
    'servidores': ['server', 'servidor'],
    'network devices': ['network', 'rede'],
    'backbone': ['switch', 'router', 'backbone'],
    'distribuição': ['distribuição', 'distribution'],
    'acesso gpon': ['gpon', 'olt', 'onu'],
    'clientes corporativos': ['corporativo', 'cliente']
  };
  
  for (const [targetGroup, keywords] of Object.entries(mappings)) {
    if (keywords.some(keyword => groupLower.includes(keyword))) {
      const match = availableGroups.value.find(g => g.toLowerCase() === targetGroup);
      return match || null;
    }
  }
  
  const exactMatch = availableGroups.value.find(g => g.toLowerCase() === groupLower);
  return exactMatch || null;
};

const saveDeviceChanges = async (payload) => {
  try {
    // Validação antes de enviar
    if (payload.mode === 'batch') {
      const validation = validateDevices(payload.devices);
      if (!validation.valid) {
        const errorMessages = Object.values(validation.deviceErrors)
          .flat()
          .join(', ');
        notifyError('Validação Falhou', errorMessages);
        return;
      }
    }

    const response = await api.post('/api/v1/inventory/devices/import-batch/', payload);
    
    if (response.success) {
      const message = payload.mode === 'batch'
        ? `${response.created + response.updated} dispositivos processados`
        : 'Dispositivo salvo com sucesso';
      
      success(
        'Importação Concluída',
        `${message} (${response.created} novos, ${response.updated} atualizados)`
      );
      
      closeModal();
      await refreshData();
    } else {
      throw new Error(response.error || 'Erro desconhecido');
    }
  } catch (error) {
    console.error('Erro ao salvar dispositivo:', error);
    notifyError('Erro ao Salvar', error.message || 'Não foi possível processar a importação.');
  }
};

const handleSync = (selectedItems) => {
  if (!Array.isArray(selectedItems) || selectedItems.length === 0) {
    notifyError('Atenção', 'Selecione ao menos um dispositivo para importar.');
    return;
  }
  
  openEditModal(null, true, selectedItems);
};

// Interfaces Modal
const openInterfacesModal = async (device) => {
  selectedInterfaceDevice.value = device;
  showInterfacesModal.value = true;
  
  await fetchInterfaces(device);
};

const fetchInterfaces = async (device) => {
  if (!device || !device.id) {
    interfacesData.value = [];
    return;
  }

  loadingInterfaces.value = true;

  try {
    console.log('[DeviceImportManager] Fetching interfaces for device:', device.id);
    
    // Chamada à API com dados em tempo real do Zabbix
    const response = await api.get(`/api/v1/inventory/devices/${device.id}/ports/live/`);
    
    if (response.ports) {
      // Dados já vêm formatados do backend com status e sinais ópticos
      interfacesData.value = response.ports.map(port => ({
        id: port.id,
        name: port.name,
        description: port.description || '',
        status: port.status || 'unknown',
        speed: port.speed || '',
        rx_power: port.rx_power,
        tx_power: port.tx_power,
        fiber_cable_id: port.fiber_cable_id,
        zabbix_item_key: port.zabbix_item_key
      }));
      
      console.log('[DeviceImportManager] Interfaces loaded:', interfacesData.value.length);
    } else {
      interfacesData.value = [];
    }
  } catch (error) {
    console.error('[DeviceImportManager] Error fetching interfaces:', error);
    notifyError('Erro', 'Não foi possível carregar as interfaces do dispositivo.');
    interfacesData.value = [];
  } finally {
    loadingInterfaces.value = false;
  }
};

onMounted(() => {
  refreshData();
  
  // Listener para evento de sincronização completa
  window.addEventListener('device-sync-complete', handleDeviceSyncComplete);
});

onUnmounted(() => {
  window.removeEventListener('device-sync-complete', handleDeviceSyncComplete);
});

// Handler para evento de sincronização completa
const handleDeviceSyncComplete = (event) => {
  console.log('[DeviceImportManager] Device sync complete event received:', event.detail);
  // Recarrega dados após sincronização
  refreshData();
};

// Delete: Handlers de exclusão com confirmação
const handleDeleteDevice = (device) => {
  deviceToDelete.value = device;
  showDeleteConfirm.value = true;
};

const confirmDelete = async () => {
  if (!deviceToDelete.value) return;
  
  try {
    await api.delete(`/api/v1/inventory/devices/${deviceToDelete.value.id}/`);
    success('Dispositivo Excluído', `${deviceToDelete.value.name} foi removido com sucesso.`);
    deviceToDelete.value = null;
    showDeleteConfirm.value = false;
    await refreshData();
  } catch (error) {
    notifyError('Erro ao Excluir', error.message || 'Não foi possível excluir o dispositivo.');
  }
};

const cancelDelete = () => {
  deviceToDelete.value = null;
  showDeleteConfirm.value = false;
};

// Export: Handler de exportação CSV
const handleExportCSV = () => {
  try {
    if (currentTab.value === 'inventory') {
      exportInventoryToCSV(inventoryData.value);
      success('Exportação Concluída', 'Inventário exportado para CSV com sucesso.');
    } else {
      exportZabbixPreviewToCSV(previewData.value);
      success('Exportação Concluída', 'Preview do Zabbix exportado para CSV com sucesso.');
    }
  } catch (error) {
    notifyError('Erro na Exportação', error.message || 'Não foi possível gerar o arquivo CSV.');
  }
};
</script>
