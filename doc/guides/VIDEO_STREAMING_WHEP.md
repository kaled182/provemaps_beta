# Guia: Streaming de Vídeo com WHEP (WebRTC)

## Visão Geral

O sistema utiliza **WHEP (WebRTC HTTP Egress Protocol)** para streaming de vídeo de baixa latência entre o MediaMTX e navegadores. Este guia explica a arquitetura, configuração e uso do composable `useWebRTC`.

---

## Arquitetura

```
Browser (Vue 3)
    ↓ WHEP negotiation (SDP offer/answer)
    ↓
Nginx Proxy (porta 8082)
    ↓ /camera-stream/* → MediaMTX:8889
    ↓
MediaMTX (porta 8889)
    ↓ WebRTC streams
Câmeras IP (RTSP/ONVIF)
```

### Fluxo de Dados

1. **Backend Django** chama `/setup_app/api/gateways/{id}/video/preview/start/` para iniciar captura RTSP→MediaMTX
2. **Frontend Vue** usa `useWebRTC()` para negociar conexão WHEP
3. **MediaMTX** envia tracks de vídeo/áudio via WebRTC
4. **Browser** renderiza stream em `<video>` com `object-fit: cover`

---

## Proxy Reverso Nginx (Recomendado)

### Por que usar proxy?

- **CSP (Content Security Policy)**: Navegadores bloqueiam requisições cross-origin para porta 8889 diretamente
- **CORS**: Headers `Access-Control-*` centralizados no Nginx
- **Firewall**: Evita expor porta MediaMTX publicamente
- **Certificados**: SSL/TLS em uma camada única

### Configuração

Arquivo: [`docker/hls/nginx.conf`](../../docker/hls/nginx.conf)

```nginx
location /camera-stream/ {
    rewrite ^/camera-stream/(.*) /$1 break;
    
    proxy_pass http://mediamtx:8889;
    proxy_http_version 1.1;
    
    # CORS para WHEP
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PATCH, DELETE' always;
    add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
}
```

### URLs de Exemplo

| Modo | URL | Observações |
|------|-----|-------------|
| **Proxy** | `http://localhost:8082/camera-stream/gateway_123/whep` | ✅ Recomendado (CSP-safe) |
| **Direto** | `http://localhost:8889/gateway_123/whep` | ⚠️ Pode ser bloqueado por CSP |

---

## Uso do Composable `useWebRTC`

### Exemplo Básico

```vue
<template>
  <video ref="videoEl" autoplay muted playsinline class="w-full h-full object-cover"></video>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useWebRTC } from '@/composables/useWebRTC';

const videoEl = ref(null);

onMounted(async () => {
  const rtc = useWebRTC();
  
  // Conectar ao stream WHEP
  await rtc.connect('http://localhost:8082/camera-stream/gateway_123/whep');
  
  // Vincular stream ao elemento de vídeo
  if (rtc.stream.value) {
    videoEl.value.srcObject = rtc.stream.value;
  }
});
</script>
```

### Exemplo com Monitoramento de Stats

```vue
<script setup>
import { useWebRTC } from '@/composables/useWebRTC';
import { ref } from 'vue';

const networkQuality = ref('good');

const rtc = useWebRTC({
  maxRetries: 5,
  maxBackoff: 30000,
  onStatsUpdate: (stats) => {
    networkQuality.value = stats.networkQuality; // 'good', 'degraded', 'poor'
    console.log(`FPS: ${stats.framesPerSecond}, Packets Lost: ${stats.packetsLost}`);
  }
});

await rtc.connect(whepUrl);
</script>

<template>
  <div class="relative">
    <video ref="videoEl" autoplay muted playsinline></video>
    
    <div v-if="networkQuality !== 'good'" class="alert">
      ⚠️ Rede Instável
    </div>
  </div>
</template>
```

### Propriedades Reativas

| Propriedade | Tipo | Descrição |
|-------------|------|-----------|
| `stream` | `ref(MediaStream)` | Stream WebRTC (vincular a `videoEl.srcObject`) |
| `isConnected` | `ref(Boolean)` | `true` quando RTCPeerConnection está conectado |
| `isConnecting` | `ref(Boolean)` | `true` durante negociação SDP |
| `error` | `ref(String)` | Mensagem de erro ou `null` |
| `stats` | `ref(Object)` | Estatísticas atualizadas a cada 10s |

### Métodos

| Método | Parâmetros | Descrição |
|--------|-----------|-----------|
| `connect(whepUrl)` | `String` | Inicia negociação WHEP |
| `close()` | - | Fecha conexão e limpa recursos |

---

## Stats de Qualidade

O composable monitora automaticamente:

- **packetsLost**: Pacotes perdidos (indica congestão)
- **framesPerSecond**: FPS real do decode
- **bytesReceived**: Tráfego total
- **jitter**: Variação de latência (ms)
- **networkQuality**: `'good'` | `'degraded'` | `'poor'`

### Regras de Classificação

| Qualidade | Perda de Pacotes | FPS |
|-----------|------------------|-----|
| `good` | < 2% | ≥ 20 |
| `degraded` | 2-5% | 10-20 |
| `poor` | > 5% | < 10 |

---

## Exponential Backoff

Em caso de falha de conexão, o composable tenta reconectar automaticamente com delays crescentes:

| Tentativa | Delay |
|-----------|-------|
| 1 | 1s |
| 2 | 2s |
| 3 | 4s |
| 4 | 8s |
| 5 | 16s |
| 6+ | 30s (max) |

Isso evita DDoS não intencional ao MediaMTX quando múltiplas câmeras falham simultaneamente.

---

## Gerenciamento de Áudio

### Regra de Exclusividade

Em mosaicos com múltiplas câmeras, **apenas UMA pode ter áudio desmutado** por vez. Implementação:

```vue
<script setup>
const unmutedCameraId = ref(null);

const toggleAudio = (cameraId) => {
  // Se já está desmutada, mutar
  if (unmutedCameraId.value === cameraId) {
    unmutedCameraId.value = null;
    return;
  }
  
  // Desmutar apenas esta
  unmutedCameraId.value = cameraId;
};

// Watch para aplicar mute/unmute nos elementos
watch(unmutedCameraId, (newId, oldId) => {
  if (oldId && videoRefs.value[oldId]) {
    videoRefs.value[oldId].muted = true;
  }
  if (newId && videoRefs.value[newId]) {
    videoRefs.value[newId].muted = false;
  }
});
</script>
```

---

## Troubleshooting

### Stream não conecta (404)

**Causa**: MediaMTX não recebeu o stream RTSP ainda

**Solução**:
1. Verificar logs do backend: `docker logs docker-web-1 | grep gateway_123`
2. Confirmar que `/preview/start/` retornou `playback_url`
3. Aguardar 2-3s para MediaMTX publicar (já implementado em `MosaicViewerView`)

### CSP bloqueia requisições

**Causa**: `connect-src` não permite porta 8889

**Solução**: Usar proxy Nginx em `localhost:8082/camera-stream/*`

### "Network Quality: Poor" persistente

**Causa**: Bandwidth insuficiente ou CPU do cliente sobrecarregado

**Solução**:
1. Reduzir número de câmeras simultâneas
2. Verificar resolução no MediaMTX (720p recomendado)
3. Monitorar CPU com `docker stats`

---

## Referências

- [WHEP Spec (RFC Draft)](https://datatracker.ietf.org/doc/html/draft-ietf-wish-whip)
- [MediaMTX Documentation](https://github.com/bluenviron/mediamtx)
- [RTCPeerConnection API](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection)
