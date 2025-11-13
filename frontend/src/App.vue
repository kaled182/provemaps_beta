<template>
  <div class="flex flex-col h-screen">
    <TheNavbar />
    
    <main class="flex-1 overflow-hidden">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router';
import TheNavbar from '@/components/Layout/TheNavbar.vue';
// Base application component
// Phase 11 Sprint 2: Full dashboard with real-time WebSocket integration
// DashboardView (sidebar + map) replaces legacy dashboard.js (1,137 lines)
</script>

<style>
/* Import temporary base styles while migrating legacy assets */
@import './assets/base.css';

/* Garanta que o app ocupe a tela inteira */
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
  background-color: #1f2937; /* gray-800 */
}

* {
  box-sizing: border-box;
}
</style>
