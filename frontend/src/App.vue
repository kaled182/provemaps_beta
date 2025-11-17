<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Menu Lateral Esquerdo -->
    <TheNavMenu />
    
    <!-- Área de Conteúdo Principal (Dashboard com sidebar + mapa) -->
    <main class="flex-1 relative overflow-hidden min-w-0">
      <router-view />
    </main>

    <SiteDeviceModal />
  </div>
</template>

<script setup>
import { RouterView, useRouter } from 'vue-router';
import { onMounted, nextTick } from 'vue';
import TheNavMenu from '@/components/Layout/TheNavMenu.vue';
import SiteDeviceModal from '@/components/Map/SiteDeviceModal.vue';
import { useUiStore } from '@/stores/ui';
import { loadGoogleMaps } from '@/utils/googleMapsLoader';

const uiStore = useUiStore();
const router = useRouter();

// Rotas que REALMENTE precisam do Google Maps
const ROUTES_WITH_MAPS = [
  '/monitoring/backbone',
  '/Network/NetworkDesign',
  '/NetworkDesign', // Legacy support
  '/dashboard'
];

// Verifica se a rota precisa de mapas
function routeNeedsMaps(path) {
  return ROUTES_WITH_MAPS.some(route => path.startsWith(route));
}

// Aplicar tema ao montar
onMounted(() => {
  console.log('[App] Mounting application...');
  uiStore.applyTheme();
  console.log('[App] Google Maps will be loaded on-demand for specific routes');
});

// Intercepta navegação e carrega Google Maps apenas quando necessário
router.beforeEach(async (to, from, next) => {
  const needsMaps = routeNeedsMaps(to.path);
  
  console.log(`[App] Navigation: ${from.path} → ${to.path}`);
  console.log(`[App] Route needs maps: ${needsMaps}`);
  
  if (needsMaps) {
    console.log('[App] Loading Google Maps for this route...');
    
    // IMPORTANTE: Aguarda o próximo tick para garantir que a meta tag foi renderizada
    await nextTick();
    
    try {
      await loadGoogleMaps();
      console.log('[App] ✅ Google Maps loaded successfully');
    } catch (err) {
      console.error('[App] ❌ Failed to load Google Maps:', err.message);
      // Continua navegação mesmo com erro - componente tentará novamente
    }
  } else {
    console.log('[App] Skipping Google Maps load (not needed for this route)');
  }
  
  next();
});
</script>

<style>
/* Import theme variables */
@import './assets/theme.css';

/* Import temporary base styles while migrating legacy assets */
@import './assets/base.css';

/* Garante que o app ocupe a tela inteira */
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
  background-color: var(--bg-primary);
  overflow: hidden;
  color: var(--text-primary);
  transition: background-color 0.3s ease, color 0.3s ease;
}

* {
  box-sizing: border-box;
}

.app-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.3s ease;
  overflow: hidden;
}

.main-content {
  flex: 1;
  overflow: hidden;
}
</style>
