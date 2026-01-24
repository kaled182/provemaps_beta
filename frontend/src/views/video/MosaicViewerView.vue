<template>
  <div class="min-h-screen bg-black flex flex-col h-[calc(100vh-64px)]">
    <!-- Header -->
    <div class="flex-none bg-gray-900 border-b border-gray-700 px-4 py-2 flex justify-between items-center z-10">
      <div class="flex items-center gap-3">
        <button @click="goBack" class="text-gray-400 hover:text-white transition-colors p-1">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
        </button>
        <h1 class="text-white font-semibold">{{ mosaic?.name || 'Mosaico' }}</h1>
        <span class="text-xs text-gray-400">{{ getLayoutLabel(mosaic?.layout) }}</span>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-xs text-gray-400">
          {{ Object.keys(connections).length }}/{{ activeCameras.filter(c => c).length }} conectadas
        </span>
        <button @click="goBack" class="text-gray-400 hover:text-white transition-colors text-sm">
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
              <!-- Tag video pura com WebRTC direto via WHEP -->
              <video 
                :ref="el => { if (el) videoRefs[camera.id] = el }"
                class="video-player w-full h-full object-cover bg-black"
                autoplay
                muted
                playsinline
              ></video>
              
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

              <!-- Indicador de Qualidade de Rede -->
              <div 
                v-if="connections[camera.id]?.stats?.networkQuality && connections[camera.id].stats.networkQuality !== 'good'"
                class="absolute top-2 left-2 z-30"
                :title="`FPS: ${connections[camera.id].stats.framesPerSecond}, Packets Lost: ${connections[camera.id].stats.packetsLost}`"
              >
                <div 
                  class="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium"
                  :class="{
                    'bg-yellow-600 text-white': connections[camera.id].stats.networkQuality === 'degraded',
                    'bg-red-600 text-white': connections[camera.id].stats.networkQuality === 'poor'
                  }"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                  </svg>
                  <span>{{ connections[camera.id].stats.networkQuality === 'degraded' ? 'Rede Instável' : 'Rede Ruim' }}</span>
                </div>
              </div>
              
              <!-- Loading overlay -->
              <div v-if="connections[camera.id]?.isConnecting" class="absolute inset-0 flex items-center justify-center bg-black/50 z-10 pointer-events-none">
                <svg class="animate-spin h-6 w-6 text-white" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>

              <!-- Erro overlay -->
              <div v-if="connections[camera.id]?.error" class="absolute inset-0 flex items-center justify-center bg-black/70 z-10">
                <div class="text-center px-4">
                  <svg class="w-8 h-8 text-red-500 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <p class="text-white text-sm">{{ connections[camera.id].error }}</p>
                </div>
              </div>
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
import { useWebRTC } from '@/composables/useWebRTC';

const router = useRouter();
const route = useRoute();
const api = useApi();
const notify = useNotification();

const mosaic = ref(null);
const cameras = ref([]);
const videoRefs = ref({});
const videoContainerRefs = ref({});
const connections = ref({});
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

// Watch para aplicar mute/unmute nos elementos de vídeo
watch(unmutedCameraId, (newId, oldId) => {
  // Mutar a câmera anterior
  if (oldId && videoRefs.value[oldId]) {
    videoRefs.value[oldId].muted = true;
  }
  
  // Desmutar a nova câmera
  if (newId && videoRefs.value[newId]) {
    videoRefs.value[newId].muted = false;
  }
});

const initWebRTCForCamera = async (camera) => {
  if (!camera) return;
  
  const streamUrl = getVideoUrl(camera);
  if (!streamUrl) {
    console.warn(`[Mosaico] URL indisponível para ${camera.name}`);
    return;
  }
  
  const whepUrl = streamUrl.endsWith('/') ? `${streamUrl}whep` : `${streamUrl}/whep`;
  
  // Criar instância do composable para esta câmera
  const rtc = useWebRTC({
    maxRetries: 5,
    maxBackoff: 30000,
    onStatsUpdate: (stats) => {
      // Atualizar stats para exibir alertas de rede
      if (connections.value[camera.id]) {
        connections.value[camera.id].stats = stats;
      }
    }
  });
  
  // Armazenar conexão
  connections.value[camera.id] = rtc;
  
  // Conectar
  await rtc.connect(whepUrl);
  
  // Vincular stream ao elemento de vídeo
  watch(rtc.stream, (newStream) => {
    if (newStream && videoRefs.value[camera.id]) {
      videoRefs.value[camera.id].srcObject = newStream;
    }
  }, { immediate: true });
};

const initPlayers = () => {
  activeCameras.value.forEach((camera) => {
    if (camera) {
      initWebRTCForCamera(camera);
    }
  });
};

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

const getVideoUrl = (camera) => {
  if (camera.playback_url) {
    console.log(`[Mosaico] Usando playback_url para ${camera.name}:`, camera.playback_url);
    return camera.playback_url;
  }
  
  if (camera.config?.stream_url && camera.config.stream_url.startsWith('http')) {
    console.log(`[Mosaico] Usando stream_url para ${camera.name}:`, camera.config.stream_url);
    return camera.config.stream_url;
  }
  
  console.warn(`[Mosaico] Nenhuma URL válida para ${camera.name}`);
  return null;
};

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
    const res = await api.get('/setup_app/api/gateways/');
    if (res.success) {
      cameras.value = (res.gateways || []).filter(gw => gw.gateway_type === 'video');
      
      const validCameras = activeCameras.value.filter(cam => cam !== null);
      
      if (validCameras.length === 0) {
        console.warn('[Mosaico] Nenhuma câmera válida no mosaico');
        notify.error('Mosaico', 'Adicione câmeras ao mosaico antes de visualizar.');
        return;
      }
      
      console.log(`[Mosaico] Iniciando ${validCameras.length} streams no backend em paralelo...`);
      
      const startPromises = validCameras.map(async (camera) => {
        try {
          const endpoint = `/setup_app/api/gateways/${camera.id}/video/preview/start/`;
          const res = await api.post(endpoint);
          
          if (res && res.success && res.playback_url) {
            camera.playback_url = res.playback_url;
            console.log(`[Mosaico] ✓ Stream backend iniciado: ${camera.name}`);
          } else {
            console.warn(`[Mosaico] Falha ao iniciar stream para ${camera.name}`);
          }
        } catch (e) {
          console.error(`[Mosaico] Erro ao iniciar backend stream para ${camera.name}:`, e);
        }
      });
      
      await Promise.all(startPromises);
      
      await nextTick();
      console.log('[Mosaico] Aguardando 2s para MediaMTX publicar streams antes de iniciar WHEP...');
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      initPlayers();
    }
  } catch (e) {
    console.error('[Mosaico] Erro ao carregar câmeras:', e);
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
  const timestamp = new Date().toISOString();
  console.log(`[Mosaico] ${timestamp} - INICIANDO CLEANUP`);
  
  // Remover listeners de fullscreen
  document.removeEventListener('fullscreenchange', handleFullscreenChange);
  document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
  document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
  document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
  
  // Fechar todas as conexões WebRTC via composable
  Object.keys(connections.value).forEach((cameraId) => {
    console.log(`[WHEP] Fechando conexão para câmera ${cameraId}`);
    connections.value[cameraId].close();
  });
  connections.value = {};
  
  // Parar streams no backend
  const validCameras = activeCameras.value.filter(cam => cam !== null);
  const stopPromises = validCameras.map(async camera => {
    try {
      console.log(`[Mosaico] Parando stream gateway ${camera.id} (${camera.name})...`);
      await api.post(`/setup_app/api/gateways/${camera.id}/video/preview/stop/`);
      console.log(`[Mosaico] ✓ Stream parado: ${camera.name}`);
    } catch (e) {
      console.warn(`[Mosaico] Erro ao parar stream ${camera.name}:`, e);
    }
  });
  
  await Promise.all(stopPromises);
  
  console.log(`[Mosaico] ${timestamp} - CLEANUP CONCLUÍDO`);
});
</script>

<style scoped>
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
