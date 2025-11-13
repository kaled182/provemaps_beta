<template>
  <div class="status-chart">
    <div class="chart-header">
      <h3 class="chart-title">Status dos Hosts</h3>
      <div class="chart-actions">
        <button 
          @click="$emit('toggle-sidebar')"
          class="collapse-btn"
          :title="'Colapsar sidebar'"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
        <button 
          @click="$emit('toggle-position')"
          class="swap-btn"
          :title="'Trocar lado'"
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
        <div class="summary-item" v-if="healthPercentage !== null">
          <span class="summary-label">Saúde:</span>
          <span class="summary-value" :class="healthClass">
            {{ healthPercentage }}%
          </span>
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
    default: () => ({ online: 0, offline: 0, warning: 0, unknown: 0 }),
  },
});

const total = computed(() => {
  return Object.values(props.distribution).reduce((sum, val) => sum + val, 0);
});

const maxValue = computed(() => {
  return Math.max(...Object.values(props.distribution), 1);
});

const healthPercentage = computed(() => {
  if (total.value === 0) return null;
  const healthy = props.distribution.online || 0;
  return Math.round((healthy / total.value) * 100);
});

const healthClass = computed(() => {
  const pct = healthPercentage.value;
  if (pct === null) return '';
  if (pct >= 80) return 'health-good';
  if (pct >= 50) return 'health-warning';
  return 'health-critical';
});

function getBarWidth(value) {
  if (total.value === 0) return '0%';
  return `${(value / maxValue.value) * 100}%`;
}

function getStatusLabel(status) {
  const labels = {
    online: 'Online',
    offline: 'Offline',
    warning: 'Alerta',
    unknown: 'Desconhecido',
  };
  return labels[status] || status;
}
</script>

<style scoped>
.status-chart {
  background: var(--bg-secondary);
  padding: 16px;
  border-radius: 8px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.chart-actions {
  display: flex;
  gap: 6px;
}

.collapse-btn,
.swap-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.collapse-btn:hover,
.swap-btn:hover {
  background: var(--menu-item-hover);
  border-color: var(--border-secondary);
  transform: translateY(-1px);
}

.collapse-btn svg,
.swap-btn svg {
  width: 16px;
  height: 16px;
  color: var(--text-tertiary);
}

.collapse-btn:hover svg,
.swap-btn:hover svg {
  color: var(--text-primary);
}

.chart-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chart-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chart-bar-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bar-wrapper {
  height: 32px;
  background: var(--bg-primary);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.bar-fill {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 8px;
  transition: width 0.3s ease;
  min-width: 32px;
}

.bar-fill.status-online {
  background: var(--gradient-online);
}

.bar-fill.status-offline {
  background: var(--gradient-offline);
}

.bar-fill.status-warning {
  background: var(--gradient-warning);
}

.bar-fill.status-unknown {
  background: var(--gradient-unknown);
}

.bar-value {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.bar-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.status-icon {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-icon.status-online {
  background: var(--status-online);
}

.status-icon.status-offline {
  background: var(--status-offline);
}

.status-icon.status-warning {
  background: var(--status-warning);
}

.status-icon.status-unknown {
  background: var(--status-unknown);
}

.status-name {
  font-weight: 500;
}

.chart-summary {
  display: flex;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--border-primary);
}

.summary-item {
  display: flex;
  gap: 6px;
  font-size: 13px;
}

.summary-label {
  color: var(--text-tertiary);
}

.summary-value {
  font-weight: 600;
  color: var(--text-primary);
}

.summary-value.health-good {
  color: var(--status-online);
}

.summary-value.health-warning {
  color: var(--status-warning);
}

.summary-value.health-critical {
  color: var(--status-offline);
}
</style>
