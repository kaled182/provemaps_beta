<template>
  <div class="pol" data-testid="pon-onu-list">
    <!-- Filtros rápidos da lista (sobre as ONUs recebidas) -->
    <div class="pol-bar">
      <div class="pills" role="group" aria-label="Filtro das ONUs">
        <button
          v-for="f in filters"
          :key="f.value"
          type="button"
          class="pill"
          :class="{ 'pill-on': quick === f.value }"
          :aria-pressed="quick === f.value"
          :data-testid="`pol-filter-${f.value}`"
          @click="quick = f.value"
        >
          {{ f.label }} <span class="num">({{ f.count }})</span>
        </button>
      </div>
      <label class="search">
        <PhMagnifyingGlass :size="13" class="text-neutral-400" />
        <input v-model="search" type="search" placeholder="Serial ou cliente…" aria-label="Buscar ONU na lista" data-testid="pol-search" />
      </label>
    </div>

    <p v-if="!filtered.length" class="p-4 text-sm text-neutral-500" data-testid="gpon-onu-empty">Nenhuma ONU neste filtro.</p>
    <table v-else class="w-full text-sm" data-testid="gpon-onu-table">
      <thead class="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
        <tr>
          <th class="th">Porta / ID</th>
          <th class="th">Serial / MAC</th>
          <th class="th">Status / Motivo</th>
          <th class="th text-right">RX ONU</th>
          <th class="th text-right">RX OLT</th>
          <th class="th">Distância / Desde</th>
          <th class="th text-right"><span class="sr-only">Gráfico</span></th>
        </tr>
      </thead>
      <tbody>
        <template v-for="o in shown" :key="o.id">
          <tr
            class="row"
            :class="{ 'row-open': openId === o.id }"
            data-testid="gpon-onu-row"
            :data-onu-id="o.id"
            :aria-expanded="openId === o.id"
            @click="toggle(o)"
          >
            <td class="td num whitespace-nowrap">
              {{ o.pon_id }} : {{ o.onu_index }}
              <span v-if="showOlt" class="block text-xs text-neutral-500 font-sans">{{ o.olt_name }}</span>
            </td>
            <td class="td">
              <button
                v-if="o.serial || o.mac"
                type="button"
                class="copy num"
                :title="copiedId === o.id ? 'Copiado' : 'Copiar'"
                :data-testid="`onu-copy-${o.id}`"
                @click.stop="copySerial(o)"
              >
                {{ o.serial || o.mac }}
                <component :is="copiedId === o.id ? PhCheck : PhCopy" :size="12" class="copy-icon" :class="{ 'copy-done': copiedId === o.id }" />
                <span v-if="copiedId === o.id" class="copied">Copiado!</span>
              </button>
              <span v-else class="num">—</span>
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
                :class="{ 'hist-on': openId === o.id }"
                :title="openId === o.id ? 'Fechar a ficha' : 'Gráfico e ficha da ONU'"
                data-testid="gpon-onu-history"
                @click.stop="toggle(o)"
              >
                <component :is="openId === o.id ? PhCaretUp : PhChartLine" :size="15" />
              </button>
            </td>
          </tr>
          <tr v-if="openId === o.id" class="row-detail">
            <td colspan="7" class="p-0">
              <OnuDetail :onu="o" :thresholds="thresholds" />
            </td>
          </tr>
        </template>
      </tbody>
    </table>
    <div v-if="filtered.length > limit" class="px-3 py-2 border-t border-neutral-200 text-xs text-neutral-500 flex items-center gap-3">
      <span class="num">{{ limit }} de {{ filtered.length }}</span>
      <button type="button" class="text-primary-600 hover:underline" data-testid="gpon-onu-more" @click="limit += PAGE">Mostrar mais</button>
    </div>
  </div>
</template>

<script setup>
/**
 * Lista de ONUs (EV-0119), partilhada pelo ecrã GPON e pelo modal de Site: pílulas rápidas
 * (Todas / Com falha-LOS / Sinal crítico-atenção) e busca sobre as ONUs recebidas, linhas
 * de 36 px, serial copiável, e a ficha com o gráfico expandida NA PRÓPRIA LINHA (accordion)
 * — sem um modal por cima de outro.
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { PhCaretUp, PhChartLine, PhCheck, PhCopy, PhMagnifyingGlass } from '@phosphor-icons/vue'
import { copyText } from './ponDiagnosis'
import OnuDetail from './OnuDetail.vue'
import { formatDbm, formatDistance, formatSince } from '@/utils/ptBrFormat'

const PAGE = 200
const props = defineProps({
  onus: { type: Array, default: () => [] },
  showOlt: { type: Boolean, default: true },
  thresholds: { type: Object, default: null },
  /** muda quando o recorte muda (outra PON/OLT): volta a «Todas», limpa a busca e fecha a ficha */
  resetKey: { type: [String, Number], default: null },
})
const emit = defineEmits(['count'])

const isFailure = (o) => o.status === 'offline'
const isSignal = (o) => o.signal === 'warning' || o.signal === 'critical'

const quick = ref('all')
const search = ref('')
const filters = computed(() => [
  { value: 'all', label: 'Todas', count: props.onus.length },
  { value: 'failure', label: 'Com falha / LOS', count: props.onus.filter(isFailure).length },
  { value: 'signal', label: 'Sinal crítico / atenção', count: props.onus.filter(isSignal).length },
])
const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return props.onus
    .filter((o) => (quick.value === 'failure' ? isFailure(o) : quick.value === 'signal' ? isSignal(o) : true))
    .filter(
      (o) =>
        !q ||
        [o.serial, o.mac, o.cliente_nome, o.login_radius, o.description, o.caixa_cto].some((v) => v && String(v).toLowerCase().includes(q)),
    )
})
watch(() => filtered.value.length, (n) => emit('count', n), { immediate: true })

// ficha aberta (uma de cada vez)
const openId = ref(null)
function toggle(o) {
  openId.value = openId.value === o.id ? null : o.id
}

watch(
  () => props.resetKey,
  () => {
    quick.value = 'all'
    search.value = ''
    openId.value = null
  },
)

// EV-0107: serial/MAC copiável com 1 clique, com confirmação breve
const copiedId = ref(null)
let copiedTimer = null
async function copySerial(o) {
  try {
    await copyText(o.serial || o.mac)
    copiedId.value = o.id
    clearTimeout(copiedTimer)
    copiedTimer = setTimeout(() => {
      copiedId.value = null
    }, 1500)
  } catch {
    copiedId.value = null
  }
}
onBeforeUnmount(() => clearTimeout(copiedTimer))

const limit = ref(PAGE)
const shown = computed(() => filtered.value.slice(0, limit.value))
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
.pol-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 6px 10px;
  border-bottom: 1px solid rgb(var(--n-200));
}
.pills {
  display: inline-flex;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  overflow: hidden;
}
.pill {
  padding: 3px 9px;
  font-size: 12px;
  color: rgb(var(--n-600));
  background: rgb(var(--surface));
  border-left: 1px solid rgb(var(--n-200));
}
.pill:first-child {
  border-left: 0;
}
.pill:hover {
  background: rgb(var(--n-100));
}
.pill-on,
.pill-on:hover {
  color: rgb(var(--primary-600));
  background: rgb(var(--primary-500) / 0.12);
  font-weight: 600;
}
.search {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid rgb(var(--n-300));
  background: rgb(var(--surface));
}
.search input {
  width: 12rem;
  border: 0;
  outline: none;
  background: transparent;
  font-size: 12px;
  color: rgb(var(--n-900));
}
.row {
  cursor: pointer;
  border-top: 1px solid rgb(var(--n-100));
}
.row:hover {
  background: rgb(var(--n-50));
}
.row-open {
  background: rgb(var(--primary-500) / 0.06);
}
.copied {
  margin-left: 4px;
  font-family: var(--font-sans, Inter, sans-serif);
  font-size: 11px;
  color: rgb(var(--success));
}
.hist-on {
  color: rgb(var(--primary-600));
}
.copy {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 2px;
  border-radius: 4px;
  color: rgb(var(--n-900));
}
.copy:hover {
  background: rgb(var(--n-100));
}
.copy-icon {
  color: rgb(var(--n-400));
}
.copy:hover .copy-icon {
  color: rgb(var(--n-700));
}
.copy-done {
  color: rgb(var(--success));
}
.th {
  padding: 6px 10px;
  text-align: left;
  font-weight: 600;
  white-space: nowrap;
}
.td {
  height: 36px;
  padding: 0 10px;
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
