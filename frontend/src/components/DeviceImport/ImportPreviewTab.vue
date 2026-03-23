<template>
  <div class="space-y-6">
    
    <!-- Header com Filtros e Ações -->
    <div class="app-surface p-4 rounded-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="flex items-center gap-4 flex-1">
        <div class="flex items-center space-x-2 app-badge app-badge-info">
          <i class="fas fa-server"></i>
          <span class="text-sm font-medium">
            {{ zabbixServerInfo }}
          </span>
        </div>

        <div class="flex-1">
          <label class="block text-xs font-medium app-text-tertiary mb-1">Filtrar Hosts</label>
          <div class="relative rounded-md">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <i class="fas fa-search app-text-tertiary"></i>
            </div>
            <input 
              type="text" 
              v-model="searchQuery" 
              class="block w-full pl-10 sm:text-sm app-input" 
              placeholder="Nome ou IP..."
            >
          </div>
        </div>
      </div>

      <div class="flex items-end gap-2">
        <button 
          @click="showIgnored = !showIgnored"
          class="inline-flex items-center px-3 py-2 text-sm font-medium rounded-md app-btn"
          :title="showIgnored ? 'Ocultar devices ignorados' : 'Mostrar devices ignorados'"
        >
          <i :class="showIgnored ? 'fas fa-eye-slash' : 'fas fa-eye'" class="mr-2"></i>
          {{ showIgnored ? 'Ocultar Ignorados' : 'Mostrar Ignorados' }}
          <span v-if="ignoredCount > 0" class="ml-2 px-2 py-0.5 text-xs rounded-full app-chip">
            {{ ignoredCount }}
          </span>
        </button>
        
        <button 
          @click="importSelected" 
          :disabled="selectedCount === 0"
          class="w-full md:w-auto inline-flex items-center px-4 py-2 text-sm font-medium rounded-md shadow-sm app-btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <i class="fas fa-cloud-download-alt mr-2"></i>
          Importar Selecionados ({{ selectedCount }})
        </button>
      </div>
    </div>

    <!-- Lista de Grupos Hierárquica -->
    <div v-if="props.loadingZabbix" class="app-surface p-8 rounded-lg flex flex-col items-center justify-center gap-3">
      <i class="fas fa-circle-notch fa-spin text-2xl" style="color: var(--accent-info);"></i>
      <span class="text-sm app-text-secondary">Consultando Zabbix...</span>
    </div>

    <div v-else class="app-surface overflow-hidden sm:rounded-md max-h-[600px] overflow-y-auto">
      <ul class="divide-y app-divide">
        <li v-for="group in filteredGroups" :key="group.zabbix_group_id" class="group-container">
          
          <!-- Cabeçalho do Grupo -->
          <div 
            class="app-surface-muted px-4 py-3 flex items-center justify-between cursor-pointer app-row transition" 
            @click="toggleGroup(group.zabbix_group_id)"
          >
            <div class="flex items-center">
              <i 
                class="fas fa-chevron-right app-text-tertiary mr-3 transition-transform duration-200"
                :class="{ 'rotate-90': expandedGroups.includes(group.zabbix_group_id) }"
              ></i>
              <span class="text-sm font-bold app-text-primary">{{ group.name }}</span>
              <span class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium app-chip">
                {{ group.hosts.length }} hosts
              </span>
            </div>
            
            <div class="flex items-center" @click.stop>
              <label class="inline-flex items-center text-xs app-text-tertiary mr-3">
                <input 
                  type="checkbox" 
                  class="form-checkbox h-4 w-4 rounded mr-1"
                  style="accent-color: var(--accent-info);"
                  @change="toggleSelectGroup(group, $event.target.checked)"
                  :checked="isGroupFullySelected(group)"
                  :indeterminate.prop="isGroupPartiallySelected(group)"
                >
                Selecionar Novos
              </label>
            </div>
          </div>

          <!-- Hosts dentro do Grupo -->
          <div v-show="expandedGroups.includes(group.zabbix_group_id)" class="border-t app-divider">
            <table class="min-w-full divide-y app-divide">
              <tbody class="app-surface divide-y app-divide">
                <tr 
                  v-for="host in group.hosts" 
                  :key="host.zabbix_id" 
                  :class="{
                    'row-imported': host.is_imported && !ignoredDevices.has(host.zabbix_id),
                    'row-ignored': ignoredDevices.has(host.zabbix_id)
                  }"
                >
                  <td class="px-6 py-4 whitespace-nowrap w-10">
                    <input 
                      v-if="!host.is_imported"
                      type="checkbox" 
                      v-model="selectedHosts" 
                      :value="host.zabbix_id"
                      class="h-4 w-4 rounded"
                      style="accent-color: var(--accent-info);"
                    >
                    <i v-else class="fas fa-check-circle text-lg" style="color: var(--status-online);" title="Já importado"></i>
                  </td>

                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                      <div class="ml-0">
                        <div class="flex items-center gap-2">
                          <div class="text-sm font-medium app-text-primary">
                            {{ host.name }}
                          </div>
                          <!-- Badge de Drift (Desatualizado) -->
                          <span 
                            v-if="host.is_imported && host.has_drift"
                            class="app-badge app-badge-warning cursor-help"
                            :title="`Dados desatualizados: ${host.drift_fields?.join(', ')}`"
                          >
                            <i class="fas fa-exclamation-triangle mr-1"></i>
                            Desatualizado
                          </span>
                        </div>
                        <div class="text-sm app-text-tertiary">
                          {{ host.ip || '(sem IP)' }}
                          <span v-if="host.mac" class="text-xs app-text-tertiary ml-2">({{ host.mac }})</span>
                        </div>
                      </div>
                    </div>
                  </td>

                  <td class="px-6 py-4 whitespace-nowrap">
                    <span 
                      v-if="ignoredDevices.has(host.zabbix_id)"
                      class="app-badge app-badge-muted"
                    >
                      <i class="fas fa-ban mr-1"></i>
                      Ignorado
                    </span>
                    <span 
                      v-else-if="host.is_imported"
                      class="app-badge app-badge-success"
                    >
                      Importado
                    </span>
                    <span 
                      v-else
                      class="app-badge app-badge-warning"
                    >
                      Novo Detectado
                    </span>
                  </td>

                  <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <!-- Device ignorado -->
                    <div v-if="ignoredDevices.has(host.zabbix_id)" class="flex items-center justify-end gap-2">
                      <button 
                        @click="restoreDevice(host.zabbix_id)"
                        class="px-3 py-1 rounded app-btn-success"
                        title="Restaurar e voltar à lista de sincronização"
                      >
                        <i class="fas fa-undo mr-1"></i>
                        Restaurar
                      </button>
                    </div>
                    
                    <!-- Device não importado e não ignorado -->
                    <div v-else-if="!host.is_imported" class="flex items-center justify-end gap-2">
                      <button 
                        @click="$emit('edit-device', host, true)" 
                        class="px-3 py-1 rounded app-btn-primary"
                      >
                        Configurar e Importar
                      </button>
                      <button 
                        @click="ignoreDevice(host.zabbix_id)"
                        class="px-3 py-1 rounded app-btn"
                        title="Ignorar este device"
                      >
                        <i class="fas fa-ban mr-1"></i>
                        Ignorar
                      </button>
                    </div>
                    <div v-else class="flex items-center justify-end gap-2">
                      <button 
                        @click="viewDeviceDetails(host)"
                        class="px-3 py-1 rounded app-btn"
                      >
                        Ver Detalhes
                      </button>
                      <!-- Botão Sincronizar (apenas se has_drift) -->
                      <button 
                        v-if="host.has_drift"
                        @click="syncDeviceChanges(host)"
                        class="px-3 py-1 rounded app-btn-warning"
                        title="Sincronizar com dados atuais do Zabbix"
                      >
                        <i class="fas fa-sync-alt mr-1"></i>
                        Sincronizar
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </li>
      </ul>
      
      <div v-if="filteredGroups.length === 0" class="text-center py-10">
        <p class="app-text-tertiary">Nenhum grupo ou host encontrado com este filtro.</p>
      </div>
    </div>

    <!-- Modal de Detalhes (Readonly) -->
    <DeviceEditModal
      v-if="showDetailsModal"
      :device="selectedDeviceForDetails"
      :read-only="true"
      :available-groups="props.availableGroups"
      :available-sites="props.availableSites"
      @close="closeDetailsModal"
      @edit="handleEditDevice"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useApi } from '@/composables/useApi';
import DeviceEditModal from './DeviceEditModal.vue';

const api = useApi();

const props = defineProps({
  data: { type: Array, default: () => [] },
  availableGroups: { type: Array, default: () => [] },
  availableSites: { type: Array, default: () => [] },
  loadingZabbix: { type: Boolean, default: false },
});
const emit = defineEmits(['edit-device', 'trigger-sync', 'refresh-data']);

// Estado Local
const searchQuery = ref('');
const expandedGroups = ref([]); // IDs dos grupos abertos
const selectedHosts = ref([]); // IDs dos hosts selecionados para importar
const zabbixServerInfo = ref('Carregando...');

// Estado para ignorados (blacklist)
const IGNORED_DEVICES_KEY = 'zabbix_ignored_devices';
const ignoredDevices = ref(new Set(JSON.parse(localStorage.getItem(IGNORED_DEVICES_KEY) || '[]')));
const showIgnored = ref(false);

// Estado para modal de detalhes (readonly)
const showDetailsModal = ref(false);
const selectedDeviceForDetails = ref(null);

// Fetch Zabbix server info
const fetchServerInfo = async () => {
  try {
    const response = await api.get('/api/v1/inventory/zabbix/lookup/server-info/');
    if (response.configured) {
      zabbixServerInfo.value = response.server_name || 'Servidor Zabbix';
    } else {
      zabbixServerInfo.value = 'Zabbix não configurado';
    }
  } catch (error) {
    console.error('Erro ao buscar info do servidor Zabbix:', error);
    zabbixServerInfo.value = 'Servidor Zabbix';
  }
};

// Computed: Filtragem
const filteredGroups = computed(() => {
  const query = searchQuery.value.toLowerCase();
  const dataSource = props.data && props.data.length > 0 ? props.data : [];
  
  return dataSource.map(group => {
    // Se o nome do grupo bate, mostra tudo. Se não, filtra os hosts dentro.
    const groupMatch = group.name.toLowerCase().includes(query);
    
    // Filtra hosts
    let filteredHosts = group.hosts.filter(h => 
      h.name.toLowerCase().includes(query) || 
      h.ip.includes(query)
    );

    // Remove ignorados se toggle estiver desativado
    if (!showIgnored.value) {
      filteredHosts = filteredHosts.filter(h => !ignoredDevices.value.has(h.zabbix_id));
    }

    // Retorna o grupo se houver match no nome ou se tiver hosts filhos filtrados
    if (groupMatch || filteredHosts.length > 0) {
      return {
        ...group,
        hosts: groupMatch ? group.hosts : filteredHosts
      };
    }
    return null;
  }).filter(g => g !== null);
});

const selectedCount = computed(() => selectedHosts.value.length);
const ignoredCount = computed(() => ignoredDevices.value.size);

// Métodos de UI
const fetchPreviewData = () => {
  console.log(`Buscando dados do servidor Zabbix ID: ${selectedServerId.value}...`);
  // TODO: Aqui chamaria API: GET /api/zabbix/preview?server_id=...
};

const toggleGroup = (id) => {
  if (expandedGroups.value.includes(id)) {
    expandedGroups.value = expandedGroups.value.filter(gId => gId !== id);
  } else {
    expandedGroups.value.push(id);
  }
};

// Lógica de Checkbox de Grupo
const isGroupFullySelected = (group) => {
  const newHosts = group.hosts.filter(h => !h.is_imported);
  if (newHosts.length === 0) return false;
  return newHosts.every(h => selectedHosts.value.includes(h.zabbix_id));
};

const isGroupPartiallySelected = (group) => {
  const newHosts = group.hosts.filter(h => !h.is_imported);
  if (newHosts.length === 0) return false;
  const selectedInGroup = newHosts.filter(h => selectedHosts.value.includes(h.zabbix_id));
  return selectedInGroup.length > 0 && selectedInGroup.length < newHosts.length;
};

const toggleSelectGroup = (group, isChecked) => {
  const newHosts = group.hosts.filter(h => !h.is_imported);
  const newHostIds = newHosts.map(h => h.zabbix_id);

  if (isChecked) {
    // Adiciona os que não estão selecionados
    newHostIds.forEach(id => {
      if (!selectedHosts.value.includes(id)) selectedHosts.value.push(id);
    });
  } else {
    // Remove todos do grupo
    selectedHosts.value = selectedHosts.value.filter(id => !newHostIds.includes(id));
  }
};

// Função para abrir modal de visualização (readonly)
const viewDeviceDetails = async (host) => {
  if (!host.is_imported) {
    console.warn('Device not imported yet:', host);
    return;
  }

  console.log('[ImportPreviewTab] Opening details for host:', host);

  try {
    let deviceData = null;

    // Tenta buscar por zabbix_hostid primeiro (mais confiável)
    if (host.zabbix_id) {
      try {
        console.log('[ImportPreviewTab] Fetching by zabbix_id:', host.zabbix_id);
        deviceData = await api.get(
          `/api/v1/devices/by-zabbix/${host.zabbix_id}/`
        );
        console.log('[ImportPreviewTab] Device found:', deviceData);
      } catch (error) {
        console.warn('[ImportPreviewTab] Not found by zabbix_id:', error);
      }
    }

    // Fallback: busca por device_id se disponível
    if (!deviceData && host.device_id) {
      console.log('[ImportPreviewTab] Fetching by device_id:', host.device_id);
      deviceData = await api.get(`/api/v1/devices/${host.device_id}/`);
    }

    // Se encontrou dados via API, abre modal readonly
    if (deviceData) {
      selectedDeviceForDetails.value = {
        ...deviceData,
        zabbix_id: host.zabbix_id || deviceData.zabbix_hostid,
      };
      
      console.log('[ImportPreviewTab] Opening readonly modal with device data:', {
        id: deviceData.id,
        name: deviceData.name,
        group_name: deviceData.group_name,
        monitoring_group: deviceData.monitoring_group,
        category: deviceData.category
      });
      showDetailsModal.value = true;
      return;
    }

    // Fallback: usa dados locais
    console.warn('[ImportPreviewTab] Using host data as fallback');
    selectedDeviceForDetails.value = {
      id: host.device_id || host.zabbix_id,
      zabbix_hostid: host.zabbix_id,
      name: host.name,
      primary_ip: host.ip,
      category: 'backbone',
      site: null,
      monitoring_group: null,
      enable_screen_alert: true,
      enable_whatsapp_alert: false,
      enable_email_alert: false
    };
    
    showDetailsModal.value = true;
    
  } catch (error) {
    console.error('[ImportPreviewTab] Error fetching device:', error);
    alert('Erro ao carregar dados do dispositivo. Tente novamente.');
  }
};

// Função para fechar modal readonly
const closeDetailsModal = () => {
  showDetailsModal.value = false;
  selectedDeviceForDetails.value = null;
};

// Função para sincronizar alterações do Zabbix
const syncDeviceChanges = async (host) => {
  if (!host.has_drift) {
    return;
  }

  const changesText = host.drift_fields.join(', ');
  const confirmMsg = `Deseja sincronizar as seguintes alterações do Zabbix?\n\n${changesText}\n\nIsso atualizará o dispositivo com os dados atuais do Zabbix.`;
  
  if (!confirm(confirmMsg)) {
    return;
  }

  try {
    console.log('[ImportPreviewTab] Syncing device changes:', host);

    // Busca device atual do banco
    let deviceData = null;
    try {
      deviceData = await api.get(`/api/v1/devices/by-zabbix/${host.zabbix_id}/`);
    } catch (error) {
      console.error('[ImportPreviewTab] Device not found:', error);
      if (error.response?.status === 404) {
        alert('Dispositivo não encontrado no sistema.\n\nEle pode ter sido excluído. Tente recarregar a página para atualizar a lista.');
      } else {
        alert('Erro ao buscar dispositivo: ' + (error.message || 'Erro desconhecido'));
      }
      return;
    }

    // Chama nova ação de sincronização completa (backend puxa Zabbix, aplica regras, grupos, site)
    try {
      const syncResp = await api.post(`/api/v1/devices/${deviceData.id}/sync/`);
      console.log('[ImportPreviewTab] Sync response:', syncResp);
    } catch (syncErr) {
      console.error('[ImportPreviewTab] Sync action failed:', syncErr);
      alert('Falha ao sincronizar com Zabbix: ' + (syncErr.response?.data?.error || syncErr.message));
      return;
    }

    console.log('[ImportPreviewTab] Device synced successfully (action)');
    alert('Dispositivo sincronizado com sucesso!');

    // Solicita refresh dos dados
    emit('refresh-data');

  } catch (error) {
    console.error('[ImportPreviewTab] Error syncing device:', error);
    alert(`Erro ao sincronizar: ${error.message || 'Tente novamente.'}`);
  }
};

// Função para ignorar device (blacklist)
const ignoreDevice = (zabbixId) => {
  if (!confirm('Deseja ignorar este dispositivo? Ele não aparecerá mais na lista de sincronização.')) {
    return;
  }

  ignoredDevices.value.add(zabbixId);
  
  // Salva no localStorage
  localStorage.setItem(
    IGNORED_DEVICES_KEY,
    JSON.stringify(Array.from(ignoredDevices.value))
  );

  console.log('[ImportPreviewTab] Device ignored:', zabbixId);
};

// Função para restaurar device ignorado
const restoreDevice = (zabbixId) => {
  ignoredDevices.value.delete(zabbixId);
  
  // Atualiza localStorage
  localStorage.setItem(
    IGNORED_DEVICES_KEY,
    JSON.stringify(Array.from(ignoredDevices.value))
  );

  console.log('[ImportPreviewTab] Device restored:', zabbixId);
};

// Função chamada pelo botão "Editar Configurações" dentro do modal readonly
// Esta função fecha o modal readonly e emite evento para o pai abrir modal de edição
const handleEditDevice = (device) => {
  console.log('[ImportPreviewTab] Edit button clicked, emitting to parent:', device);
  
  // Fecha o modal readonly
  showDetailsModal.value = false;
  
  // Emite evento para o DeviceImportManager abrir o modal de edição
  emit('edit-device', device, false);
};

const importSelected = () => {
  const hostsToImport = [];
  const dataSource = props.data && props.data.length > 0 ? props.data : [];
  
  // Encontra os objetos completos baseados nos IDs selecionados
  dataSource.forEach(group => {
    group.hosts.forEach(host => {
      if (selectedHosts.value.includes(host.zabbix_id)) {
        hostsToImport.push({
          ...host,
          group_name: group.name, // IMPORTANTE: Nome do grupo do Zabbix para matchGroup
          ip_address: host.ip      // Normaliza campo IP
        });
      }
    });
  });
  
  console.log('Importando hosts selecionados:', hostsToImport);
  emit('trigger-sync', hostsToImport);
};

onMounted(() => {
  // Buscar informações do servidor Zabbix
  fetchServerInfo();
  
  // Por padrão, expandir o primeiro grupo que tenha itens novos
  const dataSource = props.data && props.data.length > 0 ? props.data : [];
  const firstGroupWithNew = dataSource.find(g => g.hosts && g.hosts.some(h => !h.is_imported));
  if (firstGroupWithNew) {
    expandedGroups.value.push(firstGroupWithNew.zabbix_group_id);
  }
});
</script>

<style scoped>
.row-imported {
  background: var(--status-online-light);
}

.row-ignored {
  background: var(--surface-highlight);
  opacity: 0.7;
}
</style>

<style scoped>
/* Pequenos ajustes visuais */
.group-container:first-child .border-t {
  border-top: none;
}

/* Rotação do chevron */
.rotate-90 {
  transform: rotate(90deg);
}

/* Scrollbar invisível/minimalista */
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
