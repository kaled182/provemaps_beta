<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Menu Lateral Esquerdo -->
    <TheNavMenu />
    
    <!-- Área de Conteúdo Principal (Dashboard com sidebar + mapa) -->
    <main class="flex-1 relative overflow-hidden">
      <router-view />
    </main>

    <SiteDeviceModal />
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router';
import { onMounted } from 'vue';
import TheNavMenu from '@/components/Layout/TheNavMenu.vue';
import SiteDeviceModal from '@/components/Map/SiteDeviceModal.vue';
import { useUiStore } from '@/stores/ui';

const uiStore = useUiStore();

// Aplicar tema ao montar
onMounted(() => {
  uiStore.applyTheme();
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
