<template>
  <nav class="bg-gray-800 text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <!-- Menu de Navegação -->
        <div class="flex items-center space-x-1">
          <a 
            href="/maps_view/dashboard/" 
            class="px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors"
            :class="{ 'bg-gray-900': isActive('/maps_view/dashboard/') }"
          >
            Dashboard
          </a>
          <a 
            href="/setup/" 
            class="px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors"
            :class="{ 'bg-gray-900': isActive('/setup/') }"
          >
            Setup
          </a>
          <a 
            href="/admin/" 
            class="px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors"
            :class="{ 'bg-gray-900': isActive('/admin/') }"
            target="_blank"
          >
            Admin
          </a>
        </div>

        <!-- Status de Conexão e Logout -->
        <div class="flex items-center space-x-4">
          <!-- Status de Conexão -->
          <div class="flex items-center space-x-2">
            <span 
              class="w-2 h-2 rounded-full"
              :class="connectionStatus.color"
            ></span>
            <span class="text-sm font-medium">{{ connectionStatus.text }}</span>
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
              class="px-3 py-2 rounded-md text-sm font-medium bg-red-600 hover:bg-red-700 transition-colors"
            >
              Sair
            </button>
          </form>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

const csrfToken = ref(window.CSRF_TOKEN || '');
const wsConnected = ref(false);
const wsConnecting = ref(false);
let ws = null;

const connectionStatus = computed(() => {
  if (wsConnected.value) {
    return { color: 'bg-green-500', text: 'Conectado' };
  } else if (wsConnecting.value) {
    return { color: 'bg-yellow-500', text: 'Conectando...' };
  } else {
    return { color: 'bg-red-500', text: 'Desconectado' };
  }
});

function isActive(path) {
  return window.location.pathname.startsWith(path);
}

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
/* Animações suaves */
nav a, nav button {
  transition: all 0.2s ease-in-out;
}

nav a:hover, nav button:hover {
  transform: translateY(-1px);
}
</style>
