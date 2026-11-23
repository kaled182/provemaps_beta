<template>
  <div class="h-full flex flex-col app-page app-page-muted">
    <!-- Cabeçalho compacto numa linha (EV-0055): título · abas -->
    <header class="app-surface border-b app-divider px-4 md:px-6 py-2 z-10">
      <div class="flex items-center gap-3 flex-wrap">
        <h1 class="text-base font-semibold app-text-primary mr-2">Monitoramento visual</h1>
        <nav class="flex items-center gap-1" aria-label="Secções de vídeo">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'px-2.5 py-1 rounded-md text-sm font-medium transition-colors app-tab',
              activeTab === tab.id ? 'is-active' : ''
            ]"
            :data-testid="`video-tab-${tab.id}`"
          >
            {{ tab.label }}
          </button>
        </nav>
      </div>
    </header>

    <main class="flex-1 overflow-auto px-4 md:px-6 py-2 flex flex-col gap-2">
      <!-- Cameras Tab -->
      <div v-show="activeTab === 'cameras'" class="flex-1">
        <VideoCamerasView :embedded="true" />
      </div>
      
      <!-- Mosaics Tab -->
      <div v-show="activeTab === 'mosaics'" class="flex-1">
        <VideoMosaicsView :embedded="true" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import VideoCamerasView from './VideoCamerasView.vue';
import VideoMosaicsView from './VideoMosaicsView.vue';

const route = useRoute();
const router = useRouter();

const activeTab = ref('cameras');

const tabs = [
  { id: 'cameras', label: 'Câmeras' },
  { id: 'mosaics', label: 'Mosaicos' },
];

// Sincronizar activeTab com query params
watch(() => route.query.tab, (newTab) => {
  if (newTab && ['cameras', 'mosaics'].includes(newTab)) {
    activeTab.value = newTab;
  }
}, { immediate: true });

watch(activeTab, (newTab) => {
  if (route.query.tab !== newTab) {
    router.replace({ query: { ...route.query, tab: newTab } });
  }
});

onMounted(() => {
  const tabFromQuery = route.query.tab;
  if (tabFromQuery && ['cameras', 'mosaics'].includes(tabFromQuery)) {
    activeTab.value = tabFromQuery;
  }
});
</script>

<style scoped>
/* Usa classes app-* globais do tema */
</style>
