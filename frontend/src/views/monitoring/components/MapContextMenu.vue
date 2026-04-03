<template>
  <Transition name="ctx-pop">
    <div
      v-if="visible"
      class="map-ctx"
      :style="{ left: safeX + 'px', top: safeY + 'px' }"
      @click.stop
    >
      <!-- Cabeçalho com nome do mapa -->
      <div class="ctx-header">
        <span class="ctx-map-name">{{ mapName }}</span>
        <span class="ctx-map-cat">{{ mapCategory }}</span>
      </div>

      <div class="ctx-divider"/>

      <!-- Ações principais -->
      <button class="ctx-item" @click="emit('action', 'inventory')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
          <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
        </svg>
        Gerenciar Itens
      </button>

      <button
        class="ctx-item"
        :class="{ 'ctx-item--active': maintenanceActive }"
        @click="emit('action', 'maintenance')"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="3 11 22 2 13 21 11 13 3 11"/>
        </svg>
        {{ maintenanceActive ? 'Sair da Manutenção' : 'Área de Manutenção' }}
        <span v-if="maintenanceActive" class="ctx-active-dot"/>
      </button>

      <div class="ctx-divider"/>

      <button class="ctx-item" @click="emit('action', 'fullscreen')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline v-if="!isFullscreen" points="15 3 21 3 21 9"/><polyline v-if="!isFullscreen" points="9 21 3 21 3 15"/>
          <line v-if="!isFullscreen" x1="21" y1="3" x2="14" y2="10"/><line v-if="!isFullscreen" x1="3" y1="21" x2="10" y2="14"/>
          <polyline v-if="isFullscreen" points="4 14 4 20 10 20"/><polyline v-if="isFullscreen" points="20 10 20 4 14 4"/>
          <line v-if="isFullscreen" x1="14" y1="10" x2="21" y2="3"/><line v-if="isFullscreen" x1="3" y1="21" x2="10" y2="14"/>
        </svg>
        {{ isFullscreen ? 'Sair da Tela Cheia' : 'Tela Cheia' }}
      </button>

      <button class="ctx-item ctx-item--back" @click="emit('action', 'back')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="19" y1="12" x2="5" y2="12"/>
          <polyline points="12 19 5 12 12 5"/>
        </svg>
        Voltar
      </button>
    </div>
  </Transition>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  x: { type: Number, default: 0 },
  y: { type: Number, default: 0 },
  mapName: { type: String, default: '' },
  mapCategory: { type: String, default: '' },
  maintenanceActive: { type: Boolean, default: false },
  isFullscreen: { type: Boolean, default: false }
})

const emit = defineEmits(['action', 'close'])

// Evita que o menu vaze fora da tela
const safeX = computed(() => {
  const menuW = 210
  return props.x + menuW > window.innerWidth ? props.x - menuW : props.x
})

const safeY = computed(() => {
  const menuH = 220
  return props.y + menuH > window.innerHeight ? props.y - menuH : props.y
})
</script>

<style>
/* Não usar scoped — o menu é position:fixed e precisa de CSS global */
.map-ctx {
  position: fixed;
  z-index: 9000;
  min-width: 210px;
  background: rgba(13, 17, 35, 0.96);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 6px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255,255,255,0.04) inset;
  user-select: none;
}

.ctx-header {
  padding: 8px 10px 6px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.ctx-map-name {
  font-size: 0.82rem;
  font-weight: 700;
  color: #f1f5f9;
  line-height: 1.2;
}

.ctx-map-cat {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: rgba(255,255,255,0.35);
}

.ctx-divider {
  height: 1px;
  background: rgba(255,255,255,0.07);
  margin: 4px 0;
}

.ctx-item {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 8px 10px;
  background: transparent;
  border: none;
  border-radius: 7px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 0.82rem;
  font-weight: 450;
  cursor: pointer;
  text-align: left;
  transition: background 0.12s, color 0.12s;
  position: relative;
}

.ctx-item:hover {
  background: rgba(255,255,255,0.07);
  color: #fff;
}

.ctx-item svg {
  flex-shrink: 0;
  opacity: 0.7;
}

.ctx-item:hover svg {
  opacity: 1;
}

.ctx-item--active {
  color: #fbbf24;
}

.ctx-item--active svg {
  opacity: 1;
  stroke: #fbbf24;
}

.ctx-item--active:hover {
  background: rgba(245, 158, 11, 0.1);
  color: #fde68a;
}

.ctx-active-dot {
  margin-left: auto;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #f59e0b;
  flex-shrink: 0;
}

.ctx-item--back {
  color: rgba(255,255,255,0.45);
}

.ctx-item--back:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #fca5a5;
}

/* Transition */
.ctx-pop-enter-active {
  transition: opacity 0.1s ease, transform 0.12s cubic-bezier(0.2, 0, 0, 1.4);
}
.ctx-pop-leave-active {
  transition: opacity 0.08s ease, transform 0.08s ease;
}
.ctx-pop-enter-from {
  opacity: 0;
  transform: scale(0.92) translateY(-4px);
}
.ctx-pop-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
