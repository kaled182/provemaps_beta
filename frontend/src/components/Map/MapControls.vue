<template>
  <div>
    <!-- Controles do Mapa (canto superior direito) -->
    <div class="map-controls" role="toolbar" aria-label="Controles do mapa">
      <button 
        class="control-button" 
        @click="$emit('fitBounds')"
        @keydown.enter="$emit('fitBounds')"
        title="Ajustar visualização para todos os segmentos"
        aria-label="Ajustar visualização"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path d="M3 4a1 1 0 011-1h3a1 1 0 011 1v3a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 13a1 1 0 011-1h3a1 1 0 011 1v3a1 1 0 01-1 1H4a1 1 0 01-1-1v-3zM13 4a1 1 0 011-1h3a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1V4zM13 13a1 1 0 011-1h3a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-3z"/>
        </svg>
      </button>

      <button 
        class="control-button" 
        @click="$emit('toggleLegend')"
        @keydown.enter="$emit('toggleLegend')"
        title="Mostrar ou ocultar legenda de status"
        aria-label="Alternar legenda"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd"/>
        </svg>
      </button>

      <button 
        class="control-button" 
        @click="toggleFullscreen"
        @keydown.enter="toggleFullscreen"
        :title="isFullscreen ? 'Sair da tela cheia' : 'Entrar em tela cheia'"
        :aria-label="isFullscreen ? 'Sair da tela cheia' : 'Entrar em tela cheia'"
      >
        <svg v-if="!isFullscreen" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h4a1 1 0 010 2H6.414l2.293 2.293a1 1 0 11-1.414 1.414L5 6.414V8a1 1 0 01-2 0V4zm9 1a1 1 0 010-2h4a1 1 0 011 1v4a1 1 0 01-2 0V6.414l-2.293 2.293a1 1 0 11-1.414-1.414L13.586 5H12zm-9 7a1 1 0 012 0v1.586l2.293-2.293a1 1 0 111.414 1.414L6.414 15H8a1 1 0 010 2H4a1 1 0 01-1-1v-4zm13-1a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 010-2h1.586l-2.293-2.293a1 1 0 111.414-1.414L15 13.586V12a1 1 0 011-1z" clip-rule="evenodd"/>
        </svg>
        <svg v-else width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M5 4a1 1 0 00-1 1v2a1 1 0 002 0V6h1a1 1 0 000-2H5zm10 0a1 1 0 011 1v2a1 1 0 01-2 0V6h-1a1 1 0 010-2h2zM4 11a1 1 0 011-1h1a1 1 0 010 2H6v1a1 1 0 01-2 0v-2zm12-1a1 1 0 00-1 1v2a1 1 0 002 0v-1h1a1 1 0 000-2h-2z" clip-rule="evenodd"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useUiStore } from '@/stores/ui';

const uiStore = useUiStore();

defineEmits(['fitBounds', 'toggleLegend']);

const isFullscreen = ref(false);

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen();
    isFullscreen.value = true;
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen();
      isFullscreen.value = false;
    }
  }
}

// Listen for fullscreen changes
document.addEventListener('fullscreenchange', () => {
  isFullscreen.value = !!document.fullscreenElement;
});
</script>

<style scoped>
.map-controls {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 1000;
}

.control-button {
  width: 40px;
  height: 40px;
  background: var(--surface-card);
  border: 1px solid var(--border-secondary);
  border-radius: 4px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.control-button:hover {
  background: var(--surface-muted);
  box-shadow: var(--shadow-md);
  color: var(--text-primary);
}

.control-button:active {
  transform: scale(0.95);
}

.control-button:focus {
  outline: 2px solid var(--accent-info);
  outline-offset: 2px;
}

.control-button:focus:not(:focus-visible) {
  outline: none;
}
</style>
