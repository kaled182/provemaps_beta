<template>
  <article
    class="host-card"
    :class="[`status-${host.status || 'unknown'}`]"
    role="article"
    :aria-label="`Host ${host.name || host.id}, status: ${statusLabel}`"
    tabindex="0"
    @click="focusMapOnHost"
  >
    <div class="card-header">
      <div class="host-info">
        <h3 class="host-name" :id="`host-name-${host.id}`">{{ host.name || `Host #${host.id}` }}</h3>
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
      <div v-if="host.metrics" class="host-metrics" role="list" aria-label="Métricas do host">
        <div v-if="host.metrics.cpu !== undefined" class="metric" role="listitem">
          <span class="metric-label">CPU:</span>
          <span class="metric-value" :aria-label="`Uso de CPU: ${host.metrics.cpu} porcento`">{{ host.metrics.cpu }}%</span>
        </div>
        <div v-if="host.metrics.memory !== undefined" class="metric" role="listitem">
          <span class="metric-label">Memória:</span>
          <span class="metric-value" :aria-label="`Uso de memória: ${host.metrics.memory} porcento`">{{ host.metrics.memory }}%</span>
        </div>
        <div v-if="host.metrics.uptime !== undefined" class="metric" role="listitem">
          <span class="metric-label">Uptime:</span>
          <span class="metric-value" :aria-label="`Tempo de atividade: ${formatUptime(host.metrics.uptime)}`">{{ formatUptime(host.metrics.uptime) }}</span>
        </div>
      </div>

      <div v-if="host.last_update" class="last-update">
        <span class="update-label">Última atualização:</span>
        <time
          class="update-time"
          :datetime="host.last_update"
          :aria-label="`Última atualização: ${formatTimestamp(host.last_update)}`"
        >
          {{ formatTimestamp(host.last_update) }}
        </time>
      </div>
    </div>

    <div v-if="isRecentlyUpdated" class="update-pulse" aria-hidden="true"></div>
  </article>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useMapStore } from '@/stores/map';

const props = defineProps({
  host: {
    type: Object,
    required: true,
  },
});

const mapStore = useMapStore();
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

function focusMapOnHost() {
  const siteOfHost = findSiteByHostId(props.host.id);
  if (siteOfHost) {
    mapStore.focusOnItem(siteOfHost);
  } else {
    console.warn(`[HostCard] Não foi possível encontrar site para host ${props.host.id}`);
  }
}

function findSiteByHostId(hostId) {
  if (mapStore.sites && mapStore.sites.length > 0) {
    const site = mapStore.sites.find((siteItem) =>
      siteItem.devices?.some((device) => device.hostid === hostId) || siteItem.id === props.host.site_id,
    );
    if (site) {
      return site;
    }
  }

  if (props.host.latitude && props.host.longitude) {
    return {
      id: props.host.site_id || props.host.id,
      name: props.host.site_name || props.host.name,
      latitude: props.host.latitude,
      longitude: props.host.longitude,
    };
  }

  return null;
}

function formatTimestamp(timestamp) {
  if (!timestamp) {
    return '-';
  }
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
  if (!seconds) {
    return '-';
  }
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  if (days > 0) {
    return `${days}d ${hours}h`;
  }
  return `${hours}h`;
}

watch(
  () => props.host.last_update,
  () => {
    isRecentlyUpdated.value = true;
    setTimeout(() => {
      isRecentlyUpdated.value = false;
    }, 2000);
  },
);
</script>

<style scoped>
.host-card {
  background: var(--surface-card);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  position: relative;
  overflow: hidden;
  transition: all 0.2s ease;
  cursor: pointer;
}

.host-card:hover {
  box-shadow: var(--shadow-sm);
}

.host-card.status-online {
  border-left: 4px solid var(--status-online);
}

.host-card.status-offline {
  border-left: 4px solid var(--status-offline);
}

.host-card.status-warning {
  border-left: 4px solid var(--status-warning);
}

.host-card.status-maintenance {
  border-left: 4px solid var(--accent-info);
}

.host-card.status-unknown {
  border-left: 4px solid var(--text-tertiary);
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
  color: var(--text-primary);
}

.host-id {
  font-size: 11px;
  color: var(--text-tertiary);
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.status-online {
  background: var(--status-online-light);
  color: var(--status-online);
}

.status-badge.status-offline {
  background: var(--status-offline-light);
  color: var(--status-offline);
}

.status-badge.status-warning {
  background: var(--warning-soft-bg);
  color: var(--warning-soft-text);
}

.status-badge.status-maintenance {
  background: var(--info-soft-bg);
  color: var(--accent-info);
}

.status-badge.status-unknown {
  background: var(--badge-neutral-bg);
  color: var(--badge-neutral-text);
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
  color: var(--text-tertiary);
}

.metric-value {
  font-weight: 600;
  color: var(--text-primary);
}

.last-update {
  display: flex;
  gap: 4px;
  font-size: 11px;
  color: var(--text-tertiary);
}

.update-label {
  color: var(--text-tertiary);
}

.update-time {
  color: var(--text-secondary);
}

.update-pulse {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--accent-info);
  animation: pulse-slide 2s ease-out;
}

@keyframes pulse-slide {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.host-card:focus {
  outline: 2px solid var(--accent-info);
  outline-offset: 2px;
}

.host-card:focus:not(:focus-visible) {
  outline: none;
}
</style>
