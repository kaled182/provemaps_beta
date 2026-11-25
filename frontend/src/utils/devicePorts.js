/**
 * Portas do modal de Dispositivo (EV-0066).
 *
 * Limiar igual ao backend (`_classify_optical_thresholds`: `<=`) e leitura com
 * mais de 10 min = velha (`OPTICAL_STALE_AFTER_SECONDS`), que não conta como
 * estado atual. Sem leitura → «—», nunca 0.
 * @module devicePorts
 */

export const OPTICAL_STALE_AFTER_MS = 10 * 60 * 1000
export const DEFAULT_THRESHOLDS = Object.freeze({ warning: -24, critical: -27 })

const toNum = (v) => {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

/** Limiares de `/setup_app/api/config/`; valor em falta ou inválido → omissão. */
export function thresholdsFromConfig(cfg = {}) {
  const warning = toNum(cfg.OPTICAL_RX_WARNING_THRESHOLD)
  const critical = toNum(cfg.OPTICAL_RX_CRITICAL_THRESHOLD)
  return {
    warning: warning ?? DEFAULT_THRESHOLDS.warning,
    critical: critical ?? DEFAULT_THRESHOLDS.critical,
  }
}

/** Remove os prefixos que o Zabbix põe nas descrições. */
export function normalizeDescription(text) {
  if (!text || typeof text !== 'string') return ''
  return text
    .trim()
    .replace(/^Status\s+Operacional\s+da\s+(?:Porta|Interface)\s*/i, '')
    .replace(/\s+-\s*$/i, '')
}

/** Porta da API (`/api/v1/ports/`) → forma do modal. */
export function normalizePort(raw, now = Date.now()) {
  const rx = toNum(raw.last_rx_power)
  const tx = toNum(raw.last_tx_power)
  const checked = raw.last_optical_check ? Date.parse(raw.last_optical_check) : NaN
  const hasReading = rx !== null || tx !== null
  return {
    ...raw,
    description: normalizeDescription(raw.description ?? raw.notes ?? ''),
    connected_cable: raw.cable_id ? { id: raw.cable_id, name: raw.cable_name || '' } : null,
    optical_rx_power: rx,
    optical_tx_power: tx,
    lastCheck: Number.isFinite(checked) ? checked : null,
    stale: hasReading && Number.isFinite(checked) && now - checked > OPTICAL_STALE_AFTER_MS,
  }
}

/** Nível de um valor dBm: normal | warning | critical | null (sem valor). */
export function levelOf(value, th = DEFAULT_THRESHOLDS) {
  if (value === null || value === undefined) return null
  if (value <= th.critical) return 'critical'
  if (value <= th.warning) return 'warning'
  return 'normal'
}

/** Estado da porta para o selo: decide o RX fresco. */
export function portState(port, th = DEFAULT_THRESHOLDS) {
  if (port.optical_rx_power === null && port.optical_tx_power === null) {
    return port.connected_cable ? { key: 'linked', label: 'Conectada' } : { key: 'none', label: 'Sem leitura' }
  }
  if (port.stale) return { key: 'stale', label: 'Leitura antiga' }
  const level = levelOf(port.optical_rx_power, th)
  if (level === 'critical') return { key: 'critical', label: 'Sinal crítico' }
  if (level === 'warning') return { key: 'warning', label: 'Atenção' }
  return { key: 'normal', label: 'Normal' }
}

/** dBm com 2 casas ou «—». */
export function formatDbm(value) {
  return value === null || value === undefined ? '—' : value.toFixed(2)
}

/** «Em uso» = com leitura óptica ou cabo; depois a busca por nome/descrição. */
export function filterPorts(ports, { onlyInUse = true, query = '' } = {}) {
  let out = onlyInUse
    ? ports.filter((p) => p.optical_rx_power !== null || p.optical_tx_power !== null || p.connected_cable)
    : ports
  const q = query.trim().toLowerCase()
  if (q) out = out.filter((p) => p.name?.toLowerCase().includes(q) || p.description?.toLowerCase().includes(q))
  return out
}

/** Pior primeiro: crítico, atenção, normal, antiga, conectada, sem leitura; depois nome. */
const ORDER = { critical: 0, warning: 1, normal: 2, stale: 3, linked: 4, none: 5 }
export function sortPorts(ports, th = DEFAULT_THRESHOLDS) {
  return [...ports].sort(
    (a, b) =>
      ORDER[portState(a, th).key] - ORDER[portState(b, th).key] ||
      String(a.name).localeCompare(String(b.name), 'pt-BR', { numeric: true }),
  )
}

/** CSV (todas as células entre aspas, aspas internas duplicadas). */
export function portsToCsv(ports, th = DEFAULT_THRESHOLDS) {
  const headers = ['Porta', 'Descrição', 'Estado', 'RX (dBm)', 'TX (dBm)', 'Última leitura', 'Cabo conectado']
  const rows = ports.map((p) => [
    p.name || '',
    p.description || '',
    portState(p, th).label,
    p.optical_rx_power === null ? '' : p.optical_rx_power.toFixed(2),
    p.optical_tx_power === null ? '' : p.optical_tx_power.toFixed(2),
    p.lastCheck ? new Date(p.lastCheck).toISOString() : '',
    p.connected_cable?.name || p.connected_cable?.id || '',
  ])
  const cell = (c) => `"${String(c).replace(/"/g, '""')}"`
  return [headers, ...rows].map((r) => r.map(cell).join(',')).join('\n')
}
