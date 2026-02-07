<template>
  <div :class="embedded ? '' : 'min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex flex-col h-[calc(100vh-64px)] overflow-hidden transition-colors duration-300'">
    
    <div v-if="!embedded" class="flex-none px-6 py-5 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 z-10">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-2">
            <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            Câmeras
          </h1>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Gestão de câmeras e streaming de vídeo.</p>
        </div>
        
        <button @click="openVideoGatewayModal()" class="btn-primary">
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
          Nova Câmera
        </button>
      </div>
    </div>

    <div :class="embedded ? '' : 'flex-1 overflow-y-auto custom-scrollbar bg-gray-50 dark:bg-gray-900'">
      <div :class="embedded ? '' : ''">
        
        <!-- Campo de Busca -->
        <div class="sticky top-0 z-10 bg-gray-50 dark:bg-gray-900 px-6 pt-4 pb-3">
          <div class="relative">
            <svg class="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="Filtrar câmeras ou sites..." 
              class="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors"
            />
          </div>
        </div>

        <div v-if="gatewayLoading" class="text-center py-12">
          <svg class="animate-spin h-8 w-8 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p class="text-sm text-gray-500 mt-2">Carregando...</p>
        </div>

        <div v-else-if="videoGateways.length === 0" class="text-center py-12 mx-6 border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-lg">
          <svg class="w-12 h-12 mx-auto text-gray-400 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <p class="text-sm text-gray-500 mt-2">Nenhuma câmera configurada</p>
          <button @click="openVideoGatewayModal()" class="btn-primary mt-4">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            Adicionar Primeira Câmera
          </button>
        </div>

        <!-- Lista Agrupada por Site -->
        <div v-else class="space-y-2 px-6 pb-6">
          <div 
            v-for="(cameras, siteName) in camerasBySite" 
            :key="siteName"
            class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-800"
          >
            <!-- Header do Grupo (colapsável) -->
            <button
              @click="toggleSiteGroup(siteName)"
              class="w-full px-4 py-3 flex items-center justify-between bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div class="flex items-center gap-3">
                <svg 
                  class="w-4 h-4 text-gray-400 transition-transform"
                  :class="{ 'rotate-90': expandedSites[siteName] }"
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
                <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ siteName }}</span>
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                  {{ cameras.length }}
                </span>
              </div>
              <svg 
                class="w-5 h-5 text-gray-400"
                :class="{ 'rotate-180': expandedSites[siteName] }"
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>

            <!-- Tabela de Câmeras -->
            <div v-show="expandedSites[siteName]" class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/30">
                  <tr>
                    <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider w-16">Status</th>
                    <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Nome / Endereço</th>
                    <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Tipo</th>
                    <th class="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider w-48">Ações</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                  <tr 
                    v-for="camera in cameras" 
                    :key="camera.id"
                    class="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                  >
                    <!-- Status -->
                    <td class="px-4 py-3">
                      <span class="flex h-2.5 w-2.5 relative">
                        <span 
                          v-if="getVideoGatewayStatusColor(camera) === 'bg-emerald-400'" 
                          class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
                        ></span>
                        <span 
                          class="relative inline-flex rounded-full h-2.5 w-2.5" 
                          :class="getVideoGatewayStatusColor(camera)"
                        ></span>
                      </span>
                    </td>

                    <!-- Nome / IP -->
                    <td class="px-4 py-3">
                      <div class="flex flex-col">
                        <span class="font-semibold text-gray-900 dark:text-gray-100">{{ camera.name }}</span>
                        <span class="text-xs text-gray-500 dark:text-gray-400 font-mono truncate max-w-md">
                          {{ camera.config?.stream_url || 'Sem URL configurada' }}
                        </span>
                      </div>
                    </td>

                    <!-- Tipo -->
                    <td class="px-4 py-3">
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
                        {{ camera.provider || 'RTMP' }}
                      </span>
                    </td>

                    <!-- Ações -->
                    <td class="px-4 py-3">
                      <div class="flex items-center justify-end gap-2">
                        <button 
                          @click="openVideoGatewayModal(camera)" 
                          class="inline-flex items-center px-3 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
                          title="Configurar"
                        >
                          <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                          </svg>
                          Configurar
                        </button>
                        <button 
                          @click="confirmDeleteGateway(camera)" 
                          class="p-1.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                          title="Excluir"
                        >
                          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Modal Gateway de Vídeo -->
    <div v-if="showGatewayModal" class="relative z-50" aria-labelledby="gateway-config-title" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity" @click="closeGatewayModal"></div>
      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4 text-center">
          <div class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-2xl border border-gray-200 dark:border-gray-700 animate-fade-in">
            <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
              <div>
                <h3 class="text-base font-bold leading-6 text-gray-900 dark:text-white" id="gateway-config-title">{{ videoGatewayForm.id ? 'Editar Gateway de Vídeo' : 'Novo Gateway de Vídeo' }}</h3>
                <p class="text-xs text-gray-500">Transcodificação e streaming HLS com pré-visualização.</p>
              </div>
              <button @click="closeGatewayModal" class="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form class="p-6 space-y-4" autocomplete="off" @submit.prevent>
              <div v-if="activeGateway === 'video'" class="space-y-4">
                <div class="grid gap-4 md:grid-cols-3">
                  <div class="md:col-span-2">
                    <label class="label-custom">Nome da Câmera</label>
                    <input v-model="videoGatewayForm.name" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Prioridade</label>
                    <input v-model.number="videoGatewayForm.priority" type="number" min="1" class="input-custom font-mono" autocomplete="off">
                  </div>
                </div>

                <div>
                  <label class="label-custom">Site</label>
                  <input 
                    v-model="videoGatewayForm.site_name" 
                    type="text" 
                    class="input-custom" 
                    placeholder="Digite o nome do site onde a câmera está instalada"
                    autocomplete="off"
                    list="site-suggestions"
                  >
                  <datalist id="site-suggestions">
                    <option v-for="site in availableSites" :key="site" :value="site"></option>
                  </datalist>
                  <p class="text-xs text-gray-400 mt-2">Local físico onde a câmera está instalada. As câmeras serão agrupadas por site.</p>
                </div>

                <div class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Protocolo de Entrada</label>
                    <select v-model="videoGatewayForm.config.stream_type" class="input-custom">
                      <option value="rtmp">RTMP</option>
                      <option value="rtsp">RTSP</option>
                      <option value="hls">HLS</option>
                    </select>
                    <p class="text-xs text-gray-400 mt-2">Selecione o protocolo utilizado pela câmera ou encoder.</p>
                  </div>
                  <div>
                    <label class="label-custom">Chave de Restream (opcional)</label>
                    <input v-model="videoGatewayForm.config.restream_key" type="text" class="input-custom font-mono" placeholder="gateway_{{ videoGatewayForm.id || 'novo' }}" autocomplete="off">
                    <p class="text-xs text-gray-400 mt-2">Se vazio, a chave é gerada automaticamente.</p>
                  </div>
                </div>

                <div>
                  <label class="label-custom">URL do Stream</label>
                  <input v-model="videoGatewayForm.config.stream_url" type="text" class="input-custom font-mono" placeholder="rtsp://camera.local/stream" autocomplete="off">
                  <p class="text-xs text-gray-400 mt-2">Use RTSP, RTMP ou HLS conforme selecionado acima.</p>
                </div>

                <div class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Token de Reprodução (opcional)</label>
                    <input v-model="videoGatewayForm.config.playback_token" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Base pública HLS (opcional)</label>
                    <input v-model="videoGatewayForm.config.hls_public_base_url" type="text" class="input-custom font-mono" placeholder="https://videos.seudominio.com/hls" autocomplete="off">
                    <p class="text-xs text-gray-400 mt-2">Sobrescreve a URL padrão exposta pelo Docker.</p>
                  </div>
                </div>

                <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-900/40 p-4 space-y-4">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-gray-200">Pré-visualização</p>
                    <p class="text-xs text-gray-400">Gera uma saída HLS temporária para validar a entrada.</p>
                  </div>
                  <div class="flex items-center gap-3 text-xs text-gray-400">
                    <button
                      v-if="!videoPreview.url && videoGatewayForm.id && videoGatewayForm.config.stream_url"
                      class="btn-primary text-xs h-8 px-4"
                      type="button"
                      @click="startVideoPreview({ silent: false })"
                      :disabled="isVideoPreviewLoading"
                    >
                      <span v-if="isVideoPreviewLoading" class="inline-flex h-3 w-3 border border-white border-t-transparent rounded-full animate-spin mr-2"></span>
                      {{ isVideoPreviewLoading ? 'Iniciando...' : 'Iniciar transmissão' }}
                    </button>
                    <span v-else class="flex items-center gap-2">
                      <span
                        v-if="isVideoPreviewLoading"
                        class="inline-flex h-3 w-3 border border-gray-300 border-t-transparent rounded-full animate-spin"
                      ></span>
                      {{ videoPreview.url ? 'Transmissão ativa' : 'Aguardando stream URL...' }}
                    </span>
                    <button
                      v-if="videoPreview.url"
                      class="btn-secondary text-xs h-8"
                      type="button"
                      @click="stopVideoPreview()"
                    >
                      Encerrar
                    </button>
                  </div>
                </div>
                <div class="relative h-64 bg-black rounded-md overflow-hidden">
                  <!-- Usar CameraPlayer para HLS -->
                  <CameraPlayer 
                    v-if="videoPreview.url && videoGatewayForm.id"
                    :camera="{
                      id: videoGatewayForm.id,
                      name: videoGatewayForm.name || 'Prévia',
                      playback_url: videoPreview.url
                    }"
                    :muted="true"
                    class="absolute inset-0"
                  />
                  <div
                    v-if="isVideoPreviewLoading || videoPreview.status === 'retrying'"
                    class="absolute inset-0 bg-gray-900/90 flex flex-col items-center justify-center text-sm text-gray-200 gap-3"
                  >
                    <div class="flex items-center gap-3">
                      <svg class="animate-spin h-6 w-6 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span class="font-medium">{{ videoPreview.status === 'retrying' ? 'Conectando ao stream...' : 'Aguarde, carregando vídeo...' }}</span>
                    </div>
                    <span class="text-xs text-gray-300">Isso pode levar até 20 segundos</span>
                    <div class="mt-2 flex gap-1">
                      <span class="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style="animation-delay: 0s"></span>
                      <span class="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style="animation-delay: 0.2s"></span>
                      <span class="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style="animation-delay: 0.4s"></span>
                    </div>
                  </div>
                  <div
                    v-else-if="videoPreview.error"
                    class="absolute inset-0 bg-gray-900/80 flex flex-col items-center justify-center text-center px-6 py-4 gap-3"
                  >
                    <svg class="h-10 w-10 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <p class="text-sm text-red-300 font-medium">Erro ao carregar vídeo</p>
                    <p class="text-xs text-gray-400">{{ videoPreview.error }}</p>
                  </div>
                  <div
                    v-else-if="!videoPreview.url && !isVideoPreviewActive"
                    class="absolute inset-0 flex items-center justify-center text-xs text-gray-500 text-center px-4"
                  >
                    Preparando prévia automática...
                  </div>
                </div>
                <div class="flex items-center justify-between gap-4 text-[11px] text-gray-400">
                  <span v-if="previewUrlDisplay" class="truncate" :title="previewUrlDisplay">URL: {{ previewUrlDisplay }}</span>
                  <span v-else class="text-gray-500">URL ainda não gerada.</span>
                  <span
                    v-if="videoGatewayForm.config.preview_url && !videoPreview.url"
                    class="text-gray-500"
                  >Prévia anterior disponível.</span>
                </div>
              </div>
            </div>
            </form>
            <div class="bg-gray-50 dark:bg-gray-800/50 px-6 py-3 flex justify-between gap-3 border-t border-gray-100 dark:border-gray-700">
            <div class="flex items-center gap-4">
              <button
                v-if="videoGatewayForm.id"
                @click="deleteGateway"
                class="btn-secondary text-red-500 border-red-500/40 hover:border-red-400 hover:text-red-400"
              >
                Remover
              </button>
              <label class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
                <input v-model="videoGatewayForm.enabled" type="checkbox" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500 h-4 w-4" autocomplete="off">
                Ativar vídeo
              </label>
            </div>
            <div class="flex justify-end gap-3 ml-auto">
              <button @click="closeGatewayModal" class="btn-secondary">Cancelar</button>
              <button @click="saveGateway" class="btn-primary">Salvar</button>
            </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm Delete Dialog -->
    <div v-if="showDeleteConfirm" class="fixed inset-0 z-50 overflow-y-auto" @click.self="showDeleteConfirm = false">
      <div class="flex min-h-screen items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"></div>
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
          <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-2">Remover câmera</h3>
          <p class="text-sm text-gray-500 mb-6">{{ deleteMessage }}</p>
          <div class="flex justify-end gap-3">
            <button @click="showDeleteConfirm = false" class="btn-secondary">Cancelar</button>
            <button @click="confirmDelete" class="btn-primary bg-red-600 hover:bg-red-700">Remover</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick, onUnmounted } from 'vue';
import Hls from 'hls.js';
import { useApi } from '@/composables/useApi';
import { useNotification } from '@/composables/useNotification';
import CameraPlayer from '@/components/Video/CameraPlayer.vue';

const props = defineProps({
  embedded: {
    type: Boolean,
    default: false
  }
});

const api = useApi();
const notify = useNotification();

const gatewayLoading = ref(false);
const gateways = ref([]);
const showGatewayModal = ref(false);
const showDeleteConfirm = ref(false);
const gatewayToDelete = ref(null);
const activeGateway = ref('video');
const searchQuery = ref('');
const expandedSites = ref({});
const inventorySites = ref([]);

const videoGatewayForm = ref({
  id: null,
  name: 'Gateway de Vídeo',
  provider: 'restreamer',
  priority: 1,
  enabled: false,
  site_name: '',
  config: {
    stream_type: 'rtmp',
    stream_url: '',
    restream_key: '',
    preview_url: '',
    preview_active: false,
    playback_token: '',
    hls_public_base_url: '',
  },
});

const videoPreview = ref({
  url: '',
  loading: false,
  status: 'idle',
  error: '',
});

const hlsInstance = ref(null);
const videoPreviewElement = ref(null);
const previewRetryCount = ref(0);
const MAX_PREVIEW_RETRIES = 10;
const autoPreviewHandle = ref(null);
const previewLoadHandle = ref(null);
const previewReloadHandle = ref(null);
const videoElementListeners = ref([]);
const watchdogInterval = ref(null);
const useIframePreview = ref(false);
const iframeFallbackHandle = ref(null);
const iframeReady = ref(false);

const videoGateways = computed(() => gateways.value.filter((gw) => gw.gateway_type === 'video'));
const videoGatewaysSorted = computed(() => [...videoGateways.value].sort((a, b) => a.priority - b.priority));

// Agrupar câmeras por Site com busca
const camerasBySite = computed(() => {
  const filtered = videoGatewaysSorted.value.filter(camera => {
    if (!searchQuery.value) return true;
    const query = searchQuery.value.toLowerCase();
    const siteName = (camera.site_name || 'Sem Site').toLowerCase();
    const cameraName = (camera.name || '').toLowerCase();
    const streamUrl = (camera.config?.stream_url || '').toLowerCase();
    return siteName.includes(query) || cameraName.includes(query) || streamUrl.includes(query);
  });

  const grouped = {};
  filtered.forEach(camera => {
    const site = camera.site_name || 'Sem Site';
    if (!grouped[site]) {
      grouped[site] = [];
    }
    grouped[site].push(camera);
  });

  // Ordenar sites alfabeticamente
  return Object.keys(grouped)
    .sort((a, b) => {
      if (a === 'Sem Site') return 1;
      if (b === 'Sem Site') return -1;
      return a.localeCompare(b);
    })
    .reduce((acc, key) => {
      acc[key] = grouped[key];
      return acc;
    }, {});
});

// Sites disponíveis para autocomplete (do inventário)
const availableSites = computed(() => {
  return inventorySites.value
    .map(site => site.name || site.display_name)
    .filter(name => name) // Remove nulos/vazios
    .sort();
});

const isM3U8Url = computed(() => {
  const url = videoPreview.value.url || '';
  return url.toLowerCase().endsWith('.m3u8');
});
const canUseVideoElement = computed(() => {
  const url = videoPreview.value.url || '';
  return url.toLowerCase().endsWith('.m3u8');
});
const isVideoPreviewActive = computed(() => videoPreview.value.status === 'playing');
const isVideoPreviewLoading = computed(() => videoPreview.value.loading);
const previewUrlDisplay = computed(
  () =>
    videoPreview.value.url ||
    videoGatewayForm.value.config.preview_playback_url ||
    videoGatewayForm.value.config.preview_url ||
    ''
);
const deleteMessage = computed(() => {
  if (!gatewayToDelete.value) return 'Deseja remover esta câmera?';
  return `Deseja remover a câmera "${gatewayToDelete.value.name}"? Esta ação não pode ser desfeita.`;
});

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

// Resolve a URL de pré-visualização ideal para playback.
// Se houver base HLS + restream_key e o tipo for RTMP/RTSP,
// força uso de HLS (.m3u8) para evitar erros do player WebRTC.
const resolvePreviewUrl = (url) => {
  try {
    const cfg = videoGatewayForm.value?.config || {};
    const base = (cfg.hls_public_base_url || '').trim();
    const key = (cfg.restream_key || '').trim();
    const type = (cfg.stream_type || '').toLowerCase();
    if (base && key && (type === 'rtmp' || type === 'rtsp')) {
      const normalizedBase = base.replace(/\/+$/g, '');
      const resolved = `${normalizedBase}/${key}.m3u8`;
      console.debug('[VideoPreview] Resolved HLS URL', {
        base: normalizedBase,
        key,
        type,
        resolved,
      });
      return resolved;
    }
  } catch (error) {
    console.debug('[VideoPreview] Failed to resolve HLS URL', error);
  }
  return url || '';
};

const fetchGateways = async () => {
  try {
    gatewayLoading.value = true;
    const res = await api.get('/setup_app/api/gateways/');
    if (res.success) {
      gateways.value = res.gateways || [];
      // Inicializar todos os sites expandidos
      initializeExpandedSites();
    }
  } catch (e) {
    notify.error('Câmeras', e.message || 'Erro ao carregar câmeras.');
  } finally {
    gatewayLoading.value = false;
  }
};

const fetchInventorySites = async () => {
  try {
    let url = '/api/v1/sites/?page_size=500';
    const collection = [];
    
    while (url) {
      const response = await fetch(url, { credentials: 'include' });
      if (!response.ok) {
        console.warn('Erro ao buscar sites do inventário:', response.status);
        break;
      }
      const data = await response.json();
      const pageItems = Array.isArray(data) ? data : data.results || [];
      collection.push(...pageItems);
      url = data.next || null;
    }
    
    inventorySites.value = collection;
  } catch (e) {
    console.warn('Erro ao carregar sites do inventário:', e);
    inventorySites.value = [];
  }
};

const initializeExpandedSites = () => {
  const sites = {};
  videoGateways.value.forEach(camera => {
    const site = camera.site_name || 'Sem Site';
    sites[site] = true; // Todos expandidos por padrão
  });
  expandedSites.value = sites;
};

const toggleSiteGroup = (siteName) => {
  expandedSites.value[siteName] = !expandedSites.value[siteName];
};

const syncVideoGatewayInList = (gatewayId, configUpdates = {}) => {
  if (!gatewayId) return;
  const index = gateways.value.findIndex((item) => item.id === gatewayId);
  if (index === -1) return;
  const current = gateways.value[index];
  gateways.value.splice(index, 1, {
    ...current,
    config: {
      ...(current.config || {}),
      ...configUpdates,
    },
  });
};

const clearAutoPreviewHandle = () => {
  if (autoPreviewHandle.value) {
    clearTimeout(autoPreviewHandle.value);
    autoPreviewHandle.value = null;
  }
};

const clearPreviewLoadHandle = () => {
  if (previewLoadHandle.value) {
    clearTimeout(previewLoadHandle.value);
    previewLoadHandle.value = null;
  }
};

const clearPreviewReloadHandle = () => {
  if (previewReloadHandle.value) {
    clearTimeout(previewReloadHandle.value);
    previewReloadHandle.value = null;
  }
};

const clearIframeFallbackHandle = () => {
  if (iframeFallbackHandle.value) {
    clearTimeout(iframeFallbackHandle.value);
    iframeFallbackHandle.value = null;
  }
};

const startIframeFallbackTimer = (delayMs = 12000) => {
  clearIframeFallbackHandle();
  useIframePreview.value = false;
  iframeFallbackHandle.value = setTimeout(() => {
    iframeFallbackHandle.value = null;
    // Se ainda não estiver tocando, não usar iframe; mostrar erro amigável
    if (videoPreview.value.status !== 'playing') {
      videoPreview.value.loading = false;
      videoPreview.value.status = 'error';
      videoPreview.value.error = 'Stream não ficou pronto a tempo. Tente novamente.';
    }
  }, delayMs);
};

const unbindVideoElementListeners = () => {
  if (!videoPreviewElement.value || videoElementListeners.value.length === 0) return;
  for (const [event, handler] of videoElementListeners.value) {
    videoPreviewElement.value.removeEventListener(event, handler);
  }
  videoElementListeners.value = [];
};

const destroyHlsInstance = () => {
  stopPreviewWatchdog();
  unbindVideoElementListeners();
  if (hlsInstance.value) {
    try {
      hlsInstance.value.destroy();
    } catch (e) {
      console.warn('[VideoPreview] Erro ao destruir HLS', e);
    }
    hlsInstance.value = null;
  }
  if (videoPreviewElement.value) {
    try {
      videoPreviewElement.value.pause();
      videoPreviewElement.value.removeAttribute('src');
      videoPreviewElement.value.load();
    } catch (e) {}
  }
  clearIframeFallbackHandle();
};

const resetVideoPreviewState = () => {
  clearAutoPreviewHandle();
  clearPreviewLoadHandle();
  clearPreviewReloadHandle();
  destroyHlsInstance();
  videoPreview.value = {
    url: '',
    loading: false,
    status: 'idle',
    error: '',
  };
  previewRetryCount.value = 0;
  useIframePreview.value = false;
  iframeReady.value = false;
};

const startPreviewWatchdog = (onStallCallback) => {
  stopPreviewWatchdog();
  watchdogInterval.value = setInterval(() => {
    if (!videoPreviewElement.value || !videoPreview.value.url) {
      return;
    }
    if (videoPreview.value.status !== 'playing') {
      return;
    }
    const element = videoPreviewElement.value;
    const isStalled = element.readyState < 3 && !element.paused;
    if (isStalled && typeof onStallCallback === 'function') {
      onStallCallback();
    }
  }, 3500);
};

const stopPreviewWatchdog = () => {
  if (watchdogInterval.value) {
    clearInterval(watchdogInterval.value);
    watchdogInterval.value = null;
  }
};

const loadVideoPreview = async (url, { force = false } = {}) => {
  if (!url) {
    videoPreview.value.status = 'idle';
    destroyHlsInstance();
    return;
  }
  console.debug('[VideoPreview] Loading preview', {
    url,
    force,
    usingIframe: useIframePreview.value,
  });
  // Use iframe directly for non-HLS URLs
  if (!url.toLowerCase().endsWith('.m3u8')) {
    destroyHlsInstance();
    videoPreview.value.loading = true;
    videoPreview.value.status = 'loading';
    videoPreview.value.error = '';
    useIframePreview.value = true;
    iframeReady.value = false;
    // Aguardar 3 segundos antes de renderizar iframe
    setTimeout(() => {
      iframeReady.value = true;
      videoPreview.value.loading = false;
      videoPreview.value.status = 'playing';
    }, 3000);
    return;
  }
  await nextTick();
  const element = videoPreviewElement.value;
  if (!element) return;
  if (force) {
    destroyHlsInstance();
  }
  videoPreview.value.error = '';
  useIframePreview.value = false;
  startIframeFallbackTimer(15000);
  const snapPlayerToLive = () => {
    if (!element.seekable || element.seekable.length === 0) {
      return;
    }
    const liveEdge = element.seekable.end(element.seekable.length - 1);
    if (Number.isFinite(liveEdge)) {
      const target = liveEdge - 0.6;
      if (Math.abs(element.currentTime - target) > 1.5) {
        element.currentTime = target;
      }
    }
  };

  const ensurePlayback = () => {
    if (!element || !videoPreview.value.url) return;
    if (videoPreview.value.status === 'idle' || videoPreview.value.status === 'error') return;
    snapPlayerToLive();
    if (element.paused) {
      element.play().catch(() => {});
    }
  };

  const handlePlaybackStall = () => {
    if (!videoPreview.value.url) return;
    if (['retrying', 'loading', 'idle', 'error'].includes(videoPreview.value.status)) return;
    ensurePlayback();
    schedulePreviewReload(400);
  };

  const bindElementEvents = () => {
    unbindVideoElementListeners();
    const listeners = [
      ['ended', handlePlaybackStall],
      ['pause', ensurePlayback],
      ['stalled', handlePlaybackStall],
      ['waiting', ensurePlayback],
      ['error', handlePlaybackStall],
    ];
    for (const [event, handler] of listeners) {
      element.addEventListener(event, handler);
    }
    videoElementListeners.value = listeners;
  };

  try {
    element.muted = true;
    element.playsInline = true;
    element.controls = true;
    bindElementEvents();
    startPreviewWatchdog(handlePlaybackStall);
    if (Hls.isSupported()) {
      const instance = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        liveSyncDurationCount: 1,
        liveMaxLatencyDurationCount: 2,
        maxLiveSyncPlaybackRate: 1.4,
        backBufferLength: 0,
        startPosition: -1,
        maxBufferLength: 6,
        maxMaxBufferLength: 8,
        maxBufferSize: 6 * 1024 * 1024,
        fragLoadingRetryDelay: 500,
        manifestLoadingRetryDelay: 500,
        levelLoadingRetryDelay: 500,
        manifestLoadingMaxRetry: 6,
        fragLoadingMaxRetry: 4,
        levelLoadingMaxRetry: 4,
        nudgeOffset: 0.1,
      });
      instance.on(Hls.Events.ERROR, (_event, data) => {
        if (!data) return;
        if (data.details === Hls.ErrorDetails.BUFFER_STALLED_ERROR) {
          element.play().catch(() => {});
          snapPlayerToLive();
          return;
        }
        if (
          data.details === Hls.ErrorDetails.MANIFEST_LOAD_ERROR ||
          data.details === Hls.ErrorDetails.MANIFEST_LOAD_TIMEOUT ||
          data.details === Hls.ErrorDetails.FRAG_LOAD_ERROR ||
          data.details === Hls.ErrorDetails.FRAG_LOAD_TIMEOUT ||
          data.details === Hls.ErrorDetails.LEVEL_LOAD_ERROR
        ) {
          schedulePreviewReload();
          return;
        }
        if (data.type === Hls.ErrorTypes.MEDIA_ERROR && hlsInstance.value) {
          try {
            hlsInstance.value.recoverMediaError();
            return;
          } catch (recoverError) {
            console.warn('[VideoPreview] Falha ao recuperar media error', recoverError);
          }
        }
        if (data.fatal) {
          videoPreview.value.error = 'Stream indisponível ou formato inválido.';
          videoPreview.value.status = 'error';
          destroyHlsInstance();
        }
      });
      instance.on(Hls.Events.LEVEL_UPDATED, () => {
        snapPlayerToLive();
      });
      instance.on(Hls.Events.FRAG_BUFFERED, () => {
        element.play().catch(() => {});
      });
      instance.on(Hls.Events.MANIFEST_PARSED, () => {
        previewRetryCount.value = 0;
        videoPreview.value.status = 'playing';
        videoPreview.value.loading = false;
        videoPreview.value.error = '';
        snapPlayerToLive();
        element.play().catch(() => {});
        useIframePreview.value = false;
        clearIframeFallbackHandle();
      });
      instance.loadSource(url);
      instance.attachMedia(element);
      hlsInstance.value = instance;
      videoPreview.value.loading = true;
      videoPreview.value.status = 'loading';
    } else if (element.canPlayType('application/vnd.apple.mpegurl')) {
      element.src = url;
      videoPreview.value.loading = true;
      videoPreview.value.status = 'loading';
      element.onloadedmetadata = () => {
        previewRetryCount.value = 0;
        videoPreview.value.status = 'playing';
        videoPreview.value.loading = false;
        videoPreview.value.error = '';
        snapPlayerToLive();
        element.play().catch(() => {});
        useIframePreview.value = false;
        clearIframeFallbackHandle();
      };
    } else {
      throw new Error('O navegador não suporta reprodução HLS.');
    }
  } catch (error) {
    if (!isM3U8Url.value) {
      videoPreview.value.loading = false;
      videoPreview.value.status = 'playing';
      videoPreview.value.error = '';
    } else {
      videoPreview.value.status = 'error';
      videoPreview.value.error = error?.message || 'Falha ao iniciar a pré-visualização.';
      destroyHlsInstance();
      useIframePreview.value = true;
    }
  }
};

const stopVideoPreview = async ({ remote = true, silent = false, gatewayId = null } = {}) => {
  clearAutoPreviewHandle();
  const targetId = gatewayId || videoGatewayForm.value.id;
  destroyHlsInstance();
  videoPreview.value.loading = false;
  videoPreview.value.status = 'idle';
  videoPreview.value.error = '';
  videoPreview.value.url = '';
  previewRetryCount.value = 0;
  if (targetId === videoGatewayForm.value.id) {
    videoGatewayForm.value.config.preview_active = false;
  }
  if (targetId) {
    syncVideoGatewayInList(targetId, { preview_active: false });
  }
  if (targetId && remote) {
    try {
      await api.post(`/setup_app/api/gateways/${targetId}/video/preview/stop/`);
    } catch (error) {
      const status = error?.response?.status || error?.status;
      if (!silent && status !== 404) {
        notify.warning('Vídeo', error?.message || 'Não foi possível encerrar a pré-visualização.');
      }
    }
  }
};

const startVideoPreview = async ({ silent = false } = {}) => {
  clearAutoPreviewHandle();
  if (!videoGatewayForm.value.id) {
    if (!silent) {
      notify.error('Vídeo', 'Salve o gateway antes de iniciar a pré-visualização.');
    }
    return;
  }
  const streamUrl = (videoGatewayForm.value.config.stream_url || '').trim();
  if (!streamUrl) {
    if (!silent) {
      notify.error('Vídeo', 'Informe a URL do stream para pré-visualizar.');
    }
    return;
  }
  try {
    videoPreview.value.loading = true;
    videoPreview.value.status = 'loading';
    videoPreview.value.error = '';
    previewRetryCount.value = 0;
    clearPreviewReloadHandle();
    const res = await api.post(
      `/setup_app/api/gateways/${videoGatewayForm.value.id}/video/preview/start/`
    );
    if (!res?.success) {
      videoPreview.value.status = 'error';
      videoPreview.value.error = res?.message || 'Não foi possível iniciar a pré-visualização.';
      return;
    }
    
    // Usar playback_proxy_url (preferencial) ou playback_url
    const playbackUrl = res.playback_proxy_url || res.playback_url;
    
    if (!playbackUrl) {
      videoPreview.value.status = 'error';
      videoPreview.value.error = 'Backend não retornou a URL de pré-visualização.';
      console.error('[VideoPreview] Response sem playback_url:', res);
      return;
    }
    
    const previewUrl = res.preview_url || videoGatewayForm.value.config.preview_url || '';
    videoGatewayForm.value.config.preview_url = previewUrl;
    videoGatewayForm.value.config.preview_active = true;
    videoGatewayForm.value.config.preview_playback_url = playbackUrl;
    
    console.log('[VideoPreview] Preview start', {
      apiUrl: previewUrl,
      playbackUrl,
      response: res
    });
    
    videoPreview.value.url = playbackUrl;
    videoPreview.value.status = 'ready';
    
    syncVideoGatewayInList(videoGatewayForm.value.id, {
      preview_url: previewUrl,
      preview_playback_url: playbackUrl,
      preview_active: true,
    });
    if (!silent) {
      notify.success('Vídeo', 'Pré-visualização iniciada.');
    }
  } catch (error) {
    videoPreview.value.status = 'error';
    videoPreview.value.error = error?.message || 'Erro ao iniciar a pré-visualização.';
  } finally {
    videoPreview.value.loading = false;
  }
};

const scheduleVideoPreviewStart = (delayMs = 600) => {
  clearAutoPreviewHandle();
  const hasGateway = Boolean(videoGatewayForm.value.id);
  const streamUrl = (videoGatewayForm.value.config.stream_url || '').trim();
  if (!showGatewayModal.value || !hasGateway || !streamUrl) {
    return;
  }
  autoPreviewHandle.value = setTimeout(() => {
    autoPreviewHandle.value = null;
    startVideoPreview({ silent: true });
  }, delayMs);
};

const queuePreviewLoad = (url, delayMs = 600, { force = false } = {}) => {
  if (!url) return;
  clearPreviewLoadHandle();
  previewLoadHandle.value = setTimeout(() => {
    previewLoadHandle.value = null;
    loadVideoPreview(url, { force });
  }, delayMs);
};

const schedulePreviewReload = (delayMs = 800) => {
  clearPreviewReloadHandle();
  if (!videoPreview.value.url) {
    return;
  }
  if (previewRetryCount.value >= MAX_PREVIEW_RETRIES) {
    videoPreview.value.status = 'error';
    videoPreview.value.loading = false;
    videoPreview.value.error = 'Stream indisponível após múltiplas tentativas.';
    return;
  }
  previewRetryCount.value += 1;
  videoPreview.value.loading = true;
  videoPreview.value.status = 'retrying';
  videoPreview.value.error = '';
  destroyHlsInstance();
  previewReloadHandle.value = setTimeout(() => {
    previewReloadHandle.value = null;
    queuePreviewLoad(videoPreview.value.url, 200, { force: true });
  }, delayMs);
};

const openVideoGatewayModal = (gateway = null) => {
  resetVideoPreviewState();
  if (gateway) {
    videoGatewayForm.value = {
      id: gateway.id,
      name: gateway.name,
      provider: gateway.provider || 'restreamer',
      priority: gateway.priority || 1,
      enabled: !!gateway.enabled,
      site_name: gateway.site_name || '',
      config: {
        stream_type: gateway.config?.stream_type || 'rtmp',
        stream_url: gateway.config?.stream_url || '',
        restream_key: gateway.config?.restream_key || '',
        preview_url: gateway.config?.preview_url || '',
        preview_playback_url: gateway.config?.preview_playback_url || '',
        preview_active: gateway.config?.preview_active === true,
        playback_token: gateway.config?.playback_token || '',
        hls_public_base_url: gateway.config?.hls_public_base_url || '',
      },
    };
  } else {
    videoGatewayForm.value = {
      id: null,
      name: 'Gateway de Vídeo',
      provider: 'restreamer',
      priority: 1,
      enabled: false,
      site_name: '',
      config: {
        stream_type: 'rtmp',
        stream_url: '',
        restream_key: '',
        preview_url: '',
        preview_playback_url: '',
        preview_active: false,
        playback_token: '',
        hls_public_base_url: '',
      },
    };
  }
  
  // Limpar estado da pré-visualização ao abrir modal
  videoPreview.value.url = '';
  videoPreview.value.status = 'idle';
  videoPreview.value.loading = false;
  videoPreview.value.error = '';
  
  showGatewayModal.value = true;
};

const closeGatewayModal = () => {
  stopVideoPreview({ remote: true, silent: true });
  showGatewayModal.value = false;
};

const saveGateway = async () => {
  try {
    await stopVideoPreview({ remote: false, silent: true });
    const payload = {
      id: videoGatewayForm.value.id,
      name: videoGatewayForm.value.name,
      gateway_type: 'video',
      provider: videoGatewayForm.value.provider,
      priority: videoGatewayForm.value.priority,
      enabled: videoGatewayForm.value.enabled,
      site_name: videoGatewayForm.value.site_name || null,
      config: videoGatewayForm.value.config,
    };

    let res;
    if (payload.id) {
      res = await api.patch(`/setup_app/api/gateways/${payload.id}/`, payload);
    } else {
      res = await api.post('/setup_app/api/gateways/', payload);
    }

    if (res.success) {
      notify.success('Câmeras', 'Câmera salva.');
      await fetchGateways();
      closeGatewayModal();
    } else {
      notify.error('Câmeras', res.message || 'Erro ao salvar câmera.');
    }
  } catch (e) {
    notify.error('Câmeras', e.message || 'Erro ao salvar câmera.');
  }
};

const deleteGateway = () => {
  gatewayToDelete.value = videoGatewayForm.value;
  showDeleteConfirm.value = true;
};

const confirmDeleteGateway = (gateway) => {
  gatewayToDelete.value = gateway;
  showDeleteConfirm.value = true;
};

const confirmDelete = async () => {
  try {
    const gateway = gatewayToDelete.value;
    if (!gateway || !gateway.id) {
      notify.error('Câmeras', 'Câmera inválida.');
      return;
    }
    await stopVideoPreview({ remote: true, silent: true, gatewayId: gateway.id });
    const res = await api.delete(`/setup_app/api/gateways/${gateway.id}/`);
    if (res.success) {
      notify.success('Câmeras', res.message || 'Câmera removida.');
      await fetchGateways();
      if (showGatewayModal.value) {
        closeGatewayModal();
      }
    } else {
      notify.error('Câmeras', res.message || 'Erro ao remover câmera.');
    }
  } catch (e) {
    notify.error('Câmeras', e.message || 'Erro ao remover câmera.');
  } finally {
    gatewayToDelete.value = null;
    showDeleteConfirm.value = false;
  }
};

watch(
  () => videoPreview.value.url,
  (url, previous) => {
    if (!showGatewayModal.value) {
      return;
    }
    if (url && url !== previous) {
      previewRetryCount.value = 0;
      queuePreviewLoad(url, 600, { force: true });
    }
    if (!url) {
      destroyHlsInstance();
    }
  }
);

watch(showGatewayModal, (visible, previous) => {
  if (visible) {
    scheduleVideoPreviewStart(400);
  } else if (!visible && previous) {
    stopVideoPreview({ remote: true, silent: true });
  }
});

watch(
  () => videoGatewayForm.value.config.stream_url,
  (current, previous) => {
    if (current === previous) return;
    stopVideoPreview({ remote: false, silent: true });
    scheduleVideoPreviewStart(700);
  }
);

watch(
  () => videoGatewayForm.value.config.stream_type,
  (current, previous) => {
    if (current === previous) return;
    stopVideoPreview({ remote: false, silent: true });
    scheduleVideoPreviewStart(700);
  }
);

onMounted(() => {
  fetchGateways();
  fetchInventorySites();
});

onUnmounted(() => {
  resetVideoPreviewState();
});
</script>

<style scoped>
/* ESTILO PADRÃO (Clean Form) */

.label-custom {
  @apply block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5;
}

/* Input Branco Puro no Light Mode, Cinza Escuro no Dark Mode */
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

/* Dark mode overrides com escopo */
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

.input-custom--prefixed {
  padding-left: 4rem;
}

/* Botões com ícones e sombra */
.btn-primary {
  @apply inline-flex items-center justify-center rounded-md bg-primary-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200;
}

.btn-secondary {
  @apply inline-flex items-center justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-gray-700 transition-all duration-200;
}

.btn-white {
  @apply inline-flex items-center rounded-md bg-white px-2.5 py-1.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-gray-700 transition-all;
}

/* Cards de Resumo */
.stat-card {
  @apply p-4 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col;
}
.stat-label {
  @apply text-xs font-semibold text-gray-500 uppercase tracking-wide;
}
.stat-value {
  @apply text-lg font-bold;
}

/* Scrollbar */
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

/* Animations */
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

textarea.font-mono {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
</style>
