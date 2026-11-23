/**
 * EV-0059 — Alarmes: incidentes de fibra + equipamentos offline; durações e MTTR
 * formatados; sem histórico de abertura, «—» (nunca estimado).
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { defineComponent, h } from 'vue'
import { buildAlarmRows, formatDuration, groupBySeverity } from '@/utils/alarmsBoard'

const BOARD = {
  active: [
    { cable_id: 7, cable_name: 'ELAGRO-SANTA TEREZINHA', severity: 'critical', opened_at: '2026-10-02T12:12:00+00:00', duration_seconds: 52 * 86400 + 4 * 3600, rx: -40, rx_side: 'origin', center: { lat: -16, lng: -49 } },
    { cable_id: 9, cable_name: 'Anel Leste', severity: 'attention', opened_at: '2026-11-23T10:00:00+00:00', duration_seconds: 5400, rx: null, rx_side: null, center: null },
  ],
  resolved_24h: 2,
  mttr_seconds: 46800,
  mttr_sample: 8,
  window_days: 30,
}

afterEach(() => vi.restoreAllMocks())

describe('alarmsBoard', () => {
  it('formatDuration', () => {
    expect(formatDuration(52 * 86400 + 4 * 3600)).toBe('52 d 4 h')
    expect(formatDuration(5400)).toBe('1 h 30 min')
    expect(formatDuration(46800)).toBe('13 h')
    expect(formatDuration(90)).toBe('1 min')
    expect(formatDuration(null)).toBe('—')
  })

  it('equipamento offline é crítico sem duração; ordena por severidade e duração', () => {
    const rows = buildAlarmRows(BOARD, [{ id: 3, name: 'SW-Norte', site_name: 'POP Norte', center: null }])
    expect(rows.map((r) => r.key)).toEqual(['cable-7', 'device-3', 'cable-9'])
    expect(rows[1]).toMatchObject({ severity: 'critical', durationSeconds: null, openedAt: null })
    expect(groupBySeverity(rows).map((g) => [g.severity, g.rows.length])).toEqual([['critical', 2], ['attention', 1]])
  })
})

describe('AlarmsView', () => {
  const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })

  async function mountView({ statuses = { 1: 'online', 3: 'offline' }, zabbixError = false } = {}) {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url.startsWith('/api/v1/fiber-cables/alarm-board/')) return ok(BOARD)
      if (url.startsWith('/api/v1/devices/')) return ok({ results: [{ id: 1, name: 'OLT', site: 10 }, { id: 3, name: 'SW-Norte', site: 10, site_name: 'POP Norte' }], next: null })
      if (url.startsWith('/api/v1/sites/')) return ok({ results: [{ id: 10, latitude: '-16.5', longitude: '-49.1' }], next: null })
      if (url.startsWith('/api/v1/inventory/devices/zabbix-status/')) return ok({ statuses, ...(zabbixError ? { zabbix_error: true } : {}) })
      return Promise.reject(new Error(url))
    })
    const Stub = defineComponent({ render: () => h('div') })
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/alarmes', component: Stub }, { path: '/Network/NetworkDesign/', component: Stub }] })
    router.push('/alarmes')
    await router.isReady()
    const { default: AlarmsView } = await import('@/views/AlarmsView.vue')
    const w = mount(AlarmsView, { global: { plugins: [router] } })
    await flushPromises()
    return { w, router }
  }

  it('KPIs e grupos por severidade', async () => {
    const { w } = await mountView()
    expect(w.get('[data-testid="alarms-critical"]').text()).toBe('2')
    expect(w.get('[data-testid="alarms-attention"]').text()).toBe('1')
    expect(w.get('[data-testid="alarms-resolved"]').text()).toBe('2')
    expect(w.get('[data-testid="alarms-mttr"]').text()).toBe('13 h')
    expect(w.get('[data-testid="alarm-row-cable-7"]').text()).toContain('RX -40.00 dBm')
    expect(w.get('[data-testid="alarm-row-cable-7"]').text()).toContain('52 d 4 h')
    expect(w.get('[data-testid="alarm-row-device-3"]').text()).toContain('Equipamento offline')
    w.unmount()
  })

  it('localizar no mapa abre o Projeto de rede no ponto do cabo', async () => {
    const { w, router } = await mountView()
    await w.get('[data-testid="alarm-row-cable-7"] button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ foco: 'cable', id: '7', lat: '-16' })
    expect(w.get('[data-testid="alarm-row-cable-9"] button').attributes('disabled')).toBeDefined()
    w.unmount()
  })

  it('Zabbix fora é avisado', async () => {
    const { w } = await mountView({ statuses: {}, zabbixError: true })
    expect(w.find('[data-testid="alarms-zabbix-error"]').exists()).toBe(true)
    w.unmount()
  })
})
