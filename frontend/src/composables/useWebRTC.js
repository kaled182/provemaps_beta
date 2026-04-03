import { ref, onUnmounted } from 'vue';

/**
 * Composable para gerenciar conexões WebRTC/WHEP
 * 
 * @example
 * // Uso básico
 * const rtc = useWebRTC();
 * await rtc.connect('http://localhost:8889/gateway_123/whep');
 * 
 * // Com proxy reverso (CSP/CORS-safe)
 * await rtc.connect('http://localhost:8082/camera-stream/gateway_123/whep');
 * 
 * // Com monitoramento de stats
 * const rtc = useWebRTC({
 *   onStatsUpdate: (stats) => {
 *     console.log(`FPS: ${stats.framesPerSecond}, Quality: ${stats.networkQuality}`);
 *   }
 * });
 * 
 * @param {Object} options - Opções de configuração
 * @param {number} options.maxRetries - Número máximo de tentativas (padrão: 5)
 * @param {number} options.maxBackoff - Delay máximo em ms (padrão: 30000)
 * @param {Function} options.onStatsUpdate - Callback para receber stats (opcional)
 */
export function useWebRTC(options = {}) {
  const {
    maxRetries = 5,
    maxBackoff = 30000,
    onStatsUpdate = null
  } = options;

  // State
  const peerConnection = ref(null);
  const stream = ref(null);
  const isConnected = ref(false);
  const isConnecting = ref(false);
  const error = ref(null);
  const stats = ref({
    packetsLost: 0,
    framesPerSecond: 0,
    bytesReceived: 0,
    jitter: 0,
    networkQuality: 'good' // good, degraded, poor
  });

  // Internal state
  let retryCount = 0;
  let statsInterval = null;
  let reconnectTimeout = null;

  /**
   * Calcula delay usando Exponential Backoff
   * Tentativa 1: 1s, 2: 2s, 3: 4s, 4: 8s, 5: 16s, 6: 30s (max)
   */
  const calculateBackoff = (attempt) => {
    const delay = Math.min(1000 * Math.pow(2, attempt), maxBackoff);
    return delay;
  };

  /**
   * Conecta ao servidor WHEP
   * @param {string} whepUrl - URL do endpoint WHEP
   */
  const connect = async (whepUrl) => {
    if (isConnecting.value) {
      console.warn('[useWebRTC] Já existe uma tentativa de conexão em andamento');
      return;
    }

    isConnecting.value = true;
    error.value = null;

    try {
      // Criar RTCPeerConnection
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
        bundlePolicy: 'max-bundle'
      });

      peerConnection.value = pc;

      // Handler para quando receber o stream
      pc.ontrack = (event) => {
        console.log('[useWebRTC] Track recebida:', event.track.kind);
        if (event.streams && event.streams[0]) {
          stream.value = event.streams[0];
          isConnected.value = true;
          retryCount = 0; // Reset retry counter on success
          startStatsMonitoring();
        }
      };

      // Handler para mudanças de estado da conexão
      pc.onconnectionstatechange = () => {
        console.log('[useWebRTC] Connection state:', pc.connectionState);
        
        if (pc.connectionState === 'connected') {
          isConnected.value = true;
          retryCount = 0;
        } else if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
          isConnected.value = false;
          handleReconnect(whepUrl);
        }
      };

      // Handler ICE
      pc.oniceconnectionstatechange = () => {
        console.log('[useWebRTC] ICE state:', pc.iceConnectionState);
      };

      pc.onicecandidate = (event) => {
        if (event.candidate) {
          console.log('[useWebRTC] ICE Candidate:', event.candidate.candidate);
        } else {
          console.log('[useWebRTC] ICE gathering complete');
        }
      };

      // Adicionar transceiver para receber vídeo
      pc.addTransceiver('video', { direction: 'recvonly' });
      pc.addTransceiver('audio', { direction: 'recvonly' });

      // Criar oferta SDP
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      console.log('[useWebRTC] SDP Offer criado, enviando para:', whepUrl);
      console.log('[useWebRTC] SDP length:', offer.sdp.length);

      // Enviar oferta para o servidor WHEP
      const response = await fetch(whepUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/sdp',
          'Accept': 'application/sdp'
        },
        body: offer.sdp
      });
      
      console.log('[useWebRTC] Response status:', response.status);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Stream não encontrado (404)');
        }
        throw new Error(`Falha na negociação WHEP: ${response.status}`);
      }

      // Receber resposta SDP do servidor
      const answerSdp = await response.text();
      await pc.setRemoteDescription(new RTCSessionDescription({
        type: 'answer',
        sdp: answerSdp
      }));

      console.log('[useWebRTC] Conexão WHEP estabelecida com sucesso');
      isConnecting.value = false;

    } catch (err) {
      console.error('[useWebRTC] Erro na conexão:', err);
      error.value = err.message;
      isConnecting.value = false;
      isConnected.value = false;
      
      // Limpar peer connection com erro
      if (peerConnection.value) {
        peerConnection.value.close();
        peerConnection.value = null;
      }

      // Tentar reconectar se não for 404
      if (!err.message.includes('404')) {
        handleReconnect(whepUrl);
      }
    }
  };

  /**
   * Gerencia reconexão com Exponential Backoff
   */
  const handleReconnect = (whepUrl) => {
    if (retryCount >= maxRetries) {
      console.error('[useWebRTC] Número máximo de tentativas atingido');
      error.value = 'Não foi possível conectar após várias tentativas';
      return;
    }

    const delay = calculateBackoff(retryCount);
    retryCount++;

    console.log(`[useWebRTC] Tentativa ${retryCount}/${maxRetries} em ${delay}ms`);

    // Limpar timeout anterior se existir
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
    }

    reconnectTimeout = setTimeout(() => {
      connect(whepUrl);
    }, delay);
  };

  /**
   * Inicia monitoramento de estatísticas WebRTC
   */
  const startStatsMonitoring = () => {
    if (statsInterval || !peerConnection.value) return;

    statsInterval = setInterval(async () => {
      if (!peerConnection.value) {
        stopStatsMonitoring();
        return;
      }

      try {
        const statsReport = await peerConnection.value.getStats();
        let totalPacketsLost = 0;
        let totalPacketsReceived = 0;
        let currentFps = 0;
        let bytesReceived = 0;
        let jitter = 0;

        statsReport.forEach(report => {
          if (report.type === 'inbound-rtp' && report.kind === 'video') {
            totalPacketsLost += report.packetsLost || 0;
            totalPacketsReceived += report.packetsReceived || 0;
            currentFps = report.framesPerSecond || 0;
            bytesReceived += report.bytesReceived || 0;
            jitter = report.jitter || 0;
          }
        });

        // Calcular qualidade da rede
        const packetLossRate = totalPacketsReceived > 0 
          ? (totalPacketsLost / totalPacketsReceived) * 100 
          : 0;

        let quality = 'good';
        if (packetLossRate > 5 || currentFps < 10) {
          quality = 'poor';
        } else if (packetLossRate > 2 || currentFps < 20) {
          quality = 'degraded';
        }

        stats.value = {
          packetsLost: totalPacketsLost,
          framesPerSecond: Math.round(currentFps),
          bytesReceived,
          jitter: Math.round(jitter * 1000), // ms
          networkQuality: quality
        };

        // Callback externo se fornecido
        if (onStatsUpdate) {
          onStatsUpdate(stats.value);
        }

      } catch (err) {
        console.error('[useWebRTC] Erro ao obter stats:', err);
      }
    }, 10000); // A cada 10 segundos
  };

  /**
   * Para monitoramento de stats
   */
  const stopStatsMonitoring = () => {
    if (statsInterval) {
      clearInterval(statsInterval);
      statsInterval = null;
    }
  };

  /**
   * Fecha a conexão WebRTC
   */
  const close = () => {
    // Limpar timeout de reconexão
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }

    // Parar stats
    stopStatsMonitoring();

    // Fechar peer connection
    if (peerConnection.value) {
      peerConnection.value.close();
      peerConnection.value = null;
    }

    // Reset state
    stream.value = null;
    isConnected.value = false;
    isConnecting.value = false;
    error.value = null;
    retryCount = 0;
  };

  // Cleanup automático
  onUnmounted(() => {
    close();
  });

  return {
    // State
    stream,
    isConnected,
    isConnecting,
    error,
    stats,
    
    // Methods
    connect,
    close
  };
}
