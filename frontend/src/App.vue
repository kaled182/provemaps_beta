<template>
  <div class="app-container">
    <TheNavMenu />
    <div class="app-content" :style="{ marginLeft: uiStore.navMenuWidth }">
      <main class="main-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router';
import { onMounted } from 'vue';
import TheNavMenu from '@/components/Layout/TheNavMenu.vue';
import { useUiStore } from '@/stores/ui';

const uiStore = useUiStore();

// Aplicar tema ao montar
onMounted(() => {
  uiStore.applyTheme();
});

// Base application component
// Phase 11 Sprint 2: Full dashboard with real-time WebSocket integration
// DashboardView (sidebar + map) replaces legacy dashboard.js (1,137 lines)
</script>

<style>
/* Import theme variables */
@import './assets/theme.css';

/* Import temporary base styles while migrating legacy assets */
@import './assets/base.css';

/* Garanta que o app ocupe a tela inteira */
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
