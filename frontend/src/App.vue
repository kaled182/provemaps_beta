<template>
  <div class="flex h-screen flex-col overflow-hidden">
    <!-- Shell: cabeçalho de duas linhas, sem menu lateral (ADR 0007 Fase 2) -->
    <AppHeader />

    <!-- Conteúdo: as páginas posicionam-se aqui (relative), abaixo do cabeçalho -->
    <main class="relative min-h-0 min-w-0 flex-1 overflow-y-auto">
      <router-view />
    </main>

    <SiteDeviceModal />
    
    <!-- Toast Notifications -->
    <ToastContainer />
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router';
import { onMounted } from 'vue';
import AppHeader from '@/components/Layout/AppHeader.vue';
import SiteDeviceModal from '@/components/Map/SiteDeviceModal.vue';
import ToastContainer from '@/components/Notifications/ToastContainer.vue';
import { useUiStore } from '@/stores/ui';

const uiStore = useUiStore();

// Aplicar tema ao montar. Os SDKs de mapa são carregados pelo provider
// configurado (providers/maps) quando um ecrã cria o mapa — não há
// pré-carregamento do Google por rota (EV-0012c).
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

/* Altura do AppHeader (48 + 40): para o pouco que ainda se posiciona contra a janela */
:root {
  --app-header-height: 88px;
}
</style>
