<template>
  <div class="map-legend-wrap">
    <!-- Pill trigger -->
    <div class="legend-pill" @mouseenter="open = true" @mouseleave="open = false">
      <span
        v-for="status in statusLegend"
        :key="status.key"
        class="pill-dot"
        :class="status.key"
      ></span>
      <span class="pill-label">Legenda</span>
    </div>

    <!-- Tooltip popup -->
    <Transition name="legend-fade">
      <div
        v-if="open"
        class="legend-tooltip"
        @mouseenter="open = true"
        @mouseleave="open = false"
      >
        <div class="legend-item" v-for="status in statusLegend" :key="status.key">
          <span class="legend-marker" :class="status.key"></span>
          <span class="legend-label">{{ status.label }}</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  statusLegend: {
    type: Array,
    required: true
  }
})

const open = ref(false)
</script>

<style scoped>
.map-legend-wrap {
  position: absolute;
  bottom: 24px;
  right: 16px;
  z-index: 900;
}

/* ── Pill ── */
.legend-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  background: rgba(15, 23, 42, 0.82);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  cursor: default;
  user-select: none;
}

.pill-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.pill-label {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.45);
  margin-left: 2px;
}

/* ── Tooltip ── */
.legend-tooltip {
  position: absolute;
  bottom: calc(100% + 8px);
  right: 0;
  background: rgba(15, 23, 42, 0.92);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 10px 14px;
  min-width: 130px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
}

.legend-marker {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-marker.online   { background: #10b981; }
.legend-marker.warning  { background: #f59e0b; }
.legend-marker.critical { background: #ef4444; }
.legend-marker.offline  { background: #6b7280; }

.pill-dot.online   { background: #10b981; }
.pill-dot.warning  { background: #f59e0b; }
.pill-dot.critical { background: #ef4444; }
.pill-dot.offline  { background: #6b7280; }

.legend-label {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.75);
}

/* Transition */
.legend-fade-enter-active,
.legend-fade-leave-active { transition: opacity 0.15s, transform 0.15s; }
.legend-fade-enter-from,
.legend-fade-leave-to { opacity: 0; transform: translateY(4px); }

/* Light theme */
:root[data-theme="light"] .legend-pill,
:root[data-theme="light"] .legend-tooltip {
  background: rgba(255, 255, 255, 0.95);
  border-color: rgba(0, 0, 0, 0.1);
}
:root[data-theme="light"] .pill-label,
:root[data-theme="light"] .legend-label {
  color: var(--text-secondary);
}
</style>
