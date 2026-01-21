<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex flex-col h-[calc(100vh-64px)] overflow-hidden transition-colors duration-300">
    
    <div class="flex-none px-6 py-5 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 z-10">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-2">
            <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            Gateways de Vídeo
          </h1>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Transcodificação e streaming com pré-visualização ao vivo.</p>
        </div>
        
        <button @click="openVideoGatewayModal()" class="btn-primary">
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
          Novo Gateway
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto custom-scrollbar p-6 bg-gray-50 dark:bg-gray-900">
      <div class="max-w-6xl mx-auto">
        
        <div v-if="gatewayLoading" class="text-center py-12">
          <svg class="animate-spin h-8 w-8 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p class="text-sm text-gray-500 mt-2">Carregando...</p>
        </div>

        <div v-else-if="videoGateways.length === 0" class="text-center py-12 border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-lg">
          <svg class="w-12 h-12 mx-auto text-gray-400 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <p class="text-sm text-gray-500 mt-2">Nenhum gateway de vídeo configurado</p>
          <button @click="openVideoGatewayModal()" class="btn-primary mt-4">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            Criar Primeiro Gateway
          </button>
        </div>

        <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div v-for="gateway in videoGatewaysSorted" :key="gateway.id" class="group bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-all">
            <div class="flex justify-between items-start mb-3">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wide bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                {{ gateway.provider || 'RESTREAMER' }}
              </span>
              <div class="flex items-center gap-2">
                <span class="flex h-2.5 w-2.5 relative">
                  <span v-if="getVideoGatewayStatusColor(gateway) === 'bg-emerald-400'" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="getVideoGatewayStatusColor(gateway)"></span>
                </span>
              </div>
            </div>
            <h4 class="font-bold text-gray-900 dark:text-white truncate">{{ gateway.name }}</h4>
            <p class="text-xs text-gray-500 mt-1">{{ getVideoGatewayStatusLabel(gateway) }}</p>
            <p class="text-xs text-gray-400 font-mono mt-1 truncate bg-gray-50 dark:bg-gray-900/50 p-1 rounded">
              {{ gateway.config?.stream_url || 'Sem URL configurada' }}
            </p>
            
            <div class="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
              <button @click="openVideoGatewayModal(gateway)" class="p-1 text-gray-400 hover:text-blue-600 rounded transition-colors" title="Editar">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
              </button>
              <button @click="confirmDeleteGateway(gateway)" class="p-1 text-gray-400 hover:text-red-600 rounded transition-colors" title="Excluir">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Modal Gateway de Vídeo (será implementado com o código da ConfigurationPage) -->
    <div v-if="showGatewayModal" class="fixed inset-0 z-50 overflow-y-auto" @click.self="closeGatewayModal">
      <div class="flex min-h-screen items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"></div>
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full p-6">
          <p class="text-sm text-gray-500">Modal em desenvolvimento...</p>
          <button @click="closeGatewayModal" class="btn-white mt-4">Fechar</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useApi } from '@/composables/useApi';
import { useNotification } from '@/composables/useNotification';

const api = useApi();
const notify = useNotification();

const gatewayLoading = ref(false);
const gateways = ref([]);
const showGatewayModal = ref(false);

const videoGateways = computed(() => gateways.value.filter((gw) => gw.gateway_type === 'video'));
const videoGatewaysSorted = computed(() => [...videoGateways.value].sort((a, b) => a.priority - b.priority));

const getVideoGatewayStatusLabel = (gateway) => {
  if (!gateway) return '—';
  if (!gateway.enabled) return 'Inativo';
  if (gateway.config?.preview_url) return 'Prévia ativa';
  return 'Ativo';
};

const getVideoGatewayStatusColor = (gateway) => {
  if (!gateway || !gateway.enabled) return 'bg-gray-500';
  if (gateway.config?.preview_url) return 'bg-emerald-400';
  return 'bg-blue-400';
};

const fetchGateways = async () => {
  try {
    gatewayLoading.value = true;
    const res = await api.get('/setup_app/api/gateways/');
    if (res.success) {
      gateways.value = res.gateways || [];
    }
  } catch (e) {
    notify.error('Gateways', e.message || 'Erro ao carregar gateways.');
  } finally {
    gatewayLoading.value = false;
  }
};

const openVideoGatewayModal = (gateway = null) => {
  // TODO: Implementar com o código da ConfigurationPage
  showGatewayModal.value = true;
};

const closeGatewayModal = () => {
  showGatewayModal.value = false;
};

const confirmDeleteGateway = (gateway) => {
  // TODO: Implementar exclusão
  notify.info('Exclusão', 'Funcionalidade em desenvolvimento');
};

onMounted(() => {
  fetchGateways();
});
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.3);
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(156, 163, 175, 0.5);
}
</style>
