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
      <div class="host-stats">
        <div v-if="host.ip || host.primary_ip" class="stat-item">
          <span class="stat-icon">📍</span>
          <span class="stat-value">{{ host.ip || host.primary_ip }}</span>
        </div>
        <div v-if="host.uptime_value || host.metrics?.uptime" class="stat-item">
          <span class="stat-icon">⏱️</span>
          <span class="stat-value">{{ host.uptime_value || formatUptime(host.metrics.uptime) }}</span>
        </div>
        <div v-if="host.cpu_value || host.metrics?.cpu !== undefined" class="stat-item">
          <span class="stat-icon">💻</span>
          <span class="stat-value">{{ host.cpu_value || `${host.metrics.cpu}%` }}</span>
        </div>
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

// Debug: log host data
console.log('[HostCard] Host data:', props.host);

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

async function focusMapOnHost() {
  console.log('[HostCard] Clique no card, host:', props.host);
  
  // Tentar encontrar o dispositivo nas APIs
  try {
    // Primeiro, buscar o device completo com site
    const deviceResponse = await fetch('/api/v1/devices/', { credentials: 'include' });
    if (!deviceResponse.ok) {
      console.error('[HostCard] Erro ao buscar devices');
      return;
    }
    
    const devicesData = await deviceResponse.json();
    const devices = devicesData.results || devicesData;
    
    // Encontrar o device correspondente ao host
    const device = devices.find(d => 
      d.id === props.host.id || 
      d.zabbix_hostid === props.host.host_id ||
      d.name === props.host.name
    );
    
    if (!device) {
      console.warn('[HostCard] Device não encontrado para host:', props.host);
      return;
    }
    
    console.log('[HostCard] Device encontrado:', device);
    
    // Buscar o site para obter as coordenadas
    const siteResponse = await fetch(`/api/v1/sites/${device.site}/`, { credentials: 'include' });
    if (!siteResponse.ok) {
      console.error('[HostCard] Erro ao buscar site');
      return;
    }
    
    const site = await siteResponse.json();
    console.log('[HostCard] Site encontrado:', site);
    
    if (!site.latitude || !site.longitude) {
      console.warn('[HostCard] Site sem coordenadas:', site);
      return;
    }
    
    // Criar objeto para focar com flag de abrir modal
    const deviceToFocus = {
      id: device.id,
      hostid: device.zabbix_hostid,
      name: device.name,
      latitude: site.latitude,
      longitude: site.longitude,
      site_id: site.id,
      site_name: site.name || site.display_name,
      openModal: true,
    };
    
    console.log('[HostCard] Focando no dispositivo:', deviceToFocus);
    mapStore.focusOnItem(deviceToFocus);
    
  } catch (error) {
    console.error('[HostCard] Erro ao focar no host:', error);
  }
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
  background: var(--surface-highlight);
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
  background: var(--menu-item-hover);
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

.host-stats {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.stat-icon {
  font-size: 13px;
  flex-shrink: 0;
}

.stat-value {
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
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
