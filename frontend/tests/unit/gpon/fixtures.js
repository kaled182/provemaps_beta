/** Payload do contrato EV-0095 (GET /api/v1/monitoring/gpon/) para os testes do ecrã. */
import { vi } from 'vitest'
export const NOW = Date.parse('2026-11-24T02:05:00Z')

const pon = (over) => ({
  pon_id: '9/14', label: 'PON 9/14', status: 'up', capacity: 128,
  onus_provisioned: 12, onus_online: 10, occupancy_pct: 9.4, rx_avg_dbm: -21.3,
  los: 0, dying_gasp: 0, signal_warning: 0, signal_critical: 0,
  collective_drop: false, severity: 'normal', ...over,
})

const onu = (over) => ({
  id: 1, device_id: 22, olt_name: 'ZTE - OLT BRV C300', pon_id: '9/14', onu_index: 1,
  serial: 'ZYXE0000', mac: null, description: null,
  status: 'online', reason: null, reason_label: null,
  rx_onu_dbm: null, rx_olt_dbm: -20.0, signal: 'normal', distance_m: 1854,
  status_since: '2026-11-24T01:50:00Z', status_since_is_first_seen: false, last_seen: '2026-11-24T02:00:00Z',
  cliente_nome: null, login_radius: null, caixa_cto: null, severity_rank: 6, has_history: true, ...over,
})

export function payload(over = {}) {
  return {
    collected_at: '2026-11-24T02:00:00Z', zabbix_ok: true, zabbix_error: null,
    thresholds: { warning: -24.0, critical: -27.5 },
    capacity: { gpon: 128, epon: 64 },
    totals: {
      olts: 9, olts_online: 7, olts_offline: 2, pons: 30,
      onus_provisioned: 400, onus_online: 140, onus_offline: 60, onus_unknown: 200,
      signal_warning: 12, signal_critical: 5, los: 3, dying_gasp: 10, pons_collective_drop: 0,
    },
    olts: [
      {
        device_id: 22, name: 'ZTE - OLT BRV C300', vendor: 'zte', technology: 'gpon', model: 'C300',
        ip: '10.0.0.1', site_name: 'BRV', status: 'online', collection_ok: true,
        cpu_pct: 12.0, temperature_c: null, onus_total: 122, onus_online: 97,
        pons: [
          pon({ pon_id: '9/14', label: 'PON 9/14', los: 3, collective_drop: true, severity: 'critical' }),
          pon({ pon_id: '9/15', label: 'PON 9/15', signal_warning: 4, severity: 'warning', rx_avg_dbm: null }),
          pon({ pon_id: '9/16', label: 'PON 9/16', onus_provisioned: 120, occupancy_pct: 93.8, severity: 'warning' }),
        ],
      },
      {
        device_id: 11, name: 'VSOL - OLT NBR', vendor: 'vsol', technology: 'epon', model: 'V1600D',
        ip: '10.0.0.2', site_name: 'NBR', status: 'online', collection_ok: false,
        cpu_pct: null, temperature_c: 41.0, onus_total: 10, onus_online: 0,
        pons: [pon({ pon_id: '1', label: 'PON 1', capacity: 64, signal_critical: 1, severity: 'warning' })],
      },
    ],
    onus: [
      onu({ id: 501, onu_index: 1, serial: 'ZYXLOS01', status: 'offline', reason: 'los', reason_label: 'LOS', rx_olt_dbm: null, signal: null, severity_rank: 0 }),
      onu({ id: 502, onu_index: 2, serial: 'ZYXLOS02', status: 'offline', reason: 'los', reason_label: 'LOSi', rx_olt_dbm: null, signal: null, severity_rank: 0 }),
      onu({ id: 601, device_id: 11, olt_name: 'VSOL - OLT NBR', pon_id: '1', onu_index: 3, serial: null, mac: 'aa:bb:cc:00:00:01', description: 'Cliente Maria', rx_onu_dbm: -28.1, rx_olt_dbm: null, signal: 'critical', severity_rank: 1, cliente_nome: 'Maria Souza' }),
      onu({ id: 503, pon_id: '9/15', onu_index: 4, serial: 'ZYXWARN1', rx_olt_dbm: -25.0, signal: 'warning', severity_rank: 2 }),
      onu({ id: 504, pon_id: '9/15', onu_index: 5, serial: 'ZYXDG001', status: 'offline', reason: 'dying_gasp', reason_label: 'Dying Gasp', signal: null, rx_olt_dbm: null, severity_rank: 3, status_since_is_first_seen: true }),
      onu({ id: 505, pon_id: '9/16', onu_index: 6, serial: 'ZYXUNK01', status: 'unknown', signal: null, rx_olt_dbm: null, severity_rank: 5, distance_m: null, status_since: null, has_history: false }),
      onu({ id: 506, pon_id: '9/16', onu_index: 7, serial: 'ZYXOK001', severity_rank: 6 }),
    ],
    ...over,
  }
}

export const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })

export function mockFetch(body, history) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
    if (url.startsWith('/api/v1/monitoring/gpon/onus/')) return ok(history || { onu_id: 1, unit: 'dBm', label: 'RX na OLT', points: [], zabbix_ok: true, zabbix_error: null })
    if (url.startsWith('/api/v1/monitoring/gpon/')) return ok(body)
    return ok({})
  })
}
