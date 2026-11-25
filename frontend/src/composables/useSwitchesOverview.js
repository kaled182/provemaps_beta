/**
 * Monitoramento de Switches (EV-0115): carga de `GET /api/v1/monitoring/switches/`,
 * atualização a cada 60 s, recortes (fabricante, POP, switch, pílula, busca) e a porta
 * selecionada. O backend já classifica cada porta (`state`, `reasons`); aqui só se filtra.
 *
 * Endereço: lê `?pop=` e `?switch=` ao abrir (links do modal de Site), não os reescreve.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'

export const SWITCHES_URL = '/api/v1/monitoring/switches/'
export const REFRESH_MS = 60 * 1000

export const FILTERS = Object.freeze([
  { value: 'all', label: 'Todas' },
  { value: 'down', label: 'Link down / LOS' },
  { value: 'critical', label: 'Sinal crítico' },
  { value: 'utilization', label: 'Banda > 80%' },
])

export const VENDOR_LABELS = Object.freeze({ huawei: 'Huawei', ubiquiti: 'Ubiquiti' })

export const STATE_LABELS = Object.freeze({
  normal: 'Normal',
  warning: 'Atenção',
  critical: 'Crítico',
  down: 'Down',
  free: 'Livre',
  unknown: 'Sem dados',
})

/** Pílula → predicado sobre a porta (já classificada pelo backend). */
export function portMatchesFilter(port, filter) {
  if (filter === 'down') return port.state === 'down'
  if (filter === 'critical') return port.reasons?.includes('rx_critical')
  if (filter === 'utilization') return port.reasons?.includes('utilization')
  return true
}

export function portMatchesQuery(port, query) {
  const q = (query || '').trim().toLowerCase()
  if (!q) return true
  return [port.name, port.description, port.cable_name, port.switch_name].some((v) => v && String(v).toLowerCase().includes(q))
}

/** Porta mais crítica de uma lista (para o inspetor abrir já nela). */
export function mostCriticalPort(ports) {
  let best = null
  for (const p of ports || []) {
    if (p.state === 'free' || p.kind === 'mgmt') continue
    if (best === null || p.severity_rank < best.severity_rank) best = p
  }
  return best
}

export const portKey = (port) => `${port.device_id}:${port.name}`

function readUrlScope() {
  try {
    const q = new URLSearchParams(window.location.search)
    const sw = Number(q.get('switch'))
    return { pop: q.get('pop') || null, switchId: Number.isFinite(sw) && sw > 0 ? sw : null }
  } catch {
    return { pop: null, switchId: null }
  }
}

export function useSwitchesOverview({ autoRefresh = true } = {}) {
  const api = useApi()
  const data = ref(null)
  const loading = ref(false)
  const error = ref('')
  const initial = readUrlScope()

  const vendor = ref(null)
  const pop = ref(initial.pop)
  const switchId = ref(initial.switchId)
  const filter = ref('all')
  const query = ref('')
  const selectedKey = ref(null)
  let timer = null
  let seq = 0

  async function load({ refresh = false } = {}) {
    const mine = ++seq
    loading.value = true
    try {
      const body = await api.get(SWITCHES_URL, refresh ? { refresh: 'true' } : {})
      if (mine !== seq) return
      data.value = body
      error.value = ''
    } catch (e) {
      if (mine === seq) error.value = e?.message || 'erro desconhecido'
    } finally {
      if (mine === seq) loading.value = false
    }
  }

  const thresholds = computed(() => data.value?.thresholds || null)
  const allSwitches = computed(() => data.value?.switches || [])

  const vendors = computed(() =>
    [...new Set(allSwitches.value.map((s) => s.vendor))].map((v) => ({ value: v, label: VENDOR_LABELS[v] || v })),
  )
  const pops = computed(() =>
    [...new Set(allSwitches.value.filter((s) => !vendor.value || s.vendor === vendor.value).map((s) => s.site_name).filter(Boolean))]
      .sort((a, b) => a.localeCompare(b, 'pt-BR'))
      .map((p) => ({ value: p, label: p })),
  )
  /** Switches no recorte fabricante/POP (alimenta o select de switch e os KPIs). */
  const scopedSwitches = computed(() =>
    allSwitches.value.filter((s) => (!vendor.value || s.vendor === vendor.value) && (!pop.value || s.site_name === pop.value)),
  )
  const visibleSwitches = computed(() =>
    switchId.value === null ? scopedSwitches.value : scopedSwitches.value.filter((s) => s.device_id === switchId.value),
  )
  const visibleIds = computed(() => new Set(visibleSwitches.value.map((s) => s.device_id)))

  /** Portas do recorte (sem pílula nem busca) — base dos KPIs e do chassi. */
  const scopedPorts = computed(() => (data.value?.ports || []).filter((p) => visibleIds.value.has(p.device_id)))

  const visiblePorts = computed(() =>
    scopedPorts.value
      .filter((p) => p.kind !== 'mgmt')
      .filter((p) => (filter.value === 'all' ? p.state !== 'free' : portMatchesFilter(p, filter.value)))
      .filter((p) => portMatchesQuery(p, query.value))
      .slice()
      .sort(
        (a, b) =>
          a.severity_rank - b.severity_rank ||
          a.switch_name.localeCompare(b.switch_name, 'pt-BR') ||
          a.name.localeCompare(b.name, 'pt-BR', { numeric: true }),
      ),
  )
  const freeHidden = computed(() =>
    filter.value === 'all' ? scopedPorts.value.filter((p) => p.kind !== 'mgmt' && p.state === 'free').length : 0,
  )

  /** KPIs do recorte (os do backend são da rede toda). */
  const kpis = computed(() => {
    const sws = visibleSwitches.value
    const ports = scopedPorts.value.filter((p) => p.kind !== 'mgmt')
    const count = (pred) => ports.reduce((n, p) => n + (pred(p) ? 1 : 0), 0)
    const top = (field) =>
      sws.filter((s) => s[field] !== null && s[field] !== undefined).reduce((best, s) => (best === null || s[field] > best[field] ? s : best), null)
    return {
      switches: sws.length,
      online: sws.filter((s) => s.status === 'online').length,
      offline: sws.filter((s) => s.status === 'offline').length,
      unknown: sws.filter((s) => s.status === 'unknown').length,
      portsMonitored: ports.length,
      portsUp: count((p) => p.oper === 'up'),
      portsInUse: count((p) => p.in_use),
      portsFree: count((p) => p.state === 'free'),
      signalCritical: count((p) => p.reasons?.includes('rx_critical')),
      signalWarning: count((p) => p.reasons?.includes('rx_warning')),
      down: count((p) => p.state === 'down'),
      los: count((p) => p.state === 'down' && p.reasons?.includes('los')),
      highUtilization: count((p) => p.reasons?.includes('utilization')),
      hottest: top('temperature_c'),
      busiestCpu: top('cpu_pct'),
    }
  })

  const selectedPort = computed(() => {
    if (selectedKey.value === null) return null
    return (data.value?.ports || []).find((p) => portKey(p) === selectedKey.value) || null
  })
  function selectPort(port) {
    selectedKey.value = port ? portKey(port) : null
  }

  // Um POP ou switch que deixou de existir no recorte cai.
  watch([vendor, () => pops.value.length], () => {
    if (pop.value !== null && !pops.value.some((p) => p.value === pop.value)) pop.value = null
  })
  watch([vendor, pop, allSwitches], () => {
    if (switchId.value !== null && !scopedSwitches.value.some((s) => s.device_id === switchId.value)) switchId.value = null
  })

  function stop() {
    if (timer) clearInterval(timer)
    timer = null
  }
  onMounted(() => {
    load()
    if (autoRefresh) timer = setInterval(() => load(), REFRESH_MS)
  })
  onBeforeUnmount(stop)

  return {
    data,
    loading,
    error,
    load,
    thresholds,
    vendor,
    pop,
    switchId,
    filter,
    query,
    vendors,
    pops,
    scopedSwitches,
    visibleSwitches,
    scopedPorts,
    visiblePorts,
    freeHidden,
    kpis,
    selectedPort,
    selectPort,
    allCount: computed(() => allSwitches.value.length),
  }
}
