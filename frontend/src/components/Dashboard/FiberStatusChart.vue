<template>
  <div class="fiber-status-chart">
    <div class="chart-header">
      <h3 class="chart-title">Status dos Enlaces</h3>
      <div class="chart-actions">
        <button 
          @click="$emit('toggle-sidebar')"
          class="control-btn"
          title="Colapsar sidebar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
        <button 
          @click="$emit('toggle-position')"
          class="control-btn"
          title="Trocar lado"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12M8 12h12m-12 5h12M3 7h.01M3 12h.01M3 17h.01" />
          </svg>
        </button>
      </div>
    </div>
    
    <!-- Simple bar chart visualization -->
    <div class="chart-container">
      <div class="chart-bars">
        <div 
          v-for="(value, status) in distribution" 
          :key="status"
          class="chart-bar-item"
        >
          <div class="bar-wrapper">
            <div 
              class="bar-fill" 
              :class="`status-${status}`"
              :style="{ width: getBarWidth(value) }"
            >
              <span v-if="value > 0" class="bar-value">{{ value }}</span>
            </div>
          </div>
          <div class="bar-label">
            <span class="status-icon" :class="`status-${status}`"></span>
            <span class="status-name">{{ getStatusLabel(status) }}</span>
          </div>
        </div>
      </div>

      <!-- Total summary -->
      <div class="chart-summary">
        <div class="summary-item">
          <span class="summary-label">Total:</span>
          <span class="summary-value">{{ total }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  distribution: {
    type: Object,
    required: true,
    default: () => ({ up: 0, down: 0, degraded: 0, unknown: 0 }),
  },
});

const total = computed(() => {
  return Object.values(props.distribution).reduce((sum, val) => sum + val, 0);
});

const maxValue = computed(() => {
  return Math.max(...Object.values(props.distribution), 1);
});

function getBarWidth(value) {
  if (total.value === 0) return '0%';
  return `${(value / maxValue.value) * 100}%`;
}

function getStatusLabel(status) {
  const labels = {
    up: 'Operacional',
    down: 'Fora',
    degraded: 'Degradado',
    unknown: 'Desconhecido',
  };
  return labels[status] || status;
}
</script>

<style scoped>
.fiber-status-chart {
  background: transparent;
  padding: 16px;
  border-radius: 8px;
  border-bottom: 1px solid var(--border-primary);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.chart-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.chart-actions {
  display: flex;
  gap: 6px;
}

.control-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: var(--surface-highlight);
  border: 1px solid var(--border-primary);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.control-btn:hover {
  background: var(--menu-item-hover);
  border-color: var(--border-secondary);
  transform: translateY(-1px);
}

.control-btn svg {
  width: 16px;
  height: 16px;
  color: var(--text-tertiary);
}

.control-btn:hover svg {
  color: var(--text-primary);
}

.chart-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chart-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chart-bar-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.bar-wrapper {
  height: 24px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}

.bar-fill {
  height: 100%;
  min-width: 2px;
  transition: width 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 8px;
  border-radius: 3px;
}

.bar-value {
  font-size: 11px;
  font-weight: 600;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.bar-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.status-icon {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

/* Status-based colors for fiber cables */
.status-up .status-icon,
.bar-fill.status-up {
  background: #10b981;
}

.status-down .status-icon,
.bar-fill.status-down {
  background: #ef4444;
}

.status-degraded .status-icon,
.bar-fill.status-degraded {
  background: #f59e0b;
}

.status-unknown .status-icon,
.bar-fill.status-unknown {
  background: #6b7280;
}

.chart-summary {
  display: flex;
  gap: 16px;
  padding-top: 8px;
  border-top: 1px solid var(--border-primary);
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.summary-label {
  color: var(--text-tertiary);
  font-weight: 500;
}

.summary-value {
  color: var(--text-primary);
  font-weight: 600;
}
</style>
