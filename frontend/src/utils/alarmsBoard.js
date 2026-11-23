/**
 * Alarmes (EV-0059): junta os incidentes de fibra (`/api/v1/fiber-cables/alarm-board/`)
 * com os equipamentos offline (estado Zabbix) e formata durações.
 * Equipamento offline não tem histórico de abertura: duração «—», nunca estimada.
 * @module alarmsBoard
 */

export const SEVERITY_LABEL = Object.freeze({ critical: 'Crítico', attention: 'Atenção' })

/** 187_000 s → «2 d 3 h»; 5_400 → «1 h 30 min»; 90 → «1 min»; null → «—». */
export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || Number.isNaN(Number(seconds))) return '—'
  const s = Math.max(0, Math.floor(Number(seconds)))
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (d) return h ? `${d} d ${h} h` : `${d} d`
  if (h) return m ? `${h} h ${m} min` : `${h} h`
  return `${Math.max(m, s ? 1 : 0)} min`
}

/**
 * @param {object|null} board resposta do alarm-board
 * @param {object[]} offlineDevices `[{id, name, site_name, center}]`
 */
export function buildAlarmRows(board, offlineDevices = []) {
  const cables = (board?.active || []).map((a) => ({
    key: `cable-${a.cable_id}`,
    kind: 'cable',
    id: a.cable_id,
    name: a.cable_name,
    severity: a.severity,
    measured: a.rx,
    measuredSide: a.rx_side,
    openedAt: a.opened_at,
    durationSeconds: a.duration_seconds,
    center: a.center || null,
  }))
  const devices = offlineDevices.map((d) => ({
    key: `device-${d.id}`,
    kind: 'device',
    id: d.id,
    name: d.name,
    site: d.site_name || null,
    severity: 'critical',
    measured: null,
    openedAt: null,
    durationSeconds: null,
    center: d.center || null,
  }))
  const rows = [...cables, ...devices]
  const rank = { critical: 2, attention: 1 }
  return rows.sort(
    (a, b) =>
      (rank[b.severity] || 0) - (rank[a.severity] || 0) ||
      (b.durationSeconds ?? -1) - (a.durationSeconds ?? -1) ||
      a.name.localeCompare(b.name, 'pt-BR'),
  )
}

export function groupBySeverity(rows) {
  return ['critical', 'attention']
    .map((severity) => ({ severity, label: SEVERITY_LABEL[severity], rows: rows.filter((r) => r.severity === severity) }))
    .filter((g) => g.rows.length)
}
