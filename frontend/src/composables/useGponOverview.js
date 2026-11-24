/**
 * Monitoramento GPON (EV-0095): um GET a /api/v1/monitoring/gpon/ a cada 60 s,
 * filtros e seleção de PON no cliente.
 *
 * Decisão: o pedido NÃO leva `?olt=` — o payload traz todas as OLTs e ONUs (lidas da
 * base, sem Zabbix no pedido) e trocar de OLT no select é instantâneo, sem novo fetch.
 * Os KPIs são os `totals` do payload (rede inteira), não recalculados no cliente.
 *
 * Regras da tabela de ONUs (já vêm ordenadas por severity_rank — nunca se reordena):
 * - PON selecionada → as ONUs dessa PON;
 * - senão OLT escolhida → as ONUs dessa OLT;
 * - senão, com filtro (pílula) ou busca → todas as que casam;
 * - senão → só as com problema (severity_rank ≤ 4).
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'

export const GPON_URL = '/api/v1/monitoring/gpon/'
export const REFRESH_MS = 60 * 1000
export const STALE_MS = 10 * 60 * 1000
export const OCCUPANCY_LIMIT = 85
export const PROBLEM_RANK = 4
export const FILTERS = [
  { value: 'all', label: 'Todas' },
  { value: 'los', label: 'Queda em massa / LOS' },
  { value: 'critical', label: 'Sinal crítico' },
  { value: 'occupancy', label: 'Ocupação > 85%' },
]

export const ponKey = (deviceId, ponId) => `${deviceId}:${ponId}`

/** Estado do Zabbix para o badge do cabeçalho: ok | down | stale. */
export function zabbixState(data, now = Date.now()) {
  if (!data) return null
  if (!data.zabbix_ok) return 'down'
  const t = data.collected_at ? new Date(data.collected_at).getTime() : NaN
  if (!Number.isFinite(t) || now - t > STALE_MS) return 'stale'
  return 'ok'
}

function ponMatches(pon, filter) {
  if (filter === 'los') return pon.collective_drop || (pon.los ?? 0) > 0
  if (filter === 'critical') return (pon.signal_critical ?? 0) > 0
  if (filter === 'occupancy') return (pon.occupancy_pct ?? 0) > OCCUPANCY_LIMIT
  return true
}

export function useGponOverview({ autoRefresh = true } = {}) {
  const api = useApi()
  const data = ref(null)
  const loading = ref(false)
  const error = ref('')
  const oltFilter = ref(null)
  const filter = ref('all')
  const query = ref('')
  const selectedPon = ref(null)
  let timer = null

  async function load() {
    loading.value = true
    error.value = ''
    try {
      data.value = await api.get(GPON_URL)
    } catch (e) {
      error.value = e?.message || 'erro desconhecido'
    } finally {
      loading.value = false
    }
  }

  const allOlts = computed(() => data.value?.olts || [])
  const thresholds = computed(() => data.value?.thresholds || null)
  const totals = computed(() => data.value?.totals || {})
  const zabbix = computed(() => zabbixState(data.value))

  const ponIndex = computed(() => {
    const idx = new Map()
    for (const olt of allOlts.value) for (const p of olt.pons || []) idx.set(ponKey(olt.device_id, p.pon_id), p)
    return idx
  })

  /** OLTs no ecrã com as PONs que passam a pílula; OLT sem PON nesse filtro sai. */
  const visibleOlts = computed(() =>
    allOlts.value
      .filter((o) => oltFilter.value === null || o.device_id === oltFilter.value)
      .map((o) => ({ ...o, pons: (o.pons || []).filter((p) => ponMatches(p, filter.value)) }))
      .filter((o) => filter.value === 'all' || o.pons.length),
  )

  function onuMatchesFilter(onu) {
    if (filter.value === 'los') return onu.reason === 'los'
    if (filter.value === 'critical') return onu.signal === 'critical'
    if (filter.value === 'occupancy') {
      const pon = ponIndex.value.get(ponKey(onu.device_id, onu.pon_id))
      return Boolean(pon) && (pon.occupancy_pct ?? 0) > OCCUPANCY_LIMIT
    }
    return true
  }

  function onuMatchesQuery(onu, q) {
    const hay = [onu.serial, onu.mac, onu.description, onu.cliente_nome, onu.login_radius, onu.caixa_cto]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    return hay.includes(q)
  }

  const visibleOnus = computed(() => {
    const q = query.value.trim().toLowerCase()
    const sel = selectedPon.value
    const scoped = sel !== null || oltFilter.value !== null
    return (data.value?.onus || []).filter((o) => {
      if (sel !== null && ponKey(o.device_id, o.pon_id) !== sel) return false
      if (sel === null && oltFilter.value !== null && o.device_id !== oltFilter.value) return false
      if (!onuMatchesFilter(o)) return false
      if (q && !onuMatchesQuery(o, q)) return false
      if (!scoped && filter.value === 'all' && !q && o.severity_rank > PROBLEM_RANK) return false
      return true
    })
  })

  const tableScope = computed(() => {
    if (selectedPon.value !== null) {
      const pon = ponIndex.value.get(selectedPon.value)
      return pon ? pon.label : 'PON'
    }
    if (oltFilter.value !== null) return allOlts.value.find((o) => o.device_id === oltFilter.value)?.name || 'OLT'
    if (filter.value === 'all' && !query.value.trim()) return 'ONUs com problema'
    return 'ONUs'
  })

  function togglePon(deviceId, ponId) {
    const key = ponKey(deviceId, ponId)
    selectedPon.value = selectedPon.value === key ? null : key
  }

  // A PON selecionada tem de continuar no ecrã; trocar de OLT ou de filtro que a esconde desmarca.
  watch([oltFilter, filter, data], () => {
    if (selectedPon.value === null) return
    const stillVisible = visibleOlts.value.some((o) =>
      o.pons.some((p) => ponKey(o.device_id, p.pon_id) === selectedPon.value),
    )
    if (!stillVisible) selectedPon.value = null
  })

  function stop() {
    if (timer) clearInterval(timer)
    timer = null
  }

  onMounted(() => {
    load()
    if (autoRefresh) timer = setInterval(load, REFRESH_MS)
  })
  onBeforeUnmount(stop)

  return {
    data,
    loading,
    error,
    oltFilter,
    filter,
    query,
    selectedPon,
    allOlts,
    thresholds,
    totals,
    zabbix,
    visibleOlts,
    visibleOnus,
    tableScope,
    load,
    togglePon,
    stop,
  }
}
