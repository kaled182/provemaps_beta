<template>
  <aside 
    class="nav-menu"
    :class="{ 'nav-menu-collapsed': !uiStore.isNavMenuOpen }"
    :style="navMenuStyle"
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
          <div
            v-for="item in menuItems"
            :key="item.label"
            class="nav-group"
            :class="{ 'has-children': item.children?.length, 'group-active': isItemActive(item), 'expanded': isGroupExpanded(item.label) }"
          >
            <!-- Item COM submenu - apenas toggle, não navega -->
            <button
              v-if="item.children?.length"
              @click="toggleGroup(item.label)"
              class="nav-item nav-item-toggle"
              :class="{ 'active': isItemActive(item) }"
              :title="!uiStore.isNavMenuOpen ? item.label : ''"
            >
              <span class="nav-icon">
                <component :is="item.icon" :size="22" weight="regular" />
              </span>
              <transition name="fade">
                <span v-if="uiStore.isNavMenuOpen" class="nav-label">{{ item.label }}</span>
              </transition>
              <transition name="fade">
                <span v-if="uiStore.isNavMenuOpen" class="nav-chevron">
                  <PhCaretDown v-if="isGroupExpanded(item.label)" :size="16" weight="bold" />
                  <PhCaretRight v-else :size="16" weight="bold" />
                </span>
              </transition>
            </button>
            
            <!-- Item SEM submenu - comportamento normal -->
            <RouterLink
              v-else-if="item.useRouter"
              :to="item.path"
              class="nav-item"
              :class="{ 'active': isItemActive(item) }"
              :title="!uiStore.isNavMenuOpen ? item.label : ''"
            >
              <span class="nav-icon">
                <component :is="item.icon" :size="22" weight="regular" />
              </span>
              <transition name="fade">
                <span v-if="uiStore.isNavMenuOpen" class="nav-label">{{ item.label }}</span>
              </transition>
              <span v-if="item.badge && uiStore.isNavMenuOpen" class="nav-badge">{{ item.badge }}</span>
            </RouterLink>
            <a
              v-else
              :href="item.path"
              class="nav-item"
              :class="{ 'active': isItemActive(item) }"
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

            <!-- Submenu - só aparece se expandido E menu aberto -->
            <transition name="slide-fade">
              <div
                v-if="item.children?.length && uiStore.isNavMenuOpen && isGroupExpanded(item.label)"
                class="nav-children"
              >
                <RouterLink
                  v-for="child in item.children"
                  :key="child.path"
                  :to="child.path"
                  class="nav-item nav-item-child"
                  :class="{ 'active': isPathActive(child.path) }"
                  :title="child.label"
                >
                  <span class="nav-icon child-icon">
                    <component :is="child.icon" :size="18" weight="regular" />
                  </span>
                  <span class="nav-label">{{ child.label }}</span>
                </RouterLink>
              </div>
            </transition>
          </div>
        </nav>

    <!-- Footer -->
    <div class="nav-menu-footer">
      <div class="divider"></div>
      
      <!-- System com submenu -->
      <div class="nav-group footer-group" :class="{ 'has-children': true, 'expanded': isGroupExpanded('System') }">
        <button
          @click="toggleGroup('System')"
          class="nav-item nav-item-toggle"
          :class="{ 'active': isPathActive('/setup/config') || isPathActive('/metrics/health') || isPathActive('/admin/') || isPathActive('/docs') }"
          :title="!uiStore.isNavMenuOpen ? 'System' : ''"
        >
          <span class="nav-icon">
            <PhGear :size="22" weight="regular" />
          </span>
          <transition name="fade">
            <span v-if="uiStore.isNavMenuOpen" class="nav-label">System</span>
          </transition>
          <transition name="fade">
            <span v-if="uiStore.isNavMenuOpen" class="nav-chevron">
              <PhCaretDown v-if="isGroupExpanded('System')" :size="16" weight="bold" />
              <PhCaretRight v-else :size="16" weight="bold" />
            </span>
          </transition>
        </button>

        <transition name="slide-fade">
          <div
            v-if="uiStore.isNavMenuOpen && isGroupExpanded('System')"
            class="nav-children"
          >
            <RouterLink
              to="/profile"
              class="nav-item nav-item-child"
              :class="{ 'active': isPathActive('/profile') }"
              title="Meu Perfil"
            >
              <span class="nav-icon child-icon">
                <PhUser :size="18" weight="regular" />
              </span>
              <span class="nav-label">Meu Perfil</span>
            </RouterLink>
            <RouterLink
              to="/meu-cadastro"
              class="nav-item nav-item-child"
              :class="{ 'active': isPathActive('/meu-cadastro') }"
              title="Meu Cadastro"
            >
              <span class="nav-icon child-icon">
                <PhUser :size="18" weight="regular" />
              </span>
              <span class="nav-label">Meu Cadastro</span>
            </RouterLink>
            <RouterLink
              to="/system/users"
              class="nav-item nav-item-child"
              :class="{ 'active': isPathActive('/system/users') }"
              title="Users"
            >
              <span class="nav-icon child-icon">
                <PhUsers :size="18" weight="regular" />
              </span>
              <span class="nav-label">Users</span>
            </RouterLink>
            <RouterLink
              to="/setup/config"
              class="nav-item nav-item-child"
              :class="{ 'active': isPathActive('/setup/config') }"
              title="Setup"
            >
              <span class="nav-icon child-icon">
                <PhGear :size="18" weight="regular" />
              </span>
              <span class="nav-label">Setup</span>
            </RouterLink>
            <RouterLink
              to="/metrics/health"
              class="nav-item nav-item-child"
              :class="{ 'active': isPathActive('/metrics/health') }"
              title="Metrics"
            >
              <span class="nav-icon child-icon">
                <PhChartBar :size="18" weight="regular" />
              </span>
              <span class="nav-label">Metrics</span>
            </RouterLink>
            <a
              href="/admin/"
              class="nav-item nav-item-child"
              :class="{ 'active': isPathActive('/admin/') }"
              title="Admin"
            >
              <span class="nav-icon child-icon">
                <PhFaders :size="18" weight="regular" />
              </span>
              <span class="nav-label">Admin</span>
            </a>
            <RouterLink
              to="/docs"
              class="nav-item nav-item-child"
              :class="{ 'active': isPathActive('/docs') }"
              title="Docs"
            >
              <span class="nav-icon child-icon">
                <PhBook :size="18" weight="regular" />
              </span>
              <span class="nav-label">Docs</span>
            </RouterLink>
          </div>
        </transition>
      </div>
      
      <!-- Linha compacta: status + sistema + changelog + tema + sair -->
      <div class="footer-icon-row">
        <span
          class="icon-btn status-icon-btn"
          :data-status="connectionStatus.status"
          :title="connectionStatus.text"
        >
          <component :is="connectionStatus.icon" :size="20" weight="regular" />
        </span>

        <button
          @click="showSystemPanel = true"
          class="icon-btn"
          title="Sistema & Servidores"
        >
          <PhHardDrives :size="20" weight="regular" />
        </button>

        <button
          @click="showChangelog = true"
          class="icon-btn"
          title="Changelog & Sugestões"
        >
          <PhInfo :size="20" weight="regular" />
        </button>

        <button
          @click="uiStore.toggleTheme()"
          class="icon-btn theme-icon-btn"
          :title="uiStore.theme === 'dark' ? 'Modo Claro' : 'Modo Escuro'"
        >
          <PhSun v-if="uiStore.theme === 'dark'" :size="20" weight="regular" />
          <PhMoon v-else :size="20" weight="regular" />
        </button>

        <form action="/accounts/logout/" method="post" style="display:contents">
          <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken">
          <button type="submit" class="icon-btn logout-icon-btn" title="Sair">
            <PhSignOut :size="20" weight="regular" />
          </button>
        </form>
      </div>

      <ChangelogModal :show="showChangelog" @close="showChangelog = false" />
      <SystemPanel :show="showSystemPanel" @close="showSystemPanel = false" />
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, onBeforeMount, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useUiStore } from '@/stores/ui';
import ChangelogModal from './ChangelogModal.vue';
import SystemPanel from './SystemPanel.vue';
import {
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
  PhSignOut,
  PhShareNetwork,
  PhPulse,
  PhListBullets,
  PhTreeStructure,
  PhWaveform,
  PhVideoCamera,
  PhCaretDown,
  PhCaretRight,
  PhUsers,
  PhUsersThree,
  PhUser,
  PhSquaresFour,
  PhInfo,
  PhHardDrives,
} from '@phosphor-icons/vue';

const showChangelog = ref(false);
const showSystemPanel = ref(false);

const uiStore = useUiStore();
const route = useRoute();
const csrfToken = ref(window.CSRF_TOKEN || '');
const wsConnected = ref(false);
const wsConnecting = ref(false);
let ws = null;
const realtimePaths = ['/dashboard', '/monitoring'];

// Estado de expansão dos grupos com submenu
const expandedGroups = ref(new Set());

// Função para alternar expansão de um grupo
function toggleGroup(itemLabel) {
  if (expandedGroups.value.has(itemLabel)) {
    expandedGroups.value.delete(itemLabel);
  } else {
    expandedGroups.value.add(itemLabel);
  }
  // Force reactivity
  expandedGroups.value = new Set(expandedGroups.value);
}

// Verifica se um grupo está expandido
function isGroupExpanded(itemLabel) {
  return expandedGroups.value.has(itemLabel);
}

// Ref local para garantir estabilidade do CSS variable
const menuWidth = ref('280px');

const navMenuStyle = computed(() => ({
  '--nav-menu-width': menuWidth.value,
  width: menuWidth.value,
  minWidth: menuWidth.value,
  maxWidth: menuWidth.value,
  flexBasis: menuWidth.value,
  flexGrow: '0',
  flexShrink: '0',
}));

function applyWidth(widthPx) {
  menuWidth.value = widthPx;
  if (typeof document !== 'undefined') {
    document.documentElement.style.setProperty('--nav-menu-width', widthPx);
  }
}

// Garantir que o store está inicializado antes do mount
onBeforeMount(() => {
  // Força a leitura do localStorage ANTES do primeiro render
  const storedValue = localStorage.getItem('ui.navMenuOpen');
  const shouldBeOpen = storedValue === null ? true : storedValue === 'true';
  
  // Se o store não está sincronizado, força a sincronização
  if (uiStore.isNavMenuOpen !== shouldBeOpen) {
    console.warn('[NavMenu] Store dessincronizado, corrigindo:', {
      stored: storedValue,
      storeValue: uiStore.isNavMenuOpen,
      correcting: shouldBeOpen
    });
    // Força o estado correto sem trigger de save (evita loop)
    uiStore.isNavMenuOpen = shouldBeOpen;
  }
  
  // Define largura inicial baseada no estado final
  applyWidth(shouldBeOpen ? '280px' : '60px');
  console.log('[NavMenu] onBeforeMount - menuWidth:', menuWidth.value, 'isOpen:', shouldBeOpen);
});

const connectionStatus = computed(() => {
  if (wsConnected.value) {
    return { 
      status: 'online', 
      text: 'Conectado',
      icon: PhLightning
    };
  } else if (wsConnecting.value) {
    return { 
      status: 'connecting', 
      text: 'Conectando',
      icon: PhClock
    };
  } else {
    return { 
      status: 'offline', 
      text: 'Desconectado',
      icon: PhWifiSlash
    };
  }
});

function shouldUseWebSocket() {
  return true;
}

function closeWebSocket() {
  if (ws) {
    ws.onopen = null;
    ws.onclose = null;
    ws.onerror = null;
    ws.close();
    ws = null;
  }
  wsConnected.value = false;
  wsConnecting.value = false;
}

function connectWebSocket() {
  if (!shouldUseWebSocket() || ws) {
    return;
  }
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
      ws = null;
      
      setTimeout(() => {
        if (!wsConnected.value && shouldUseWebSocket()) {
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
    ws = null;
  }
}

onMounted(() => {
  applyWidth(menuWidth.value);
  // Debug helper to inspect sidebar dimensions and state after navigation / refresh
  window.__navMenuDebug = () => {
    const el = document.querySelector('.nav-menu');
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    return {
      width: rect.width,
      height: rect.height,
      isNavMenuOpen: uiStore.isNavMenuOpen,
      path: window.location.pathname,
    };
  };
  // Log initial state for diagnostics
  console.log('[NavMenu] mounted debug state', window.__navMenuDebug());
});

onUnmounted(() => {
  closeWebSocket();
});

watch(
  () => route.path,
  () => {
    if (shouldUseWebSocket()) {
      connectWebSocket();
    } else {
      closeWebSocket();
    }
  },
  { immediate: true },
);

const menuItems = [
  {
    label: 'Monitoring',
    path: '/monitoring/monitoring-all',
    icon: PhPulse,
    useRouter: true,
    children: [
      {
        label: 'Overview',
        path: '/monitoring/monitoring-all',
        icon: PhListBullets,
      },
      {
        label: 'Backbone',
        path: '/monitoring/backbone',
        icon: PhShareNetwork,
      },
      {
        label: 'GPON',
        path: '/monitoring/gpon',
        icon: PhTreeStructure,
      },
      {
        label: 'DWDM',
        path: '/monitoring/dwdm',
        icon: PhWaveform,
      },
    ],
  },
  {
    label: 'Network',
    path: '/Network/NetworkDesign/',
    icon: PhShareNetwork,
    useRouter: true,
    children: [
      {
        label: 'Device Import',
        path: '/Network/DeviceImport/',
        icon: PhPlusCircle,
      },
      {
        label: 'Network Design',
        path: '/Network/NetworkDesign/',
        icon: PhGitBranch,
      },
      {
        label: 'Network Inventory',
        path: '/network/inventory',
        icon: PhListBullets,
      },
      {
        label: 'Monitoramento Visual',
        path: '/video',
        icon: PhVideoCamera,
      },
    ],
  },
];

function normalizePath(path = '/') {
  if (!path) {
    return '/';
  }

  if (path.length > 1 && path.endsWith('/')) {
    return path.slice(0, -1);
  }

  return path;
}

const currentPath = computed(() => {
  const routePath = route?.path || '';
  if (routePath) {
    return normalizePath(routePath);
  }
  return normalizePath(window.location.pathname);
});

function isPathActive(path) {
  const target = normalizePath(path);
  const current = currentPath.value;

  if (current === target) {
    return true;
  }

  return current.startsWith(`${target}/`);
}

function isItemActive(item) {
  if (!item?.children?.length) {
    return isPathActive(item.path);
  }
  return (
    isPathActive(item.path) ||
    item.children.some(child => isPathActive(child.path))
  );
}

// Watch route path and menu open state to catch unexpected collapses
watch(() => route.path, () => {
  console.log('[NavMenu] route changed', route.path, 'state', window.__navMenuDebug());
  applyWidth(menuWidth.value);
});
watch(() => uiStore.isNavMenuOpen, (newValue) => {
  console.log('[NavMenu] isNavMenuOpen changed ->', newValue);
  applyWidth(newValue ? '280px' : '60px');
  console.log('[NavMenu] menuWidth updated to', menuWidth.value);
});
</script>

<style scoped>
.nav-menu {
  /* CSS Variable binding com fallback robusto */
  flex: none;
  width: var(--nav-menu-width,280px) !important;
  min-width: var(--nav-menu-width,280px) !important;
  max-width: var(--nav-menu-width,280px) !important;

  background: linear-gradient(160deg, var(--menu-bg-start), var(--menu-bg-end));
  background-color: var(--menu-bg) !important;
  box-shadow: var(--shadow-accent);
  border-right: 1px solid var(--menu-border-primary);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease, background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
  z-index: 100;
  overflow: hidden;
  height: 100vh;
  backdrop-filter: blur(12px);
}

.nav-menu-header {
  padding: 1.5rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--menu-border-primary);
  background: var(--menu-item-base);
  backdrop-filter: blur(12px);
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
  color: var(--menu-text-primary);
  font-weight: 600;
  font-size: 0.875rem;
  white-space: nowrap;
}

.toggle-btn {
  background: transparent;
  border: none;
  color: var(--menu-text-tertiary);
  cursor: pointer;
  padding: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
  flex-shrink: 0;
}

.toggle-btn:hover {
  color: var(--menu-text-primary);
}

.toggle-btn svg {
  width: 20px;
  height: 20px;
}

.nav-items {
  flex: 1;
  padding: 1.25rem 0.75rem;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.nav-group {
  margin-bottom: 0.25rem;
}

.nav-group.group-active > .nav-item {
  box-shadow: var(--shadow-accent);
}

.nav-children {
  display: flex;
  flex-direction: column;
  padding-left: 2.75rem;
  gap: 0.125rem;
  margin-top: 0.35rem;
}

.nav-menu-collapsed .nav-children {
  display: none;
}

.nav-items::-webkit-scrollbar {
  width: 4px;
}

.nav-items::-webkit-scrollbar-track {
  background: transparent;
}

.nav-items::-webkit-scrollbar-thumb {
  background: var(--menu-border-primary);
  border-radius: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  margin-bottom: 0.15rem;
  border-radius: 10px;
  color: var(--menu-text-secondary);
  text-decoration: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease, color 0.2s ease, background 0.2s ease, border-color 0.2s ease;
  position: relative;
  overflow: hidden;
  white-space: nowrap;
  background: var(--menu-item-base);
  border: 1px solid var(--menu-border-secondary);
  box-shadow: var(--shadow-sm);
  transform: translateY(0);
  backdrop-filter: blur(8px);
}

/* Bot\u00e3o de toggle para grupos com submenu */
.nav-item-toggle {
  width: 100%;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  font-size: inherit;
}

.nav-chevron {
  margin-left: auto;
  display: flex;
  align-items: center;
  color: inherit;
  transition: transform 0.2s;
}

.nav-item-child {
  padding: 0.6rem 1rem;
  margin-bottom: 0;
  border-radius: 8px;
  background: var(--menu-item-base);
  border: 1px solid var(--menu-border-secondary);
}

.nav-item-child.active {
  background: var(--menu-item-hover);
  color: var(--menu-text-primary);
  border-color: transparent;
}

.nav-menu-collapsed .nav-item {
  justify-content: center;
  padding: 0.75rem 0.5rem;
}

.nav-item:hover {
  background: var(--menu-item-hover);
  color: var(--menu-text-primary);
  border-color: var(--menu-border-primary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.nav-item.router-link-active,
.nav-item.router-link-exact-active,
.nav-item.active {
  background: linear-gradient(160deg, var(--menu-item-active-start) 0%, var(--menu-item-active-end) 100%);
  color: var(--menu-text-primary);
  box-shadow: 0 8px 24px var(--status-online-light);
  border-color: transparent;
  transform: translateY(-1px);
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  margin-right: 0.75rem;
  color: inherit;
}

.child-icon {
  min-width: 18px;
  margin-right: 0.5rem;
}

.nav-menu-collapsed .nav-icon {
  margin-right: 0;
}

.nav-label {
  font-size: 0.875rem;
  font-weight: 500;
}

.nav-badge {
  margin-left: auto;
  background: var(--status-online-light);
  color: var(--status-online);
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.55rem;
  border: 1px solid var(--status-online-light);
}

.nav-item.router-link-active .nav-badge,
.nav-item.router-link-exact-active .nav-badge,
.nav-item.active .nav-badge {
  background: var(--status-online-light);
  color: var(--menu-text-primary);
  border-color: transparent;
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


.nav-menu-footer {
  padding: 1.5rem 0.75rem;
  border-top: 1px solid var(--menu-border-primary);
  background: linear-gradient(160deg, var(--menu-bg-start), var(--menu-bg-end));
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.nav-menu-footer .divider {
  width: 100%;
  height: 1px;
  background: var(--menu-border-primary);
  opacity: 0.6;
  border-radius: 999px;
}

.ws-status {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  margin-bottom: 0.5rem;
  border-radius: 10px;
  background: var(--menu-item-base);
  border: 1px solid var(--menu-border-secondary);
  font-size: 0.8rem;
  overflow: hidden;
  white-space: nowrap;
  transition: background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
  box-shadow: var(--shadow-sm);
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
  color: var(--menu-text-secondary);
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
  color: var(--menu-text-secondary);
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
  color: var(--menu-text-primary);
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
  color: var(--menu-text-secondary);
  width: 100%;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  border-radius: 10px;
  overflow: hidden;
  white-space: nowrap;
  font-size: 0.875rem;
  font-weight: 500;
}

.nav-menu-collapsed .nav-item.theme-toggle {
  justify-content: center;
  padding: 0.75rem 0.5rem;
}

.status-item {
  background: var(--menu-item-base);
  border: 1px solid var(--menu-border-secondary);
  box-shadow: var(--shadow-sm);
}

.status-item[data-status="online"] {
  background: var(--status-online-light);
  border-color: var(--status-online-light);
  color: var(--status-online);
}

.status-item[data-status="connecting"] {
  background: var(--status-warning-light);
  border-color: var(--status-warning-light);
  color: var(--status-warning);
}

.status-item[data-status="offline"] {
  background: var(--status-offline-light);
  border-color: var(--status-offline-light);
  color: var(--status-offline);
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

/* Linha compacta de ícones (tema + sair) */
.footer-icon-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 8px;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background 0.15s;
  color: var(--menu-text-secondary);
  flex-shrink: 0;
}

.icon-btn:hover {
  background: var(--menu-item-hover);
  color: var(--menu-text-primary);
}

.logout-icon-btn {
  color: var(--status-offline);
}

.logout-icon-btn:hover {
  background: var(--status-offline-light);
  color: var(--status-offline);
}

.status-icon-btn {
  cursor: default;
}

.status-icon-btn:hover {
  background: transparent;
}

.status-icon-btn[data-status="online"] {
  color: var(--status-online);
}

.status-icon-btn[data-status="connecting"] {
  color: var(--status-warning);
}

.status-icon-btn[data-status="offline"] {
  color: var(--status-offline);
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

/* Anima\u00e7\u00f5es de submenu */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from {
  transform: translateY(-10px);
  opacity: 0;
  max-height: 0;
}

.slide-fade-enter-to {
  transform: translateY(0);
  opacity: 1;
  max-height: 500px;
}

.slide-fade-leave-from {
  transform: translateY(0);
  opacity: 1;
  max-height: 500px;
}

.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
  max-height: 0;
}

.nav-children {
  overflow: hidden;
  padding-left: 0.5rem;
}
</style>
