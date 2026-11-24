/**
 * Estado dos equipamentos no modal de Site (EV-0065).
 *
 * Antes o estado era adivinhado: sem uptime → «offline», CPU ≥ 70 % → «atenção»,
 * sem perguntar ao Zabbix se o host estava disponível e contando CPU *manual*
 * como medida. Agora: disponibilidade real (`devices/zabbix-status/`) decide
 * online/offline/sem estado; atenção/crítico só por CPU/memória **medidas**.
 * @module siteDevices
 */

export const METRIC_WARNING = 70
export const METRIC_CRITICAL = 90

/**
 * @param {string|undefined} availability online | offline | unknown | disabled
 * @param {{cpu?: number|null, cpu_source?: string|null, memory?: number|null, memory_source?: string|null}} m
 * @returns {'online'|'warning'|'critical'|'offline'|'unknown'}
 */
export function deriveDeviceStatus(availability, m = {}) {
  if (availability === 'offline') return 'offline'
  if (availability !== 'online') return 'unknown'
  const measured = [
    m.cpu_source === 'zabbix' ? m.cpu : null,
    m.memory_source === 'zabbix' ? m.memory : null,
  ].filter((v) => typeof v === 'number')
  const worst = measured.length ? Math.max(...measured) : null
  if (worst !== null && worst >= METRIC_CRITICAL) return 'critical'
  if (worst !== null && worst >= METRIC_WARNING) return 'warning'
  return 'online'
}

/** Contagens dos KPIs do site. */
export function countDeviceStatuses(devices) {
  const counts = { online: 0, warning: 0, critical: 0, offline: 0, unknown: 0 }
  for (const d of devices || []) counts[d.status in counts ? d.status : 'unknown'] += 1
  return counts
}

/** Pior estado do site, para a cor do ícone do cabeçalho do modal. */
export function siteHeaderStatus(counts) {
  if (counts.critical || counts.offline) return 'critical'
  if (counts.warning) return 'attention'
  if (counts.online) return 'online'
  return 'neutral'
}

/** Barra de métrica: null quando não há valor (nunca «0 %» inventado). */
export function metricBar(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return null
  const pct = Math.max(0, Math.min(100, value))
  const level = pct >= METRIC_CRITICAL ? 'critical' : pct >= METRIC_WARNING ? 'warning' : 'normal'
  return { pct, level, label: `${Math.round(value)}%` }
}

export const DEVICE_STATUS_LABELS = {
  online: 'Online',
  warning: 'Atenção',
  critical: 'Crítico',
  offline: 'Offline',
  unknown: 'Sem estado',
}

/** Segundos → «3d 4h» / «5h 12m» / «7m»; null quando não há valor. */
export function formatUptimeSeconds(seconds) {
  if (typeof seconds !== 'number' || !(seconds > 0)) return null
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

const num = (v) => (typeof v === 'number' && !Number.isNaN(v) ? v : null)

/**
 * Monta o equipamento do modal a partir do inventário (`/api/v1/devices/`),
 * da disponibilidade Zabbix e das métricas em lote. Sem métrica → null, nunca 0.
 */
export function buildSiteDevice(raw, availability, m = {}) {
  const device = {
    id: raw.id,
    name: raw.name || 'Dispositivo sem nome',
    type: raw.group_name || 'Dispositivo',
    ip: raw.primary_ip || null,
    zabbixHostId: raw.zabbix_hostid || null,
    availability: availability || 'unknown',
    cpu: num(m.cpu),
    cpuSource: m.cpu_source || null,
    memory: num(m.memory),
    memorySource: m.memory_source || null,
    uptime: num(m.uptime_seconds),
    uptimeHuman: m.uptime_human || null,
  }
  device.status = deriveDeviceStatus(device.availability, {
    cpu: device.cpu,
    cpu_source: device.cpuSource,
    memory: device.memory,
    memory_source: device.memorySource,
  })
  return device
}

/** Atualização do WebSocket: só disponibilidade e uptime (o canal não traz CPU/memória). */
export function applyRealtimeHost(device, host) {
  if (host.status === 'online' || host.status === 'offline') device.availability = host.status
  const up = num(host.raw?.uptime_seconds)
  if (up !== null && up > 0) {
    device.uptime = up
    device.uptimeHuman = host.raw?.uptime_human || null
  }
  device.status = deriveDeviceStatus(device.availability, {
    cpu: device.cpu,
    cpu_source: device.cpuSource,
    memory: device.memory,
    memory_source: device.memorySource,
  })
  return device
}

/**
 * EV-0111: indicador operacional do card no modal de Site, a partir dos resumos
 * `olt-summary` (GPON) e `ports-summary` (inventário). Sem resumo → null (o card não
 * inventa «0 ONUs» nem «0 portas»).
 *  - OLT: «282/347 ONUs» + alertas ópticos (críticas/atenção).
 *  - Resto: «N portas em uso» + pior RX fresco com o nível pelos limiares.
 */
export function deviceIndicator(device) {
  const olt = device?.olt
  if (olt) {
    const alerts = []
    if (olt.signal_critical) alerts.push({ level: 'critical', text: `${olt.signal_critical} crít.` })
    if (olt.signal_warning) alerts.push({ level: 'warning', text: `${olt.signal_warning} atenção` })
    return {
      kind: 'olt',
      badge: `OLT ${String(olt.technology || '').toUpperCase()}`.trim(),
      main: olt.onus_total ? `${olt.onus_online}/${olt.onus_total} ONUs` : 'sem ONUs coletadas',
      alerts,
    }
  }
  const ports = device?.ports
  if (!ports) return null
  return {
    kind: 'ports',
    badge: null,
    main: `${ports.ports_in_use} de ${ports.ports_total} portas em uso`,
    worstRx: ports.worst_rx_dbm,
    worstLevel: ports.worst_rx_level,
    alerts: [],
  }
}
