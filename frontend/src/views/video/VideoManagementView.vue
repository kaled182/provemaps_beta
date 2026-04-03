<template>
  <div class="h-full flex flex-col app-page app-page-muted">
    <header class="app-surface shadow-sm border-b app-divider py-3 px-4 md:px-6 z-10">
      <div class="flex flex-col gap-3">
        <div class="flex items-start gap-3 justify-between">
          <div class="leading-tight">
            <h1 class="text-xl font-bold app-text-primary">Monitoramento Visual</h1>
            <p class="text-xs app-text-tertiary mt-0.5">
              Câmeras e mosaicos de vídeo
            </p>
          </div>
        </div>

        <div class="app-surface rounded-xl p-2 flex items-center gap-2 justify-between">
          <div class="flex items-center gap-2 flex-wrap">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              @click="activeTab = tab.id"
              :class="[
                'px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors app-tab',
                activeTab === tab.id ? 'is-active' : ''
              ]"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>
      </div>
    </header>

    <main class="flex-1 overflow-auto px-4 md:px-6 py-3 flex flex-col gap-3">
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
