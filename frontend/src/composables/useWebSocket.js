import { ref, onUnmounted, watch } from 'vue';

/**
 * WebSocket composable with auto-reconnect and lifecycle management.
 * 
 * @param {string} url - WebSocket URL (e.g., 'ws://localhost:8000/ws/dashboard/status/')
 * @param {Object} options - Configuration options
 * @param {number} options.reconnectDelay - Delay before reconnecting (ms, default 3000)
 * @param {number} options.maxReconnectAttempts - Max reconnect attempts (default 5)
 * @param {boolean} options.autoConnect - Auto-connect on mount (default true)
 * @returns {Object} WebSocket state and methods
 */
export function useWebSocket(url, options = {}) {
  const {
    reconnectDelay = 3000,
    maxReconnectAttempts = 5,
    autoConnect = true,
  } = options;

  const socket = ref(null);
  const connected = ref(false);
  const connecting = ref(false);
  const lastMessage = ref(null);
  const error = ref(null);
  const reconnectAttempts = ref(0);

  let reconnectTimer = null;

  function connect() {
    if (connecting.value || connected.value) return;
    
    connecting.value = true;
    error.value = null;

    try {
      socket.value = new WebSocket(url);

      socket.value.onopen = () => {
        connected.value = true;
        connecting.value = false;
        reconnectAttempts.value = 0;
        console.log('[useWebSocket] Connected to', url);
      };

      socket.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          lastMessage.value = data;
        } catch (e) {
          console.error('[useWebSocket] Failed to parse message', e);
          lastMessage.value = event.data;
        }
      };

      socket.value.onerror = (evt) => {
        error.value = 'WebSocket error occurred';
        console.error('[useWebSocket] Error', evt);
      };

      socket.value.onclose = () => {
        connected.value = false;
        connecting.value = false;
        console.log('[useWebSocket] Disconnected from', url);

        // Auto-reconnect if not exceeded max attempts
        if (reconnectAttempts.value < maxReconnectAttempts) {
          reconnectAttempts.value++;
          console.log(`[useWebSocket] Reconnecting... (attempt ${reconnectAttempts.value}/${maxReconnectAttempts})`);
          reconnectTimer = setTimeout(connect, reconnectDelay);
        } else {
          error.value = 'Max reconnect attempts reached';
        }
      };
    } catch (e) {
      error.value = e.message;
      connecting.value = false;
      console.error('[useWebSocket] Failed to connect', e);
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (socket.value) {
      socket.value.close();
      socket.value = null;
    }
    connected.value = false;
    connecting.value = false;
    reconnectAttempts.value = 0;
  }

  function send(data) {
    if (!connected.value || !socket.value) {
      console.warn('[useWebSocket] Not connected, cannot send message');
      return false;
    }
    const payload = typeof data === 'string' ? data : JSON.stringify(data);
    socket.value.send(payload);
    return true;
  }

  // Auto-connect on mount if enabled
  if (autoConnect) {
    connect();
  }

  // Cleanup on unmount
  onUnmounted(() => {
    disconnect();
  });

  return {
    socket,
    connected,
    connecting,
    lastMessage,
    error,
    reconnectAttempts,
    connect,
    disconnect,
    send,
  };
}
