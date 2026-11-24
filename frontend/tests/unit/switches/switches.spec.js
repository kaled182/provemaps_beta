/**
 * EV-0115 — tela de Switches: recortes (POP, switch, pílulas, busca), KPIs do recorte sem
 * números inventados, tabela pior-primeiro com livres ocultas, gráfico só com porta no
 * inventário, Zabbix fora avisado, e a entrada no menu Monitoramento.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { portMatchesFilter, portMatchesQuery, mostCriticalPort } from '@/composables/useSwitchesOverview'
import { NAV_SECTIONS } from '@/composables/useNavSections'

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
  window.history.replaceState(null, '', '/')
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
  async function mountPage(body = PAYLOAD) {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok(body))
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
