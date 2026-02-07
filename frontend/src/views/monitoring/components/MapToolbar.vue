<template>
  <div class="map-toolbar">
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
</template>

<script setup>
defineProps({
  mapName: {
    type: String,
    required: true
  },
  mapCategory: {
    type: String,
    default: ''
  },
  isFullscreen: {
    type: Boolean,
    default: false
  }
})

defineEmits(['toggle-inventory', 'toggle-fullscreen'])
</script>

<style scoped>
.map-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: rgba(30, 33, 57, 0.95);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  z-index: 1000;
}

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
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  font-weight: 500;
}

.btn-back:hover,
.btn-toolbar:hover {
  background: rgba(16, 185, 129, 0.2);
  border-color: rgba(16, 185, 129, 0.5);
  transform: translateY(-1px);
}

.map-title h2 {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  margin: 0;
}

.map-category {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
</style>
