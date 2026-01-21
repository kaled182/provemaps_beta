<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex flex-col h-[calc(100vh-64px)] overflow-hidden transition-colors duration-300">
    
    <div class="flex-none px-6 py-5 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 z-10">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-2">
            <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-3zM14 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1h-4a1 1 0 01-1-1v-3z"/>
            </svg>
            Mosaicos
          </h1>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Visualização em grade de múltiplas câmeras.</p>
        </div>
        
        <button @click="openMosaicModal()" class="btn-primary">
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
          Novo Mosaico
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto custom-scrollbar p-6 bg-gray-50 dark:bg-gray-900">
      <div class="max-w-7xl mx-auto">
        
        <div v-if="mosaicsLoading" class="text-center py-12">
          <svg class="animate-spin h-8 w-8 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p class="text-sm text-gray-500 mt-2">Carregando...</p>
        </div>

        <div v-else-if="mosaics.length === 0" class="text-center py-12 border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-lg">
          <svg class="w-12 h-12 mx-auto text-gray-400 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-3zM14 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1h-4a1 1 0 01-1-1v-3z"/>
          </svg>
          <p class="text-sm text-gray-500 mt-2">Nenhum mosaico configurado</p>
          <button @click="openMosaicModal()" class="btn-primary mt-4">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            Criar Primeiro Mosaico
          </button>
        </div>

        <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div v-for="mosaic in mosaicsSorted" :key="mosaic.id" class="group bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-all cursor-pointer" @click="viewMosaic(mosaic)">
            <div class="flex justify-between items-start mb-3">
              <div class="flex-1">
                <h4 class="font-bold text-gray-900 dark:text-white">{{ mosaic.name }}</h4>
                <p class="text-xs text-gray-500 mt-1">{{ getLayoutLabel(mosaic.layout) }}</p>
              </div>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wide bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400">
                {{ mosaic.cameras?.length || 0 }} câm.
              </span>
            </div>
            
            <div class="mt-3 grid gap-1" :class="getGridClass(mosaic.layout)">
              <div v-for="(camera, idx) in getMosaicCameras(mosaic).slice(0, getLayoutCapacity(mosaic.layout))" :key="idx" class="aspect-video bg-gray-100 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 flex items-center justify-center text-[10px] text-gray-400 overflow-hidden">
                <span class="truncate px-1">{{ camera?.name || '—' }}</span>
              </div>
              <div v-for="n in (getLayoutCapacity(mosaic.layout) - getMosaicCameras(mosaic).length)" :key="'empty-' + n" class="aspect-video bg-gray-50 dark:bg-gray-900/50 rounded border border-dashed border-gray-300 dark:border-gray-700"></div>
            </div>
            
            <div class="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
              <button @click.stop="openMosaicModal(mosaic)" class="p-1 text-gray-400 hover:text-blue-600 rounded transition-colors" title="Editar">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
              </button>
              <button @click.stop="confirmDeleteMosaic(mosaic)" class="p-1 text-gray-400 hover:text-red-600 rounded transition-colors" title="Excluir">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Modal de Edição de Mosaico -->
    <div v-if="showMosaicModal" class="relative z-50" aria-labelledby="mosaic-config-title" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity" @click="closeMosaicModal"></div>
      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4 text-center">
          <div class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-3xl border border-gray-200 dark:border-gray-700 animate-fade-in">
            <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
              <div>
                <h3 class="text-base font-bold leading-6 text-gray-900 dark:text-white" id="mosaic-config-title">{{ mosaicForm.id ? 'Editar Mosaico' : 'Novo Mosaico' }}</h3>
                <p class="text-xs text-gray-500">Configure o layout e selecione as câmeras.</p>
              </div>
              <button @click="closeMosaicModal" class="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form class="p-6 space-y-4" autocomplete="off" @submit.prevent>
              <div class="space-y-4">
                <div class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Nome do Mosaico</label>
                    <input v-model="mosaicForm.name" type="text" class="input-custom" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Layout</label>
                    <select v-model="mosaicForm.layout" class="input-custom">
                      <option value="2x2">2x2 (4 câmeras)</option>
                      <option value="3x2">3x2 (6 câmeras)</option>
                      <option value="3x3">3x3 (9 câmeras)</option>
                      <option value="4x3">4x3 (12 câmeras)</option>
                      <option value="4x4">4x4 (16 câmeras)</option>
                    </select>
                    <p class="text-xs text-gray-400 mt-2">Escolha a disposição das câmeras na grade.</p>
                  </div>
                </div>

                <div>
                  <label class="label-custom">Câmeras Selecionadas</label>
                  <div class="border border-gray-200 dark:border-gray-700 rounded-md p-3 bg-gray-50 dark:bg-gray-900/50 min-h-[120px] max-h-[200px] overflow-y-auto custom-scrollbar">
                    <div v-if="selectedCameras.length === 0" class="text-center py-6 text-sm text-gray-400">
                      Nenhuma câmera selecionada
                    </div>
                    <div v-else class="flex flex-wrap gap-2">
                      <div v-for="camera in selectedCameras" :key="camera.id" class="inline-flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md text-sm">
                        <span class="text-gray-900 dark:text-gray-100">{{ camera.name }}</span>
                        <button @click="removeCameraFromSelection(camera.id)" class="text-gray-400 hover:text-red-500 transition-colors" type="button">
                          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                        </button>
                      </div>
                    </div>
                  </div>
                  <p class="text-xs text-gray-400 mt-2">{{ selectedCameras.length }} de {{ getLayoutCapacity(mosaicForm.layout) }} câmeras</p>
                </div>

                <div>
                  <label class="label-custom">Câmeras Disponíveis</label>
                  <div class="border border-gray-200 dark:border-gray-700 rounded-md max-h-[240px] overflow-y-auto custom-scrollbar">
                    <div v-if="availableCameras.length === 0" class="text-center py-6 text-sm text-gray-400">
                      Nenhuma câmera disponível
                    </div>
                    <button v-for="camera in availableCameras" :key="camera.id" @click="addCameraToSelection(camera)" type="button" class="w-full px-4 py-2.5 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 border-b border-gray-100 dark:border-gray-700 last:border-b-0 transition-colors flex items-center justify-between group">
                      <span class="text-sm text-gray-900 dark:text-gray-100">{{ camera.name }}</span>
                      <svg class="w-4 h-4 text-gray-400 group-hover:text-primary-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                    </button>
                  </div>
                </div>

              </div>
            </form>
            <div class="bg-gray-50 dark:bg-gray-800/50 px-6 py-3 flex justify-between gap-3 border-t border-gray-100 dark:border-gray-700">
              <div>
                <button v-if="mosaicForm.id" @click="deleteMosaic" class="btn-secondary text-red-500 border-red-500/40 hover:border-red-400 hover:text-red-400">
                  Remover
                </button>
              </div>
              <div class="flex gap-3">
                <button @click="closeMosaicModal" class="btn-secondary">Cancelar</button>
                <button @click="saveMosaic" class="btn-primary" :disabled="!mosaicForm.name.trim()">Salvar</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de Confirmação de Exclusão -->
    <div v-if="showDeleteConfirm" class="relative z-50" aria-labelledby="delete-confirm-title" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity"></div>
      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4">
          <div class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 text-left shadow-2xl transition-all sm:w-full sm:max-w-lg border border-gray-200 dark:border-gray-700">
            <div class="px-6 py-4">
              <h3 class="text-base font-semibold text-gray-900 dark:text-white mb-2" id="delete-confirm-title">Confirmar Exclusão</h3>
              <p class="text-sm text-gray-500 dark:text-gray-400">{{ deleteMessage }}</p>
            </div>
            <div class="bg-gray-50 dark:bg-gray-800/50 px-6 py-3 flex justify-end gap-3">
              <button @click="showDeleteConfirm = false; mosaicToDelete = null" class="btn-secondary">Cancelar</button>
              <button @click="confirmDelete" class="btn-primary bg-red-600 hover:bg-red-700">Excluir</button>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useApi } from '@/composables/useApi';
import { useNotification } from '@/composables/useNotification';

const router = useRouter();
const api = useApi();
const notify = useNotification();

const mosaicsLoading = ref(false);
const mosaics = ref([]);
const cameras = ref([]);
const showMosaicModal = ref(false);
const showDeleteConfirm = ref(false);
const mosaicToDelete = ref(null);

const mosaicForm = ref({
  id: null,
  name: '',
  layout: '2x2',
  cameras: [],
});

const mosaicsSorted = computed(() => [...mosaics.value].sort((a, b) => a.name.localeCompare(b.name)));

const selectedCameras = computed(() => {
  const ids = mosaicForm.value.cameras || [];
  return ids.map(id => cameras.value.find(c => c.id === id)).filter(Boolean);
});

const availableCameras = computed(() => {
  const selectedIds = new Set(mosaicForm.value.cameras || []);
  return cameras.value.filter(c => !selectedIds.has(c.id) && c.enabled);
});

const deleteMessage = computed(() => {
  if (!mosaicToDelete.value) return 'Deseja remover este mosaico?';
  return `Deseja remover o mosaico "${mosaicToDelete.value.name}"? Esta ação não pode ser desfeita.`;
});

const getLayoutLabel = (layout) => {
  const labels = {
    '2x2': '2×2 (4 câmeras)',
    '3x2': '3×2 (6 câmeras)',
    '3x3': '3×3 (9 câmeras)',
    '4x3': '4×3 (12 câmeras)',
    '4x4': '4×4 (16 câmeras)',
  };
  return labels[layout] || layout;
};

const getLayoutCapacity = (layout) => {
  const capacities = {
    '2x2': 4,
    '3x2': 6,
    '3x3': 9,
    '4x3': 12,
    '4x4': 16,
  };
  return capacities[layout] || 4;
};

const getGridClass = (layout) => {
  const classes = {
    '2x2': 'grid-cols-2',
    '3x2': 'grid-cols-3',
    '3x3': 'grid-cols-3',
    '4x3': 'grid-cols-4',
    '4x4': 'grid-cols-4',
  };
  return classes[layout] || 'grid-cols-2';
};

const getMosaicCameras = (mosaic) => {
  const ids = mosaic.cameras || [];
  return ids.map(id => cameras.value.find(c => c.id === id)).filter(Boolean);
};

const fetchMosaics = async () => {
  try {
    mosaicsLoading.value = true;
    const res = await api.get('/setup_app/video/api/mosaics/');
    if (res.success) {
      mosaics.value = res.mosaics || [];
    }
  } catch (e) {
    notify.error('Mosaicos', e.message || 'Erro ao carregar mosaicos.');
  } finally {
    mosaicsLoading.value = false;
  }
};

const fetchCameras = async () => {
  try {
    const res = await api.get('/setup_app/api/gateways/');
    if (res.success) {
      cameras.value = (res.gateways || []).filter(gw => gw.gateway_type === 'video');
    }
  } catch (e) {
    console.error('Erro ao carregar câmeras', e);
  }
};

const openMosaicModal = (mosaic = null) => {
  if (mosaic) {
    mosaicForm.value = {
      id: mosaic.id,
      name: mosaic.name,
      layout: mosaic.layout || '2x2',
      cameras: mosaic.cameras || [],
    };
  } else {
    mosaicForm.value = {
      id: null,
      name: '',
      layout: '2x2',
      cameras: [],
    };
  }
  showMosaicModal.value = true;
};

const closeMosaicModal = () => {
  showMosaicModal.value = false;
};

const addCameraToSelection = (camera) => {
  const capacity = getLayoutCapacity(mosaicForm.value.layout);
  if (mosaicForm.value.cameras.length >= capacity) {
    notify.warning('Mosaico', `Layout ${mosaicForm.value.layout} comporta apenas ${capacity} câmeras.`);
    return;
  }
  mosaicForm.value.cameras.push(camera.id);
};

const removeCameraFromSelection = (cameraId) => {
  mosaicForm.value.cameras = mosaicForm.value.cameras.filter(id => id !== cameraId);
};

const saveMosaic = async () => {
  try {
    const payload = {
      id: mosaicForm.value.id,
      name: mosaicForm.value.name,
      layout: mosaicForm.value.layout,
      cameras: mosaicForm.value.cameras,
    };

    let res;
    if (payload.id) {
      res = await api.patch(`/setup_app/video/api/mosaics/${payload.id}/`, payload);
    } else {
      res = await api.post('/setup_app/video/api/mosaics/', payload);
    }

    if (res.success) {
      notify.success('Mosaicos', 'Mosaico salvo com sucesso.');
      await fetchMosaics();
      closeMosaicModal();
    } else {
      notify.error('Mosaicos', res.message || 'Erro ao salvar mosaico.');
    }
  } catch (e) {
    notify.error('Mosaicos', e.message || 'Erro ao salvar mosaico.');
  }
};

const deleteMosaic = () => {
  mosaicToDelete.value = mosaicForm.value;
  showDeleteConfirm.value = true;
};

const confirmDeleteMosaic = (mosaic) => {
  mosaicToDelete.value = mosaic;
  showDeleteConfirm.value = true;
};

const confirmDelete = async () => {
  try {
    const mosaic = mosaicToDelete.value;
    if (!mosaic || !mosaic.id) {
      notify.error('Mosaicos', 'Mosaico inválido.');
      return;
    }
    const res = await api.delete(`/setup_app/video/api/mosaics/${mosaic.id}/`);
    if (res.success) {
      notify.success('Mosaicos', res.message || 'Mosaico removido.');
      await fetchMosaics();
      if (showMosaicModal.value) {
        closeMosaicModal();
      }
    } else {
      notify.error('Mosaicos', res.message || 'Erro ao remover mosaico.');
    }
  } catch (e) {
    notify.error('Mosaicos', e.message || 'Erro ao remover mosaico.');
  } finally {
    mosaicToDelete.value = null;
    showDeleteConfirm.value = false;
  }
};

const viewMosaic = (mosaic) => {
  router.push({ name: 'mosaic-viewer', params: { id: mosaic.id } });
};

onMounted(() => {
  fetchMosaics();
  fetchCameras();
});
</script>

<style scoped>
.label-custom {
  @apply block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5;
}

.input-custom {
  width: 100%;
  border-radius: 0.375rem;
  border: 1px solid #d1d5db;
  background-color: #ffffff;
  color: #111827;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  line-height: 1.25rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
  transition: box-shadow 0.15s ease, border-color 0.15s ease, background-color 0.15s ease;
}

.input-custom::placeholder {
  color: #9ca3af;
}

.input-custom:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.35);
}

html.dark .input-custom,
html[data-theme="dark"] .input-custom {
  background-color: #374151 !important;
  border-color: #4b5563 !important;
  color: #ffffff !important;
}

html.dark .input-custom::placeholder,
html[data-theme="dark"] .input-custom::placeholder {
  color: #9ca3af !important;
}

html.dark .input-custom:focus,
html[data-theme="dark"] .input-custom:focus {
  border-color: #818cf8 !important;
  box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.45) !important;
}

html.dark .input-custom:-webkit-autofill,
html[data-theme="dark"] .input-custom:-webkit-autofill {
  -webkit-box-shadow: 0 0 0 1000px #374151 inset !important;
  -webkit-text-fill-color: #ffffff !important;
}

html[data-theme="light"] .input-custom,
html:not(.dark)[data-theme="light"] .input-custom {
  background-color: #ffffff !important;
  border-color: #d1d5db !important;
  color: #111827 !important;
}

.btn-primary {
  @apply inline-flex items-center justify-center rounded-md bg-primary-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200;
}

.btn-secondary {
  @apply inline-flex items-center justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-gray-700 transition-all duration-200;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  @apply bg-gray-300 dark:bg-gray-600 rounded-full;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-400 dark:bg-gray-500;
}

.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
