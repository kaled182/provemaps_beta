import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

/**
 * UI Store - Gerencia estado da interface (painéis, modais, etc)
 * Persiste preferências no localStorage
 */
const STORAGE_KEYS = {
  theme: 'ui.theme',
  navMenuOpen: 'ui.navMenuOpen',
  sidebarOpen: 'ui.sidebarOpen',
  headerOpen: 'ui.headerOpen',
  sidebarPosition: 'ui.sidebarPosition',
  legendOpen: 'ui.legendOpen',
  legendCollapsed: 'ui.legendCollapsed',
};

function getBool(key, fallback = true) {
  const stored = localStorage.getItem(key);
  if (stored === null) return fallback;
  return stored === 'true';
}

export const useUiStore = defineStore('ui', () => {
  // Estado do tema (dark/light)
  const theme = ref(
    localStorage.getItem(STORAGE_KEYS.theme) || 'dark'
  );
  
  // Estado do menu lateral de navegação (esquerda)
  const isNavMenuOpen = ref(getBool(STORAGE_KEYS.navMenuOpen, true));
  
  // Estado do sidebar (painel lateral "Status dos Hosts" - direita)
  const isSidebarOpen = ref(getBool(STORAGE_KEYS.sidebarOpen, true));
  
  // Estado do header superior
  const isHeaderOpen = ref(getBool(STORAGE_KEYS.headerOpen, true));
  
  const sidebarPosition = ref(
    localStorage.getItem(STORAGE_KEYS.sidebarPosition) || 'right'
  );
  
  // Estado da legenda do mapa
  const isLegendOpen = ref(getBool(STORAGE_KEYS.legendOpen, false));
  
  const isLegendCollapsed = ref(getBool(STORAGE_KEYS.legendCollapsed, false));
  
  // Actions - Theme
  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark';
    localStorage.setItem(STORAGE_KEYS.theme, theme.value);
    applyTheme();
  }
  
  function setTheme(newTheme) {
    if (newTheme === 'dark' || newTheme === 'light') {
      theme.value = newTheme;
      localStorage.setItem(STORAGE_KEYS.theme, newTheme);
      applyTheme();
    }
  }
  
  function applyTheme() {
    document.documentElement.setAttribute('data-theme', theme.value);
    
    // Adicionar/remover classe 'dark' para Tailwind CSS
    if (theme.value === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    
    console.log('[UI Store] Theme applied:', theme.value);
  }
  
  // Aplicar tema imediatamente ao carregar a store
  applyTheme();
  
  // Actions - Nav Menu
  function toggleNavMenu() {
    isNavMenuOpen.value = !isNavMenuOpen.value;
    localStorage.setItem(STORAGE_KEYS.navMenuOpen, isNavMenuOpen.value);
  }
  
  function setNavMenuOpen(value) {
    isNavMenuOpen.value = value;
    localStorage.setItem(STORAGE_KEYS.navMenuOpen, value);
  }
  
  // Actions - Sidebar
  function toggleSidebar() {
    isSidebarOpen.value = !isSidebarOpen.value;
    localStorage.setItem(STORAGE_KEYS.sidebarOpen, isSidebarOpen.value);
  }
  
  function setSidebarOpen(value) {
    isSidebarOpen.value = value;
    localStorage.setItem(STORAGE_KEYS.sidebarOpen, value);
  }
  
  function toggleSidebarPosition() {
    sidebarPosition.value = sidebarPosition.value === 'left' ? 'right' : 'left';
    localStorage.setItem(STORAGE_KEYS.sidebarPosition, sidebarPosition.value);
  }
  
  function setSidebarPosition(position) {
    if (position === 'left' || position === 'right') {
      sidebarPosition.value = position;
      localStorage.setItem(STORAGE_KEYS.sidebarPosition, position);
    }
  }
  
  // Actions - Header
  function toggleHeader() {
    isHeaderOpen.value = !isHeaderOpen.value;
    localStorage.setItem(STORAGE_KEYS.headerOpen, isHeaderOpen.value);
  }
  
  function setHeaderOpen(value) {
    isHeaderOpen.value = value;
    localStorage.setItem(STORAGE_KEYS.headerOpen, value);
  }
  
  // Actions - Legend
  function toggleLegend() {
    isLegendOpen.value = !isLegendOpen.value;
    localStorage.setItem(STORAGE_KEYS.legendOpen, isLegendOpen.value);
  }
  
  function toggleLegendCollapse() {
    isLegendCollapsed.value = !isLegendCollapsed.value;
    localStorage.setItem(STORAGE_KEYS.legendCollapsed, isLegendCollapsed.value);
  }
  
  // Computed properties
  const navMenuWidth = computed(() => isNavMenuOpen.value ? 280 : 60);
  const sidebarWidth = computed(() => isSidebarOpen.value ? 350 : 15);
  const headerHeight = computed(() => isHeaderOpen.value ? 60 : 0);
  
  return {
    // State
    theme,
    isNavMenuOpen,
    isSidebarOpen,
    isHeaderOpen,
    sidebarPosition,
    isLegendOpen,
    isLegendCollapsed,
    
    // Actions - Theme
    toggleTheme,
    setTheme,
    applyTheme,
    
    // Actions - Nav Menu
    toggleNavMenu,
    setNavMenuOpen,
    
    // Actions - Sidebar
    toggleSidebar,
    setSidebarOpen,
    toggleSidebarPosition,
    setSidebarPosition,
    
    // Actions - Header
    toggleHeader,
    setHeaderOpen,
    
    // Actions - Legend
    toggleLegend,
    toggleLegendCollapse,
    
    // Computed
    navMenuWidth,
    sidebarWidth,
    headerHeight,
  };
});
