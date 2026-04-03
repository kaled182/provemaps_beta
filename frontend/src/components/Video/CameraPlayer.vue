<template>
  <div class="camera-player relative w-full h-full bg-black">
    <video
      ref="videoElement"
      class="w-full h-full object-cover"
      autoplay
      :muted="muted"
      playsinline
    ></video>
    
    <!-- Loading/Error indicator -->
    <div v-if="(isInitializing && !isPlaying) || (consecutiveErrors > 0 && !isPlaying)" 
         class="absolute inset-0 flex items-center justify-center pointer-events-none transition-opacity duration-300"
         :class="{ 
           'bg-black/70': isInitializing && !isPlaying, 
           'bg-red-900/40': consecutiveErrors > 0 && !isPlaying 
         }">
      <div class="text-center bg-black/60 px-4 py-3 rounded-lg backdrop-blur-sm">
        <svg v-if="isInitializing && !isPlaying" class="animate-spin h-7 w-7 mx-auto text-blue-400 mb-2" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p v-if="isInitializing && !isPlaying" class="text-xs text-gray-300 font-medium">Carregando...</p>
        <div v-else-if="consecutiveErrors > 0 && !isPlaying && consecutiveErrors < MAX_CONSECUTIVE_ERRORS">
          <svg class="animate-spin h-6 w-6 mx-auto text-yellow-400 mb-2" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p class="text-xs text-yellow-300 font-medium">
            Reconectando... {{ consecutiveErrors }}/{{ MAX_CONSECUTIVE_ERRORS }}
          </p>
        </div>
        <div v-else-if="consecutiveErrors >= MAX_CONSECUTIVE_ERRORS">
          <svg class="h-7 w-7 mx-auto text-red-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          <p class="text-xs text-red-300 font-medium">Stream indisponível</p>
        </div>
      </div>
    </div>
    
    <slot name="overlay"></slot>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import Hls from 'hls.js';

const props = defineProps({
  camera: {
    type: Object,
    required: true
  },
  muted: {
    type: Boolean,
    default: true
  }
});

const videoElement = ref(null);
const isInitializing = ref(false);
const consecutiveErrors = ref(0);
const isPlaying = ref(false);
const MAX_CONSECUTIVE_ERRORS = 5;

let hlsInstance = null;
let retryTimer = null;
let initTimer = null;
let attempt = 0;
let isDestroyed = false;
let hasLoadedSuccessfully = false;

const cleanup = () => {
  if (retryTimer) {
    clearTimeout(retryTimer);
    retryTimer = null;
  }
  if (initTimer) {
    clearTimeout(initTimer);
    initTimer = null;
  }
  if (hlsInstance) {
    try { 
      hlsInstance.destroy(); 
    } catch (e) {
      console.warn(`[CameraPlayer] Erro ao destruir HLS:`, e);
    }
    hlsInstance = null;
  }
  isInitializing.value = false;
  isPlaying.value = false;
};

const scheduleRetry = () => {
  if (isDestroyed) return;
  
  // Limitar tentativas consecutivas de erro
  if (consecutiveErrors.value >= MAX_CONSECUTIVE_ERRORS) {
    console.error(`[CameraPlayer] ❌ Limite de erros atingido: ${props.camera.name}`);
    return;
  }
  
  // Exponential backoff: 3s, 6s, 12s, 24s, 48s, 60s
  const baseDelay = hasLoadedSuccessfully ? 3000 : 5000; // Mais rápido se já funcionou antes
  const delay = Math.min(60000, baseDelay * Math.pow(2, Math.min(attempt, 4)));
  
  if (consecutiveErrors.value > 2) {
    console.warn(`[CameraPlayer] 🔄 Retry em ${Math.round(delay/1000)}s (${props.camera.name}) - erro ${consecutiveErrors.value}/${MAX_CONSECUTIVE_ERRORS}`);
  }
  
  retryTimer = setTimeout(() => {
    if (!isDestroyed) {
      initHLS();
    }
  }, delay);
};

const initHLS = () => {
  // Prevenir múltiplas inicializações simultâneas
  if (isInitializing.value || isDestroyed) {
    return;
  }
  
  if (!videoElement.value || !props.camera.playback_url) {
    console.warn(`[CameraPlayer] ⚠️ Sem playback_url: ${props.camera.name}`);
    return;
  }

  const hlsUrl = props.camera.playback_url;
  const hlsStartTime = performance.now();

  if (Hls.isSupported()) {
    isInitializing.value = true;
    cleanup();
    attempt += 1;
    
    hlsInstance = new Hls({
      enableWorker: true,
      lowLatencyMode: false,
      backBufferLength: 90,
      maxBufferLength: 30,
      maxMaxBufferLength: 60,
      manifestLoadingTimeOut: 10000, // Reduzido de 15s para 10s
      manifestLoadingMaxRetry: 2, // Reduzido de 3 para 2
      manifestLoadingRetryDelay: 1000, // Reduzido de 2s para 1s
      levelLoadingTimeOut: 10000, // Reduzido de 15s para 10s
      levelLoadingMaxRetry: 3, // Reduzido de 4 para 3
      levelLoadingRetryDelay: 1000, // Reduzido de 1.5s para 1s
      fragLoadingTimeOut: 8000, // Reduzido de 10s para 8s
      fragLoadingMaxRetry: 2, // Reduzido de 3 para 2
      fragLoadingRetryDelay: 500, // Reduzido de 1s para 500ms
      startFragPrefetch: true,
      testBandwidth: false,
    });

    hlsInstance.loadSource(hlsUrl);
    hlsInstance.attachMedia(videoElement.value);

    hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
      const manifestTime = performance.now() - hlsStartTime;
      console.log(`[CameraPlayer] ✓ Manifest: ${props.camera.name} - ${manifestTime.toFixed(0)}ms`);
      attempt = 0;
      consecutiveErrors.value = 0;
      hasLoadedSuccessfully = true;
      isInitializing.value = false;
      
      if (!isDestroyed && videoElement.value) {
        videoElement.value.play().catch(err => {
          if (err.name === 'NotAllowedError') {
            console.warn(`[CameraPlayer] 🔇 Autoplay bloqueado - interação necessária`);
          } else {
            console.warn(`[CameraPlayer] Erro ao dar play:`, err);
          }
        });
      }
    });
    
    // Detectar quando o vídeo está realmente tocando
    hlsInstance.on(Hls.Events.FRAG_LOADED, () => {
      if (!isPlaying.value) {
        const totalTime = performance.now() - hlsStartTime;
        isPlaying.value = true;
        console.log(`[CameraPlayer] ▶️ Stream ativo: ${props.camera.name} - Total: ${totalTime.toFixed(0)}ms`);
      }
      // Reset erros se fragmentos estão carregando normalmente
      if (consecutiveErrors.value > 0) {
        consecutiveErrors.value = 0;
      }
    });

    hlsInstance.on(Hls.Events.ERROR, (event, data) => {
      if (isDestroyed) return;
      
      const detail = data?.details || 'unknown';
      
      if (data.fatal) {
        // Se o stream já está tocando, tentar recovery suave primeiro
        if (isPlaying.value) {
          console.warn(`[CameraPlayer] ⚠️ Erro durante playback ${props.camera.name}: ${detail}`);
          
          switch(data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              // Tentar recarregar sem destruir tudo
              try {
                hlsInstance.startLoad();
                return; // Não contar como erro fatal se já estava tocando
              } catch (e) {
                console.error(`[CameraPlayer] Recovery falhou, reiniciando...`);
              }
              break;
              
            case Hls.ErrorTypes.MEDIA_ERROR:
              try {
                hlsInstance.recoverMediaError();
                return; // Não contar como erro fatal se recovery funcionar
              } catch (e) {
                console.error(`[CameraPlayer] Media recovery falhou`);
              }
              break;
          }
        }
        
        // Erro fatal durante inicialização ou recovery falhou
        consecutiveErrors.value++;
        console.error(`[CameraPlayer] ❌ Erro fatal ${props.camera.name}: ${detail}`);
        
        switch(data.type) {
          case Hls.ErrorTypes.NETWORK_ERROR:
            if (detail === 'manifestLoadError' || detail === 'manifestLoadTimeOut') {
              cleanup();
              scheduleRetry();
            } else {
              try {
                hlsInstance.startLoad();
              } catch (e) {
                cleanup();
                scheduleRetry();
              }
            }
            break;
            
          case Hls.ErrorTypes.MEDIA_ERROR:
            try {
              hlsInstance.recoverMediaError();
              consecutiveErrors.value = Math.max(0, consecutiveErrors.value - 1);
            } catch (e) {
              cleanup();
              scheduleRetry();
            }
            break;
            
          default:
            cleanup();
            scheduleRetry();
            break;
        }
      } else {
        // Erros não-fatais - ignorar os mais comuns
        if (detail !== 'fragGap' && detail !== 'bufferStalledError' && detail !== 'levelLoadTimeOut') {
          console.warn(`[CameraPlayer] Aviso ${props.camera.name}: ${detail}`);
        }
      }
    });
    
    // Timeout de segurança para inicialização (20s é suficiente)
    initTimer = setTimeout(() => {
      if (isInitializing.value && !isDestroyed) {
        console.warn(`[CameraPlayer] ⏱️ Timeout: ${props.camera.name}`);
        isInitializing.value = false;
        cleanup();
        scheduleRetry();
      }
    }, 20000);
    
  } else if (videoElement.value.canPlayType('application/vnd.apple.mpegurl')) {
    // Safari nativo
    isInitializing.value = true;
    videoElement.value.src = hlsUrl;
    
    const onLoadedMetadata = () => {
      console.log(`[CameraPlayer] ✓ Stream Safari: ${props.camera.name}`);
      isInitializing.value = false;
      consecutiveErrors.value = 0;
      hasLoadedSuccessfully = true;
      isPlaying.value = true;
      
      if (!isDestroyed) {
        videoElement.value.play().catch(err => {
          console.warn(`[CameraPlayer] 🔇 Autoplay bloqueado:`, err);
        });
      }
    };
    
    const onError = (e) => {
      console.error(`[CameraPlayer] ❌ Erro Safari ${props.camera.name}:`, e);
      isInitializing.value = false;
      consecutiveErrors.value++;
      scheduleRetry();
    };
    
    videoElement.value.addEventListener('loadedmetadata', onLoadedMetadata, { once: true });
    videoElement.value.addEventListener('error', onError, { once: true });
  }
};

// Watch muted prop changes
watch(() => props.muted, (newMuted) => {
  if (videoElement.value && !isDestroyed) {
    videoElement.value.muted = newMuted;
  }
});

// Reinicializa quando a URL de playback mudar
watch(() => props.camera?.playback_url, (newUrl, oldUrl) => {
  if (isDestroyed) return;
  
  if (newUrl !== oldUrl) {
    attempt = 0;
    consecutiveErrors.value = 0;
    cleanup();
    
    if (newUrl) {
      // Pequeno delay para evitar inicializações simultâneas
      setTimeout(() => {
        if (!isDestroyed) initHLS();
      }, 300);
    }
  }
});

onMounted(() => {
  isDestroyed = false;
  
  // Delay inicial para distribuir carga quando múltiplas câmeras carregam juntas
  const initialDelay = Math.random() * 1000; // 0-1s aleatório
  setTimeout(() => {
    if (!isDestroyed && props.camera?.playback_url) {
      initHLS();
    }
  }, initialDelay);
});

onUnmounted(() => {
  isDestroyed = true;
  cleanup();
});

// Expose video element para controles externos se necessário
defineExpose({
  videoElement
});
</script>
