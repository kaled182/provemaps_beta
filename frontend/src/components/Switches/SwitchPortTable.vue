<template>
  <section class="spt" data-testid="sw-port-table">
    <header class="spt-head">
      <span class="text-sm font-semibold text-neutral-700">Portas</span>
      <span class="num text-sm text-neutral-500" data-testid="sw-port-count">{{ ports.length }}</span>
      <span v-if="freeHidden" class="text-xs text-neutral-500">· {{ freeHidden }} livres ocultas (filtro «Todas» mostra só as em uso)</span>
    </header>
    <p v-if="!ports.length" class="p-4 text-sm text-neutral-500" data-testid="sw-port-empty">Nenhuma porta neste recorte.</p>
    <div v-else class="spt-scroll">
      <table class="w-full text-sm">
        <thead>
          <tr>
            <th>Porta</th>
            <th>Descrição / destino</th>
            <th>Tipo</th>
            <th>Status</th>
            <th class="r">RX (dBm)</th>
            <th class="r">TX (dBm)</th>
            <th class="r">Tráfego ↓ / ↑</th>
            <th class="r">Uptime</th>
            <th class="c"><span class="sr-only">Gráfico</span></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="p in ports"
            :key="`${p.device_id}:${p.name}`"
            :class="{ 'row-on': isSelected(p) }"
            data-testid="sw-port-row"
            @click="$emit('select', p)"
          >
            <td>
              <span class="num font-semibold text-neutral-900">{{ p.name }}</span>
              <span v-if="showSwitch" class="spt-sw">{{ p.switch_name }}</span>
            </td>
            <td class="spt-desc" :title="[p.description, p.cable_name].filter(Boolean).join(' · ')">
              {{ p.description || '—' }}
              <span v-if="p.cable_name" class="spt-cable">{{ p.cable_name }}</span>
            </td>
            <td class="whitespace-nowrap text-neutral-600">{{ KIND[p.kind] }}<template v-if="p.speed_label"> · {{ p.speed_label }}</template></td>
            <td>
              <span class="tag" :class="`tag-${p.state}`" :title="reasonText(p)" data-testid="sw-port-state">{{ stateLabel(p) }}</span>
            </td>
            <td class="r num" :class="rxClass(p)">{{ dbm(p.rx_dbm, p.los) }}</td>
            <td class="r num text-neutral-600">{{ dbm(p.tx_dbm) }}</td>
            <td class="r num whitespace-nowrap" :class="{ 'text-warning': p.reasons.includes('utilization') }" :title="p.utilization_pct === null ? '' : `${p.utilization_pct}% da velocidade`">
              {{ formatBps(p.in_bps) }} / {{ formatBps(p.out_bps) }}
            </td>
            <td class="r num whitespace-nowrap text-neutral-600">{{ p.uptime_s ? formatDuration(p.uptime_s) : '—' }}</td>
            <td class="c">
              <button
                type="button"
                class="spt-chart"
                :disabled="!p.port_id"
                :title="p.port_id ? 'Gráfico histórico de tráfego e sinal' : 'Porta sem cadastro no inventário — sem gráfico'"
                data-testid="sw-port-chart"
                @click.stop="$emit('history', p)"
              >
                <PhChartLine :size="15" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
/** Tabela densa das portas (EV-0115): 36 px por linha, pior primeiro, gráfico por porta. */
import { PhChartLine } from '@phosphor-icons/vue'
import { STATE_LABELS } from '@/composables/useSwitchesOverview'
import { formatBps, formatDuration } from '@/utils/ptBrFormat'

const props = defineProps({
  ports: { type: Array, default: () => [] },
  thresholds: { type: Object, default: null },
  /** mais de um switch no recorte → mostra de qual é a porta */
  showSwitch: { type: Boolean, default: false },
  selectedKey: { type: String, default: null },
  freeHidden: { type: Number, default: 0 },
})
defineEmits(['select', 'history'])

const KIND = { optical: 'Óptica', electrical: 'Elétrica', mgmt: 'Gerência' }
const REASONS = {
  los: 'Sem luz no transceptor (LOS, -40 dBm)',
  link_down: 'Porta em uso sem link',
  rx_critical: 'RX abaixo do limiar crítico',
  rx_warning: 'RX abaixo do limiar de atenção',
  utilization: 'Banda acima de 80% da velocidade',
}

const isSelected = (p) => props.selectedKey === `${p.device_id}:${p.name}`
const stateLabel = (p) => (p.state === 'down' && p.reasons.includes('los') ? 'LOS' : STATE_LABELS[p.state])
const reasonText = (p) => p.reasons.map((r) => REASONS[r] || r).join(' · ')
const dbm = (v, los = false) => (los ? '-40 (LOS)' : v === null || v === undefined ? '—' : v.toFixed(2))
function rxClass(p) {
  const t = props.thresholds
  if (p.los) return 'text-danger'
  if (p.rx_dbm === null || p.rx_dbm === undefined || !t) return 'text-neutral-500'
  if (p.rx_dbm < t.critical) return 'text-danger'
  if (p.rx_dbm <= t.warning) return 'text-warning'
  return 'text-success'
}
</script>

<style scoped>
.spt {
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  background: rgb(var(--surface));
  overflow: hidden;
}
.spt-head {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid rgb(var(--n-200));
}
.spt-scroll {
  overflow-x: auto;
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
thead {
  background: rgb(var(--n-50));
}
th {
  padding: 6px 10px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgb(var(--n-500));
  white-space: nowrap;
}
td {
  height: 36px;
  padding: 0 10px;
  border-top: 1px solid rgb(var(--n-100));
  vertical-align: middle;
}
tbody tr {
  cursor: pointer;
}
tbody tr:hover {
  background: rgb(var(--n-50));
}
.row-on,
.row-on:hover {
  background: rgb(var(--primary-500) / 0.08);
}
.r {
  text-align: right;
}
.c {
  text-align: center;
  width: 40px;
}
.spt-sw {
  display: block;
  font-size: 10px;
  color: rgb(var(--n-500));
  line-height: 1.1;
}
.spt-desc {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgb(var(--n-700));
}
.spt-cable {
  margin-left: 6px;
  font-size: 11px;
  color: rgb(var(--n-500));
}
.tag {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid rgb(var(--n-300));
  color: rgb(var(--n-600));
}
.tag-normal { color: rgb(var(--success)); border-color: rgb(var(--success) / 0.4); background: rgb(var(--success) / 0.1); }
.tag-warning { color: rgb(var(--warning)); border-color: rgb(var(--warning) / 0.45); background: rgb(var(--warning) / 0.1); }
.tag-critical,
.tag-down { color: rgb(var(--danger)); border-color: rgb(var(--danger) / 0.45); background: rgb(var(--danger) / 0.1); }
.spt-chart {
  display: inline-flex;
  padding: 4px;
  border-radius: 6px;
  color: rgb(var(--n-500));
}
.spt-chart:hover:not(:disabled) {
  background: rgb(var(--n-100));
  color: rgb(var(--primary-600));
}
.spt-chart:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
</style>
