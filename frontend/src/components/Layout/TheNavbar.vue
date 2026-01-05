<template>
  <nav class="top-navbar" :class="{ 'navbar-collapsed': !uiStore.isHeaderOpen }">
    <div class="navbar-content">
      <!-- Botão de toggle do header -->
      <button @click="uiStore.toggleHeader()" class="header-toggle-btn">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
            :d="uiStore.isHeaderOpen ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'" />
        </svg>
      </button>

      <transition name="fade">
        <div v-if="uiStore.isHeaderOpen" class="navbar-items">
          <!-- Título da página -->
          <div class="page-title">
            <h1>Dashboard</h1>
          </div>
          
          <!-- Actions: Status, Logout -->
          <div class="navbar-actions">
            <!-- Status de Conexão -->
            <div class="connection-status">
              <span
                class="status-dot"
                :style="connectionStatus.style"
              ></span>
              <span class="status-text">{{ connectionStatus.text }}</span>
            </div>
            
            <!-- Botão Logout -->
            <form 
              action="/accounts/logout/" 
              method="post" 
              class="inline"
            >
              <input 
                type="hidden" 
                name="csrfmiddlewaretoken" 
                :value="csrfToken"
              >
              <button 
                type="submit" 
                class="logout-btn"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                <span>Sair</span>
              </button>
            </form>
          </div>
        </div>
      </transition>
    </div>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useUiStore } from '@/stores/ui';

const uiStore = useUiStore();
const csrfToken = ref(window.CSRF_TOKEN || '');
const wsConnected = ref(false);
const wsConnecting = ref(false);
let ws = null;

const connectionStatus = computed(() => {
  if (wsConnected.value) {
    return {
      text: 'Conectado',
      style: {
        background: 'var(--status-online)',
        boxShadow: '0 0 8px rgba(34, 197, 94, 0.55)',
      },
    };
  } else if (wsConnecting.value) {
    return {
      text: 'Conectando...',
      style: {
        background: 'var(--status-warning)',
        boxShadow: '0 0 8px rgba(245, 158, 11, 0.45)',
      },
    };
  } else {
    return {
      text: 'Desconectado',
      style: {
        background: 'var(--status-offline)',
        boxShadow: '0 0 8px rgba(248, 113, 113, 0.45)',
      },
    };
  }
});

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/dashboard/status/`;
  
  wsConnecting.value = true;
  
  try {
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      wsConnected.value = true;
      wsConnecting.value = false;
    };
    
    ws.onclose = () => {
      wsConnected.value = false;
      wsConnecting.value = false;
      
      // Tentar reconectar após 5 segundos
      setTimeout(() => {
        if (!wsConnected.value) {
          connectWebSocket();
        }
      }, 5000);
    };
    
    ws.onerror = () => {
      wsConnected.value = false;
      wsConnecting.value = false;
    };
  } catch (err) {
    wsConnected.value = false;
    wsConnecting.value = false;
  }
}

onMounted(() => {
  connectWebSocket();
});

onUnmounted(() => {
  if (ws) {
    ws.close();
  }
});
</script>

<style scoped>
.top-navbar {
  position: fixed;
  top: 0;
  left: 280px;
  right: 0;
  height: 64px;
  background: var(--menu-bg);
  box-shadow: var(--shadow-md);
  z-index: 1100;
  transition: all 0.3s ease;
}

.top-navbar.navbar-collapsed {
  height: 40px;
}

.navbar-content {
  height: 100%;
  display: flex;
  align-items: center;
  padding: 0 1.5rem;
}

.header-toggle-btn {
  background: transparent;
  border: none;
  color: var(--menu-text-tertiary);
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
  margin-right: 1rem;
}

.header-toggle-btn:hover {
  color: var(--menu-text-primary);
}

.header-toggle-btn svg {
  width: 20px;
  height: 20px;
}

.navbar-items {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 1;
}

.page-title h1 {
  color: var(--menu-text-primary);
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.navbar-actions {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--menu-item-hover);
  border-radius: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-text {
  color: var(--menu-text-primary);
  font-size: 0.875rem;
  font-weight: 500;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--danger-soft-bg);
  border: 1px solid var(--accent-danger);
  border-radius: 8px;
  color: var(--accent-danger);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: var(--accent-danger);
  color: #ffffff;
  border-color: var(--accent-danger);
}

.logout-btn svg {
  width: 18px;
  height: 18px;
}

/* Animações */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* Ajuste quando menu lateral colapsar */
@media (min-width: 769px) {
  .top-navbar {
    left: var(--nav-menu-width, 280px);
  }
}

@media (max-width: 768px) {
  .top-navbar {
    left: 0;
  }
}
</style>
