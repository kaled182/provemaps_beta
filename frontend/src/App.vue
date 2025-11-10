<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
// Base application component
// Fase 7 migration: Dashboard.vue (1,137 lines) and RouteBuilder.vue (1,039 lines) will replace legacy JS
</script>

<style>
/* Import legacy CSS for gradual migration */
@import url('/static/css/base.css');

#app {
  width: 100%;
  height: 100vh;
}
</style>
