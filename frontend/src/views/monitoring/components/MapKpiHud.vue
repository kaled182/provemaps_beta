<template>
  <div class="kpi-hud" data-testid="map-kpi-hud">
    <!-- 1. Sites / POPs — filtra os sites em baixo -->
    <button
      type="button"
      class="kpi-card"
      :class="{ 'kpi-card--active': filter === KPI_FILTERS.SITES_OFFLINE }"
      :disabled="!kpis.sites.total"
      :aria-pressed="filter === KPI_FILTERS.SITES_OFFLINE"
      title="Mostrar só os sites offline (clique de novo para mostrar todos)"
      data-testid="kpi-sites"
      @click="toggle(KPI_FILTERS.SITES_OFFLINE)"
    >
      <span class="kpi-label">Sites / POPs</span>
      <span class="kpi-value">
        <span class="text-success">{{ kpis.sites.online }}</span><span class="kpi-unit"> online</span>
        <span class="kpi-sep">·</span>
        <span :class="kpis.sites.offline ? 'text-danger' : 'text-neutral-500'">{{ kpis.sites.offline }}</span><span class="kpi-unit"> offline</span>
        <template v-if="kpis.sites.unknown">
          <span class="kpi-sep">·</span>
          <span class="text-neutral-500">{{ kpis.sites.unknown }}</span><span class="kpi-unit"> s/ estado</span>
        </template>
      </span>
    </button>

    <!-- 2. Enlaces ópticos — filtra críticos + atenção -->
    <button
      type="button"
      class="kpi-card"
      :class="{ 'kpi-card--active': filter === KPI_FILTERS.LINKS_PROBLEM }"
      :disabled="!kpis.links.total"
      :aria-pressed="filter === KPI_FILTERS.LINKS_PROBLEM"
      title="Mostrar só os enlaces críticos ou em atenção (clique de novo para mostrar todos)"
      data-testid="kpi-links"
      @click="toggle(KPI_FILTERS.LINKS_PROBLEM)"
    >
      <span class="kpi-label">Enlaces ópticos</span>
      <span class="kpi-value">
        <span class="text-success">{{ kpis.links.healthy }}</span><span class="kpi-unit">/{{ kpis.links.total }} ok</span>
        <span class="kpi-sep">·</span>
        <span :class="kpis.links.critical ? 'text-danger' : 'text-neutral-500'">{{ kpis.links.critical }}</span><span class="kpi-unit"> crít.</span>
        <span class="kpi-sep">·</span>
        <span :class="kpis.links.attention ? 'text-warning' : 'text-neutral-500'">{{ kpis.links.attention }}</span><span class="kpi-unit"> aten.</span>
      </span>
    </button>

    <!-- 3. Pior RX da rede (EV-0049): leitura fresca mais baixa; sem leitura → «sem dados» -->
    <div
      class="kpi-card kpi-card--static"
      :title="worstTitle"
      data-testid="kpi-attenuation"
    >
      <span class="kpi-label">Pior sinal RX</span>
      <span v-if="optical?.error" class="kpi-value"><span class="kpi-unit text-danger">erro ao ler</span></span>
      <span v-else-if="optical?.worst" class="kpi-value">
        <span :class="worstClass">{{ Number(optical.worst.rx).toFixed(2) }}</span><span class="kpi-unit"> dBm · {{ optical.worst.cable_name }}</span>
      </span>
      <span v-else class="kpi-value text-neutral-500"><span class="kpi-unit">sem dados</span></span>
    </div>

    <!-- 4. Telemetria / coleta -->
    <div class="kpi-card kpi-card--static" :title="telemetryView.title" data-testid="kpi-telemetry">
      <span class="kpi-label">Telemetria</span>
      <span class="kpi-value">
        <span class="kpi-dot" :class="telemetryView.dot"></span>
        <span class="kpi-unit text-neutral-800">{{ telemetryView.label }}</span>
        <template v-if="ago">
          <span class="kpi-sep">·</span>
          <span class="text-neutral-600">{{ ago }}</span>
        </template>
      </span>
    </div>
  </div>
</template>

<script setup>
/**
 * HUD de KPIs no topo do mapa (EV-0048). Substitui a pílula
 * «N online · M offline · Xs atrás» do canto inferior.
 */
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import { KPI_FILTERS, formatAgo } from '@/utils/mapKpis';

const props = defineProps({
  kpis: { type: Object, required: true },
  filter: { type: String, default: null },
  /** 'live' (WebSocket), 'degraded' (polling REST), 'connecting', 'offline' */
  telemetry: { type: String, default: 'connecting' },
  lastUpdate: { type: Date, default: null },
  /** { worst: {rx, cable_name, side} | null, critical: number|null, error: string } (EV-0049) */
  optical: { type: Object, default: null },
});
const emit = defineEmits(['update:filter']);

function toggle(key) {
  emit('update:filter', props.filter === key ? null : key);
}

const TELEMETRY = {
  live: { label: 'Tempo real', dot: 'bg-success', title: 'Estado chega pelo WebSocket' },
  degraded: { label: 'Polling 60 s', dot: 'bg-warning', title: 'WebSocket indisponível; estado lido por REST a cada 60 s' },
  connecting: { label: 'Conectando', dot: 'bg-warning', title: 'A ligar ao canal em tempo real' },
  offline: { label: 'Sem coleta', dot: 'bg-danger', title: 'Sem canal em tempo real; o estado pode estar desatualizado' },
};
const telemetryView = computed(() => TELEMETRY[props.telemetry] || TELEMETRY.connecting);

// Relógio próprio: «há X s» tem de andar mesmo sem mensagens novas.
const now = ref(Date.now());
let clock = null;
onMounted(() => {
  clock = setInterval(() => {
    now.value = Date.now();
  }, 5000);
});
onBeforeUnmount(() => clearInterval(clock));

const ago = computed(() => formatAgo(props.lastUpdate, now.value));

const worstClass = computed(() => {
  const w = props.optical?.worst;
  const critical = props.optical?.critical;
  if (!w || critical === null || critical === undefined) return '';
  return w.rx <= critical ? 'text-danger' : '';
});
const worstTitle = computed(() => {
  if (props.optical?.error) return `Erro ao ler os níveis ópticos: ${props.optical.error}`;
  const w = props.optical?.worst;
  if (!w) return 'Sem leituras ópticas recentes';
  const side = w.side === 'origin' ? 'ponta A' : 'ponta B';
  return `Menor RX entre leituras recentes: ${w.cable_name} (${side}). Ver todos em Rede › Enlaces & fibra.`;
});
</script>

<style scoped>
.kpi-hud {
  position: absolute;
  top: 12px;
  left: 12px;
  /* deixa livre o controlo de zoom/navegação do provider à direita */
  right: 64px;
  z-index: 900;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  pointer-events: none;
}
.kpi-card {
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid rgb(var(--n-200));
  background: rgb(var(--surface) / 0.9);
  backdrop-filter: blur(12px);
  box-shadow: 0 4px 12px rgb(0 0 0 / 0.12);
  text-align: left;
  color: rgb(var(--n-900));
  transition: border-color 0.15s ease;
}
button.kpi-card:not(:disabled) {
  cursor: pointer;
}
button.kpi-card:not(:disabled):hover {
  border-color: rgb(var(--n-400));
}
.kpi-card:disabled {
  opacity: 0.6;
}
.kpi-card--active {
  border-color: rgb(var(--primary-500));
  box-shadow: 0 0 0 1px rgb(var(--primary-500)), 0 4px 12px rgb(0 0 0 / 0.12);
}
.kpi-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: rgb(var(--n-500));
}
.kpi-value {
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
  font-weight: 600;
}
.kpi-unit {
  font-family: Inter, system-ui, sans-serif;
  font-size: 11px;
  font-weight: 500;
  color: rgb(var(--n-600));
}
.kpi-sep {
  color: rgb(var(--n-400));
}
.kpi-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
@media (max-width: 640px) {
  .kpi-hud {
    right: 56px;
  }
  .kpi-card {
    padding: 4px 8px;
  }
  .kpi-card--static[data-testid='kpi-attenuation'] {
    display: none;
  }
}
</style>
