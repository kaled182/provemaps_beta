import { ref, onUnmounted } from 'vue';

/**
 * Shared WebSocket por URL — singleton com refcount.
 *
 * Diferente de `useWebSocket`, esta versão reutiliza uma única conexão
 * WebSocket entre todos os componentes que pedirem a mesma URL. Cada
 * chamada incrementa o refcount; quando o último consumidor desmonta,
 * a conexão é fechada (com debounce de 1s para evitar reconectar logo
 * em seguida em navegação).
 *
 * Use para tópicos broadcast (ex.: dashboard.status), onde múltiplos
 * componentes consomem o mesmo stream.
 */

const pool = new Map(); // url → { socket, refcount, lastMessage, connected, closeTimer, listeners }

function getEntry(url) {
  let entry = pool.get(url);
  if (!entry) {
    entry = {
      socket: null,
      refcount: 0,
      lastMessage: ref(null),
      connected: ref(false),
      closeTimer: null,
      reconnectTimer: null,
      reconnectAttempts: 0,
      maxReconnectAttempts: 10,
      reconnectDelay: 5000,
    };
    pool.set(url, entry);
  }
  return entry;
}

function connect(url, entry) {
  if (entry.socket) return; // já conectado/conectando

  try {
    const ws = new WebSocket(url);
    entry.socket = ws;

    ws.onopen = () => {
      entry.connected.value = true;
      entry.reconnectAttempts = 0;
      console.log('[useSharedWebSocket] Connected:', url);
    };

    ws.onmessage = (event) => {
      try {
        entry.lastMessage.value = JSON.parse(event.data);
      } catch {
        entry.lastMessage.value = event.data;
      }
    };

    ws.onerror = (evt) => {
      console.warn('[useSharedWebSocket] Error:', url, evt);
    };

    ws.onclose = () => {
      entry.connected.value = false;
      entry.socket = null;

      // Só reconecta se ainda houver consumidores
      if (entry.refcount > 0 && entry.reconnectAttempts < entry.maxReconnectAttempts) {
        entry.reconnectAttempts++;
        console.log(`[useSharedWebSocket] Reconnecting ${url} (${entry.reconnectAttempts}/${entry.maxReconnectAttempts})`);
        entry.reconnectTimer = setTimeout(() => connect(url, entry), entry.reconnectDelay);
      }
    };
  } catch (e) {
    console.error('[useSharedWebSocket] Failed to connect:', url, e);
  }
}

function teardown(url, entry) {
  if (entry.reconnectTimer) {
    clearTimeout(entry.reconnectTimer);
    entry.reconnectTimer = null;
  }
  if (entry.socket) {
    try { entry.socket.close(); } catch { /* noop */ }
    entry.socket = null;
  }
  entry.connected.value = false;
  pool.delete(url);
}

export function useSharedWebSocket(url, options = {}) {
  const entry = getEntry(url);

  if (options.maxReconnectAttempts) entry.maxReconnectAttempts = options.maxReconnectAttempts;
  if (options.reconnectDelay) entry.reconnectDelay = options.reconnectDelay;

  // Cancelar fechamento pendente, se houver
  if (entry.closeTimer) {
    clearTimeout(entry.closeTimer);
    entry.closeTimer = null;
  }

  entry.refcount += 1;
  if (!entry.socket) connect(url, entry);

  onUnmounted(() => {
    entry.refcount = Math.max(0, entry.refcount - 1);
    if (entry.refcount === 0) {
      // Debounce de 1s antes de fechar — evita ping-pong em navegação
      entry.closeTimer = setTimeout(() => {
        if (entry.refcount === 0) teardown(url, entry);
      }, 1000);
    }
  });

  return {
    connected: entry.connected,
    lastMessage: entry.lastMessage,
  };
}
