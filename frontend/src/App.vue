<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
// Base application component
// Phase 11 Sprint 2: Full dashboard with real-time WebSocket integration
// DashboardView (sidebar + map) replaces legacy dashboard.js (1,137 lines)
</script>

<style>
/* Import temporary base styles while migrating legacy assets */
@import './assets/base.css';

#app {
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

* {
  box-sizing: border-box;
}
</style>
