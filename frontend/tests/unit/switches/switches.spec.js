/**
 * EV-0115 — tela de Switches: recortes (POP, switch, pílulas, busca), KPIs do recorte sem
 * números inventados, tabela pior-primeiro com livres ocultas, gráfico só com porta no
 * inventário, Zabbix fora avisado, e a entrada no menu Monitoramento.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { portMatchesFilter, portMatchesQuery, mostCriticalPort } from '@/composables/useSwitchesOverview'
import { NAV_SECTIONS } from '@/composables/useNavSections'

const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('chart.js/auto', () => ({
  default: vi.fn(function FakeChart(el, config) {
    this.data = config.data
    this.options = config.options
    this.destroy = vi.fn()
    this.update = vi.fn()
  }),
}))
vi.mock('@/components/PortTrafficModal.vue', () => ({
  __esModule: true,
  default: { props: ['isOpen', 'port'], template: '<div v-if="isOpen" data-testid="traffic-modal">{{ port.id }} {{ port.name }}</div>' },
}))

import MonitoringSwitches from '@/components/Monitoring/MonitoringSwitches.vue'

const port = (over) => ({
  device_id: 6, switch_name: 'huawei - Switch Confresa', name: 'XGigabitEthernet0/0/1', description: 'Enlace-Veranopolis',
  kind: 'optical', speed_mbps: 10000, speed_label: '10G', admin: 'up', oper: 'up', in_use: true, state: 'normal', reasons: [],
  rx_dbm: -15.39, tx_dbm: 1.28, los: false, in_bps: 1254920192, out_bps: 147114224, utilization_pct: 12.5,
  in_errors: 0, out_errors: 0, uptime_s: 3383530, port_id: 101, cable_id: null, cable_name: null, severity_rank: 4,
  ...over,
})
const sw = (over) => ({
  device_id: 6, name: 'huawei - Switch Confresa', vendor: 'huawei', model: 'S6730-H24X6C', ip: '198.18.27.1',
  site_id: 3, site_name: 'SITE - CONFRESA', status: 'online', collection_ok: true, cpu_pct: 5, temperature_c: 33,
  uptime_s: 7046891, ports_total: 4, ports_up: 2, ports_in_use: 3, ports_down: 1, signal_warning: 1, signal_critical: 0,
  high_utilization: 0, worst_rx_dbm: -21.43, last_clock: '2026-11-24T18:00:00Z', ...over,
})
const PAYLOAD = {
  collected_at: '2026-11-24T18:00:30Z', zabbix_ok: true, zabbix_error: null,
  thresholds: { warning: -20, critical: -24, utilization_pct: 80 },
  totals: {},
  switches: [
    sw({}),
    sw({ device_id: 8, name: 'Huawei - Switch Santa terezinha', site_name: 'SITE - SANTA TEREZINHA', status: 'offline', model: null, cpu_pct: null, temperature_c: null, worst_rx_dbm: null, ports_in_use: 0, ports_down: 0 }),
  ],
  ports: [
    port({}),
    port({ name: 'XGigabitEthernet0/0/2', description: null, state: 'down', reasons: ['los'], rx_dbm: null, los: true, oper: 'down', in_bps: 0, out_bps: 0, uptime_s: null, cable_name: 'CONFRESA - VLR', cable_id: 9, severity_rank: 0 }),
    port({ name: 'XGigabitEthernet0/0/3', description: 'Enlace-Elagro', state: 'warning', reasons: ['rx_warning'], rx_dbm: -21.43, severity_rank: 2, port_id: null }),
    port({ name: 'XGigabitEthernet0/0/4', description: null, state: 'free', in_use: false, oper: 'down', rx_dbm: null, severity_rank: 5 }),
    port({ name: 'MEth0/0/1', kind: 'mgmt', speed_label: '1G' }),
    port({ device_id: 8, switch_name: 'Huawei - Switch Santa terezinha', name: 'XGigabitEthernet0/0/1', state: 'unknown', oper: 'unknown', in_use: false, rx_dbm: null, severity_rank: 3 }),
  ],
  duration_ms: 900,
}

const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })

afterEach(() => {
  vi.restoreAllMocks()
  push.mockClear()
  window.history.replaceState(null, '', '/')
  try { localStorage.clear() } catch { /* sem armazenamento */ }
})

describe('regras puras', () => {
  it('pílulas, busca e porta mais crítica', () => {
    const down = port({ state: 'down', reasons: ['los'], severity_rank: 0 })
    expect(portMatchesFilter(down, 'down')).toBe(true)
    expect(portMatchesFilter(port({ reasons: ['rx_critical'] }), 'critical')).toBe(true)
    expect(portMatchesFilter(port({ reasons: ['utilization'] }), 'utilization')).toBe(true)
    expect(portMatchesFilter(port({}), 'down')).toBe(false)
    expect(portMatchesQuery(port({ cable_name: 'CONFRESA - VLR' }), 'vlr')).toBe(true)
    expect(portMatchesQuery(port({}), 'elagro')).toBe(false)
    expect(mostCriticalPort([port({}), down, port({ kind: 'mgmt', severity_rank: 0, state: 'down' })])).toBe(down)
  })

  it('Switches entra no menu Monitoramento logo depois do GPON', () => {
    const items = NAV_SECTIONS.find((s) => s.id === 'monitoramento').items.map((i) => i.path)
    expect(items.indexOf('/monitoring/switches')).toBe(items.indexOf('/monitoring/gpon') + 1)
  })
})

describe('MonitoringSwitches', () => {
  async function mountPage(body = PAYLOAD, { view = 'grid', history = {} } = {}) {
    localStorage.setItem('provemaps.switches.view', view)
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      for (const [prefix, reply] of Object.entries(history)) if (url.startsWith(prefix)) return ok(reply)
      return ok(body)
    })
    const w = mount(MonitoringSwitches, { attachTo: document.body })
    await flushPromises()
    return { w, spy }
  }

  it('KPIs do recorte, cartões e tabela pior primeiro sem as livres nem a gerência', async () => {
    const { w, spy } = await mountPage()
    expect(spy.mock.calls[0][0]).toBe('/api/v1/monitoring/switches/')
    expect(w.get('[data-testid="sw-zabbix-badge"]').text()).toBe('Zabbix ativo')
    expect(w.get('[data-testid="sw-kpi-switches"]').text()).toContain('1/ 2')
    expect(w.get('[data-testid="sw-kpi-down"]').text()).toContain('1 sem luz (LOS)')
    expect(w.get('[data-testid="sw-kpi-hardware"]').text()).toContain('33 °C')
    expect(w.findAll('[data-testid="sw-card"]')).toHaveLength(2)
    const rows = w.findAll('[data-testid="sw-port-row"]')
    expect(rows.map((r) => r.find('td').text())).toEqual([
      'XGigabitEthernet0/0/2huawei - Switch Confresa',
      'XGigabitEthernet0/0/3huawei - Switch Confresa',
      'XGigabitEthernet0/0/1Huawei - Switch Santa terezinha',
      'XGigabitEthernet0/0/1huawei - Switch Confresa',
    ])
    expect(rows[0].get('[data-testid="sw-port-state"]').text()).toBe('LOS')
    expect(rows[0].text()).toContain('-40 (LOS)')
    expect(w.get('[data-testid="sw-port-table"]').text()).toContain('1 livres ocultas')
    w.unmount()
  })

  it('switch, pílula e busca recortam; gráfico abre o modal da porta do inventário', async () => {
    const { w } = await mountPage()
    await w.get('[data-testid="sw-switch-select"]').setValue('6')
    await w.get('[data-testid="sw-filter-down"]').trigger('click')
    expect(w.findAll('[data-testid="sw-port-row"]')).toHaveLength(1)
    await w.get('[data-testid="sw-filter-all"]').trigger('click')
    await w.get('[data-testid="sw-query"]').setValue('veranopolis')
    const rows = w.findAll('[data-testid="sw-port-row"]')
    expect(rows).toHaveLength(1)
    await rows[0].get('[data-testid="sw-port-chart"]').trigger('click')
    expect(w.get('[data-testid="traffic-modal"]').text()).toBe('101 XGigabitEthernet0/0/1 · Enlace-Veranopolis')
    w.unmount()
  })

  it('porta sem inventário não tem gráfico; ?pop= do endereço recorta ao abrir', async () => {
    window.history.replaceState(null, '', '/monitoring/switches?pop=SITE%20-%20CONFRESA')
    const { w } = await mountPage()
    expect(w.findAll('[data-testid="sw-card"]')).toHaveLength(1)
    const elagro = w.findAll('[data-testid="sw-port-row"]').find((r) => r.text().includes('Enlace-Elagro'))
    expect(elagro.get('[data-testid="sw-port-chart"]').attributes('disabled')).toBeDefined()
    w.unmount()
  })

  it('Zabbix fora é avisado e o switch sem dados diz isso', async () => {
    const down = { ...PAYLOAD, zabbix_ok: false, zabbix_error: 'item.get sem resposta', ports: [], switches: PAYLOAD.switches.map((s) => ({ ...s, status: 'unknown', collection_ok: false })) }
    const { w } = await mountPage(down)
    expect(w.get('[data-testid="sw-zabbix-badge"]').text()).toBe('Zabbix indisponível')
    expect(w.find('[data-testid="sw-zabbix-down"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="sw-card-nodata"]')).toHaveLength(2)
    w.unmount()
  })
})

describe('vista do chassi (EV-0116)', () => {
  async function mountChassis(history = {}) {
    localStorage.setItem('provemaps.switches.view', 'chassis')
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      for (const [prefix, reply] of Object.entries(history)) if (url.startsWith(prefix)) return ok(reply)
      return ok(PAYLOAD)
    })
    const w = mount(MonitoringSwitches, { attachTo: document.body })
    await flushPromises()
    return { w, spy }
  }

  it('desenha as portas reais com LED pelo estado e a legenda de portas', async () => {
    const { w } = await mountChassis()
    const chassis = w.get('[data-testid="sw-chassis-6"]')
    expect(chassis.find('[data-testid="sw-port-XGigabitEthernet0/0/2"]').classes()).toContain('led-critical')
    expect(chassis.find('[data-testid="sw-port-XGigabitEthernet0/0/3"]').classes()).toContain('led-warning')
    expect(chassis.find('[data-testid="sw-port-XGigabitEthernet0/0/4"]').classes()).toContain('led-off')
    expect(chassis.find('[data-testid="sw-port-MEth0/0/1"]').exists()).toBe(true)
    expect(chassis.get('[data-testid="chassis-legend-count"]').text()).toBe('3 portas ativas · 1 livres')
    expect(chassis.text()).toContain('10G SFP+')
    w.unmount()
  })

  it('o inspetor abre na porta mais crítica e segue o clique; copiar resumo e enlace no mapa', async () => {
    const writeText = vi.fn(() => Promise.resolve())
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const { w } = await mountChassis()
    const insp = () => w.get('[data-testid="sw-inspector-6"]')
    expect(insp().get('[data-testid="spi-name"]').text()).toBe('XGigabitEthernet0/0/2')
    expect(insp().get('[data-testid="spi-state"]').text()).toBe('DOWN · LOS')
    expect(insp().find('[data-testid="spi-preview"]').exists()).toBe(true)
    await insp().get('[data-testid="spi-map"]').trigger('click')
    expect(push).toHaveBeenCalledWith({ path: '/monitoring/backbone/map/default', query: { cable: '9' } })
    await w.get('[data-testid="sw-port-XGigabitEthernet0/0/1"]').trigger('click')
    expect(insp().get('[data-testid="spi-name"]').text()).toBe('XGigabitEthernet0/0/1')
    expect(insp().find('[data-testid="spi-preview"]').exists()).toBe(false)
    expect(insp().get('[data-testid="spi-map"]').attributes('disabled')).toBeDefined() // sem cabo
    await insp().get('[data-testid="spi-copy"]').trigger('click')
    await flushPromises()
    expect(writeText.mock.calls[0][0]).toContain('Porta: XGigabitEthernet0/0/1 — Enlace-Veranopolis')
    expect(insp().get('[data-testid="spi-copy"]').text()).toBe('Copiado!')
    w.unmount()
  })

  it('24 h de tráfego e RX pela porta do inventário; sem inventário diz que não há histórico', async () => {
    const t0 = 1795453740
    const traffic = { in: { history: [{ timestamp: t0, value: 1.2e9 }, { timestamp: t0 + 60, value: 1.1e9 }] }, out: { history: [{ timestamp: t0, value: 1e8 }, { timestamp: t0 + 60, value: 2e8 }] } }
    const optical = [{ timestamp: '2026-11-24T10:00:00+00:00', rx_power: -15.4, tx_power: 1.3 }, { timestamp: '2026-11-24T11:00:00+00:00', rx_power: -15.5, tx_power: 1.3 }]
    const { w, spy } = await mountChassis({ '/api/v1/ports/101/traffic_history/': traffic, '/api/v1/ports/101/optical_history/': optical })
    await w.get('[data-testid="sw-port-XGigabitEthernet0/0/1"]').trigger('click')
    await flushPromises()
    const urls = spy.mock.calls.map(([u]) => u)
    expect(urls).toContain('/api/v1/ports/101/traffic_history/?hours=24')
    expect(urls).toContain('/api/v1/ports/101/optical_history/?hours=24')
    expect(w.get('[data-testid="sw-inspector-6"]').findAll('canvas')).toHaveLength(2)
    await w.get('[data-testid="sw-port-XGigabitEthernet0/0/3"]').trigger('click') // port_id null
    await flushPromises()
    expect(w.find('[data-testid="spi-no-inventory"]').exists()).toBe(true)
    w.unmount()
  })

  it('filtro esbate no chassi as portas que não passam', async () => {
    const { w } = await mountChassis()
    await w.get('[data-testid="sw-filter-down"]').trigger('click')
    const chassis = w.get('[data-testid="sw-chassis-6"]')
    expect(chassis.get('[data-testid="sw-port-XGigabitEthernet0/0/1"]').classes()).toContain('port-dim')
    expect(chassis.get('[data-testid="sw-port-XGigabitEthernet0/0/2"]').classes()).not.toContain('port-dim')
    w.unmount()
  })

  it('a vista escolhida fica guardada', async () => {
    const { w } = await mountChassis()
    await w.get('[data-testid="sw-view-grid"]').trigger('click')
    expect(localStorage.getItem('provemaps.switches.view')).toBe('grid')
    expect(w.findAll('[data-testid="sw-card"]')).toHaveLength(2)
    w.unmount()
  })
})

describe('EV-0117: Ubiquiti no chassi', () => {
  it('portas «0/n» num grupo neutro «Portas», marca UBIQUITI, e o filtro de fabricante tem Ubiquiti', async () => {
    const { default: SwitchChassis1u } = await import('@/components/Switches/SwitchChassis1u.vue')
    const ubq = { ...PAYLOAD.switches[0], device_id: 12, name: 'Ubiquiti - Switch Barreira velha', vendor: 'ubiquiti', model: 'EdgeSwitch 16 XG' }
    const ports = [
      port({ device_id: 12, name: '0/1', kind: 'electrical', speed_label: '> 4G' }),
      port({ device_id: 12, name: '0/2', kind: 'electrical', speed_label: '1G', state: 'free', in_use: false }),
    ]
    const w = mount(SwitchChassis1u, { props: { sw: ubq, ports } })
    expect(w.text()).toContain('UBIQUITI')
    expect(w.text()).toContain('Portas')
    expect(w.text()).not.toContain('SFP+')
    expect(w.find('[data-testid="sw-port-0/1"]').classes()).toContain('led-ok')
    const { VENDOR_LABELS } = await import('@/composables/useSwitchesOverview')
    expect(VENDOR_LABELS.ubiquiti).toBe('Ubiquiti')
  })
})

