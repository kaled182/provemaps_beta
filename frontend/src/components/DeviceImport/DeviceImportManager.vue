<template>
  <div class="min-h-screen app-page p-6">
    <header class="mb-8 flex flex-col md:flex-row md:items-center md:justify-between">
      <div>
        <h1 class="text-2xl font-bold app-text-primary">Gestão de Dispositivos</h1>
        <p class="text-sm app-text-tertiary mt-1">Sincronize com o Zabbix e configure alertas operacionais.</p>
      </div>
      <div class="mt-4 md:mt-0 flex space-x-3">
        <button 
          @click="showImportRulesModal = true"
          class="inline-flex items-center px-4 py-2 rounded-md shadow-sm text-sm font-medium app-btn-primary"
        >
          <i class="fas fa-robot mr-2"></i>
          Configurar Regras
        </button>
        <button 
          @click="handleExportCSV"
          class="inline-flex items-center px-4 py-2 rounded-md shadow-sm text-sm font-medium app-btn"
        >
          <i class="fas fa-file-csv mr-2"></i>
          Exportar CSV
        </button>
        <button 
          @click="refreshData" 
          class="inline-flex items-center px-4 py-2 rounded-md shadow-sm text-sm font-medium app-btn"
        >
          <i class="fas fa-sync-alt mr-2" :class="{ 'fa-spin': loading }"></i>
          Recarregar Dados
        </button>
      </div>
    </header>

    <div class="app-surface rounded-lg mb-6">
      <div class="border-b app-divider">
        <nav class="-mb-px flex" aria-label="Tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="currentTab = tab.id"
            :class="[
              'w-1/2 py-4 px-1 text-center font-medium text-sm transition-colors duration-200 app-tab-underline',
              { 'is-active': currentTab === tab.id }
            ]"
          >
            <i :class="[tab.icon, 'mr-2']"></i>
            {{ tab.name }}
            <span v-if="tab.count" class="ml-2 py-0.5 px-2.5 rounded-full text-xs font-medium app-chip">
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
              :loading-zabbix="loadingZabbix"
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
      :saving="isSaving"
      :available-groups="availableGroups"
      :available-sites="availableSites"
      @close="closeModal"
      @save="saveDeviceChanges"
    />

    <!-- Interfaces Modal (Standalone) -->
    <div v-if="showInterfacesModal" class="fixed inset-0 z-[60] overflow-y-auto flex items-center justify-center">
      <div class="fixed inset-0 bg-black bg-opacity-60" @click="showInterfacesModal = false"></div>
      <div class="app-surface w-full max-w-3xl rounded-lg relative z-[70] flex flex-col m-4 max-h-[80vh]">
        <div class="p-4 border-b app-divider flex justify-between items-center app-surface-muted rounded-t-lg">
          <div>
            <h3 class="font-bold app-text-primary flex items-center">
              <i class="fas fa-network-wired mr-2" style="color: var(--accent-info);"></i>
              Interfaces do Dispositivo
            </h3>
            <p class="text-xs app-text-tertiary mt-1">
              {{ selectedInterfaceDevice?.name || '' }}
            </p>
          </div>
          <button @click="showInterfacesModal = false" class="app-text-tertiary close-icon-btn">
            <i class="fas fa-times text-xl"></i>
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-4">
          <!-- Loading state -->
          <div v-if="loadingInterfaces" class="flex flex-col items-center justify-center py-12">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 app-spinner mb-4"></div>
            <p class="text-sm app-text-secondary">Carregando interfaces...</p>
          </div>

          <!-- Empty state -->
          <div v-else-if="!interfacesData || interfacesData.length === 0" class="flex flex-col items-center justify-center py-12">
            <i class="fas fa-inbox app-text-tertiary text-5xl mb-4"></i>
            <p class="app-text-secondary font-medium">Nenhuma interface encontrada</p>
            <p class="text-sm app-text-tertiary mt-2">Este dispositivo não possui interfaces cadastradas.</p>
          </div>

          <!-- Interfaces list -->
          <div v-else class="space-y-3">
            <div 
              v-for="(iface, index) in interfacesData" 
              :key="index"
              class="app-surface rounded-lg p-4 transition-shadow"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="flex items-center">
                    <i class="fas fa-ethernet mr-2" style="color: var(--accent-info);"></i>
                    <h4 class="font-medium app-text-primary">{{ iface.name }}</h4>
                    <span 
                      v-if="iface.status === 'up'" 
                      class="ml-2 app-badge app-badge-success"
                    >
                      <i class="fas fa-check-circle mr-1"></i>UP
                    </span>
                    <span 
                      v-else 
                      class="ml-2 app-badge app-badge-muted"
                    >
                      <i class="fas fa-times-circle mr-1"></i>DOWN
                    </span>
                  </div>
                  <p class="text-sm app-text-tertiary mt-1">{{ iface.description || 'Sem descrição' }}</p>
                  
                  <!-- Signal levels -->
                  <div v-if="iface.rx_power || iface.tx_power" class="mt-3 grid grid-cols-2 gap-3">
                    <div v-if="iface.rx_power" class="app-surface-muted p-2 rounded">
                      <p class="text-xs app-text-tertiary">RX Power</p>
                      <p class="text-sm font-medium app-text-primary">
                        {{ iface.rx_power }} dBm
                      </p>
                    </div>
                    <div v-if="iface.tx_power" class="app-surface-muted p-2 rounded">
                      <p class="text-xs app-text-tertiary">TX Power</p>
                      <p class="text-sm font-medium app-text-primary">
                        {{ iface.tx_power }} dBm
                      </p>
                    </div>
                  </div>

                  <!-- Bandwidth -->
                  <div v-if="iface.speed" class="mt-2">
                    <p class="text-xs app-text-tertiary">
                      <i class="fas fa-tachometer-alt mr-1"></i>
                      Velocidade: <span class="font-medium app-text-secondary">{{ iface.speed }}</span>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="p-4 border-t app-divider app-surface rounded-b-lg flex justify-end">
          <button @click="showInterfacesModal = false" class="px-4 py-2 rounded app-btn">
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
const loadingZabbix = ref(false);
const isSaving = ref(false);
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
  loadingZabbix.value = true;

  try {
    // Todas as 3 chamadas rápidas em paralelo
    const [grouped, allGroupsResponse, sitesResponse] = await Promise.all([
      api.get('/api/v1/inventory/devices/grouped/'),
      api.get('/api/v1/device-groups/').catch(() => null),
      api.get('/api/v1/inventory/sites/').catch(() => null),
    ]);

    inventoryData.value = grouped;

    // Monta lista de grupos disponíveis
    const uniqueGroups = new Set();
    grouped.forEach(group => {
      if (group.group_name && group.group_name !== 'Sem Grupo Definido') {
        uniqueGroups.add(group.group_name);
      }
    });
    if (allGroupsResponse) {
      const rawGroups = Array.isArray(allGroupsResponse)
        ? allGroupsResponse
        : (allGroupsResponse.results || allGroupsResponse.data || []);
      rawGroups.map(g => g && (g.name || g.group_name)).filter(Boolean)
        .forEach(name => uniqueGroups.add(name));
    }
    availableGroups.value = Array.from(uniqueGroups).sort((a, b) => a.localeCompare(b, 'pt-BR'));

    availableSites.value = sitesResponse?.sites || [];

  } catch (error) {
    console.error('Erro ao carregar dados:', error);
    notifyError('Erro ao Carregar', error.message || 'Não foi possível conectar ao servidor.');
  } finally {
    loading.value = false;
  }

  // Carrega Zabbix separadamente sem bloquear a aba de inventário
  try {
    const response = await api.get('/api/v1/inventory/zabbix/lookup/hosts/grouped/');
    const zabbixGroups = response.data || [];

    const importedIPs = new Set();
    const importedZabbixIds = new Set();
    inventoryData.value.forEach(group => {
      group.devices?.forEach(device => {
        if (device.primary_ip) importedIPs.add(device.primary_ip);
        if (device.zabbix_hostid) importedZabbixIds.add(device.zabbix_hostid);
      });
    });

    previewData.value = zabbixGroups.map(group => ({
      ...group,
      hosts: group.hosts.map(host => ({
        ...host,
        is_imported: importedIPs.has(host.ip) || importedZabbixIds.has(host.zabbix_id),
      })),
    }));
  } catch (zabbixError) {
    console.warn('Erro ao buscar preview Zabbix:', zabbixError);
    notifyError('Aviso', 'Não foi possível carregar dispositivos do Zabbix.');
    previewData.value = [];
  } finally {
    loadingZabbix.value = false;
  }
};

const openEditModal = async (device, isNew = false, devices = null) => {
  // Batch mode: multiple devices from bulk selection
  if (devices && Array.isArray(devices) && devices.length > 0) {
    selectedDevices.value = devices.map(d => JSON.parse(JSON.stringify(d)));
    selectedDevice.value = null;
    isEditingNewDevice.value = true;
    showModal.value = true;
    return;
  }

  // Single device mode
  selectedDevices.value = [];

  if (!isNew && device?.id) {
    try {
      const freshData = await api.get(`/api/v1/devices/${device.id}/`);
      selectedDevice.value = JSON.parse(JSON.stringify(freshData));
    } catch (error) {
      console.warn('[DeviceImportManager] Error fetching fresh device data, using cached:', error);
      selectedDevice.value = JSON.parse(JSON.stringify(device));
    }
  } else {
    selectedDevice.value = device ? JSON.parse(JSON.stringify(device)) : null;
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
  // Validação antes de enviar
  if (payload.mode === 'batch') {
    const validation = validateDevices(payload.devices);
    if (!validation.valid) {
      const errorMessages = Object.values(validation.deviceErrors).flat().join(', ');
      notifyError('Validação Falhou', errorMessages);
      return;
    }
  }

  isSaving.value = true;
  try {
    const response = await api.post('/api/v1/inventory/devices/import-batch/', payload);

    if (response.success) {
      const total = response.created + response.updated;
      const message = payload.mode === 'batch'
        ? `${total} dispositivo${total !== 1 ? 's' : ''} processado${total !== 1 ? 's' : ''}`
        : 'Dispositivo salvo com sucesso';

      success('Importação Concluída', `${message} (${response.created} novos, ${response.updated} atualizados)`);

      if (response.proximity_warnings?.length) {
        response.proximity_warnings.forEach(w => {
          notifyError(
            'Regra de Proximidade Aplicada',
            `O site "${w.new_site_name}" não foi criado pois já existe "${w.reused_site}" a ${w.distance_m}m. O equipamento foi associado ao site existente.`
          );
        });
      }

      closeModal();
      currentTab.value = 'inventory';
      await refreshData();
    } else {
      throw new Error(response.error || 'Erro desconhecido');
    }
  } catch (error) {
    console.error('Erro ao salvar dispositivo:', error);
    notifyError('Erro ao Salvar', error.message || 'Não foi possível processar a importação.');
  } finally {
    isSaving.value = false;
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

<style scoped>
.close-icon-btn:hover {
  color: var(--text-primary);
}
</style>
