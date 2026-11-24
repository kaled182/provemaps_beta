/**
 * EV-0101 — chassi interativo da OLT: regras dos LEDs (chassisLed.js), painel da ZTE C300
 * (21 baias, placas do payload), seleção de porta e de placa a filtrar a tabela, inspetor
 * (só factos; temperatura SFP «—»), rack 1U e alternador chassi/grade em localStorage.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('chart.js/auto', () => ({
  default: vi.fn(function FakeChart(el, config) {
    this.data = config.data
    this.destroy = vi.fn()
    this.update = vi.fn()
  }),
}))

import MonitoringGpon from '@/components/Monitoring/MonitoringGpon.vue'
import ChassisRack1u from '@/components/Gpon/ChassisRack1u.vue'
import { VIEW_KEY } from '@/composables/useGponOverview'
import {
  cardLeds,
  indexPons,
  linkLed,
  linkTooltip,
  ponDiagnostics,
  ponLed,
  ponState,
  ponTooltip,
  portLed,
} from '@/components/Gpon/chassisLed'
import { NOW, payload, mockFetch } from './fixtures'

const t = (w, id) => w.find(`[data-testid="${id}"]`)
const rowIds = (w) => w.findAll('[data-testid="gpon-onu-row"]').map((r) => Number(r.attributes('data-onu-id')))
const ports = (slot, n, down = []) =>
  Array.from({ length: n }, (_, i) => ({ port_id: `${slot}/${i + 1}`, port: i + 1, status: down.includes(i + 1) ? 'down' : 'up' }))
const card = (slot, card_type, role, over = {}) => ({
  slot, card_type, role, in_service: true, oper_status_code: 1, standby: null, cpu_pct: 10.0, mem_pct: 40.0, ports: [], ...over,
})

/** Payload do EV-0095 com `chassis` e `rx_worst_dbm` (EV-0101), como a ZTE BRV e uma VSOL 1U. */
function chassisPayload() {
  const body = payload()
  const [zte, vsol] = body.olts
  zte.pons = zte.pons.map((p) => ({ ...p, rx_worst_dbm: p.pon_id === '9/15' ? -25.7 : -22.0 }))
  zte.chassis = {
    layout: 'zte_c300',
    slots: [
      card(0, 'PRWH', 'power'),
      card(1, 'PRWH', 'power'),
      card(9, 'GTGHK', 'pon', { ports: ports(9, 16, [3]) }),
      card(10, 'SCXN', 'control', { standby: 'active', ports: ports(10, 4, [1, 2, 3, 4]) }),
      card(11, 'SCXN', 'control', { standby: 'standby', ports: ports(11, 4, [1, 2, 3, 4]) }),
      card(19, 'HUVQ', 'uplink', { ports: ports(19, 4, [3, 4]) }),
      card(20, 'HUVQ', 'uplink', { in_service: null, oper_status_code: null, ports: [] }),
    ],
    ports: [],
  }
  vsol.pons = [{ ...vsol.pons[0], pon_id: '0/1', label: 'PON 0/1', rx_worst_dbm: -28.1 }]
  vsol.chassis = { layout: 'rack_1u', slots: [], ports: ports(0, 8, [5]) }
  body.onus = body.onus.map((o) => (o.device_id === 11 ? { ...o, pon_id: '0/1' } : o))
  return body
}

async function mountView(body = chassisPayload()) {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(NOW)
  mockFetch(body)
  const w = mount(MonitoringGpon, { attachTo: document.body })
  await flushPromises()
  return w
}

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
  localStorage.clear()
})

describe('chassisLed — regras', () => {
  const pon = (over) => ({ pon_id: '9/1', label: 'PON 9/1', onus_provisioned: 8, capacity: 128, rx_avg_dbm: -26.3, los: 0, signal_warning: 0, signal_critical: 0, severity: 'normal', status: 'up', collective_drop: false, ...over })

  it('LED de porta PON: sem PON/sem ONUs apagado; depois a severity', () => {
    expect(ponLed(undefined)).toBe('off')
    expect(ponLed(pon({ onus_provisioned: 0, severity: 'critical' }))).toBe('off')
    expect(ponLed(pon({ severity: 'critical' }))).toBe('critical')
    expect(ponLed(pon({ severity: 'warning' }))).toBe('warning')
    expect(ponLed(pon())).toBe('ok')
  })

  it('LED de uplink/controlo: up ok, down apagado (não é alarme), unknown tracejado', () => {
    expect(linkLed('up')).toBe('ok')
    expect(linkLed('down')).toBe('off')
    expect(linkLed('unknown')).toBe('unknown')
    expect(linkLed(undefined)).toBe('unknown')
    const idx = indexPons([pon({ pon_id: '9/1', severity: 'warning' })])
    expect(portLed({ port_id: '9/1', status: 'up' }, 'pon', idx)).toBe('warning')
    expect(portLed({ port_id: '9/2', status: 'up' }, 'pon', idx)).toBe('off')
    expect(portLed({ port_id: '19/1', status: 'up' }, 'uplink', idx)).toBe('ok')
  })

  it('LEDs da placa: PWR/RUN pelo in_service, ALM por PON crítica, M/S só em controlo', () => {
    const idx = indexPons([pon({ pon_id: '9/2', severity: 'critical' }), pon({ pon_id: '8/1', severity: 'normal' })])
    expect(cardLeds(card(9, 'GTGHK', 'pon'), idx)).toEqual({ pwr: 'ok', run: 'ok', alm: 'critical', ms: null })
    expect(cardLeds(card(8, 'GTGHK', 'pon', { in_service: false }), idx)).toEqual({ pwr: 'critical', run: 'off', alm: 'off', ms: null })
    expect(cardLeds(card(0, 'PRWH', 'power', { in_service: null }), idx)).toEqual({ pwr: 'off', run: 'off', alm: 'off', ms: null })
    expect(cardLeds(card(10, 'SCXN', 'control', { standby: 'active' }), idx).ms).toBe('M')
    expect(cardLeds(card(11, 'SCXN', 'control', { standby: 'standby' }), idx).ms).toBe('S')
    expect(cardLeds(card(11, 'SCXN', 'control', { standby: null }), idx).ms).toBe(null)
    expect(cardLeds(card(9, 'GTGHK', 'pon', { standby: 'active' }), idx).ms).toBe(null)
  })

  it('tooltip, estado e diagnóstico só com factos', () => {
    expect(ponTooltip('9/13', pon({ label: 'PON 9/13', signal_warning: 5, signal_critical: 2 }))).toBe('PON 9/13 · 8/128 ONUs · RX méd: -26,3 dBm · 7 atenção')
    expect(ponTooltip('9/3', null, 'down')).toBe('PON 9/3 · sem ONUs · porta em baixo')
    expect(linkTooltip('19/1', 'uplink', 'up')).toBe('Uplink 19/1 · up')

    expect(ponState(pon()).label).toBe('Operacional')
    expect(ponState(pon({ signal_warning: 1 })).label).toBe('Atenção óptica')
    expect(ponState(pon({ collective_drop: true, los: 5 })).label).toBe('Queda massiva')
    expect(ponState(pon({ status: 'down' })).label).toBe('Porta em baixo')
    expect(ponState(null, 'down').label).toBe('Porta em baixo')
    expect(ponState(null, 'up').label).toBe('Sem ONUs')
    expect(ponState(pon({ severity: 'warning' })).label).toBe('Operacional')

    const th = { warning: -24.0, critical: -27.5 }
    expect(ponDiagnostics(pon(), th)).toEqual([])
    expect(ponDiagnostics(pon({ collective_drop: true, los: 5 }), th)[0]).toBe(
      'Queda massiva: 5 ONUs em LOS na mesma janela de 10 min — provável rompimento a montante (cabo/fusão/splitter primário).',
    )
    expect(ponDiagnostics(pon({ signal_warning: 3, signal_critical: 1 }), th)).toEqual([
      '4 ONUs com sinal abaixo de -24 dBm — verificar fusão, conector ou splitter da caixa.',
    ])
    expect(ponDiagnostics(null, th, 'down')).toEqual(['Porta PON em baixo no Zabbix.'])
  })
})

describe('Chassi ZTE C300', () => {
  it('é a vista padrão: 21 baias, placas do payload com o tipo, baias vazias sem placa', async () => {
    const w = await mountView()
    expect(t(w, 'chassis-c300').exists()).toBe(true)
    expect(w.findAll('[data-testid^="chassis-bay-"]')).toHaveLength(21)
    expect(w.findAll('[data-testid^="chassis-card-"]').map((c) => c.attributes('data-testid'))).toEqual(
      [0, 1, 9, 10, 11, 19, 20].map((n) => `chassis-card-${n}`),
    )
    expect(t(w, 'chassis-type-9').text()).toBe('GTGHK')
    expect(t(w, 'chassis-type-10').text()).toBe('SCXN')
    expect(t(w, 'chassis-type-0').text()).toBe('PRWH')
    expect(t(w, 'chassis-bay-5').find('[data-testid^="chassis-card-"]').exists()).toBe(false)
    expect(t(w, 'chassis-card-9').findAll('[data-testid^="chassis-port-"]')).toHaveLength(16)
    expect(t(w, 'chassis-card-0').findAll('[data-testid^="chassis-port-"]')).toHaveLength(0)
    expect(t(w, 'gpon-olt-22').exists()).toBe(false)
    w.unmount()
  })

  it('LEDs das portas e das placas seguem as regras', async () => {
    const w = await mountView()
    expect(t(w, 'chassis-port-9/14').classes()).toContain('led-critical')
    expect(t(w, 'chassis-port-9/15').classes()).toContain('led-warning')
    expect(t(w, 'chassis-port-9/1').classes()).toContain('led-off')
    expect(t(w, 'chassis-port-19/1').classes()).toContain('led-ok')
    expect(t(w, 'chassis-port-19/3').classes()).toContain('led-off')
    expect(t(w, 'chassis-port-10/1').classes()).toContain('led-off')
    expect(t(w, 'chassis-led-9-ALM').classes()).toContain('led-critical')
    expect(t(w, 'chassis-led-20-PWR').classes()).toContain('led-off')
    expect(t(w, 'chassis-ms-10').text()).toBe('M')
    expect(t(w, 'chassis-ms-11').text()).toBe('S')
    const port = t(w, 'chassis-port-9/14')
    expect(port.attributes('role')).toBe('button')
    expect(port.attributes('tabindex')).toBe('0')
    expect(port.attributes('aria-label')).toBe('PON 9/14 · 12/128 ONUs · RX méd: -21,3 dBm · 3 LOS')
    expect(t(w, 'chassis-port-19/1').attributes('role')).toBeUndefined()
    w.unmount()
  })

  it('hover numa porta mostra o tooltip HTML com o mesmo texto', async () => {
    const w = await mountView()
    await t(w, 'chassis-port-9/15').trigger('mouseenter')
    expect(t(w, 'chassis-tooltip').text()).toBe('PON 9/15 · 12/128 ONUs · RX méd: — · 4 atenção')
    await t(w, 'chassis-port-9/15').trigger('mouseleave')
    expect(t(w, 'chassis-tooltip').exists()).toBe(false)
    w.unmount()
  })

  it('clicar numa porta seleciona a PON e filtra a tabela; Enter também; de novo desmarca', async () => {
    const w = await mountView()
    await t(w, 'chassis-port-9/16').trigger('click')
    expect(t(w, 'chassis-port-9/16').attributes('aria-pressed')).toBe('true')
    expect(t(w, 'chassis-port-9/16').classes()).toContain('port-selected')
    expect(rowIds(w)).toEqual([505, 506])
    expect(t(w, 'insp-title').text()).toBe('PON 9/16')
    await t(w, 'chassis-port-9/16').trigger('keydown', { key: 'Enter' })
    expect(t(w, 'chassis-port-9/16').attributes('aria-pressed')).toBe('false')
    expect(rowIds(w)).toEqual([501, 502, 601, 503, 504])
    expect(t(w, 'insp-empty').exists()).toBe(true)
    w.unmount()
  })

  it('clicar no cabeçalho da placa seleciona o slot: tabela só com ONUs «9/…», âmbito «Slot 9»', async () => {
    const w = await mountView()
    await t(w, 'chassis-slot-9').trigger('click')
    expect(t(w, 'chassis-slot-9').attributes('aria-pressed')).toBe('true')
    expect(rowIds(w)).toEqual([501, 502, 503, 504, 505, 506])
    expect(t(w, 'gpon-onu-panel').find('h2').text()).toContain('Slot 9')
    expect(t(w, 'insp-title').text()).toBe('Slot 9 · GTGHK')
    expect(t(w, 'insp-slot-los').text()).toBe('3')
    expect(t(w, 'insp-slot-attention').text()).toBe('4')
    // selecionar uma porta troca a seleção (exclusivas)
    await t(w, 'chassis-port-9/15').trigger('click')
    expect(t(w, 'chassis-slot-9').attributes('aria-pressed')).toBe('false')
    expect(rowIds(w)).toEqual([503, 504])
    // trocar para outra OLT esconde a placa → desmarca
    await t(w, 'chassis-slot-9').trigger('click')
    await t(w, 'gpon-olt-select').setValue(11)
    await t(w, 'gpon-olt-select').findAll('option')[0].setSelected()
    expect(t(w, 'chassis-slot-9').exists()).toBe(true)
    expect(t(w, 'chassis-slot-9').attributes('aria-pressed')).toBe('false')
    w.unmount()
  })

  it('inspetor: temperatura SFP «—» não coletada, pior RX e diagnóstico só quando há dados', async () => {
    const w = await mountView()
    await t(w, 'chassis-port-9/15').trigger('click')
    expect(t(w, 'insp-state').text()).toBe('Atenção óptica')
    expect(t(w, 'insp-sfp-temp').text()).toBe('—')
    expect(t(w, 'insp-sfp-temp').attributes('title')).toBe('não coletado')
    expect(t(w, 'insp-rx-avg').text()).toBe('—')
    expect(t(w, 'insp-rx-worst').text()).toBe('-25,7 dBm')
    expect(t(w, 'insp-rx-worst').classes()).toContain('text-warning')
    expect(t(w, 'insp-occupancy').text()).toBe('12 / 128 ONUs · 9,4%')
    expect(t(w, 'insp-diagnostics').text()).toContain('4 ONUs com sinal abaixo de -24 dBm')

    await t(w, 'chassis-port-9/16').trigger('click')
    expect(t(w, 'insp-state').text()).toBe('Ocupação alta')
    expect(t(w, 'insp-diagnostics').findAll('li').map((l) => l.text())).toEqual([
      'Ocupação de 94% da capacidade da PON — planear expansão ou balanceamento.',
    ])

    await t(w, 'chassis-port-9/14').trigger('click')
    expect(t(w, 'insp-state').text()).toBe('Queda massiva')
    expect(t(w, 'insp-diagnostics').text()).toContain('Queda massiva: 3 ONUs em LOS')

    await t(w, 'chassis-port-9/3').trigger('click')
    expect(t(w, 'insp-state').text()).toBe('Porta em baixo')
    expect(t(w, 'insp-occupancy').text()).toBe('—')
    expect(t(w, 'insp-diagnostics').findAll('li').map((l) => l.text())).toEqual(['Porta PON em baixo no Zabbix.'])
    expect(rowIds(w)).toEqual([])
    w.unmount()
  })

  it('pílula ativa esbate as PONs fora dela sem as apagar', async () => {
    const w = await mountView()
    await t(w, 'gpon-filter-los').trigger('click')
    expect(t(w, 'chassis-port-9/14').classes()).not.toContain('port-dim')
    expect(t(w, 'chassis-port-9/15').classes()).toContain('port-dim')
    expect(t(w, 'chassis-port-9/15').classes()).toContain('led-warning')
    w.unmount()
  })
})

describe('Chassi 1U', () => {
  it('desenha as portas do payload e seleciona a PON pelo port_id', async () => {
    const w = await mountView()
    const rack = t(w, 'gpon-chassis-11').find('[data-testid="chassis-1u"]')
    expect(rack.exists()).toBe(true)
    expect(rack.findAll('[data-testid^="chassis-port-"]').map((p) => p.attributes('data-testid'))).toEqual(
      Array.from({ length: 8 }, (_, i) => `chassis-port-0/${i + 1}`),
    )
    expect(t(w, 'chassis-port-0/1').classes()).toContain('led-warning')
    expect(t(w, 'chassis-port-0/2').classes()).toContain('led-off')
    await t(w, 'chassis-port-0/1').trigger('click')
    expect(rowIds(w)).toEqual([601])
    expect(t(w, 'gpon-chassis-11').find('[data-testid="insp-rx-worst"]').text()).toBe('-28,1 dBm')
    w.unmount()
  })

  it('16 portas em duas filas e nota quando não há portas', () => {
    const olt = { vendor: 'vsol', model: 'V1600G', technology: 'gpon', status: 'online' }
    const w = mount(ChassisRack1u, { props: { chassis: { layout: 'rack_1u', slots: [], ports: ports(0, 16) }, olt } })
    expect(w.findAll('[data-testid^="chassis-port-"]')).toHaveLength(16)
    expect(t(w, 'chassis-1u-sys').classes()).toContain('led-ok')
    const e = mount(ChassisRack1u, { props: { chassis: { layout: 'rack_1u', slots: [], ports: [] }, olt } })
    expect(t(e, 'chassis-1u-empty').exists()).toBe(true)
  })
})

describe('Alternador de vista', () => {
  it('grade compacta mostra os OltCard e fica guardada no localStorage', async () => {
    const w = await mountView()
    expect(t(w, 'gpon-view-chassis').attributes('aria-pressed')).toBe('true')
    await t(w, 'gpon-view-grid').trigger('click')
    expect(t(w, 'gpon-olt-22').exists()).toBe(true)
    expect(t(w, 'gpon-olt-11').exists()).toBe(true)
    expect(t(w, 'chassis-c300').exists()).toBe(false)
    expect(localStorage.getItem(VIEW_KEY)).toBe('grid')
    w.unmount()
    vi.restoreAllMocks()
    const again = await mountView()
    expect(t(again, 'gpon-olt-22').exists()).toBe(true)
    again.unmount()
  })

  it('localStorage indisponível não parte o ecrã (padrão chassi)', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const w = await mountView()
    expect(t(w, 'chassis-c300').exists()).toBe(true)
    await t(w, 'gpon-view-grid').trigger('click')
    expect(t(w, 'gpon-olt-22').exists()).toBe(true)
    w.unmount()
  })
})

describe('EV-0101 — ocupação alta no inspetor', () => {
  it('PON em warning só por ocupação diz «Ocupação alta» e explica', async () => {
    const { ponState, ponDiagnostics } = await import('@/components/Gpon/chassisLed.js')
    const pon = { pon_id: '0/1', onus_provisioned: 60, capacity: 64, occupancy_pct: 93.8, severity: 'warning', status: 'up', los: 0, signal_warning: 0, signal_critical: 0, collective_drop: false }
    expect(ponState(pon)).toEqual({ label: 'Ocupação alta', tone: 'warning' })
    expect(ponDiagnostics(pon, { warning: -24 }).join(' ')).toMatch(/Ocupação de 94%/)
  })
})

describe('EV-0102 — chassi em grafite fixo', () => {
  it('as molduras usam os tokens --chassis-* (não a escala da marca) e os tokens não invertem no escuro', async () => {
    const { readFileSync } = await import('node:fs')
    const { resolve } = await import('node:path')
    const read = (p) => readFileSync(resolve(__dirname, '../../../src', p), 'utf8')
    for (const f of ['components/Gpon/ChassisZteC300.vue', 'components/Gpon/ChassisRack1u.vue']) {
      const css = read(f).split('<style')[1]
      expect(css).not.toMatch(/--primary-(50|[1-36-9]00|950)\b/) // primary só no realce (400/500)
      expect(css).toContain('--chassis-body')
      expect(css).not.toMatch(/#[0-9a-fA-F]{3,6}\b/)
    }
    const tokens = read('design-system/tokens.css')
    expect(tokens).toMatch(/--chassis-body: 22 25 31;/)
    expect(tokens.match(/--chassis-body:/g)).toHaveLength(1) // só no :root
  })
})
