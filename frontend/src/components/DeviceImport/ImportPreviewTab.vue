<template>
  <div class="space-y-6">
    
    <!-- Header com Filtros e Ações -->
    <div class="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="flex items-center gap-4 flex-1">
        <div class="w-64">
          <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Origem da Importação</label>
          <select 
            v-model="selectedServerId" 
            @change="fetchPreviewData" 
            class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
          >
            <option value="1">Zabbix Principal (10.0.0.50)</option>
            <option value="2">Zabbix Secundário / Proxy</option>
          </select>
        </div>

        <div class="flex-1">
          <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Filtrar Hosts</label>
          <div class="relative rounded-md shadow-sm">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <i class="fas fa-search text-gray-400 dark:text-gray-500"></i>
            </div>
            <input 
              type="text" 
              v-model="searchQuery" 
              class="focus:ring-indigo-500 focus:border-indigo-500 block w-full pl-10 sm:text-sm border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 rounded-md" 
              placeholder="Nome ou IP..."
            >
          </div>
        </div>
      </div>

      <div class="flex items-end">
        <button 
          @click="importSelected" 
          :disabled="selectedCount === 0"
          class="w-full md:w-auto inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <i class="fas fa-cloud-download-alt mr-2"></i>
          Importar Selecionados ({{ selectedCount }})
        </button>
      </div>
    </div>

    <!-- Lista de Grupos Hierárquica -->
    <div class="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
      <ul class="divide-y divide-gray-200 dark:divide-gray-700">
        <li v-for="group in filteredGroups" :key="group.zabbix_group_id" class="group-container">
          
          <!-- Cabeçalho do Grupo -->
          <div 
            class="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition" 
            @click="toggleGroup(group.zabbix_group_id)"
          >
            <div class="flex items-center">
              <i 
                class="fas fa-chevron-right text-gray-400 dark:text-gray-500 mr-3 transition-transform duration-200"
                :class="{ 'rotate-90': expandedGroups.includes(group.zabbix_group_id) }"
              ></i>
              <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ group.name }}</span>
              <span class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-200">
                {{ group.hosts.length }} hosts
              </span>
            </div>
            
            <div class="flex items-center" @click.stop>
              <label class="inline-flex items-center text-xs text-gray-500 dark:text-gray-400 mr-3">
                <input 
                  type="checkbox" 
                  class="form-checkbox h-4 w-4 text-indigo-600 rounded border-gray-300 mr-1"
                  @change="toggleSelectGroup(group, $event.target.checked)"
                  :checked="isGroupFullySelected(group)"
                  :indeterminate.prop="isGroupPartiallySelected(group)"
                >
                Selecionar Novos
              </label>
            </div>
          </div>

          <!-- Hosts dentro do Grupo -->
          <div v-show="expandedGroups.includes(group.zabbix_group_id)" class="border-t border-gray-200 dark:border-gray-700">
            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                <tr v-for="host in group.hosts" :key="host.zabbix_id" :class="{'bg-green-50 dark:bg-green-900/20': host.is_imported}">
                  <td class="px-6 py-4 whitespace-nowrap w-10">
                    <input 
                      v-if="!host.is_imported"
                      type="checkbox" 
                      v-model="selectedHosts" 
                      :value="host.zabbix_id"
                      class="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300 rounded"
                    >
                    <i v-else class="fas fa-check-circle text-green-500 dark:text-green-400 text-lg" title="Já importado"></i>
                  </td>

                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                      <div class="ml-0">
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {{ host.name }}
                        </div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">
                          {{ host.ip }} 
                          <span v-if="host.mac" class="text-xs text-gray-400 dark:text-gray-500 ml-2">({{ host.mac }})</span>
                        </div>
                      </div>
                    </div>
                  </td>

                  <td class="px-6 py-4 whitespace-nowrap">
                    <span 
                      class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                      :class="host.is_imported ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400' : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400'"
                    >
                      {{ host.is_imported ? 'Importado' : 'Novo Detectado' }}
                    </span>
                  </td>

                  <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button 
                      v-if="!host.is_imported"
                      @click="$emit('edit-device', host, true)" 
                      class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300"
                    >
                      Configurar e Importar
                    </button>
                    <button 
                      v-else
                      class="text-gray-400 dark:text-gray-600 cursor-not-allowed"
                      disabled
                    >
                      Ver Detalhes
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </li>
      </ul>
      
      <div v-if="filteredGroups.length === 0" class="text-center py-10">
        <p class="text-gray-500 dark:text-gray-400">Nenhum grupo ou host encontrado com este filtro.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';

const props = defineProps(['data']); // Dados brutos passados pelo pai
const emit = defineEmits(['edit-device', 'trigger-sync']);

// Estado Local
const selectedServerId = ref('1');
const searchQuery = ref('');
const expandedGroups = ref([]); // IDs dos grupos abertos
const selectedHosts = ref([]); // IDs dos hosts selecionados para importar

// Mock Data (Isso viria do seu Backend Python futuramente)
// Estrutura: Lista de Grupos, cada um contendo uma lista de Hosts
const mockZabbixData = ref([
  {
    zabbix_group_id: 101,
    name: 'Zabbix Servers',
    hosts: [
      { zabbix_id: '10084', name: 'Zabbix server', ip: '127.0.0.1', is_imported: true }
    ]
  },
  {
    zabbix_group_id: 102,
    name: 'Linux Servers',
    hosts: [
      { zabbix_id: '10085', name: 'Web-App-01', ip: '192.168.1.10', is_imported: true },
      { zabbix_id: '10086', name: 'DB-Master-01', ip: '192.168.1.15', is_imported: false }, // Novo
      { zabbix_id: '10087', name: 'Cache-Redis-01', ip: '192.168.1.20', is_imported: false } // Novo
    ]
  },
  {
    zabbix_group_id: 103,
    name: 'Network Devices',
    hosts: [
      { zabbix_id: '10090', name: 'Core-Switch-L3', ip: '10.0.0.1', mac: 'AA:BB:CC:DD:EE:FF', is_imported: false },
      { zabbix_id: '10091', name: 'Border-Router', ip: '200.200.200.1', is_imported: true }
    ]
  }
]);

// Computed: Filtragem
const filteredGroups = computed(() => {
  const query = searchQuery.value.toLowerCase();
  
  return mockZabbixData.value.map(group => {
    // Se o nome do grupo bate, mostra tudo. Se não, filtra os hosts dentro.
    const groupMatch = group.name.toLowerCase().includes(query);
    
    // Filtra hosts
    const filteredHosts = group.hosts.filter(h => 
      h.name.toLowerCase().includes(query) || 
      h.ip.includes(query)
    );

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

const importSelected = () => {
  const hostsToImport = [];
  // Encontra os objetos completos baseados nos IDs selecionados
  mockZabbixData.value.forEach(group => {
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
  // Por padrão, expandir o primeiro grupo que tenha itens novos
  const firstGroupWithNew = mockZabbixData.value.find(g => g.hosts.some(h => !h.is_imported));
  if (firstGroupWithNew) {
    expandedGroups.value.push(firstGroupWithNew.zabbix_group_id);
  }
});
</script>

<style scoped>
/* Pequenos ajustes visuais */
.group-container:first-child .border-t {
  border-top: none;
}

/* Rotação do chevron */
.rotate-90 {
  transform: rotate(90deg);
}
</style>
