/**
 * EV-0109 — tendência 24 h do RX médio da PON (médias horárias do Zabbix + ponto atual)
 * e tráfego da porta; VSOL sem tráfego por PON; Zabbix fora; formatBps.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('chart.js/auto', () => ({
  default: vi.fn(function FakeChart(el, config) {
    this.data = config.data
    this.options = config.options
    this.destroy = vi.fn()
    this.update = vi.fn()
  }),
}))

import Chart from 'chart.js/auto'
import PonTrend from '@/components/Gpon/PonTrend.vue'
import { formatBps } from '@/utils/ptBrFormat'

const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
const trend = (over = {}) => ({
  device_id: 24,
  pon_id: '12/8',
  hours: 24,
  rx: [
    { t: '2026-11-24T11:00:00Z', rx_avg_dbm: -24.9, rx_worst_dbm: -30.3, onus: 49 },
    { t: '2026-11-24T12:00:00Z', rx_avg_dbm: -24.8, rx_worst_dbm: -29.8, onus: 49 },
  ],
  traffic: { available: true, in_bps: 8802480, out_bps: 96842704, at: '2026-11-24T13:53:55Z', stale: false, in: [], out: [] },
  zabbix_ok: true,
  zabbix_error: null,
  ...over,
})

afterEach(() => {
  vi.restoreAllMocks()
  Chart.mockClear()
})

describe('PonTrend', () => {
  it('pede a tendência da PON e desenha RX médio (com o ponto atual) e pior RX em modo compacto', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok(trend()))
    const w = mount(PonTrend, { props: { deviceId: 24, ponId: '12/8', currentRx: -24.6, thresholds: { warning: -24, critical: -27 } } })
    await flushPromises()
    expect(spy.mock.calls[0][0]).toBe('/api/v1/monitoring/gpon/pon-trend/?device=24&pon=12%2F8')
    const cfg = Chart.mock.calls[0][1]
    expect(cfg.data.datasets[0].label).toBe('RX médio')
    expect(cfg.data.datasets[0].data).toHaveLength(3) // 2 horas + coleta atual
    expect(cfg.data.datasets[0].data.at(-1).y).toBe(-24.6)
    expect(cfg.data.datasets[1].label).toBe('Pior RX (hora)')
    expect(cfg.options.plugins.legend.display).toBe(false)
    expect(cfg.options.scales.x.display).toBe(false)
    expect(w.get('[data-testid="pon-traffic"]').text()).toBe('↓ 8,8 Mbps · ↑ 96,8 Mbps')
  })

  it('VSOL: sem tendência e sem tráfego por PON dizem isso', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      ok(trend({ rx: [], traffic: { available: false, in_bps: null, out_bps: null, at: null, stale: false, in: [], out: [] } })),
    )
    const w = mount(PonTrend, { props: { deviceId: 11, ponId: '0/1', currentRx: null } })
    await flushPromises()
    expect(w.find('[data-testid="pon-trend-empty"]').exists()).toBe(true)
    expect(w.get('[data-testid="pon-traffic"]').text()).toBe('tráfego da PON indisponível')
    expect(Chart).not.toHaveBeenCalled()
  })

  it('Zabbix fora é avisado', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok(trend({ rx: [], zabbix_ok: false, zabbix_error: 'x' })))
    const w = mount(PonTrend, { props: { deviceId: 24, ponId: '12/8' } })
    await flushPromises()
    expect(w.find('[data-testid="pon-trend-zabbix"]').exists()).toBe(true)
  })
})

describe('formatBps', () => {
  it('escolhe a unidade e usa vírgula decimal', () => {
    expect(formatBps(950_000)).toBe('950 kbps')
    expect(formatBps(8_802_480)).toBe('8,8 Mbps')
    expect(formatBps(1_234_000_000)).toBe('1,2 Gbps')
    expect(formatBps(null)).toBe('—')
  })
})
