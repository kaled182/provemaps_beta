<template>
  <div class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      
      <div class="fixed inset-0 bg-gray-500 dark:bg-gray-900/80 bg-opacity-75 transition-opacity" @click="$emit('close')"></div>
      <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

      <div class="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
        
        <!-- Header -->
        <div class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
          <div>
            <h3 class="text-lg leading-6 font-bold text-gray-900 dark:text-white flex items-center">
              <i :class="isBatch ? 'fas fa-layer-group text-indigo-600 dark:text-indigo-400' : 'fas fa-server text-gray-500 dark:text-gray-400'" class="mr-2"></i>
              {{ modalTitle }}
            </h3>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {{ isBatch ? 'Defina as configurações comuns para todos os itens selecionados.' : 'Dados de identificação e monitoramento.' }}
            </p>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 focus:outline-none">
            <span class="sr-only">Fechar</span>
            <i class="fas fa-times text-xl"></i>
          </button>
        </div>

        <!-- Content -->
        <div class="px-6 py-6 space-y-8">
          
          <!-- Seleção de Categoria -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-3">
              Categoria {{ isBatch ? 'dos Equipamentos' : '(Mapa)' }}
            </label>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              
              <!-- Card Backbone -->
              <div 
                @click="setCategory('backbone')"
                class="cursor-pointer border-2 rounded-lg p-3 flex flex-col items-center text-center transition-all duration-200 hover:shadow-md h-24 justify-center"
                :class="getCardClass('backbone')"
              >
                <div class="h-10 w-10 rounded-full flex items-center justify-center mb-2 text-2xl bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-400">
                  🖥️
                </div>
                <span class="font-bold text-gray-900 dark:text-white text-sm">Backbone</span>
                <span class="text-xs text-gray-500 dark:text-gray-400 mt-1">Routers, Switches L3</span>
              </div>

              <!-- Card GPON -->
              <div 
                @click="setCategory('gpon')"
                class="cursor-pointer border-2 rounded-lg p-3 flex flex-col items-center text-center transition-all duration-200 hover:shadow-md h-24 justify-center"
                :class="getCardClass('gpon')"
              >
                <div class="h-10 w-10 rounded-full flex items-center justify-center mb-2 text-2xl bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400">
                  📡
                </div>
                <span class="font-bold text-gray-900 dark:text-white text-sm">GPON / FTTx</span>
                <span class="text-xs text-gray-500 dark:text-gray-400 mt-1">OLTs, Splitters, ONUs</span>
              </div>

              <!-- Card DWDM -->
              <div 
                @click="setCategory('dwdm')"
                class="cursor-pointer border-2 rounded-lg p-3 flex flex-col items-center text-center transition-all duration-200 hover:shadow-md h-24 justify-center"
                :class="getCardClass('dwdm')"
              >
                <div class="h-10 w-10 rounded-full flex items-center justify-center mb-2 text-2xl bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-400">
                  🔬
                </div>
                <span class="font-bold text-gray-900 dark:text-white text-sm">DWDM</span>
                <span class="text-xs text-gray-500 dark:text-gray-400 mt-1">Transponders, Amplificadores</span>
              </div>

            </div>
          </div>

          <div class="border-t border-gray-200 dark:border-gray-700"></div>

          <!-- Grid 2 Colunas: Destino + Alertas -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            <!-- Coluna Esquerda: Destino -->
            <div class="space-y-4">
              <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Destino</h4>

              <!-- Grupo de Monitoramento -->
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
                  Grupo de Monitoramento
                </label>
                
                <!-- Modo: Lista de Seleção (Padrão) -->
                <div v-if="!isCreatingGroup">
                  <select 
                    v-model="selectedGroupProxy" 
                    @change="handleGroupChange"
                    class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md transition-shadow"
                    :class="{'text-gray-400 dark:text-gray-500': !selectedGroupProxy}"
                  >
                    <option value="" disabled>Escolha um grupo existente ou crie novo...</option>
                    <option v-for="grp in filteredGroups" :key="grp" :value="grp">{{ grp }}</option>
                    <option disabled>──────────────</option>
                    <option value="__CREATE_NEW__" class="text-indigo-600 font-medium">➕ Criar Novo Grupo...</option>
                  </select>
                  
                  <p v-if="!selectedGroupProxy && !isBatch" class="mt-1 text-xs text-indigo-600 dark:text-indigo-400 animate-pulse">
                    <i class="fas fa-info-circle"></i> Dica: Role até o final da lista para criar um novo grupo
                  </p>
                  <p v-else-if="selectedGroupProxy && !isBatch" class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Vincula o device às regras de alerta deste grupo.
                  </p>
                  <p v-else-if="isBatch" class="mt-1 text-xs text-orange-600 dark:text-orange-400">
                    <i class="fas fa-exclamation-triangle mr-1"></i> Todos os {{ activeDevices.length }} devices serão movidos para este grupo.
                  </p>
                </div>

                <!-- Modo: Criar Novo Grupo -->
                <div v-else class="animate-fade-in">
                  <div class="flex rounded-md shadow-sm">
                    <input 
                      ref="newGroupInput"
                      v-model="newGroupName" 
                      type="text" 
                      class="flex-1 min-w-0 block w-full px-3 py-2 rounded-l-md border border-gray-300 dark:border-gray-600 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm bg-indigo-50 dark:bg-indigo-900/30 text-gray-900 dark:text-white placeholder-indigo-400 dark:placeholder-indigo-500" 
                      placeholder="Digite o nome do novo grupo..." 
                    />
                    <button 
                      @click="cancelCreation"
                      type="button" 
                      class="inline-flex items-center px-3 py-2 border border-l-0 border-gray-300 dark:border-gray-600 rounded-r-md bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 text-sm transition-colors"
                      title="Voltar para lista"
                    >
                      <i class="fas fa-undo mr-1"></i> Lista
                    </button>
                  </div>
                  <p class="mt-1 text-xs text-indigo-600 dark:text-indigo-400">
                    <i class="fas fa-info-circle"></i> Este grupo será criado ao salvar.
                  </p>
                </div>
              </div>

              <!-- Lista de Dispositivos (Modo Batch) -->
              <div v-if="isBatch" class="bg-gray-50 dark:bg-gray-700/50 rounded-md p-3 border border-gray-200 dark:border-gray-600 max-h-40 overflow-y-auto">
                <h5 class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2 sticky top-0 bg-gray-50 dark:bg-gray-700/50">
                  Itens selecionados ({{ activeDevices.length }})
                </h5>
                <ul class="text-xs text-gray-600 dark:text-gray-300 space-y-1">
                  <li v-for="(dev, idx) in activeDevices" :key="idx" class="truncate">
                    <i class="fas fa-check text-green-500 dark:text-green-400 mr-1"></i> 
                    <strong>{{ dev.name }}</strong> 
                    <span class="text-gray-400 dark:text-gray-500">({{ dev.ip || dev.ip_address }})</span>
                  </li>
                </ul>
              </div>

              <!-- Campos Individuais (Modo Single) -->
              <div v-else class="space-y-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">Nome do Host</label>
                  <input 
                    v-model="formState.name" 
                    type="text" 
                    class="mt-1 input-standard" 
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">IP de Gerência</label>
                  <div class="mt-1 flex rounded-md shadow-sm">
                    <span class="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 text-sm">
                      <i class="fas fa-globe"></i>
                    </span>
                    <input 
                      v-model="formState.ip_address" 
                      type="text" 
                      class="flex-1 min-w-0 block w-full px-3 py-2 rounded-none rounded-r-md border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 sm:text-sm focus:ring-indigo-500 focus:border-indigo-500 cursor-not-allowed" 
                      readonly 
                    />
                  </div>
                </div>
              </div>
            </div>

            <!-- Coluna Direita: Canais de Alerta -->
            <div class="space-y-4">
              <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Canais de Alerta</h4>
              
              <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-3 border border-gray-200 dark:border-gray-600">
                
                <!-- Dashboard Alert Toggle -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center">
                    <i class="fas fa-desktop text-gray-400 dark:text-gray-500 w-6"></i>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Dashboard Map</span>
                  </div>
                  <button 
                    @click="formState.alerts.screen = !formState.alerts.screen"
                    type="button" 
                    class="relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none"
                    :class="formState.alerts.screen ? getCategoryColorClass() : 'bg-gray-200 dark:bg-gray-600'"
                  >
                    <span 
                      aria-hidden="true" 
                      class="translate-x-0 pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200" 
                      :class="{'translate-x-5': formState.alerts.screen}"
                    ></span>
                  </button>
                </div>

                <!-- WhatsApp Alert Toggle -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center">
                    <i class="fab fa-whatsapp text-green-500 dark:text-green-400 w-6"></i>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-200">WhatsApp Ops</span>
                  </div>
                  <button 
                    @click="formState.alerts.whatsapp = !formState.alerts.whatsapp"
                    type="button" 
                    class="relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none"
                    :class="formState.alerts.whatsapp ? 'bg-green-500 dark:bg-green-600' : 'bg-gray-200 dark:bg-gray-600'"
                  >
                    <span 
                      aria-hidden="true" 
                      class="translate-x-0 pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200" 
                      :class="{'translate-x-5': formState.alerts.whatsapp}"
                    ></span>
                  </button>
                </div>

                <!-- Info condicional WhatsApp -->
                <div v-if="formState.alerts.whatsapp" class="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600 animate-fade-in">
                  <p class="text-xs text-gray-500 dark:text-gray-400">
                    Será enviado para o grupo padrão da categoria <strong class="text-gray-700 dark:text-gray-300">{{ formState.category.toUpperCase() }}</strong>.
                  </p>
                </div>

                <!-- Info Zabbix ID (Modo Single) -->
                <div v-if="!isBatch" class="mt-4 pt-3 border-t border-gray-200 dark:border-gray-600 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>Origem Zabbix:</span>
                  <span class="font-mono bg-gray-200 dark:bg-gray-600 dark:text-gray-200 px-2 py-0.5 rounded">
                    {{ activeDevices[0]?.zabbix_id || 'Manual' }}
                  </span>
                </div>
              </div>
            </div>

          </div>
        </div>

        <!-- Footer Actions -->
        <div class="bg-gray-50 dark:bg-gray-800 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-gray-200 dark:border-gray-700">
          <button 
            @click="handleSave"
            type="button" 
            class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 text-base font-medium text-white focus:outline-none sm:ml-3 sm:w-auto sm:text-sm transition-colors"
            :class="saveButtonClass"
          >
            <i :class="isBatch ? 'fas fa-cloud-download-alt' : 'fas fa-save'" class="mr-2 mt-0.5"></i> 
            {{ isBatch ? `Importar ${activeDevices.length} Dispositivos` : 'Confirmar Importação' }}
          </button>
          <button 
            @click="$emit('close')"
            type="button" 
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-700 text-base font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Cancelar
          </button>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch, nextTick } from 'vue';

// Props polimórficas: suporta array (batch) OU objeto único (legacy)
const props = defineProps({
  devices: { type: Array, default: () => [] }, // Modo Batch
  device: { type: Object, default: null },     // Modo Single (Legacy support)
  isNew: { type: Boolean, default: false },    // Legacy flag
  availableGroups: { type: Array, default: () => [] }
});

const emit = defineEmits(['close', 'save']);

// Estado do Formulário (compartilhado entre single e batch)
const formState = reactive({
  category: 'backbone',
  group: '',
  alerts: { screen: true, whatsapp: false },
  name: '',       // Apenas para single mode
  ip_address: ''  // Apenas para single mode
});

// Variáveis de Controle de Interface
const isCreatingGroup = ref(false);
const newGroupName = ref('');
const selectedGroupProxy = ref('');
const newGroupInput = ref(null);

// --- LÓGICA DE INICIALIZAÇÃO ---

// Detecta se estamos em modo Batch ou Single
const isBatch = computed(() => props.devices && props.devices.length > 1);

// Normaliza a lista de devices em uso
const activeDevices = computed(() => {
  if (isBatch.value) return props.devices;
  if (props.device) return [props.device];
  return props.devices.length ? [props.devices[0]] : [];
});

// Watch para carregar dados quando o modal abre
watch(() => [props.device, props.devices], () => {
  // Reset estado de criação de grupo
  isCreatingGroup.value = false;
  newGroupName.value = '';
  
  if (isBatch.value) {
    // Lógica BATCH: Usa defaults
    formState.category = 'backbone';
    formState.group = '';
    formState.alerts = { screen: true, whatsapp: false };
    selectedGroupProxy.value = '';
  } else if (activeDevices.value.length > 0) {
    // Lógica SINGLE: Copia dados do primeiro device
    const singleDev = activeDevices.value[0];
    Object.assign(formState, {
      category: singleDev.category || 'backbone',
      group: singleDev.group || '',
      alerts: singleDev.alerts || { screen: true, whatsapp: false },
      name: singleDev.name,
      ip_address: singleDev.ip_address || singleDev.ip
    });
    selectedGroupProxy.value = formState.group || '';
  }
}, { immediate: true });

// --- LÓGICA DE UI ---

const modalTitle = computed(() => {
  return isBatch.value 
    ? `Importação em Lote (${activeDevices.value.length} itens)` 
    : (props.isNew ? 'Classificar e Importar Dispositivo' : 'Editar Configurações');
});

const filteredGroups = computed(() => {
  const term = formState.category.toLowerCase();
  if (!props.availableGroups.length) return [];
  
  return props.availableGroups.filter(g => {
    const gName = g.toLowerCase();
    if (term === 'backbone') return !gName.includes('olt') && !gName.includes('dwdm');
    if (term === 'gpon') return gName.includes('olt') || gName.includes('gpon') || gName.includes('ftth') || gName.includes('acesso');
    if (term === 'dwdm') return gName.includes('dwdm') || gName.includes('opt') || gName.includes('óptico');
    return true;
  });
});

const setCategory = (cat) => {
  formState.category = cat;
};

const handleGroupChange = async () => {
  if (selectedGroupProxy.value === '__CREATE_NEW__') {
    isCreatingGroup.value = true;
    selectedGroupProxy.value = '';
    newGroupName.value = '';
    await nextTick();
    newGroupInput.value?.focus();
  } else {
    formState.group = selectedGroupProxy.value;
    isCreatingGroup.value = false;
  }
};

const cancelCreation = () => {
  isCreatingGroup.value = false;
  selectedGroupProxy.value = formState.group || '';
};

// --- SALVAMENTO ---

const handleSave = () => {
  // Tratamento do Grupo
  let finalGroup = formState.group;
  let isNewGroup = false;

  if (isCreatingGroup.value) {
    if (!newGroupName.value.trim()) {
      alert('Por favor, digite o nome do novo grupo.');
      return;
    }
    finalGroup = newGroupName.value.trim();
    isNewGroup = true;
  } else {
    finalGroup = selectedGroupProxy.value;
  }

  // Validação básica
  if (!finalGroup) {
    alert('Selecione um grupo de monitoramento.');
    return;
  }

  // Prepara o Payload de Saída
  if (isBatch.value) {
    // Em Batch, aplicamos as configurações comuns a TODOS os itens originais
    const batchPayload = activeDevices.value.map(dev => ({
      ...dev, // Mantém dados originais (ID Zabbix, IP, etc)
      category: formState.category,
      group: finalGroup,
      is_new_group: isNewGroup, // Flag para backend saber se cria grupo
      alerts: { ...formState.alerts }
    }));
    
    emit('save', { mode: 'batch', devices: batchPayload });
  } else {
    // Em Single, mandamos o objeto único atualizado
    const singlePayload = {
      ...activeDevices.value[0],
      name: formState.name, // Nome pode ter sido editado
      category: formState.category,
      group: finalGroup,
      is_new_group: isNewGroup,
      alerts: { ...formState.alerts }
    };
    
    // Mantém compatibilidade com API antiga
    emit('save', singlePayload);
  }
};

// --- ESTILOS ---

const getCardClass = (cat) => {
  const isActive = formState.category === cat;
  const colors = {
    backbone: isActive 
      ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 ring-1 ring-indigo-500' 
      : 'border-gray-200 dark:border-gray-600 hover:border-indigo-300 dark:hover:border-indigo-400',
    gpon: isActive 
      ? 'border-green-500 bg-green-50 dark:bg-green-900/20 ring-1 ring-green-500' 
      : 'border-gray-200 dark:border-gray-600 hover:border-green-300 dark:hover:border-green-400',
    dwdm: isActive 
      ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20 ring-1 ring-purple-500' 
      : 'border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-400'
  };
  return colors[cat];
};

const getCategoryColorClass = () => {
  const colors = {
    backbone: 'bg-indigo-600 dark:bg-indigo-500',
    gpon: 'bg-green-600 dark:bg-green-500',
    dwdm: 'bg-purple-600 dark:bg-purple-500'
  };
  return colors[formState.category] || 'bg-indigo-600';
};

const saveButtonClass = computed(() => {
  if (formState.category === 'gpon') return 'bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600';
  if (formState.category === 'dwdm') return 'bg-purple-600 hover:bg-purple-700 dark:bg-purple-500 dark:hover:bg-purple-600';
  return 'bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600';
});
</script>

<style scoped>
.input-standard {
  @apply block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2 px-3 border;
}
.animate-fade-in {
  animation: fadeIn 0.2s ease-in-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-2px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
