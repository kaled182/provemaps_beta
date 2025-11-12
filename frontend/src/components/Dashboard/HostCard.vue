<template>
  <article 
    class="host-card" 
    :class="`status-${host.status || 'unknown'}`"
    role="article"
    :aria-label="`Host ${host.name || host.id}, status: ${statusLabel}`"
    tabindex="0"
  >
    <div class="card-header">
      <div class="host-info">
        <h3 class="host-name" id="`host-name-${host.id}`">{{ host.name || `Host #${host.id}` }}</h3>
        <span class="host-id" aria-label="Identificador do host">ID: {{ host.id }}</span>
      </div>
      <div 
        class="status-badge" 
        :class="`status-${host.status || 'unknown'}`"
        role="status"
        :aria-label="`Status atual: ${statusLabel}`"
      >
        {{ statusLabel }}
      </div>
    </div>

    <div class="card-body">
      <!-- Metrics if available -->
      <div v-if="host.metrics" class="host-metrics" role="list" aria-label="Métricas do host">
        <div class="metric" v-if="host.metrics.cpu !== undefined" role="listitem">
          <span class="metric-label">CPU:</span>
          <span class="metric-value" :aria-label="`Uso de CPU: ${host.metrics.cpu} porcento`">{{ host.metrics.cpu }}%</span>
        </div>
        <div class="metric" v-if="host.metrics.memory !== undefined" role="listitem">
          <span class="metric-label">Memória:</span>
          <span class="metric-value" :aria-label="`Uso de memória: ${host.metrics.memory} porcento`">{{ host.metrics.memory }}%</span>
        </div>
        <div class="metric" v-if="host.metrics.uptime !== undefined" role="listitem">
          <span class="metric-label">Uptime:</span>
          <span class="metric-value" :aria-label="`Tempo de atividade: ${formatUptime(host.metrics.uptime)}`">{{ formatUptime(host.metrics.uptime) }}</span>
        </div>
      </div>

      <!-- Last update timestamp -->
      <div class="last-update" v-if="host.last_update">
        <span class="update-label">Última atualização:</span>
        <time class="update-time" :datetime="host.last_update" :aria-label="`Última atualização: ${formatTimestamp(host.last_update)}`">
          {{ formatTimestamp(host.last_update) }}
        </time>
      </div>
    </div>

    <!-- Pulse animation for real-time updates -->
    <div v-if="isRecentlyUpdated" class="update-pulse" aria-hidden="true"></div>
  </article>
</template>

<script setup>
import { computed, ref, watch } from 'vue';

const props = defineProps({
  host: {
    type: Object,
    required: true,
  },
});

const isRecentlyUpdated = ref(false);

const statusLabel = computed(() => {
  const statusMap = {
    online: 'Online',
    offline: 'Offline',
    warning: 'Alerta',
    maintenance: 'Manutenção',
    unknown: 'Desconhecido',
  };
  return statusMap[props.host.status] || 'Desconhecido';
});

function formatTimestamp(timestamp) {
  if (!timestamp) return '-';
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  
  if (diffSec < 60) return `${diffSec}s atrás`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m atrás`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h atrás`;
  return date.toLocaleString('pt-BR');
}

function formatUptime(seconds) {
  if (!seconds) return '-';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  if (days > 0) return `${days}d ${hours}h`;
  return `${hours}h`;
}

// Flash update indicator when host updates
watch(() => props.host.last_update, () => {
  isRecentlyUpdated.value = true;
  setTimeout(() => {
    isRecentlyUpdated.value = false;
  }, 2000);
});
</script>

<style scoped>
.host-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  position: relative;
  overflow: hidden;
  transition: all 0.2s ease;
}

.host-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.host-card.status-online {
  border-left: 4px solid #10b981;
}

.host-card.status-offline {
  border-left: 4px solid #ef4444;
}

.host-card.status-warning {
  border-left: 4px solid #f59e0b;
}

.host-card.status-maintenance {
  border-left: 4px solid #3b82f6;
}

.host-card.status-unknown {
  border-left: 4px solid #6b7280;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.host-info {
  flex: 1;
}

.host-name {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.host-id {
  font-size: 11px;
  color: #6b7280;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.status-online {
  background: #d1fae5;
  color: #065f46;
}

.status-badge.status-offline {
  background: #fee2e2;
  color: #991b1b;
}

.status-badge.status-warning {
  background: #fef3c7;
  color: #92400e;
}

.status-badge.status-maintenance {
  background: #dbeafe;
  color: #1e40af;
}

.status-badge.status-unknown {
  background: #f3f4f6;
  color: #374151;
}

.card-body {
  font-size: 12px;
}

.host-metrics {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.metric {
  display: flex;
  gap: 4px;
}

.metric-label {
  color: #6b7280;
}

.metric-value {
  font-weight: 600;
  color: #111827;
}

.last-update {
  display: flex;
  gap: 4px;
  color: #9ca3af;
  font-size: 11px;
}

.update-label {
  color: #9ca3af;
}

.update-time {
  color: #6b7280;
}

.update-pulse {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #3b82f6;
  animation: pulse-slide 2s ease-out;
}

@keyframes pulse-slide {
  0% {
    transform: translateX(-100%);
    opacity: 1;
  }
  100% {
    transform: translateX(100%);
    opacity: 0;
  }
}

/* Accessibility: Focus styles */
.host-card:focus {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}

.host-card:focus:not(:focus-visible) {
  outline: none;
}
</style>
