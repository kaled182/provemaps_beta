<template>
  <section class="rounded-lg border border-neutral-200 bg-surface overflow-auto" data-testid="gpon-onu-panel">
    <h2 class="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-neutral-600 border-b border-neutral-200">
      {{ scope }} · <span class="num">{{ onus.length }}</span>
    </h2>
    <p v-if="!onus.length" class="p-4 text-sm text-neutral-500" data-testid="gpon-onu-empty">Nenhuma ONU neste filtro.</p>
    <table v-else class="w-full text-sm" data-testid="gpon-onu-table">
      <thead class="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
        <tr>
          <th class="th">Porta / ID</th>
          <th class="th">Serial / MAC</th>
          <th class="th">Status / Motivo</th>
          <th class="th text-right">RX ONU</th>
          <th class="th text-right">RX OLT</th>
          <th class="th">Distância / Desde</th>
          <th class="th text-right">Ações</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-neutral-100">
        <tr v-for="o in shown" :key="o.id" class="h-9 hover:bg-neutral-50" data-testid="gpon-onu-row" :data-onu-id="o.id">
          <td class="td num whitespace-nowrap">
            {{ o.pon_id }} : {{ o.onu_index }}
            <span v-if="showOlt" class="block text-xs text-neutral-500 font-sans">{{ o.olt_name }}</span>
          </td>
          <td class="td">
            <span class="num">{{ o.serial || o.mac || '—' }}</span>
            <span v-if="o.serial && o.mac" class="num text-xs text-neutral-500 ml-2">{{ o.mac }}</span>
            <span v-if="subline(o)" class="block text-xs text-neutral-500 truncate max-w-xs">{{ subline(o) }}</span>
          </td>
          <td class="td whitespace-nowrap">
            <span class="tag" :class="statusOf(o).cls" :title="o.reason_label || ''" data-testid="gpon-onu-status">{{ statusOf(o).label }}</span>
          </td>
          <td class="td text-right num whitespace-nowrap" :class="rxClass(o, 'onu')" data-testid="gpon-onu-rx">
            {{ formatDbm(o.rx_onu_dbm) }}
            <span v-if="o.rx_onu_dbm !== null && o.rx_onu_dbm !== undefined" class="q" aria-hidden="true">
              <span class="q-fill" :class="signalBg(o.signal)" :style="{ width: `${quality(o.rx_onu_dbm)}%` }"></span>
            </span>
          </td>
          <td class="td text-right num whitespace-nowrap" :class="rxClass(o, 'olt')">{{ formatDbm(o.rx_olt_dbm) }}</td>
          <td class="td num whitespace-nowrap text-neutral-600" data-testid="gpon-onu-since">{{ distanceSince(o) }}</td>
          <td class="td text-right">
            <button
              type="button"
              class="hist"
              :disabled="!o.has_history"
              :title="o.has_history ? 'Histórico de sinal' : 'Sem histórico no Zabbix'"
              data-testid="gpon-onu-history"
              @click="$emit('history', o)"
            >
              <PhChartLine :size="15" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="onus.length > limit" class="px-3 py-2 border-t border-neutral-200 text-xs text-neutral-500 flex items-center gap-3">
      <span class="num">{{ limit }} de {{ onus.length }}</span>
      <button type="button" class="text-primary-600 hover:underline" data-testid="gpon-onu-more" @click="limit += PAGE">Mostrar mais</button>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { PhChartLine } from '@phosphor-icons/vue'
import { formatDbm, formatDistance, formatSince } from '@/utils/ptBrFormat'

const PAGE = 200
const props = defineProps({
  onus: { type: Array, default: () => [] },
  scope: { type: String, default: 'ONUs' },
  showOlt: { type: Boolean, default: true },
})
defineEmits(['history'])

const limit = ref(PAGE)
const shown = computed(() => props.onus.slice(0, limit.value))
watch(() => props.onus, () => { limit.value = PAGE })

function statusOf(o) {
  if (o.status === 'online') return { label: 'Online', cls: 'tag-success' }
  if (o.status === 'offline') {
    if (o.reason === 'los') return { label: 'LOS (fibra)', cls: 'tag-danger' }
    if (o.reason === 'dying_gasp') return { label: 'Dying Gasp', cls: 'tag-info' }
    return { label: 'Offline', cls: '' }
  }
  return { label: 'Desconhecido', cls: 'tag-unknown' }
}

function subline(o) {
  return [o.cliente_nome, o.login_radius, o.caixa_cto ? `CTO ${o.caixa_cto}` : null, o.description]
    .filter(Boolean)
    .join(' · ')
}

const SIGNAL_TEXT = { normal: 'text-success', warning: 'text-warning', critical: 'text-danger' }
const SIGNAL_BG = { normal: 'bg-success', warning: 'bg-warning', critical: 'bg-danger' }
const signalBg = (s) => SIGNAL_BG[s] || 'bg-neutral-400'

/** O `signal` vem do RX ONU quando existe, senão do RX OLT: só esse leva a cor. */
function rxClass(o, side) {
  const hasOnu = o.rx_onu_dbm !== null && o.rx_onu_dbm !== undefined
  const source = hasOnu ? 'onu' : 'olt'
  return side === source ? SIGNAL_TEXT[o.signal] || '' : ''
}

/** Mini-barra: −8 dBm (cheia) a −30 dBm (vazia); só desenha um valor real. */
function quality(dbm) {
  return Math.round(Math.max(0, Math.min(1, (Number(dbm) + 30) / 22)) * 100)
}

function distanceSince(o) {
  const parts = []
  if (o.distance_m !== null && o.distance_m !== undefined) parts.push(formatDistance(o.distance_m))
  if (o.status_since) parts.push(formatSince(o.status_since, Boolean(o.status_since_is_first_seen)))
  return parts.length ? parts.join(' · ') : '—'
}
</script>

<style scoped>
.th {
  padding: 6px 10px;
  text-align: left;
  font-weight: 600;
  white-space: nowrap;
}
.td {
  padding: 3px 10px;
  vertical-align: middle;
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.tag {
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: rgb(var(--n-600));
  border: 1px solid rgb(var(--n-300));
}
.tag-success {
  color: rgb(var(--success));
  border-color: rgb(var(--success) / 0.4);
  background: rgb(var(--success) / 0.1);
}
.tag-danger {
  color: rgb(var(--danger));
  border-color: rgb(var(--danger) / 0.4);
  background: rgb(var(--danger) / 0.1);
}
.tag-info {
  color: rgb(var(--info));
  border-color: rgb(var(--info) / 0.4);
  background: rgb(var(--info) / 0.1);
}
.tag-unknown {
  color: rgb(var(--n-500));
  border-style: dashed;
}
.q {
  display: block;
  margin-left: auto;
  width: 48px;
  height: 3px;
  border-radius: 2px;
  background: rgb(var(--n-200));
  overflow: hidden;
}
.q-fill {
  display: block;
  height: 100%;
}
.hist {
  padding: 4px;
  border-radius: 4px;
  color: rgb(var(--n-600));
}
.hist:hover:not(:disabled) {
  color: rgb(var(--primary-600));
  background: rgb(var(--n-100));
}
.hist:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
</style>
