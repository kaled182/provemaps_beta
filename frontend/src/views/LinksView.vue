<template>
  <div class="h-full flex flex-col bg-canvas text-neutral-900">
    <!-- Cabeçalho numa linha: título · filtros · busca · atualização -->
    <header class="flex-none px-4 md:px-6 py-2 border-b border-neutral-200 bg-surface flex items-center gap-3 flex-wrap">
      <h1 class="text-base font-semibold mr-2">Enlaces &amp; fibra</h1>
      <nav class="flex items-center gap-1 flex-wrap" aria-label="Filtrar enlaces">
        <button
          v-for="f in LINK_FILTERS"
          :key="f.id"
          type="button"
          class="px-2.5 py-1 rounded-md text-sm font-medium transition-colors"
          :class="filter === f.id ? 'bg-primary-500/10 text-primary-700 dark:text-primary-400' : 'text-neutral-600 hover:bg-neutral-100'"
          :data-testid="`links-filter-${f.id}`"
          @click="filter = f.id"
        >
          {{ f.label }} <span class="font-mono tabular-nums text-xs text-neutral-500">{{ counts[f.id] }}</span>
        </button>
      </nav>
      <input
        v-model="query"
        type="search"
        placeholder="Buscar enlace, site, equipamento…"
        class="ml-auto w-64 px-2.5 py-1.5 rounded-md border border-neutral-300 bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30"
        aria-label="Buscar enlaces"
      />
      <span class="text-xs text-neutral-500 whitespace-nowrap" data-testid="links-updated">
        <template v-if="summary?.last_check">leitura {{ lastCheckLabel }}</template>
        <template v-else-if="summary">sem leituras</template>
      </span>
      <button
        type="button"
        class="px-2 py-1.5 rounded-md text-neutral-600 hover:bg-neutral-100"
        title="Atualizar"
        :disabled="loading"
        @click="load"
      >
        <i class="fas fa-rotate" :class="{ 'animate-spin': loading }"></i>
      </button>
    </header>

    <main class="flex-1 min-h-0 overflow-auto px-4 md:px-6 py-3 flex flex-col gap-3">
      <!-- 4 KPIs -->
      <section class="grid grid-cols-2 lg:grid-cols-4 gap-2" aria-label="Resumo dos enlaces">
        <div class="kpi"><span class="kpi-label">Total de enlaces</span><span class="kpi-value">{{ totals.total }}</span></div>
        <div class="kpi"><span class="kpi-label">Saudáveis</span><span class="kpi-value text-success">{{ totals.healthy }}</span></div>
        <div class="kpi"><span class="kpi-label">Em atenção</span><span class="kpi-value text-warning">{{ totals.attention }}</span></div>
        <div class="kpi">
          <span class="kpi-label">Críticos / LOS</span>
          <span class="kpi-value text-danger">{{ totals.critical }}</span>
          <span v-if="totals.unknown" class="text-xs text-neutral-500">{{ totals.unknown }} sem leitura</span>
        </div>
      </section>

      <p v-if="error" class="px-3 py-2 rounded-md border border-danger/40 bg-danger/10 text-sm text-danger" role="alert">
        Erro ao ler os níveis ópticos: {{ error }}
      </p>

      <div class="rounded-lg border border-neutral-200 bg-surface overflow-auto">
        <p v-if="loading && !summary" class="p-4 text-sm text-neutral-500">Carregando enlaces…</p>
        <p v-else-if="summary && !rows.length" class="p-4 text-sm text-neutral-500">Nenhum enlace neste filtro.</p>
        <table v-else-if="summary" class="w-full text-sm" data-testid="links-table">
          <thead class="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th class="th">Enlace</th>
              <th class="th">Ponta A</th>
              <th class="th text-right">RX / TX A</th>
              <th class="th">Ponta B</th>
              <th class="th text-right">RX / TX B</th>
              <th class="th text-right" title="TX que sai de uma ponta menos o RX que chega à outra">Perda A→B / B→A</th>
              <th class="th">Estado</th>
              <th class="th text-right">Ações</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            <tr v-for="c in rows" :key="c.id" class="hover:bg-neutral-50" :data-testid="`link-row-${c.id}`">
              <td class="td whitespace-nowrap">
                <span class="font-semibold">{{ c.name }}</span>
                <span v-if="c.length_km !== null" class="ml-2 text-xs text-neutral-500 font-mono tabular-nums">{{ formatDb(c.length_km) }} km</span>
              </td>
              <td class="td whitespace-nowrap">
                <span>{{ c.origin.device_name || '—' }}</span>
                <span class="text-neutral-500"> · {{ c.origin.port_name || '—' }}</span>
              </td>
              <td class="td text-right num" :class="endClass(c.origin)" :title="endTitle(c.origin)">
                {{ formatDb(c.origin.rx) }} <span class="text-neutral-400">/</span> {{ formatDb(c.origin.tx) }}
              </td>
              <td class="td whitespace-nowrap">
                <span>{{ c.destination.device_name || '—' }}</span>
                <span class="text-neutral-500"> · {{ c.destination.port_name || '—' }}</span>
              </td>
              <td class="td text-right num" :class="endClass(c.destination)" :title="endTitle(c.destination)">
                {{ formatDb(c.destination.rx) }} <span class="text-neutral-400">/</span> {{ formatDb(c.destination.tx) }}
              </td>
              <td class="td text-right num">
                {{ formatDb(c.loss_ab_db) }} <span class="text-neutral-400">/</span> {{ formatDb(c.loss_ba_db) }}
              </td>
              <td class="td">
                <span class="badge" :class="`badge-${c.health}`">{{ HEALTH_LABEL[c.health] || c.health }}</span>
              </td>
              <td class="td text-right whitespace-nowrap">
                <button type="button" class="icon-btn" title="Gráfico óptico" @click="openChart(c)">
                  <i class="fas fa-chart-line"></i>
                </button>
                <button type="button" class="icon-btn" title="Ver no mapa" :disabled="!c.center" @click="openOnMap(c)">
                  <i class="fas fa-map-marked-alt"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>

    <FiberCableDetailModal v-if="chartCable" :show="Boolean(chartCable)" :cable="chartCable" @close="chartCable = null" />
  </div>
</template>

<script setup>
/**
 * Enlaces & fibra (EV-0057): todos os cabos com RX/TX das duas pontas, perda por
 * sentido e estado pelos limiares da configuração. Dados do banco (tarefa de 60 s).
 */
import { computed, defineAsyncComponent, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useOpticalSummary } from '@/composables/useOpticalSummary'
import { LINK_FILTERS, HEALTH_LABEL, filterAndSortLinks, formatDb, countByFilter } from '@/utils/linksTable'
import { buildFocusLocation } from '@/utils/mapFocus'
import { formatAgo } from '@/utils/mapKpis'

const FiberCableDetailModal = defineAsyncComponent(() => import('@/components/FiberCableDetailModal.vue'))

const router = useRouter()
const { data: summary, loading, error, load } = useOpticalSummary()
const filter = ref('all')
const query = ref('')
const chartCable = ref(null)

const cables = computed(() => summary.value?.cables || [])
const totals = computed(() => summary.value?.totals || { total: 0, healthy: 0, attention: 0, critical: 0, unknown: 0 })
const counts = computed(() => countByFilter(cables.value))
const rows = computed(() => filterAndSortLinks(cables.value, { filter: filter.value, query: query.value }))
const lastCheckLabel = computed(() => {
  const iso = summary.value?.last_check
  return iso ? formatAgo(new Date(iso)) : ''
})

const STATUS_CLASS = { critical: 'text-danger', offline: 'text-danger', warning: 'text-warning', online: '' }
function endClass(end) {
  if (end.stale) return 'text-neutral-400'
  return STATUS_CLASS[end.status] || ''
}
function endTitle(end) {
  if (end.rx === null) return 'Sem leitura'
  const thr = `limiares atenção ${formatDb(end.warning_threshold)} · crítico ${formatDb(end.critical_threshold)} dBm`
  return end.stale ? `Leitura antiga (${end.last_check}) — ${thr}` : thr
}

function openChart(c) {
  chartCable.value = { id: c.id, name: c.name, status: c.status, length_km: c.length_km }
}

function openOnMap(c) {
  const loc = c.center && buildFocusLocation({ type: 'cable', id: c.id, name: c.name, lat: c.center.lat, lng: c.center.lng })
  if (loc) router.push(loc)
}

onMounted(load)
</script>

<style scoped>
.kpi {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgb(var(--n-200));
  background: rgb(var(--surface));
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgb(var(--n-500));
}
.kpi-value {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 20px;
  font-weight: 600;
}
.th {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  white-space: nowrap;
}
.td {
  /* linhas de ~36 px */
  padding: 6px 12px;
  vertical-align: middle;
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}
.badge-healthy { background: rgb(var(--success) / 0.12); color: rgb(var(--success)); }
.badge-attention { background: rgb(var(--warning) / 0.15); color: rgb(var(--warning)); }
.badge-critical { background: rgb(var(--danger) / 0.12); color: rgb(var(--danger)); }
.badge-unknown { background: rgb(var(--n-100)); color: rgb(var(--n-600)); }
.icon-btn {
  padding: 4px 6px;
  border-radius: 6px;
  color: rgb(var(--n-500));
}
.icon-btn:hover:not(:disabled) {
  background: rgb(var(--n-100));
  color: rgb(var(--n-900));
}
.icon-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
</style>
