<template>
  <div class="status-chart">
    <h3 class="chart-title">Status dos Hosts</h3>
    
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
  background: #fff;
  padding: 16px;
  border-radius: 8px;
}

.chart-title {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
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
  background: #f3f4f6;
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
  background: linear-gradient(90deg, #10b981, #059669);
}

.bar-fill.status-offline {
  background: linear-gradient(90deg, #ef4444, #dc2626);
}

.bar-fill.status-warning {
  background: linear-gradient(90deg, #f59e0b, #d97706);
}

.bar-fill.status-unknown {
  background: linear-gradient(90deg, #9ca3af, #6b7280);
}

.bar-value {
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.bar-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
}

.status-icon {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-icon.status-online {
  background: #10b981;
}

.status-icon.status-offline {
  background: #ef4444;
}

.status-icon.status-warning {
  background: #f59e0b;
}

.status-icon.status-unknown {
  background: #6b7280;
}

.status-name {
  font-weight: 500;
}

.chart-summary {
  display: flex;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.summary-item {
  display: flex;
  gap: 6px;
  font-size: 13px;
}

.summary-label {
  color: #6b7280;
}

.summary-value {
  font-weight: 600;
  color: #111827;
}

.summary-value.health-good {
  color: #10b981;
}

.summary-value.health-warning {
  color: #f59e0b;
}

.summary-value.health-critical {
  color: #ef4444;
}
</style>
