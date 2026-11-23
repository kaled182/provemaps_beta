<template>
  <div class="h-full flex flex-col bg-canvas text-neutral-900">
    <header class="flex-none px-4 md:px-6 py-2 border-b border-neutral-200 bg-surface flex items-center gap-3 flex-wrap">
      <h1 class="text-base font-semibold mr-2">Ativos</h1>
      <nav class="flex items-center gap-1 flex-wrap" aria-label="Filtrar ativos">
        <button
          v-for="f in ASSET_FILTERS"
          :key="f.id"
          type="button"
          class="px-2.5 py-1 rounded-md text-sm font-medium transition-colors"
          :class="filter === f.id ? 'bg-primary-500/10 text-primary-700 dark:text-primary-400' : 'text-neutral-600 hover:bg-neutral-100'"
          :data-testid="`assets-filter-${f.id}`"
          @click="filter = f.id"
        >
          {{ f.label }}
        </button>
      </nav>
      <input
        v-model="query"
        type="search"
        placeholder="Buscar equipamento, site, IP…"
        class="ml-auto w-64 px-2.5 py-1.5 rounded-md border border-neutral-300 bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30"
        aria-label="Buscar ativos"
      />
      <button type="button" class="px-2 py-1.5 rounded-md text-neutral-600 hover:bg-neutral-100" title="Atualizar" :disabled="loading" @click="load">
        <i class="fas fa-rotate" :class="{ 'animate-spin': loading }"></i>
      </button>
    </header>

    <main class="flex-1 min-h-0 overflow-auto px-4 md:px-6 py-3 flex flex-col gap-3">
      <section class="grid grid-cols-2 lg:grid-cols-4 gap-2" aria-label="Resumo dos ativos">
        <div class="kpi"><span class="kpi-label">Total de ativos</span><span class="kpi-value">{{ kpis.total }}</span></div>
        <div class="kpi">
          <span class="kpi-label">Online</span>
          <span class="kpi-value text-success">{{ kpis.online }}</span>
          <span class="text-xs text-neutral-500" data-testid="assets-availability">
            {{ kpis.availability === null ? 'disponibilidade sem dados' : `${kpis.availability.toFixed(1)} % disponível` }}
          </span>
        </div>
        <div class="kpi"><span class="kpi-label">Offline / inacessíveis</span><span class="kpi-value text-danger">{{ kpis.offline }}</span></div>
        <div class="kpi" data-testid="assets-cpu-kpi">
          <span class="kpi-label">CPU ≥ {{ CPU_ALERT_PERCENT }} %</span>
          <span v-if="kpis.cpuMeasured" class="kpi-value" :class="kpis.cpuAlerts ? 'text-warning' : ''">{{ kpis.cpuAlerts }}</span>
          <span v-else class="kpi-value text-neutral-500 text-sm">sem dados</span>
          <span class="text-xs text-neutral-500">{{ kpis.cpuMeasured }} com CPU medida</span>
        </div>
      </section>

      <p v-if="zabbixError" class="px-3 py-2 rounded-md border border-warning/40 bg-warning/10 text-sm text-warning" role="alert" data-testid="assets-zabbix-error">
        O Zabbix não respondeu: estado, uptime e CPU podem estar em falta. Os dados de inventário estão completos.
      </p>
      <p v-if="error" class="px-3 py-2 rounded-md border border-danger/40 bg-danger/10 text-sm text-danger" role="alert">
        Erro ao carregar os ativos: {{ error }}
      </p>

      <div class="rounded-lg border border-neutral-200 bg-surface overflow-auto">
        <p v-if="loading && !rows.length" class="p-4 text-sm text-neutral-500">Carregando ativos…</p>
        <p v-else-if="!visible.length" class="p-4 text-sm text-neutral-500">Nenhum ativo neste filtro.</p>
        <table v-else class="w-full text-sm" data-testid="assets-table">
          <thead class="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th class="th">Dispositivo</th>
              <th class="th">POP / site</th>
              <th class="th">IP de gestão</th>
              <th class="th">Estado · uptime</th>
              <th class="th text-right" title="Portas em cabos com leitura óptica recente / total em cabos">Portas ópticas</th>
              <th class="th text-right">CPU</th>
              <th class="th">Última coleta</th>
              <th class="th text-right">Ações</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            <tr v-for="r in visible" :key="r.id" class="hover:bg-neutral-50" :data-testid="`asset-row-${r.id}`">
              <td class="td whitespace-nowrap">
                <span class="font-semibold">{{ r.name }}</span>
                <span v-if="r.vendorModel" class="ml-2 text-xs text-neutral-500">{{ r.vendorModel }}</span>
              </td>
              <td class="td whitespace-nowrap">{{ r.siteName || '—' }}</td>
              <td class="td num">{{ r.ip || '—' }}</td>
              <td class="td whitespace-nowrap">
                <span class="dot" :class="`dot-${r.status}`"></span>
                <span class="ml-1.5">{{ STATUS_LABEL[r.status] || r.status }}</span>
                <span v-if="r.uptime" class="ml-2 text-xs text-neutral-500 num">{{ r.uptime }}</span>
              </td>
              <td class="td text-right num">
                <template v-if="r.opticalTotal !== null">{{ r.opticalWithReading }}/{{ r.opticalTotal }}</template>
                <template v-else>—</template>
              </td>
              <td class="td text-right num" :class="cpuClass(r)">
                <template v-if="r.cpu !== null">
                  {{ r.cpu.toFixed(1) }} %
                  <span v-if="r.cpuSource === 'manual'" class="tag" title="Valor configurado à mão no equipamento, não medido">manual</span>
                </template>
                <template v-else>—</template>
              </td>
              <td class="td whitespace-nowrap text-neutral-600">{{ ago(r.lastCollected) }}</td>
              <td class="td text-right whitespace-nowrap">
                <button type="button" class="icon-btn" title="Abrir no mapa" :disabled="!r.center" @click="openOnMap(r)">
                  <i class="fas fa-map-marked-alt"></i>
                </button>
                <button type="button" class="icon-btn" title="Ver no inventário" @click="openInventory">
                  <i class="fas fa-list"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>
  </div>
</template>

<script setup>
/**
 * Ativos (POPs & rede) — EV-0058. Inventário + estado Zabbix + métricas (uma
 * chamada item.get para todos) + portas ópticas com leitura (optical-summary).
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { OPTICAL_SUMMARY_URL } from '@/composables/useOpticalSummary'
import {
  ASSET_FILTERS,
  CPU_ALERT_PERCENT,
  buildAssetRows,
  computeAssetKpis,
  filterAndSortAssets,
  opticalPortsByDevice,
} from '@/utils/assetsTable'
import { buildFocusLocation } from '@/utils/mapFocus'
import { formatAgo } from '@/utils/mapKpis'

const STATUS_LABEL = { online: 'Online', offline: 'Offline', unknown: 'Sem estado', disabled: 'Desativado no Zabbix' }

const api = useApi()
const router = useRouter()
const rows = ref([])
const loading = ref(false)
const error = ref('')
const zabbixError = ref(false)
const filter = ref('all')
const query = ref('')

const kpis = computed(() => computeAssetKpis(rows.value))
const visible = computed(() => filterAndSortAssets(rows.value, { filter: filter.value, query: query.value }))

async function getAllPages(url) {
  const out = []
  let next = url
  while (next) {
    const data = await api.get(next)
    if (Array.isArray(data)) return data
    out.push(...(data.results || []))
    next = data.next ? new URL(data.next, window.location.origin).pathname + new URL(data.next, window.location.origin).search : null
  }
  return out
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [devices, sites] = await Promise.all([getAllPages('/api/v1/devices/'), getAllPages('/api/v1/sites/')])
    const ids = devices.map((d) => d.id).join(',')
    const [status, metrics, optical] = await Promise.all([
      ids ? api.get('/api/v1/inventory/devices/zabbix-status/', { device_ids: ids }).catch(() => ({ statuses: {}, zabbix_error: true })) : { statuses: {} },
      ids ? api.get('/api/v1/devices/metrics-batch/', { ids }).catch(() => ({ results: {}, zabbix_error: true })) : { results: {} },
      api.get(OPTICAL_SUMMARY_URL).catch(() => null),
    ])
    zabbixError.value = Boolean(status.zabbix_error || metrics.zabbix_error)
    const siteMap = new Map(
      sites.map((s) => [s.id, { name: s.display_name || s.name, lat: s.latitude === null ? null : Number(s.latitude), lng: s.longitude === null ? null : Number(s.longitude) }]),
    )
    rows.value = buildAssetRows(devices, {
      statuses: status.statuses || {},
      metrics: metrics.results || {},
      optical: opticalPortsByDevice(optical),
      sites: siteMap,
    })
  } catch (e) {
    error.value = e?.message || 'erro desconhecido'
  } finally {
    loading.value = false
  }
}

function cpuClass(r) {
  if (r.cpu === null || r.cpuSource !== 'zabbix') return r.cpuSource === 'manual' ? 'text-neutral-500' : ''
  return r.cpu >= CPU_ALERT_PERCENT ? 'text-warning' : ''
}

function ago(iso) {
  return iso ? formatAgo(new Date(iso)) : '—'
}

function openOnMap(r) {
  const loc = r.center && buildFocusLocation({ type: 'device', id: r.id, name: r.name, lat: r.center.lat, lng: r.center.lng })
  if (loc) router.push(loc)
}

function openInventory() {
  router.push('/network/inventory')
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
  padding: 6px 12px;
  vertical-align: middle;
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgb(var(--n-400));
}
.dot-online { background: rgb(var(--success)); }
.dot-offline { background: rgb(var(--danger)); }
.tag {
  margin-left: 4px;
  padding: 0 5px;
  border-radius: 4px;
  border: 1px solid rgb(var(--n-300));
  font-family: Inter, system-ui, sans-serif;
  font-size: 10px;
  color: rgb(var(--n-500));
}
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
