/**
 * Ativos (POPs & rede) — EV-0058: junta equipamentos, estado Zabbix, métricas e
 * portas ópticas com leitura numa linha por equipamento, e calcula os KPIs.
 * Regra: nada estimado — sem métrica é «—»; valor manual vem marcado como manual.
 * @module assetsTable
 */
import { foldText } from '@/composables/useNavSections'

export const CPU_ALERT_PERCENT = 90

const STATUS_ORDER = { offline: 4, unknown: 3, disabled: 2, online: 1 }

/** Portas ópticas com leitura fresca, por device_id, a partir do optical-summary. */
export function opticalPortsByDevice(summary) {
  const map = new Map()
  for (const cable of summary?.cables || []) {
    for (const end of [cable.origin, cable.destination]) {
      if (!end || end.device_id === null || end.device_id === undefined) continue
      const entry = map.get(end.device_id) || { withReading: 0, total: 0 }
      entry.total += 1
      if (end.rx !== null && end.rx !== undefined && !end.stale) entry.withReading += 1
      map.set(end.device_id, entry)
    }
  }
  return map
}

/**
 * @param {object[]} devices `/api/v1/devices/`
 * @param {{statuses?: object, metrics?: object, optical?: Map, sites?: Map}} sources
 */
export function buildAssetRows(devices, { statuses = {}, metrics = {}, optical = new Map(), sites = new Map() } = {}) {
  return (devices || []).map((d) => {
    const m = metrics[String(d.id)] || {}
    const site = sites.get(d.site) || null
    const optic = optical.get(d.id) || null
    return {
      id: d.id,
      name: d.name,
      vendorModel: [d.vendor, d.model].filter(Boolean).join(' · '),
      siteName: d.site_name || site?.name || null,
      ip: d.primary_ip || null,
      status: statuses[String(d.id)] || 'unknown',
      uptime: m.uptime_human || null,
      cpu: m.cpu ?? null,
      cpuSource: m.cpu_source || null,
      lastCollected: m.last_collected || null,
      opticalWithReading: optic ? optic.withReading : null,
      opticalTotal: optic ? optic.total : null,
      center: site && site.lat !== null && site.lng !== null ? { lat: site.lat, lng: site.lng } : null,
    }
  })
}

/** KPIs: CPU só conta quando é medida pelo Zabbix (manual não é alerta). */
export function computeAssetKpis(rows) {
  const total = rows.length
  const online = rows.filter((r) => r.status === 'online').length
  const offline = rows.filter((r) => r.status === 'offline').length
  const known = rows.filter((r) => r.status === 'online' || r.status === 'offline').length
  const measuredCpu = rows.filter((r) => r.cpuSource === 'zabbix' && r.cpu !== null)
  return {
    total,
    online,
    offline,
    availability: known ? Math.round((online / known) * 1000) / 10 : null,
    cpuMeasured: measuredCpu.length,
    cpuAlerts: measuredCpu.filter((r) => r.cpu >= CPU_ALERT_PERCENT).length,
  }
}

export const ASSET_FILTERS = Object.freeze([
  { id: 'all', label: 'Todos' },
  { id: 'offline', label: 'Offline' },
  { id: 'online', label: 'Online' },
  { id: 'cpu', label: `CPU ≥ ${CPU_ALERT_PERCENT}%` },
])

/** Filtra e ordena: offline primeiro, depois desconhecido; dentro, por nome. */
export function filterAndSortAssets(rows, { filter = 'all', query = '' } = {}) {
  const q = foldText(query).trim()
  return rows
    .filter((r) => {
      if (filter === 'offline') return r.status === 'offline'
      if (filter === 'online') return r.status === 'online'
      if (filter === 'cpu') return r.cpuSource === 'zabbix' && r.cpu !== null && r.cpu >= CPU_ALERT_PERCENT
      return true
    })
    .filter((r) => !q || foldText([r.name, r.vendorModel, r.siteName, r.ip].filter(Boolean).join(' ')).includes(q))
    .slice()
    .sort((a, b) => (STATUS_ORDER[b.status] ?? 0) - (STATUS_ORDER[a.status] ?? 0) || a.name.localeCompare(b.name, 'pt-BR'))
}
