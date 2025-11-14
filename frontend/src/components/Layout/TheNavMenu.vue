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
        <span class="nav-icon">
          <component :is="item.icon" :size="22" weight="regular" />
        </span>
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
        <span class="nav-icon">
          <component :is="connectionStatus.icon" :size="22" weight="regular" />
        </span>
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
          <PhGear :size="22" weight="regular" />
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
          <PhFaders :size="22" weight="regular" />
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
          <PhSun v-if="uiStore.theme === 'dark'" :size="22" weight="regular" />
          <PhMoon v-else :size="22" weight="regular" />
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
            <PhSignOut :size="22" weight="regular" />
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
import { 
  PhHouse, 
  PhChartBar, 
  PhGitBranch, 
  PhBook, 
  PhPlusCircle,
  PhLightning,
  PhClock,
  PhWifiSlash,
  PhGear,
  PhFaders,
  PhSun,
  PhMoon,
  PhSignOut
} from '@phosphor-icons/vue';

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
      icon: PhLightning
    };
  } else if (wsConnecting.value) {
    return { 
      color: 'bg-yellow-500', 
      text: 'Conectando',
      icon: PhClock
    };
  } else {
    return { 
      color: 'bg-red-500', 
      text: 'Desconectado',
      icon: PhWifiSlash
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
    icon: PhHouse
  },
  {
    label: 'Metrics',
    path: '/maps_view/metrics/',
    icon: PhChartBar
  },
  {
    label: 'Routes',
    path: '/routes/fiber-route-builder/',
    icon: PhGitBranch
  },
  {
    label: 'Docs',
    path: '/docs/',
    icon: PhBook
  },
  {
    label: 'Add Device',
    path: '/zabbix/lookup/',
    icon: PhPlusCircle,
    badge: '+'
  }
];

function isActive(path) {
  return window.location.pathname.startsWith(path);
}
</script>

<style scoped>
.nav-menu {
  flex-shrink: 0;
  width: 280px;
  background: linear-gradient(195deg, var(--menu-bg-start) 0%, var(--menu-bg-end) 100%);
  box-shadow: var(--shadow-accent);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease, background 0.3s ease;
  z-index: 100;
  overflow: hidden;
  height: 100vh;
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
