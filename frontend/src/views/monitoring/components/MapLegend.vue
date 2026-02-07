<template>
  <div class="map-legend">
    <div class="legend-item" v-for="status in statusLegend" :key="status.key">
      <span :class="['legend-marker', status.key]"></span>
      <span class="legend-label">{{ status.label }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  statusLegend: {
    type: Array,
    required: true,
    validator: (value) => {
      return value.every(item => 
        item && 
        typeof item.key === 'string' && 
        typeof item.label === 'string'
      )
    }
  }
})
</script>

<style scoped>
.map-legend {
  position: absolute;
  bottom: 24px;
  left: 24px;
  background: rgba(30, 33, 57, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  backdrop-filter: blur(10px);
  z-index: 100;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.legend-item:last-child {
  margin-bottom: 0;
}

.legend-marker {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #fff;
}

.legend-marker.online {
  background: #10b981;
}

.legend-marker.warning {
  background: #f59e0b;
}

.legend-marker.critical {
  background: #ef4444;
}

.legend-marker.offline {
  background: #6b7280;
}

.legend-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
}

/* ==========================================
   LIGHT THEME OVERRIDES
   ========================================== */
:root[data-theme="light"] .map-legend,
html:not(.dark)[data-theme="light"] .map-legend {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .legend-label,
html:not(.dark)[data-theme="light"] .legend-label {
  color: var(--text-secondary);
}
</style>
