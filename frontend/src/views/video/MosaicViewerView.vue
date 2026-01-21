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
      <button @click="goBack" class="text-gray-400 hover:text-white transition-colors text-sm">
        Fechar
      </button>
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
        <div v-for="(camera, idx) in activeCameras" :key="camera?.id || `empty-${idx}`" class="relative bg-gray-900 rounded overflow-hidden border border-gray-800">
          <template v-if="camera">
            <!-- Player de Vídeo: iframe para MediaMTX WebRTC, video para HLS -->
            <div class="absolute inset-0">
              <template v-if="isMediaMtxUrl(getVideoUrl(camera))">
                <!-- Usar iframe para MediaMTX WebRTC player -->
                <iframe 
                  :src="getVideoUrl(camera)"
                  class="absolute inset-0 w-full h-full border-0"
                  allow="autoplay; fullscreen"
                  style="display: block; margin: 0; padding: 0;"
                ></iframe>
              </template>
              <template v-else-if="isHlsUrl(preferHlsUrl(camera))">
                <!-- Usar video element apenas para URLs HLS (.m3u8) -->
                <video 
                  :ref="el => { if (el) videoRefs[idx] = el }"
                  class="absolute inset-0 w-full h-full object-cover bg-black"
                  muted
                  playsinline
                  autoplay
                  controls
                ></video>
              </template>
              <div v-else class="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
                Stream não disponível
              </div>
            </div>
            <!-- Overlay com Nome -->
            <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3 pointer-events-none">
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
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useApi } from '@/composables/useApi';
import { useNotification } from '@/composables/useNotification';
import Hls from 'hls.js';

const router = useRouter();
const route = useRoute();
const api = useApi();
const notify = useNotification();

const mosaic = ref(null);
const cameras = ref([]);
const videoRefs = ref([]);
const hlsInstances = ref([]);
const startedStreams = ref(new Set()); // Cache de streams já iniciados
const streamStartAttempts = ref(new Map()); // Contador de tentativas por câmera

const activeCameras = computed(() => {
  if (!mosaic.value) return [];
  const capacity = getLayoutCapacity(mosaic.value.layout);
  const selected = (mosaic.value.cameras || []).map(id => cameras.value.find(c => c.id === id)).filter(Boolean);
  
  // Preencher slots vazios até a capacidade
  while (selected.length < capacity) {
    selected.push(null);
  }
  
  return selected.slice(0, capacity);
});

const getLayoutLabel = (layout) => {
  const labels = {
    '2x2': '2×2',
    '3x2': '3×2',
    '3x3': '3×3',
    '4x3': '4×3',
    '4x4': '4×4',
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
    '2x2': 'grid-cols-2 grid-rows-2',
    '3x2': 'grid-cols-3 grid-rows-2',
    '3x3': 'grid-cols-3 grid-rows-3',
    '4x3': 'grid-cols-4 grid-rows-3',
    '4x4': 'grid-cols-4 grid-rows-4',
  };
  return classes[layout] || 'grid-cols-2 grid-rows-2';
};

const isMediaMtxUrl = (url) => {
  if (!url) return false;
  // URLs do MediaMTX WebRTC player (porta 8889)
  return url.includes(':8889/') || url.includes('localhost:8889');
};

const isHlsUrl = (url) => {
  return url && url.toLowerCase().endsWith('.m3u8');
};

// Converte URL de player WebRTC do MediaMTX (porta 8889) para manifesto HLS (porta 8888)
// Ex.: http://localhost:8889/gateway_29/ -> http://localhost:8888/gateway_29/index.m3u8
const mediaMtxToHls = (url) => {
  if (!isMediaMtxUrl(url)) return null;
  try {
    const u = new URL(url);
    // Trocar para porta HLS
    const host = u.hostname;
    const hlsPort = '8888';
    // Normalizar path e acrescentar index.m3u8
    const path = u.pathname.replace(/\/+$/g, '');
    const hlsPath = `${path}/index.m3u8`;
    const hlsUrl = `${u.protocol}//${host}:${hlsPort}${hlsPath}`;
    return hlsUrl;
  } catch (e) {
    console.warn('[Mosaico] Falha ao converter MediaMTX URL para HLS:', e);
    return null;
  }
};

// Prefere HLS quando possível (para permitir object-fit: cover); fallback para WebRTC (iframe)
const preferHlsUrl = (camera) => {
  const url = getVideoUrl(camera);
  if (!url) return null;
  if (isHlsUrl(url)) return url;
  if (isMediaMtxUrl(url)) {
    const hls = mediaMtxToHls(url);
    if (hls) return hls;
  }
  return null;
};

const resolvePreviewUrl = (camera) => {
  // Mesma lógica do VideoCamerasView
  try {
    const cfg = camera.config || {};
    const base = (cfg.hls_public_base_url || '').trim();
    const key = (cfg.restream_key || '').trim();
    const type = (cfg.stream_type || '').toLowerCase();
    
    console.log(`[Mosaico] Resolvendo URL para ${camera.name}:`, { base, key, type, config: cfg });
    
    if (base && key && (type === 'rtmp' || type === 'rtsp')) {
      const normalizedBase = base.replace(/\/+$/g, '');
      const resolved = `${normalizedBase}/${key}.m3u8`;
      console.log(`[Mosaico] Resolved HLS URL para ${camera.name}:`, resolved);
      return resolved;
    }
  } catch (error) {
    console.warn('[Mosaico] Failed to resolve HLS URL', error);
  }
  return null;
};

const getVideoUrl = (camera) => {
  console.log(`[Mosaico] getVideoUrl para ${camera.name}:`, {
    playback_url: camera.playback_url,
    preview_playback_url: camera.config?.preview_playback_url,
    preview_url: camera.preview_url,
    config_preview_url: camera.config?.preview_url,
    has_hls_config: !!(camera.config?.hls_public_base_url && camera.config?.restream_key),
    stream_url: camera.config?.stream_url
  });
  
  // 1. PRIORIDADE MÁXIMA: playback_url direto do gateway (construído pelo backend)
  if (camera.playback_url) {
    console.log(`[Mosaico] Usando playback_url do gateway (BACKEND) para ${camera.name}:`, camera.playback_url);
    return camera.playback_url;
  }
  
  // 2. Tentar resolver URL HLS via config (hls_public_base_url + restream_key)
  const resolved = resolvePreviewUrl(camera);
  if (resolved) {
    console.log(`[Mosaico] Usando URL resolvida (HLS config) para ${camera.name}`);
    return resolved;
  }
  
  // 3. Tentar preview_playback_url (URL já resolvida e salva)
  if (camera.config && camera.config.preview_playback_url) {
    console.log(`[Mosaico] Usando preview_playback_url para ${camera.name}`);
    return camera.config.preview_playback_url;
  }
  
  // 4. Tentar preview_url
  if (camera.preview_url) {
    console.log(`[Mosaico] Usando preview_url para ${camera.name}`);
    return camera.preview_url;
  }
  
  // 5. Tentar config.preview_url
  if (camera.config && camera.config.preview_url) {
    console.log(`[Mosaico] Usando config.preview_url para ${camera.name}`);
    return camera.config.preview_url;
  }
  
  // 6. Se tiver stream_url e for HTTP/HTTPS, usar direto
  if (camera.config && camera.config.stream_url) {
    const streamUrl = camera.config.stream_url;
    if (streamUrl.toLowerCase().startsWith('http')) {
      console.log(`[Mosaico] Usando stream_url HTTP para ${camera.name}`);
      return streamUrl;
    }
  }
  
  console.warn(`[Mosaico] Nenhuma URL válida encontrada para ${camera.name}`);
  return null;
};

const goBack = () => {
  router.push({ name: 'video-mosaics' });
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

const startStreamForCamera = async (camera) => {
  if (!camera || !camera.id) {
    console.warn('[Mosaico] Camera inválida:', camera);
    return null;
  }
  
  // Verificar se já tentamos iniciar este stream
  const attempts = streamStartAttempts.value.get(camera.id) || 0;
  if (attempts >= 2) {
    console.warn(`[Mosaico] Limite de tentativas atingido para ${camera.name}, pulando`);
    return null;
  }
  
  // Verificar se já iniciamos este stream
  if (startedStreams.value.has(camera.id)) {
    console.log(`[Mosaico] Stream já iniciado para ${camera.name}, reutilizando`);
    return camera.playback_url || null;
  }
  
  try {
    streamStartAttempts.value.set(camera.id, attempts + 1);
    
    const endpoint = `/setup_app/api/gateways/${camera.id}/video/preview/start/`;
    console.log(`[Mosaico] POST ${endpoint} para ${camera.name}...`);
    
    const res = await api.post(endpoint);
    
    console.log(`[Mosaico] Resposta completa para ${camera.name}:`, JSON.stringify(res, null, 2));
    
    if (res && res.success) {
      if (res.playback_url) {
        console.log(`[Mosaico] ✓ Stream iniciado: ${camera.name} -> ${res.playback_url}`);
        camera.playback_url = res.playback_url;
        if (res.preview_url) {
          camera.preview_url = res.preview_url;
        }
        startedStreams.value.add(camera.id); // Marcar como iniciado
        return res.playback_url;
      } else {
        console.warn(`[Mosaico] ⚠ Success mas sem playback_url para ${camera.name}`);
      }
    } else {
      console.error(`[Mosaico] ✗ Falha na resposta para ${camera.name}:`, res);
    }
  } catch (e) {
    console.error(`[Mosaico] ✗ Exceção ao iniciar ${camera.name}:`, e);
    if (e.response) {
      console.error(`[Mosaico]   HTTP ${e.response.status}:`, e.response.data);
    }
  }
  return null;
};

const fetchCameras = async () => {
  try {
    const res = await api.get('/setup_app/api/gateways/');
    if (res.success) {
      cameras.value = (res.gateways || []).filter(gw => gw.gateway_type === 'video');
      
      // FILTRAR apenas câmeras válidas (não-null) antes de iniciar streams
      const validCameras = activeCameras.value.filter(cam => cam !== null);
      
      if (validCameras.length === 0) {
        console.warn('[Mosaico] Nenhuma câmera válida no mosaico');
        notify.error('Mosaico', 'Adicione câmeras ao mosaico antes de visualizar.');
        return;
      }
      
      console.log(`[Mosaico] Iniciando ${validCameras.length} streams (com rate limiting)...`);
      
      // Rate limiting: iniciar streams sequencialmente com 800ms de delay
      const results = [];
      for (const camera of validCameras) {
        results.push(await startStreamForCamera(camera));
        if (validCameras.indexOf(camera) < validCameras.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 800));
        }
      }
      
      const successCount = results.filter(r => r !== null).length;
      console.log(`[Mosaico] ${successCount}/${validCameras.length} streams iniciados com sucesso`);
      
      // Aguardar 2s para os iframes/players carregarem
      console.log('[Mosaico] Aguardando 2s para players ficarem prontos...');
      await new Promise(resolve => setTimeout(resolve, 2000));
      await nextTick();
      
      // Inicializar HLS apenas para câmeras com URLs HLS (.m3u8)
      initializeHlsPlayers();
    }
  } catch (e) {
    console.error('Erro ao carregar câmeras', e);
  }
};

const initializeHlsPlayers = () => {
  videoRefs.value.forEach((videoEl, idx) => {
    if (!videoEl) return;
    
    const camera = activeCameras.value[idx];
    if (!camera) return;
    
    const url = preferHlsUrl(camera);
    if (!url) return;
    
    // Processar APENAS URLs HLS (.m3u8)
    // URLs MediaMTX são renderizadas via iframe no template
    if (!isHlsUrl(url)) {
      console.log(`[Mosaico] Não é HLS, será renderizado via iframe: ${getVideoUrl(camera)}`);
      return;
    }
    
    console.log(`[Mosaico] Iniciando HLS.js para ${camera.name}: ${url}`);
    
    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 0,
        maxBufferLength: 6,
        maxMaxBufferLength: 8,
        manifestLoadingMaxRetry: 3,
        levelLoadingMaxRetry: 3,
        fragLoadingMaxRetry: 3,
        manifestLoadingRetryDelay: 2000,
        levelLoadingRetryDelay: 2000,
      });
      
      hls.loadSource(url);
      hls.attachMedia(videoEl);
      
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        console.log(`[Mosaico] ✓ HLS pronto para ${camera.name}`);
        videoEl.play().catch(e => console.warn('Play failed:', e));
      });
      
      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          console.error(`[Mosaico] HLS fatal error para ${camera.name}:`, data.type, data.details);
          // NÃO fazer retry automático para evitar loops infinitos
          // Deixar HLS.js gerenciar retries através das configs
          if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
            try {
              hls.recoverMediaError();
            } catch (e) {
              console.error(`[Mosaico] Falha ao recuperar de media error:`, e);
            }
          }
        }
      });
      
      hlsInstances.value[idx] = hls;
    } else if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
      videoEl.src = url;
      videoEl.play().catch(e => console.warn('Play failed:', e));
    }
  });
};

const destroyHlsPlayers = () => {
  hlsInstances.value.forEach(hls => {
    if (hls) {
      try {
        hls.destroy();
      } catch (e) {
        console.warn('Erro ao destruir HLS:', e);
      }
    }
  });
  hlsInstances.value = [];
  videoRefs.value = [];
};

onMounted(async () => {
  await fetchMosaic();
  await fetchCameras();
});

onUnmounted(async () => {
  const timestamp = new Date().toISOString();
  console.log(`[Mosaico] ${timestamp} - INICIANDO CLEANUP (onUnmounted)`);
  
  // Destruir players HLS
  destroyHlsPlayers();
  
  // Parar streams no backend para liberar recursos do transmuxer
  const validCameras = activeCameras.value.filter(cam => cam !== null);
  console.log(`[Mosaico] ${validCameras.length} cameras para parar:`, validCameras.map(c => ({ id: c.id, name: c.name })));
  
  const stopPromises = validCameras.map(async camera => {
    try {
      console.log(`[Mosaico] Parando stream gateway ${camera.id} (${camera.name})...`);
      await api.post(`/setup_app/api/gateways/${camera.id}/video/preview/stop/`);
      console.log(`[Mosaico] ✓ Stream parado com sucesso: ${camera.name}`);
    } catch (e) {
      console.warn(`[Mosaico] ✗ Erro ao parar stream ${camera.name}:`, e);
    }
  });
  
  await Promise.all(stopPromises);
  
  // Limpar caches
  startedStreams.value.clear();
  streamStartAttempts.value.clear();
  
  console.log(`[Mosaico] ${timestamp} - CLEANUP CONCLUÍDO`);
});
</script>

<style scoped>
/* Garantir que o grid ocupe todo o espaço */
.grid {
  height: 100%;
}

/* Garantir que vídeo cubra todo o quadro do mosaico */
video {
  object-fit: cover;
}

/* Iframe ocupa todo o quadro; conteúdo interno pode ter letterboxing do player */
iframe {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
}
</style>
