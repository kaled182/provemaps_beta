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
 * - slot selecionado (chassi, EV-0101) → as ONUs da OLT com pon_id «<slot>/…»;
 * - senão OLT escolhida → as ONUs dessa OLT;
 * - senão, com filtro (pílula) ou busca → todas as que casam;
 * - senão → só as com problema (severity_rank ≤ 4).
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import { mostCriticalPon } from '@/components/Gpon/chassisLed'

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

const BAND_LABEL = { normal: 'bom', warning: 'em atenção', critical: 'crítico' }
export const slotKey = (deviceId, slot) => `${deviceId}:${slot}`

/** Chave do localStorage da vista do ecrã (EV-0101): 'chassis' | 'grid'. */
export const VIEW_KEY = 'provemaps.gpon.view'

const splitKey = (key) => {
  const i = key.indexOf(':')
  return [Number(key.slice(0, i)), key.slice(i + 1)]
}

/** Estado do Zabbix para o badge do cabeçalho: ok | down | stale. */
export function zabbixState(data, now = Date.now()) {
  if (!data) return null
  if (!data.zabbix_ok) return 'down'
  const t = data.collected_at ? new Date(data.collected_at).getTime() : NaN
  if (!Number.isFinite(t) || now - t > STALE_MS) return 'stale'
  return 'ok'
}

export const VENDOR_LABELS = { zte: 'ZTE', vsol: 'VSOL' }
export const NO_POP = '__sem_pop__'

/**
 * Totais do recorte (EV-0105): as mesmas contas do backend (`gpon_overview` → `totals`), sobre as
 * OLTs e ONUs filtradas. Sem recorte usa-se o `totals` do payload, tal e qual.
 */
export function computeTotals(olts, onus) {
  const pons = olts.flatMap((o) => o.pons || [])
  const count = (list, pred) => list.reduce((n, x) => n + (pred(x) ? 1 : 0), 0)
  return {
    olts: olts.length,
    olts_online: count(olts, (o) => o.status === 'online'),
    olts_offline: count(olts, (o) => o.status === 'offline'),
    pons: pons.length,
    onus_provisioned: onus.length,
    onus_online: count(onus, (o) => o.status === 'online'),
    onus_offline: count(onus, (o) => o.status === 'offline'),
    onus_unknown: count(onus, (o) => o.status === 'unknown'),
    signal_warning: count(onus, (o) => o.signal === 'warning'),
    signal_critical: count(onus, (o) => o.signal === 'critical'),
    los: count(onus, (o) => o.reason === 'los'),
    dying_gasp: count(onus, (o) => o.reason === 'dying_gasp'),
    pons_collective_drop: count(pons, (p) => p.collective_drop),
  }
}

/** Filtros de recorte no endereço (?fabricante=zte&pop=…), para o link ser partilhável. */
function readUrlScope() {
  try {
    const q = new URLSearchParams(window.location.search)
    return { vendor: q.get('fabricante') || null, pop: q.get('pop') || null }
  } catch {
    return { vendor: null, pop: null }
  }
}

function writeUrlScope(vendor, pop) {
  try {
    const url = new URL(window.location.href)
    for (const [k, v] of [['fabricante', vendor], ['pop', pop]]) {
      if (v) url.searchParams.set(k, v)
      else url.searchParams.delete(k)
    }
    window.history.replaceState(window.history.state, '', url.toString())
  } catch {
    /* sem history (testes/SSR): o filtro funciona na mesma */
  }
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
  const initialScope = readUrlScope()
  const vendorFilter = ref(initialScope.vendor)
  const popFilter = ref(initialScope.pop)
  const filter = ref('all')
  const query = ref('')
  const selectedPon = ref(null)
  const selectedSlot = ref(null)
  /**
   * EV-0107: faixa de sinal escolhida no histograma ({ key: PON, band }). Só vale para a PON
   * em que foi escolhida — selecionar outra porta deixa-a sem efeito, sem `watch` a limpar.
   */
  const bandChoice = ref(null)
  const signalBand = computed(() =>
    bandChoice.value !== null && bandChoice.value.key === selectedPon.value ? bandChoice.value.band : null,
  )
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

  // EV-0105: recorte por fabricante e por POP (site da OLT).
  const popOf = (o) => o.site_name || NO_POP
  const vendors = computed(() =>
    [...new Set(allOlts.value.map((o) => o.vendor).filter(Boolean))]
      .sort()
      .map((v) => ({ value: v, label: VENDOR_LABELS[v] || v.toUpperCase() })),
  )
  const pops = computed(() => {
    const inVendor = allOlts.value.filter((o) => vendorFilter.value === null || o.vendor === vendorFilter.value)
    return [...new Set(inVendor.map(popOf))]
      .sort((a, b) => (a === NO_POP) - (b === NO_POP) || a.localeCompare(b, 'pt-BR'))
      .map((p) => ({ value: p, label: p === NO_POP ? 'Sem POP' : p }))
  })
  const scopeActive = computed(() => vendorFilter.value !== null || popFilter.value !== null)
  const scopedOlts = computed(() =>
    allOlts.value.filter(
      (o) =>
        (vendorFilter.value === null || o.vendor === vendorFilter.value) &&
        (popFilter.value === null || popOf(o) === popFilter.value),
    ),
  )
  const scopedIds = computed(() => new Set(scopedOlts.value.map((o) => o.device_id)))
  const scopedOnus = computed(() =>
    scopeActive.value ? (data.value?.onus || []).filter((o) => scopedIds.value.has(o.device_id)) : data.value?.onus || [],
  )
  const totals = computed(() =>
    scopeActive.value ? computeTotals(scopedOlts.value, scopedOnus.value) : data.value?.totals || {},
  )

  // Um POP que não existe no fabricante escolhido cai; a OLT escolhida fora do recorte também.
  watch([vendorFilter, data], () => {
    if (popFilter.value !== null && data.value && !pops.value.some((p) => p.value === popFilter.value)) popFilter.value = null
  })
  watch([vendorFilter, popFilter, data], () => {
    if (oltFilter.value !== null && data.value && !scopedIds.value.has(oltFilter.value)) oltFilter.value = null
  })
  watch([vendorFilter, popFilter], ([v, p]) => writeUrlScope(v, p))
  const zabbix = computed(() => zabbixState(data.value))

  const ponIndex = computed(() => {
    const idx = new Map()
    for (const olt of allOlts.value) for (const p of olt.pons || []) idx.set(ponKey(olt.device_id, p.pon_id), p)
    return idx
  })

  /** OLTs no ecrã com as PONs que passam a pílula; OLT sem PON nesse filtro sai. */
  const visibleOlts = computed(() =>
    scopedOlts.value
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
    const slot = selectedSlot.value === null ? null : splitKey(selectedSlot.value)
    const scoped = sel !== null || slot !== null || oltFilter.value !== null
    return scopedOnus.value.filter((o) => {
      if (sel !== null && ponKey(o.device_id, o.pon_id) !== sel) return false
      if (slot !== null && (o.device_id !== slot[0] || !String(o.pon_id).startsWith(`${slot[1]}/`))) return false
      if (sel === null && slot === null && oltFilter.value !== null && o.device_id !== oltFilter.value) return false
      if (!onuMatchesFilter(o)) return false
      if (sel !== null && signalBand.value !== null && o.signal !== signalBand.value) return false
      if (q && !onuMatchesQuery(o, q)) return false
      if (!scoped && filter.value === 'all' && !q && o.severity_rank > PROBLEM_RANK) return false
      return true
    })
  })

  const tableScope = computed(() => {
    if (selectedPon.value !== null) {
      const pon = ponIndex.value.get(selectedPon.value)
      const label = pon ? pon.label : `PON ${splitKey(selectedPon.value)[1]}`
      return signalBand.value === null ? label : `${label} · sinal ${BAND_LABEL[signalBand.value]}`
    }
    if (selectedSlot.value !== null) return `Slot ${splitKey(selectedSlot.value)[1]}`
    if (oltFilter.value !== null) return allOlts.value.find((o) => o.device_id === oltFilter.value)?.name || 'OLT'
    if (scopeActive.value && filter.value === 'all' && !query.value.trim()) return 'ONUs com problema no recorte'
    if (filter.value === 'all' && !query.value.trim()) return 'ONUs com problema'
    return 'ONUs'
  })

  function togglePon(deviceId, ponId) {
    bandChoice.value = null
    const key = ponKey(deviceId, ponId)
    selectedPon.value = selectedPon.value === key ? null : key
    if (selectedPon.value !== null) selectedSlot.value = null
  }

  /** Seleção de placa do chassi (EV-0101); exclusiva com a de PON. */
  function toggleSlot(deviceId, slot) {
    const key = slotKey(deviceId, slot)
    selectedSlot.value = selectedSlot.value === key ? null : key
    if (selectedSlot.value !== null) selectedPon.value = null
  }

  /**
   * O que pode continuar selecionado: as PONs que passam o filtro e, sem pílula, também as
   * portas e placas do chassi (porta sem ONUs é clicável no chassi).
   */
  function selectableKeys() {
    const pons = new Set()
    const slots = new Set()
    for (const o of visibleOlts.value) {
      for (const p of o.pons) {
        pons.add(ponKey(o.device_id, p.pon_id))
        const slash = String(p.pon_id).indexOf('/')
        if (slash > 0) slots.add(slotKey(o.device_id, String(p.pon_id).slice(0, slash)))
      }
      if (filter.value !== 'all') continue
      const ch = o.chassis || {}
      for (const port of ch.ports || []) pons.add(ponKey(o.device_id, port.port_id))
      for (const s of ch.slots || []) {
        slots.add(slotKey(o.device_id, s.slot))
        for (const port of s.ports || []) pons.add(ponKey(o.device_id, port.port_id))
      }
    }
    return { pons, slots }
  }

  // A seleção tem de continuar no ecrã; trocar de OLT ou de filtro que a esconde desmarca.
  watch([oltFilter, vendorFilter, popFilter, filter, data], () => {
    if (selectedPon.value === null && selectedSlot.value === null) return
    const keys = selectableKeys()
    if (selectedPon.value !== null && !keys.pons.has(selectedPon.value)) selectedPon.value = null
    if (selectedSlot.value !== null && !keys.slots.has(selectedSlot.value)) selectedSlot.value = null
  })

  function clearSelection() {
    bandChoice.value = null
    selectedPon.value = null
    selectedSlot.value = null
  }

  /**
   * EV-0107: clique numa faixa do histograma — seleciona a PON (se era a pré-visualização) e
   * filtra a tabela por essa faixa; a mesma faixa outra vez limpa o filtro.
   */
  function toggleSignalBand(deviceId, ponId, band) {
    const key = ponKey(deviceId, ponId)
    if (selectedPon.value !== key) {
      selectedSlot.value = null
      selectedPon.value = key
    }
    bandChoice.value = signalBand.value === band ? null : { key, band }
  }

  /**
   * EV-0106: com UMA OLT em foco (escolhida no seletor, ou a única do recorte fabricante/POP),
   * seleciona a PON mais crítica dela ao abrir e ao trocar — o inspetor nunca começa vazio e a
   * tabela mostra logo essa PON. Só reage à troca de OLT (não a cada atualização de 60 s), para
   * não desfazer o «Todas as portas» nem a escolha do operador.
   */
  const focusOltId = computed(() => {
    if (oltFilter.value !== null) return oltFilter.value
    return scopedOlts.value.length === 1 ? scopedOlts.value[0].device_id : null
  })
  watch(
    [focusOltId, () => data.value !== null],
    ([id, loaded], [prevId, prevLoaded]) => {
      if (id === null || !loaded || (id === prevId && prevLoaded)) return
      const olt = allOlts.value.find((o) => o.device_id === id)
      const ponId = mostCriticalPon(olt?.pons)
      selectedSlot.value = null
      selectedPon.value = ponId === null ? null : ponKey(id, ponId)
    },
  )

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
    vendorFilter,
    popFilter,
    vendors,
    pops,
    scopedOlts,
    filter,
    query,
    selectedPon,
    selectedSlot,
    allOlts,
    thresholds,
    totals,
    zabbix,
    visibleOlts,
    visibleOnus,
    tableScope,
    load,
    togglePon,
    toggleSlot,
    clearSelection,
    signalBand,
    toggleSignalBand,
    focusOltId,
    stop,
  }
}
