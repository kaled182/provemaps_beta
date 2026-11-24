<template>
  <article
    class="sdc"
    :class="`sdc-${device.status}`"
    role="button"
    tabindex="0"
    :title="tooltip"
    data-testid="site-device-card"
    @click="emit('open', device)"
    @keydown.enter.prevent="emit('open', device)"
  >
    <header class="sdc-head">
      <span class="sdc-dot" aria-hidden="true" />
      <div class="sdc-titles">
        <h4 class="sdc-name" :title="device.name">{{ device.name }}</h4>
        <span class="sdc-type" data-testid="site-device-type">{{ indicator?.badge || device.type }}</span>
      </div>
      <span class="sdc-badge" data-testid="site-device-status">{{ statusLabel }}</span>
      <button type="button" class="sdc-edit" title="Configurar dispositivo" @click.stop="emit('edit', device)">
        <PhGear :size="14" />
      </button>
    </header>

    <div class="sdc-metrics">
      <div v-for="m in metrics" :key="m.key" class="sdc-metric">
        <span class="sdc-metric-label">{{ m.label }}</span>
        <div class="sdc-track">
          <div v-if="m.bar" class="sdc-fill" :class="`sdc-fill-${m.bar.level}`" :style="{ width: `${m.bar.pct}%` }" />
        </div>
        <span class="sdc-metric-value" :data-testid="`site-device-${m.key}`">
          {{ m.bar ? m.bar.label : '—' }}<small v-if="m.bar && m.manual" class="sdc-manual">manual</small>
        </span>
      </div>
    </div>

    <!-- EV-0111: indicador por tipo (OLT: ONUs; switch/roteador: portas e pior RX) -->
    <div v-if="indicator" class="sdc-ind" data-testid="site-device-indicator">
      <span class="sdc-ind-main">{{ indicator.main }}</span>
      <span
        v-if="indicator.kind === 'ports' && indicator.worstRx !== null && indicator.worstRx !== undefined"
        class="sdc-ind-rx"
        :class="`sdc-lv-${indicator.worstLevel}`"
        title="Pior RX óptico entre as portas com leitura recente"
        data-testid="site-device-worst-rx"
      >pior RX {{ indicator.worstRx.toFixed(2) }} dBm</span>
      <span
        v-for="a in indicator.alerts"
        :key="a.level"
        class="sdc-ind-alert"
        :class="`sdc-lv-${a.level}`"
        :title="a.level === 'critical' ? 'ONUs com sinal crítico' : 'ONUs com sinal em atenção'"
      >{{ a.text }}</span>
    </div>

    <footer class="sdc-foot">
      <span><span class="sdc-k">uptime</span> {{ uptimeText }}</span>
      <span class="sdc-sep">·</span>
      <span class="sdc-ip"><span class="sdc-k">IP</span> {{ device.ip || '—' }}</span>
      <span class="sdc-go" aria-hidden="true">Inspecionar →</span>
    </footer>
  </article>
</template>

<script setup>
/** Card de equipamento do modal de Site (EV-0065): borda 1 px, barras finas, uptime e IP numa linha. */
import { computed } from 'vue'
import { PhGear } from '@phosphor-icons/vue'
import { metricBar, formatUptimeSeconds, DEVICE_STATUS_LABELS, deviceIndicator } from '@/utils/siteDevices'

const props = defineProps({
  device: { type: Object, required: true },
})
const emit = defineEmits(['open', 'edit'])

const indicator = computed(() => deviceIndicator(props.device))

const statusLabel = computed(() => DEVICE_STATUS_LABELS[props.device.status] || DEVICE_STATUS_LABELS.unknown)

const metrics = computed(() => [
  { key: 'cpu', label: 'CPU', bar: metricBar(props.device.cpu), manual: props.device.cpuSource === 'manual' },
  { key: 'memory', label: 'Mem', bar: metricBar(props.device.memory), manual: props.device.memorySource === 'manual' },
])

const uptimeText = computed(() => props.device.uptimeHuman || formatUptimeSeconds(props.device.uptime) || '—')

const tooltip = computed(() =>
  [
    props.device.name,
    `Estado: ${statusLabel.value}`,
    props.device.zabbixHostId ? `Zabbix host ID: ${props.device.zabbixHostId}` : 'Sem host Zabbix',
  ].join('\n'),
)
</script>

<style scoped>
.sdc {
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
.sdc:hover,
.sdc:focus-visible {
  border-color: rgb(var(--primary-500));
  outline: none;
}
.sdc-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
}
.sdc-dot {
  margin-top: 5px;
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  flex-shrink: 0;
  background: rgb(var(--n-400));
}
.sdc-titles {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}
/* EV-0111: até 2 linhas — «… C600 - 01» e «… C600 - 02» não podem perder o sufixo */
.sdc-name {
  margin: 0;
  font-size: 12px;
  line-height: 1.3;
  font-weight: 600;
  color: rgb(var(--n-900));
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
}
.sdc-type {
  align-self: flex-start;
  max-width: 100%;
  font-size: 10px;
  line-height: 16px;
  padding: 0 6px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 4px;
  color: rgb(var(--n-600));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sdc-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 9999px;
  white-space: nowrap;
  background: rgb(var(--n-100));
  color: rgb(var(--n-600));
}
.sdc-edit {
  display: inline-flex;
  padding: 4px;
  border-radius: 6px;
  color: rgb(var(--n-500));
}
.sdc-edit:hover {
  background: rgb(var(--n-100));
  color: rgb(var(--n-900));
}

/* Estado: só o ponto e o selo levam cor; a borda fica neutra (1 px) */
.sdc-online .sdc-dot { background: rgb(var(--success)); }
.sdc-online .sdc-badge { background: rgb(var(--success) / 0.14); color: rgb(var(--success)); }
.sdc-warning .sdc-dot { background: rgb(var(--warning)); }
.sdc-warning .sdc-badge { background: rgb(var(--warning) / 0.16); color: rgb(var(--warning)); }
.sdc-critical .sdc-dot,
.sdc-offline .sdc-dot { background: rgb(var(--danger)); }
.sdc-critical .sdc-badge,
.sdc-offline .sdc-badge { background: rgb(var(--danger) / 0.14); color: rgb(var(--danger)); }
.sdc-offline { border-color: rgb(var(--danger) / 0.4); }

.sdc-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.sdc-metric {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 6px;
}
.sdc-metric-label,
.sdc-k {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgb(var(--n-500));
}
.sdc-track {
  height: 3px;
  border-radius: 9999px;
  background: rgb(var(--n-200));
  overflow: hidden;
}
.sdc-fill {
  height: 100%;
  border-radius: 9999px;
}
.sdc-fill-normal { background: rgb(var(--success)); }
.sdc-fill-warning { background: rgb(var(--warning)); }
.sdc-fill-critical { background: rgb(var(--danger)); }
.sdc-metric-value,
.sdc-foot {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 11px;
  color: rgb(var(--n-700));
}
.sdc-manual {
  margin-left: 4px;
  font-family: Inter, sans-serif;
  font-size: 9px;
  color: rgb(var(--n-500));
}
.sdc-foot {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  overflow: hidden;
}
.sdc-sep { color: rgb(var(--n-300)); }
.sdc-ip {
  overflow: hidden;
  text-overflow: ellipsis;
}
.sdc-go {
  margin-left: auto;
  font-family: Inter, sans-serif;
  font-size: 11px;
  color: rgb(var(--n-500));
  transition: color 0.15s ease;
}
.sdc:hover .sdc-go,
.sdc:focus-visible .sdc-go {
  color: rgb(var(--primary-600));
}
.sdc-ind {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 11px;
}
.sdc-ind-main {
  color: rgb(var(--n-800));
  font-weight: 600;
}
.sdc-ind-rx,
.sdc-ind-alert {
  padding: 0 6px;
  border-radius: 4px;
  background: rgb(var(--n-100));
  color: rgb(var(--n-700));
}
.sdc-lv-normal { background: rgb(var(--success) / 0.12); color: rgb(var(--success)); }
.sdc-lv-warning { background: rgb(var(--warning) / 0.14); color: rgb(var(--warning)); }
.sdc-lv-critical { background: rgb(var(--danger) / 0.12); color: rgb(var(--danger)); }
</style>
