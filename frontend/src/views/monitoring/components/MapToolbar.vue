<template>
  <div class="map-toolbar" :class="{ 'map-toolbar--collapsed': collapsed }">

    <!-- Conteúdo — tem overflow:hidden com transição de altura -->
    <div class="toolbar-inner">
      <div class="toolbar-left">
        <button @click="$router.back()" class="btn-back">
          <i class="fas fa-arrow-left"></i>
          Voltar
        </button>
        <div class="map-title">
          <h2>{{ mapName }}</h2>
          <span class="map-category">{{ mapCategory }}</span>
        </div>
      </div>

      <div class="toolbar-right">
        <button @click="$emit('toggle-inventory')" class="btn-toolbar">
          <i class="fas fa-layer-group"></i>
          Gerenciar Itens
        </button>
        <button @click="$emit('toggle-fullscreen')" class="btn-toolbar">
          <i :class="isFullscreen ? 'fas fa-compress' : 'fas fa-expand'"></i>
        </button>
      </div>
    </div>

    <!-- Tab de colapso — fica sempre visível como faixa inferior -->
    <button
      class="toolbar-handle"
      :title="collapsed ? 'Expandir barra' : 'Recolher barra'"
      @click="$emit('toggle-collapse')"
    >
      <svg
        width="13"
        height="13"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        class="handle-icon"
        :class="{ 'handle-icon--collapsed': collapsed }"
      >
        <polyline points="18 15 12 9 6 15"/>
      </svg>
    </button>
  </div>
</template>

<script setup>
defineProps({
  mapName: { type: String, required: true },
  mapCategory: { type: String, default: '' },
  isFullscreen: { type: Boolean, default: false },
  collapsed: { type: Boolean, default: false }
})

defineEmits(['toggle-inventory', 'toggle-fullscreen', 'toggle-collapse'])
</script>

<style scoped>
/* ── Toolbar shell — sempre visível, define o fundo escuro ── */
.map-toolbar {
  position: relative;
  flex-shrink: 0;
  background: rgba(20, 24, 46, 0.97);
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(10px);
  z-index: 1000;
}

/* ── Conteúdo colapsável ── */
.toolbar-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 24px;
  overflow: hidden;
  max-height: 80px;
  opacity: 1;
  transition: max-height 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.2s ease,
              padding 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.map-toolbar--collapsed .toolbar-inner {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}

/* ── Handle (faixa fina sempre visível) ── */
.toolbar-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 18px;
  background: transparent;
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.25);
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.toolbar-handle:hover {
  background: rgba(16, 185, 129, 0.08);
  color: #10b981;
}

.handle-icon {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.handle-icon--collapsed {
  transform: rotate(180deg);
}

/* ── Buttons ── */
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toolbar-right {
  display: flex;
  gap: 12px;
}

.btn-back,
.btn-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.btn-back:hover,
.btn-toolbar:hover {
  background: rgba(16, 185, 129, 0.2);
  border-color: rgba(16, 185, 129, 0.5);
}

.map-title h2 {
  font-size: 17px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  line-height: 1.2;
}

.map-category {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.45);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
</style>
