<template>
  <div class="min-h-screen bg-black flex flex-col h-[calc(100vh-64px)]">
    <!-- Header -->
    <div class="mosaic-header flex-none px-4 py-2 flex justify-between items-center z-10">
      <div class="flex items-center gap-3">
        <button @click="goBack" class="mosaic-header-btn transition-colors p-1">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
        </button>
        <h1 class="mosaic-header-title font-semibold">{{ mosaic?.name || 'Mosaico' }}</h1>
        <span class="text-xs mosaic-header-sub">{{ getLayoutLabel(mosaic?.layout) }}</span>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-xs mosaic-header-sub">
          {{ Object.keys(cameraPlayerRefs).length }}/{{ activeCameras.filter(c => c).length }} ativas
        </span>
        <button @click="goBack" class="mosaic-header-btn transition-colors text-sm">
          Fechar
        </button>
      </div>
    </div>

    <!-- Grid de Vídeos -->
    <div class="flex-1 p-2 overflow-hidden">
      <div v-if="!mosaic" class="h-full flex items-center justify-center">
        <div class="text-center">
          <svg class="animate-spin h-8 w-8 mx-auto text-gray-400 mb-2" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p class="text-sm text-gray-400">Carregando mosaico...</p>
        </div>
      </div>

      <div v-else class="h-full grid gap-2" :class="getGridClass(mosaic.layout)">
        <div
          v-for="(camera, idx) in activeCameras"
          :key="camera?.id || `empty-${idx}`"
          class="mosaic-cell relative bg-gray-900 rounded overflow-hidden border border-gray-800"
        >
          <template v-if="camera">
            <div 
              class="video-wrapper absolute inset-0"
              :ref="el => { if (el) videoContainerRefs[camera.id] = el }"
              @dblclick="toggleFullscreen(camera.id)"
            >
              <!-- Componente CameraPlayer -->
              <CameraPlayer
                :ref="el => { if (el) cameraPlayerRefs[camera.id] = el }"
                :camera="camera"
                :muted="unmutedCameraId !== camera.id"
              >
                <template #overlay>
                  <!-- Controles de Áudio e Fullscreen -->
                  <div class="absolute top-2 right-2 z-30 flex gap-2">
                <!-- Botão Fullscreen -->
                <button
                  @click="toggleFullscreen(camera.id)"
                  class="bg-black/60 hover:bg-black/80 text-white p-2 rounded transition-colors"
                  :title="fullscreenCameraId === camera.id ? 'Sair da tela cheia (ESC)' : 'Tela cheia (duplo clique)'"
                >
                  <svg v-if="fullscreenCameraId !== camera.id" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
                  </svg>
                  <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                </button>
                
                <!-- Botão Unmute (apenas se muted) -->
                <button
                  v-if="!unmutedCameraId || unmutedCameraId !== camera.id"
                  @click="toggleAudio(camera.id)"
                  class="bg-black/60 hover:bg-black/80 text-white p-2 rounded transition-colors"
                  title="Ativar áudio desta câmera"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" clip-rule="evenodd"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"/>
                  </svg>
                </button>
                
                <!-- Botão Mute (se esta estiver com áudio) -->
                <button
                  v-if="unmutedCameraId === camera.id"
                  @click="toggleAudio(null)"
                  class="bg-green-600 hover:bg-green-700 text-white p-2 rounded transition-colors"
                  title="Desativar áudio"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/>
                  </svg>
                </button>
              </div>

                </template>
              </CameraPlayer>
            </div>

            <!-- Overlay com Nome -->
            <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3 pointer-events-none z-20">
              <p class="text-white text-sm font-medium truncate">{{ camera.name }}</p>
            </div>
          </template>
          
          <template v-else>
            <div class="absolute inset-0 flex items-center justify-center border-2 border-dashed border-gray-800">
              <span class="text-gray-600 text-sm">Sem câmera</span>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useApi } from '@/composables/useApi';
import { useNotification } from '@/composables/useNotification';
import CameraPlayer from '@/components/Video/CameraPlayer.vue';

const router = useRouter();
const route = useRoute();
const api = useApi();
const notify = useNotification();

const mosaic = ref(null);
const cameras = ref([]);
const cameraPlayerRefs = ref({});
const videoContainerRefs = ref({});
const unmutedCameraId = ref(null);
const fullscreenCameraId = ref(null);

const activeCameras = computed(() => {
  if (!mosaic.value) return [];
  const capacity = getLayoutCapacity(mosaic.value.layout);
  const selected = (mosaic.value.cameras || []).map(id => cameras.value.find(c => c.id === id)).filter(Boolean);
  
  while (selected.length < capacity) {
    selected.push(null);
  }
  return selected.slice(0, capacity);
});

// Gerenciamento de áudio exclusivo
const toggleAudio = (cameraId) => {
  // Se clicar na mesma câmera, desligar
  if (unmutedCameraId.value === cameraId) {
    unmutedCameraId.value = null;
    return;
  }
  
  // Desmutar apenas esta câmera
  unmutedCameraId.value = cameraId;
};

// Gerenciamento de tela cheia
const toggleFullscreen = async (cameraId) => {
  const container = videoContainerRefs.value[cameraId];
  if (!container) return;

  try {
    // Se já está em fullscreen, sair
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      fullscreenCameraId.value = null;
      return;
    }

    // Entrar em fullscreen
    if (container.requestFullscreen) {
      await container.requestFullscreen();
    } else if (container.webkitRequestFullscreen) {
      await container.webkitRequestFullscreen();
    } else if (container.mozRequestFullScreen) {
      await container.mozRequestFullScreen();
    } else if (container.msRequestFullscreen) {
      await container.msRequestFullscreen();
    }
    
    fullscreenCameraId.value = cameraId;
  } catch (err) {
    console.error('[Fullscreen] Erro ao alternar tela cheia:', err);
  }
};

// Listener para detectar quando sai do fullscreen via ESC
const handleFullscreenChange = () => {
  if (!document.fullscreenElement) {
    fullscreenCameraId.value = null;
  }
};

// CameraPlayer components gerenciam mute/unmute via prop reativa :muted

// Não precisamos mais de initHLSForCamera - o componente CameraPlayer cuida disso

// Funções auxiliares de layout

const getLayoutLabel = (layout) => {
  const labels = { '2x2': '2×2', '3x2': '3×2', '3x3': '3×3', '4x3': '4×3', '4x4': '4×4' };
  return labels[layout] || layout;
};

const getLayoutCapacity = (layout) => {
  const capacities = { '2x2': 4, '3x2': 6, '3x3': 9, '4x3': 12, '4x4': 16 };
  return capacities[layout] || 4;
};

const getGridClass = (layout) => {
  const classes = {
    '2x2': 'grid-cols-2 grid-rows-2',
    '3x2': 'grid-cols-3 grid-rows-2',
    '3x3': 'grid-cols-3 grid-rows-3',
    '4x3': 'grid-cols-4 grid-rows-3',
    '4x4': 'grid-cols-4 grid-rows-4',
  };
  return classes[layout] || 'grid-cols-2 grid-rows-2';
};

// Removido: uso direto de playback_url para construir WHEP incorreto

const goBack = () => {
  router.push({ path: '/video', query: { tab: 'mosaics' } });
};

const fetchMosaic = async () => {
  try {
    const res = await api.get(`/setup_app/video/api/mosaics/${route.params.id}/`);
    if (res.success) {
      mosaic.value = res.mosaic;
    } else {
      notify.error('Mosaico', 'Mosaico não encontrado.');
      goBack();
    }
  } catch (e) {
    notify.error('Mosaico', e.message || 'Erro ao carregar mosaico.');
    goBack();
  }
};

const fetchCameras = async () => {
  try {
    // Usar API dedicada que expõe whep_url
    const siteId = mosaic.value?.site_id;
    const endpoint = siteId ? `/api/v1/cameras/?site=${siteId}` : '/api/v1/cameras/';
    const res = await api.get(endpoint);
    if (res && res.success) {
      cameras.value = res.results || [];

      const validCameras = activeCameras.value.filter(cam => cam !== null);

      if (validCameras.length === 0) {
        console.warn('[Mosaico] Nenhuma câmera válida no mosaico');
        notify.error('Mosaico', 'Adicione câmeras ao mosaico antes de visualizar.');
        return;
      }

      // Limitar paralelismo para evitar sobrecarga
      const CONCURRENT_LIMIT = 3;
      console.log(`[Mosaico] 🚀 Iniciando ${validCameras.length} streams (batches de ${CONCURRENT_LIMIT})...`);

      const results = [];
      
      for (let i = 0; i < validCameras.length; i += CONCURRENT_LIMIT) {
        const batch = validCameras.slice(i, i + CONCURRENT_LIMIT);
        
        const batchPromises = batch.map(async (camera, idx) => {
          // Pequeno delay escalonado dentro do batch
          await new Promise(resolve => setTimeout(resolve, idx * 200));
          
          try {
            const startEndpoint = `/setup_app/api/gateways/${camera.id}/video/preview/start/`;
            const startRes = await api.post(startEndpoint);

            if (startRes && startRes.success && startRes.playback_url) {
              camera.playback_url = startRes.playback_proxy_url || startRes.playback_url;
              return { success: true, camera };
            } else {
              console.warn(`[Mosaico] ⚠️ Falha: ${camera.name}`);
              return { success: false, camera };
            }
          } catch (e) {
            console.error(`[Mosaico] Erro ao iniciar backend stream para ${camera.name}:`, e);
            return { success: false, camera, error: e };
          }
        });

        const batchResults = await Promise.all(batchPromises);
        results.push(...batchResults);
        
        // Pequeno delay entre batches
        if (i + CONCURRENT_LIMIT < validCameras.length) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
      
      const successCount = results.filter(r => r.success).length;
      const failedCameras = results.filter(r => !r.success).map(r => r.camera.name);
      
      if (successCount === validCameras.length) {
        console.log(`[Mosaico] ✅ ${successCount}/${validCameras.length} streams prontos`);
      } else {
        console.warn(`[Mosaico] ⚠️ ${successCount}/${validCameras.length} streams prontos. Falhas:`, failedCameras.join(', '));
      }
      
      await nextTick();
    }
  } catch (e) {
    console.error('[Mosaico] Erro ao carregar câmeras:', e);
    notify.error('Mosaico', 'Erro ao carregar câmeras');
  }
};

// Registrar listener de fullscreen
onMounted(async () => {
  document.addEventListener('fullscreenchange', handleFullscreenChange);
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
  document.addEventListener('mozfullscreenchange', handleFullscreenChange);
  document.addEventListener('MSFullscreenChange', handleFullscreenChange);
  
  await fetchMosaic();
  await fetchCameras();
});

onUnmounted(async () => {
  console.log(`[Mosaico] 🧹 Limpando ${activeCameras.value.filter(cam => cam !== null).length} streams...`);
  
  // Remover listeners de fullscreen
  document.removeEventListener('fullscreenchange', handleFullscreenChange);
  document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
  document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
  document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
  
  // CameraPlayer components serão destruídos automaticamente e farão cleanup do HLS
  cameraPlayerRefs.value = {};
  
  // Parar streams no backend com limite de paralelismo
  const validCameras = activeCameras.value.filter(cam => cam !== null);
  
  if (validCameras.length === 0) {
    return;
  }
  
  const CONCURRENT_STOP_LIMIT = 5;
  const stopResults = [];
  
  for (let i = 0; i < validCameras.length; i += CONCURRENT_STOP_LIMIT) {
    const batch = validCameras.slice(i, i + CONCURRENT_STOP_LIMIT);
    
    const batchPromises = batch.map(async camera => {
      try {
        await api.post(`/setup_app/api/gateways/${camera.id}/video/preview/stop/`);
        console.log(`[Mosaico] ✓ Stream parado: ${camera.name}`);
        return { success: true, camera };
      } catch (e) {
        console.warn(`[Mosaico] Erro ao parar stream ${camera.name}:`, e);
        return { success: false, camera, error: e };
      }
    });
    
    const batchResults = await Promise.allSettled(batchPromises);
    stopResults.push(...batchResults);
  }
  
  const stoppedCount = stopResults.filter(r => r.status === 'fulfilled' && r.value.success).length;
  console.log(`[Mosaico] ✅ ${stoppedCount}/${validCameras.length} streams parados`);
});
</script>

<style scoped>
.mosaic-header {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.mosaic-header-title {
  color: var(--text-primary);
}

.mosaic-header-sub {
  color: var(--text-tertiary);
}

.mosaic-header-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary);
}

.mosaic-header-btn:hover {
  color: var(--text-primary);
}

.grid {
  height: 100%;
}

.mosaic-cell {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background-color: black;
}

.video-wrapper {
  position: absolute;
  inset: 0;
}

.video-player {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  background: black;
}
</style>
