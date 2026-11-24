<template>
  <article
    class="swc"
    :class="[`swc-${sw.status}`, { 'swc-on': selected }]"
    role="button"
    tabindex="0"
    :aria-pressed="selected"
    data-testid="sw-card"
    @click="$emit('select', sw.device_id)"
    @keydown.enter.prevent="$emit('select', sw.device_id)"
  >
    <header class="swc-head">
      <span class="swc-dot" aria-hidden="true" />
      <div class="min-w-0 flex-1">
        <h3 class="swc-name" :title="sw.name">{{ sw.name }}</h3>
        <p class="swc-meta">
          <span>{{ sw.model || 'modelo —' }}</span>
          <span v-if="sw.site_name"> · {{ sw.site_name }}</span>
        </p>
      </div>
      <span class="swc-badge" data-testid="sw-card-status">{{ STATUS[sw.status] }}</span>
    </header>

    <!-- Mini-régua das portas: uma marca por porta, cor do estado -->
    <div class="swc-strip" aria-hidden="true">
      <span v-for="p in ports" :key="p.name" class="swc-tick" :class="`tick-${p.state}`" :title="`${p.name} · ${STATE_LABELS[p.state]}`" />
    </div>

    <dl class="swc-nums">
      <div><dt>Em uso</dt><dd>{{ sw.ports_in_use }}<small>/{{ sw.ports_total }}</small></dd></div>
      <div><dt>Down</dt><dd :class="{ 'text-danger': sw.ports_down }">{{ sw.ports_down }}</dd></div>
      <div><dt>Pior RX</dt><dd :class="rxClass">{{ sw.worst_rx_dbm === null ? '—' : sw.worst_rx_dbm.toFixed(2) }}</dd></div>
      <div><dt>CPU</dt><dd>{{ sw.cpu_pct === null ? '—' : `${sw.cpu_pct}%` }}</dd></div>
      <div><dt>Temp.</dt><dd>{{ sw.temperature_c === null ? '—' : `${sw.temperature_c} °C` }}</dd></div>
    </dl>
    <p v-if="!sw.collection_ok" class="swc-warn" data-testid="sw-card-nodata">Sem dados do Zabbix para as portas deste switch.</p>
  </article>
</template>

<script setup>
/** Cartão de switch da «grade compacta» (EV-0115): estado, régua de portas e números. */
import { computed } from 'vue'
import { STATE_LABELS } from '@/composables/useSwitchesOverview'

const props = defineProps({
  sw: { type: Object, required: true },
  ports: { type: Array, default: () => [] },
  thresholds: { type: Object, default: null },
  selected: { type: Boolean, default: false },
})
defineEmits(['select'])

const STATUS = { online: 'Online', offline: 'Offline', unknown: 'Sem dados' }

const rxClass = computed(() => {
  const rx = props.sw.worst_rx_dbm
  const t = props.thresholds
  if (rx === null || rx === undefined || !t) return ''
  if (rx < t.critical) return 'text-danger'
  if (rx <= t.warning) return 'text-warning'
  return 'text-success'
})
</script>

<style scoped>
.swc {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  background: rgb(var(--surface));
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.swc:hover,
.swc:focus-visible {
  border-color: rgb(var(--primary-500));
  outline: none;
}
.swc-on {
  border-color: rgb(var(--primary-500));
  box-shadow: 0 0 0 1px rgb(var(--primary-500));
}
.swc-offline {
  border-color: rgb(var(--danger) / 0.45);
}
.swc-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.swc-dot {
  margin-top: 5px;
  width: 8px;
  height: 8px;
  flex-shrink: 0;
  border-radius: 999px;
  background: rgb(var(--n-400));
}
.swc-online .swc-dot { background: rgb(var(--success)); }
.swc-offline .swc-dot { background: rgb(var(--danger)); }
.swc-name {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: rgb(var(--n-900));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.swc-meta {
  margin: 0;
  font-size: 11px;
  color: rgb(var(--n-500));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.swc-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 999px;
  background: rgb(var(--n-100));
  color: rgb(var(--n-600));
}
.swc-online .swc-badge { background: rgb(var(--success) / 0.14); color: rgb(var(--success)); }
.swc-offline .swc-badge { background: rgb(var(--danger) / 0.14); color: rgb(var(--danger)); }
.swc-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}
.swc-tick {
  width: 7px;
  height: 10px;
  border-radius: 2px;
  background: rgb(var(--n-200));
}
.tick-normal { background: rgb(var(--success)); }
.tick-warning { background: rgb(var(--warning)); }
.tick-critical,
.tick-down { background: rgb(var(--danger)); }
.tick-unknown { background: rgb(var(--n-300)); }
.swc-nums {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 4px;
  margin: 0;
}
.swc-nums dt {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgb(var(--n-500));
}
.swc-nums dd {
  margin: 0;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
  font-weight: 600;
  color: rgb(var(--n-900));
}
.swc-nums small {
  font-size: 11px;
  font-weight: 400;
  color: rgb(var(--n-500));
}
.swc-warn {
  margin: 0;
  font-size: 11px;
  color: rgb(var(--warning));
}
</style>
