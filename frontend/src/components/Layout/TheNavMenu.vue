<template>
  <aside 
    class="nav-menu"
    :class="{ 'nav-menu-collapsed': !uiStore.isNavMenuOpen }"
  >
    <!-- Header do Menu -->
    <div class="nav-menu-header">
      <div class="logo-container">
        <div class="logo-icon">
          <span v-if="uiStore.isNavMenuOpen">SI</span>
          <span v-else class="logo-icon-small">S</span>
        </div>
        <transition name="fade">
          <span v-if="uiStore.isNavMenuOpen" class="logo-text">SIMPLES INTERNET</span>
        </transition>
      </div>
      <button 
        @click="uiStore.toggleNavMenu()" 
        class="toggle-btn"
        :title="uiStore.isNavMenuOpen ? 'Recolher menu' : 'Expandir menu'"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
            :d="uiStore.isNavMenuOpen ? 'M11 19l-7-7 7-7m8 14l-7-7 7-7' : 'M13 5l7 7-7 7M5 5l7 7-7 7'" />
        </svg>
      </button>
    </div>

    <!-- Menu Items -->
    <nav class="nav-items">
      <a 
        v-for="item in menuItems" 
        :key="item.path"
        :href="item.path" 
        class="nav-item"
        :class="{ 'active': isActive(item.path) }"
        :title="!uiStore.isNavMenuOpen ? item.label : ''"
      >
        <span class="nav-icon" v-html="item.icon"></span>
        <transition name="fade">
          <span v-if="uiStore.isNavMenuOpen" class="nav-label">{{ item.label }}</span>
        </transition>
        <span v-if="item.badge && uiStore.isNavMenuOpen" class="nav-badge">{{ item.badge }}</span>
      </a>
    </nav>

    <!-- Footer -->
    <div class="nav-menu-footer">
      <div class="divider"></div>
      
      <!-- Status de Conexão -->
      <div class="nav-item status-item" :class="connectionStatus.color">
        <span class="nav-icon" v-html="connectionStatus.icon"></span>
        <transition name="fade">
          <span v-if="uiStore.isNavMenuOpen" class="nav-label">{{ connectionStatus.text }}</span>
        </transition>
      </div>
      
      <a 
        href="/setup/" 
        class="nav-item"
        :class="{ 'active': isActive('/setup/') }"
        :title="!uiStore.isNavMenuOpen ? 'Setup' : ''"
      >
        <span class="nav-icon">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </span>
        <transition name="fade">
          <span v-if="uiStore.isNavMenuOpen" class="nav-label">Setup</span>
        </transition>
      </a>
      
      <a 
        href="/admin/" 
        class="nav-item"
        target="_blank"
        :title="!uiStore.isNavMenuOpen ? 'Admin' : ''"
      >
        <span class="nav-icon">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
        </span>
        <transition name="fade">
          <span v-if="uiStore.isNavMenuOpen" class="nav-label">Admin</span>
        </transition>
      </a>
      
      <!-- Theme Toggle Button -->
      <button 
        @click="uiStore.toggleTheme()"
        class="nav-item theme-toggle"
        :title="!uiStore.isNavMenuOpen ? (uiStore.theme === 'dark' ? 'Modo Claro' : 'Modo Escuro') : ''"
      >
        <span class="nav-icon">
          <!-- Sun icon for dark mode (clicking switches to light) -->
          <svg v-if="uiStore.theme === 'dark'" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
          <!-- Moon icon for light mode (clicking switches to dark) -->
          <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
          </svg>
        </span>
        <transition name="fade">
          <span v-if="uiStore.isNavMenuOpen" class="nav-label">
            {{ uiStore.theme === 'dark' ? 'Modo Claro' : 'Modo Escuro' }}
          </span>
        </transition>
      </button>
      
      <!-- Botão Sair -->
      <form action="/accounts/logout/" method="post">
        <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken">
        <button 
          type="submit" 
          class="nav-item logout-item"
          :title="!uiStore.isNavMenuOpen ? 'Sair' : ''"
        >
          <span class="nav-icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </span>
          <transition name="fade">
            <span v-if="uiStore.isNavMenuOpen" class="nav-label">Sair</span>
          </transition>
        </button>
      </form>
    </div>
  </aside>
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
      color: 'bg-green-500', 
      text: 'Conectado',
      icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>'
    };
  } else if (wsConnecting.value) {
    return { 
      color: 'bg-yellow-500', 
      text: 'Conectando',
      icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>'
    };
  } else {
    return { 
      color: 'bg-red-500', 
      text: 'Desconectado',
      icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414" /></svg>'
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

const menuItems = [
  {
    label: 'Dashboard',
    path: '/maps_view/dashboard/',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>'
  },
  {
    label: 'Metrics',
    path: '/maps_view/metrics/',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>'
  },
  {
    label: 'Routes',
    path: '/routes/fiber-route-builder/',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" /></svg>'
  },
  {
    label: 'Docs',
    path: '/docs/',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>'
  },
  {
    label: 'Add Device',
    path: '/zabbix/lookup/',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>',
    badge: '+'
  }
];

function isActive(path) {
  return window.location.pathname.startsWith(path);
}
</script>

<style scoped>
.nav-menu {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 280px;
  background: linear-gradient(195deg, var(--menu-bg-start) 0%, var(--menu-bg-end) 100%);
  box-shadow: var(--shadow-accent);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease, transform 0.3s ease, background 0.3s ease;
  z-index: 1200;
  overflow: hidden;
}

.nav-menu-collapsed {
  width: 60px;
}

.nav-menu-header {
  padding: 1.5rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-primary);
  min-height: 64px;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  overflow: hidden;
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(195deg, var(--menu-item-active-start) 0%, var(--menu-item-active-end) 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
  box-shadow: var(--shadow-accent);
}

.logo-icon-small {
  font-size: 18px;
}

.logo-text {
  color: var(--text-primary);
  font-weight: 600;
  font-size: 0.875rem;
  white-space: nowrap;
}

.toggle-btn {
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
  flex-shrink: 0;
}

.toggle-btn:hover {
  color: var(--text-primary);
}

.toggle-btn svg {
  width: 20px;
  height: 20px;
}

.nav-items {
  flex: 1;
  padding: 1rem 0.5rem;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-items::-webkit-scrollbar {
  width: 4px;
}

.nav-items::-webkit-scrollbar-track {
  background: transparent;
}

.nav-items::-webkit-scrollbar-thumb {
  background: var(--border-primary);
  border-radius: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  margin-bottom: 0.25rem;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
  white-space: nowrap;
}

.nav-menu-collapsed .nav-item {
  justify-content: center;
  padding: 0.75rem 0.5rem;
}

.nav-item:hover {
  background: var(--menu-item-hover);
  color: var(--text-primary);
}

.nav-item.router-link-active,
.nav-item.router-link-exact-active {
  background: linear-gradient(195deg, var(--menu-item-active-start) 0%, var(--menu-item-active-end) 100%);
  color: white;
  box-shadow: var(--shadow-accent);
}

.nav-item-icon {
  font-size: 1.125rem;
  min-width: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-item-text {
  margin-left: 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  flex: 1;
}

.nav-menu-collapsed .nav-item-text {
  display: none;
}

.nav-footer {
  padding: 1rem 0.5rem;
  border-top: 1px solid var(--border-primary);
}

.ws-status {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  margin-bottom: 0.5rem;
  border-radius: 8px;
  background: var(--menu-item-hover);
  font-size: 0.8rem;
  overflow: hidden;
  white-space: nowrap;
  transition: background 0.3s ease;
}

.nav-menu-collapsed .ws-status {
  justify-content: center;
  padding: 0.75rem 0.5rem;
}

.ws-status-icon {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 0.75rem;
  flex-shrink: 0;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.ws-status-icon.online {
  background-color: var(--status-online);
  box-shadow: 0 0 0 2px var(--status-online-light);
}

.ws-status-icon.connecting {
  background-color: var(--status-warning);
  box-shadow: 0 0 0 2px var(--status-warning-light);
}

.ws-status-icon.offline {
  background-color: var(--status-offline);
  box-shadow: 0 0 0 2px var(--status-offline-light);
  animation: none;
}

.nav-menu-collapsed .ws-status-icon {
  margin-right: 0;
}

.ws-status-text {
  font-weight: 500;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-menu-collapsed .ws-status-text {
  display: none;
}

.footer-actions {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.footer-item {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s;
  overflow: hidden;
  white-space: nowrap;
  background: transparent;
  border: none;
  width: 100%;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
}

.nav-menu-collapsed .footer-item {
  justify-content: center;
  padding: 0.75rem 0.5rem;
}

.footer-item:hover {
  background: var(--menu-item-hover);
  color: var(--text-primary);
}

.footer-item-icon {
  font-size: 1.125rem;
  min-width: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.footer-item-text {
  margin-left: 1rem;
  flex: 1;
  text-align: left;
}

.nav-menu-collapsed .footer-item-text {
  display: none;
}

.footer-item.logout-item {
  color: var(--status-offline);
}

.footer-item.logout-item:hover {
  background: var(--status-offline-light);
  color: var(--status-offline);
}

.nav-item.theme-toggle {
  color: var(--text-secondary);
  background: transparent;
  border: none;
  width: 100%;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  overflow: hidden;
  white-space: nowrap;
  font-size: 0.875rem;
  font-weight: 500;
}

.nav-menu-collapsed .nav-item.theme-toggle {
  justify-content: center;
  padding: 0.75rem 0.5rem;
}

.nav-item.theme-toggle:hover {
  background: var(--menu-item-hover);
  color: var(--text-primary);
}

.nav-item.theme-toggle .nav-icon {
  font-size: 1.125rem;
  min-width: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-item.theme-toggle .nav-label {
  margin-left: 1rem;
  flex: 1;
}

.nav-menu-collapsed .nav-item.theme-toggle .nav-label {
  display: none;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* Hidden logout form */
#logout-form {
  display: none;
}

/* Responsivo */
@media (max-width: 768px) {
  .nav-menu {
    transform: translateX(-100%);
  }
  
  .nav-menu.mobile-open {
    transform: translateX(0);
  }
}
</style>
