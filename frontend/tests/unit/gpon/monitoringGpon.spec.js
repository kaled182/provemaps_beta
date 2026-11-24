/**
 * EV-0095 — ecrã Monitoramento GPON com o payload do contrato: seleção de PON,
 * «sem seleção só problemas», pílulas, busca, ordem preservada, badge do Zabbix,
 * modal de histórico e limpeza do intervalo.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

vi.mock('chart.js/auto', () => ({
  default: vi.fn(function FakeChart(el, config) {
    this.data = config.data
    this.options = config.options
    this.destroy = vi.fn()
    this.update = vi.fn()
  }),
}))

import MonitoringGpon from '@/components/Monitoring/MonitoringGpon.vue'
import { useGponOverview, REFRESH_MS, VIEW_KEY } from '@/composables/useGponOverview'
import { NOW, payload, mockFetch } from './fixtures'

const t = (w, id) => w.find(`[data-testid="${id}"]`)
const rowIds = (w) => w.findAll('[data-testid="gpon-onu-row"]').map((r) => Number(r.attributes('data-onu-id')))

async function mountView(body = payload(), history) {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(NOW)
  const spy = mockFetch(body, history)
  // Estes testes são da grade compacta (OltCard/PonCard); o chassi tem o seu spec (EV-0101).
  localStorage.setItem(VIEW_KEY, 'grid')
  const w = mount(MonitoringGpon, { attachTo: document.body })
  await flushPromises()
  return { w, spy }
}

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
  localStorage.clear()
})

describe('MonitoringGpon', () => {
  it('pede o overview sem ?olt e, sem seleção, mostra só as ONUs com problema na ordem do payload', async () => {
    const { w, spy } = await mountView()
    expect(spy.mock.calls[0][0]).toBe('/api/v1/monitoring/gpon/')
    expect(rowIds(w)).toEqual([501, 502, 601, 503, 504])
    w.unmount()
  })

  it('clicar numa PON filtra a tabela e clicar de novo desmarca', async () => {
    const { w } = await mountView()
    await t(w, 'gpon-pon-9/16').trigger('click')
    expect(t(w, 'gpon-pon-9/16').classes()).toContain('pon-selected')
    expect(rowIds(w)).toEqual([505, 506])
    await t(w, 'gpon-pon-9/16').trigger('click')
    expect(t(w, 'gpon-pon-9/16').classes()).not.toContain('pon-selected')
    expect(rowIds(w)).toEqual([501, 502, 601, 503, 504])
    w.unmount()
  })

  it('escolher a OLT mostra todas as ONUs dela', async () => {
    const { w } = await mountView()
    await t(w, 'gpon-olt-select').setValue(11)
    expect(rowIds(w)).toEqual([601])
    expect(w.find('[data-testid="gpon-olt-22"]').exists()).toBe(false)
    w.unmount()
  })

  it('pílulas LOS, sinal crítico e ocupação filtram PONs e ONUs', async () => {
    const { w } = await mountView()
    await t(w, 'gpon-filter-los').trigger('click')
    expect(rowIds(w)).toEqual([501, 502])
    expect(t(w, 'gpon-pon-9/14').exists()).toBe(true)
    expect(t(w, 'gpon-pon-9/15').exists()).toBe(false)
    expect(t(w, 'gpon-olt-11').exists()).toBe(false)

    await t(w, 'gpon-filter-critical').trigger('click')
    expect(rowIds(w)).toEqual([601])
    expect(t(w, 'gpon-olt-22').exists()).toBe(false)

    await t(w, 'gpon-filter-occupancy').trigger('click')
    expect(rowIds(w)).toEqual([505, 506])
    expect(t(w, 'gpon-pon-9/16').exists()).toBe(true)
    w.unmount()
  })

  it('busca por serial, MAC ou cliente (inclui ONUs online)', async () => {
    const { w } = await mountView()
    await t(w, 'gpon-query').setValue('maria')
    expect(rowIds(w)).toEqual([601])
    await t(w, 'gpon-query').setValue('AA:BB')
    expect(rowIds(w)).toEqual([601])
    await t(w, 'gpon-query').setValue('zyxok')
    expect(rowIds(w)).toEqual([506])
    await t(w, 'gpon-query').setValue('zyx')
    expect(rowIds(w)).toEqual([501, 502, 503, 504, 505, 506])
    w.unmount()
  })

  it('badges de estado, cliente por baixo e «desde» na tabela', async () => {
    const { w } = await mountView()
    const rows = w.findAll('[data-testid="gpon-onu-row"]')
    const status = rows.map((r) => r.find('[data-testid="gpon-onu-status"]'))
    expect(status[0].text()).toBe('LOS (fibra)')
    expect(status[0].classes()).toContain('tag-danger')
    expect(status[0].attributes('title')).toBe('LOS')
    expect(status[4].text()).toBe('Dying Gasp')
    expect(status[4].classes()).toContain('tag-info')
    expect(rows[2].text()).toContain('Maria Souza')
    expect(rows[2].find('[data-testid="gpon-onu-rx"]').classes()).toContain('text-danger')
    expect(rows[2].find('[data-testid="gpon-onu-rx"]').text()).toContain('-28,1 dBm')
    expect(rows[0].find('[data-testid="gpon-onu-since"]').text()).toBe('1,9 km · há 15 min')
    expect(rows[4].find('[data-testid="gpon-onu-since"]').text()).toBe('1,9 km · ≥ 15 min')
    await t(w, 'gpon-pon-9/16').trigger('click')
    const unk = w.findAll('[data-testid="gpon-onu-row"]')[0]
    expect(unk.find('[data-testid="gpon-onu-status"]').classes()).toContain('tag-unknown')
    expect(unk.find('[data-testid="gpon-onu-since"]').text()).toBe('—')
    // EV-0119: a ficha abre na linha mesmo sem histórico, e diz que não há
    await unk.find('[data-testid="gpon-onu-history"]').trigger('click')
    expect(w.find('[data-testid="onu-detail-no-history"]').exists()).toBe(true)
    w.unmount()
  })

  it('badge do Zabbix: ativo, coleta atrasada, indisponível; tooltip dos limiares', async () => {
    let { w } = await mountView()
    expect(t(w, 'gpon-zabbix-badge').text()).toBe('Zabbix ativo')
    expect(t(w, 'gpon-thresholds').attributes('title')).toBe('Normal > -24 dBm · Atenção -24 a -27,5 · Crítico < -27,5')
    w.unmount()
    vi.restoreAllMocks()
    ;({ w } = await mountView(payload({ collected_at: '2026-11-24T01:50:00Z' })))
    expect(t(w, 'gpon-zabbix-badge').text()).toBe('Coleta atrasada')
    w.unmount()
    vi.restoreAllMocks()
    ;({ w } = await mountView(payload({ zabbix_ok: false, zabbix_error: 'timeout' })))
    expect(t(w, 'gpon-zabbix-badge').text()).toBe('Zabbix indisponível')
    expect(t(w, 'gpon-zabbix-down').exists()).toBe(true)
    w.unmount()
  })

  it('EV-0119: ficha na linha — pede hours, 24 h / 7 d, distingue «Zabbix indisponível», uma aberta de cada vez', async () => {
    const { w, spy } = await mountView(payload(), { onu_id: 501, unit: 'dBm', label: 'RX na OLT', points: [], zabbix_ok: false, zabbix_error: null })
    await w.findAll('[data-testid="gpon-onu-row"]')[0].trigger('click')
    await flushPromises()
    expect(spy.mock.calls.at(-1)[0]).toBe('/api/v1/monitoring/gpon/onus/501/history/?hours=24')
    expect(t(w, 'onu-detail-501').exists()).toBe(true)
    expect(t(w, 'onu-detail-zabbix-down').text()).toContain('Zabbix indisponível')
    expect(t(w, 'onu-detail-diagnosis').text()).toContain('LOS')
    await t(w, 'onu-detail-hours-168').trigger('click')
    await flushPromises()
    expect(spy.mock.calls.at(-1)[0]).toBe('/api/v1/monitoring/gpon/onus/501/history/?hours=168')
    expect(document.body.querySelector('[data-testid="base-modal"]')).toBeNull() // nada de modal
    await w.findAll('[data-testid="gpon-onu-row"]')[1].trigger('click')
    await flushPromises()
    expect(w.findAll('[data-testid^="onu-detail-5"]').filter((x) => /^onu-detail-\d+$/.test(x.attributes('data-testid')))).toHaveLength(1)
    await w.findAll('[data-testid="gpon-onu-history"]')[1].trigger('click') // fecha
    expect(w.find('[data-testid="onu-detail-502"]').exists()).toBe(false)
    w.unmount()
  })

  it('EV-0119: histórico sem pontos diz «Sem leituras no período»', async () => {
    const { w } = await mountView(payload(), { onu_id: 501, unit: 'dBm', label: 'RX na OLT', points: [], zabbix_ok: true, zabbix_error: null })
    await w.findAll('[data-testid="gpon-onu-row"]')[0].trigger('click')
    await flushPromises()
    expect(t(w, 'onu-detail-empty').text()).toBe('Sem leituras no período.')
    w.unmount()
  })

  it('EV-0119: pílulas Todas / Com falha / Sinal e busca dentro da lista; trocar de PON repõe', async () => {
    const { w } = await mountView()
    await t(w, 'gpon-pon-9/15').trigger('click')
    expect(t(w, 'pol-filter-all').text()).toBe('Todas (2)')
    expect(t(w, 'pol-filter-failure').text()).toBe('Com falha / LOS (1)')
    expect(t(w, 'pol-filter-signal').text()).toBe('Sinal crítico / atenção (1)')
    await t(w, 'pol-filter-signal').trigger('click')
    expect(w.findAll('[data-testid="gpon-onu-row"]').map((r) => r.attributes('data-onu-id'))).toEqual(['503'])
    await t(w, 'pol-filter-all').trigger('click')
    await t(w, 'pol-search').setValue('zyxdg')
    expect(w.findAll('[data-testid="gpon-onu-row"]').map((r) => r.attributes('data-onu-id'))).toEqual(['504'])
    await t(w, 'gpon-pon-9/16').trigger('click')
    expect(t(w, 'pol-search').element.value).toBe('')
    w.unmount()
  })

  it('EV-0120: rede → OLT → PON — KPIs, trilha e tabela afunilam; × volta um nível', async () => {
    const { w } = await mountView()
    expect(t(w, 'gpon-funnel').exists()).toBe(false)
    expect(t(w, 'gpon-kpi-olts').text()).toContain('OLTs ativas')
    await t(w, 'gpon-olt-select').setValue('22')
    await flushPromises()
    // a OLT abre já na PON mais crítica (EV-0106): nível PON
    expect(t(w, 'gpon-funnel-olt').text()).toContain('ZTE - OLT BRV C300')
    expect(t(w, 'gpon-funnel-pon').text()).toContain('PON 9/14')
    expect(t(w, 'gpon-kpi-olt-status').text()).toBe('Online')
    expect(t(w, 'gpon-kpi-los').text()).toContain('2')
    expect(t(w, 'gpon-kpi-dying').text()).toContain('0')
    expect(t(w, 'gpon-kpi-olts').text()).toContain('1 PON')
    // × da porta: a OLT inteira, sem reescolher a PON
    await t(w, 'gpon-funnel-pon-clear').trigger('click')
    await flushPromises()
    expect(t(w, 'gpon-funnel-pon').exists()).toBe(false)
    expect(t(w, 'gpon-kpi-dying').text()).toContain('1')
    expect(t(w, 'gpon-kpi-onus').text()).toContain('/ 6')
    expect(t(w, 'gpon-kpi-olts').text()).toContain('3 PONs')
    expect(w.findAll('[data-testid="gpon-onu-row"]')).toHaveLength(6)
    // × da OLT: rede inteira
    await t(w, 'gpon-funnel-network').trigger('click')
    await flushPromises()
    expect(t(w, 'gpon-funnel').exists()).toBe(false)
    expect(t(w, 'gpon-olt-select').element.selectedIndex).toBe(0)
    expect(t(w, 'gpon-kpi-olts').text()).toContain('OLTs ativas')
    w.unmount()
  })

  it('EV-0120: clicar numa PON no chassi sem OLT escolhida também afunila', async () => {
    const { w } = await mountView()
    await t(w, 'gpon-pon-9/15').trigger('click')
    expect(t(w, 'gpon-funnel-pon').text()).toContain('PON 9/15')
    expect(t(w, 'gpon-kpi-signal').text()).toContain('+ 1')
    expect(t(w, 'gpon-kpi-onus').text()).toContain('/ 2')
    w.unmount()
  })

  it('EV-0122: a lista não encolhe a 0 px debaixo de um chassi alto (flex-col com min-h-0)', async () => {
    const { w } = await mountView()
    const panel = t(w, 'gpon-onu-panel')
    expect(panel.classes()).toContain('shrink-0')
    expect(panel.classes()).not.toContain('overflow-auto')
    w.unmount()
  })

  it('limita a renderização a 200 linhas com «Mostrar mais»', async () => {
    const base = payload()
    const many = Array.from({ length: 250 }, (_, i) => ({ ...base.onus[0], id: 1000 + i, onu_index: i }))
    const { w } = await mountView({ ...base, onus: many })
    expect(rowIds(w)).toHaveLength(200)
    await t(w, 'gpon-onu-more').trigger('click')
    expect(rowIds(w)).toHaveLength(250)
    w.unmount()
  })
})

describe('useGponOverview', () => {
  it('refresca a cada 60 s e limpa o intervalo ao desmontar', async () => {
    mockFetch(payload())
    const setSpy = vi.spyOn(globalThis, 'setInterval')
    const clearSpy = vi.spyOn(globalThis, 'clearInterval')
    const Host = defineComponent({ setup() { useGponOverview(); return () => h('div') } })
    const w = mount(Host)
    await flushPromises()
    const call = setSpy.mock.calls.find((c) => c[1] === REFRESH_MS)
    expect(call).toBeTruthy()
    const id = setSpy.mock.results[setSpy.mock.calls.indexOf(call)].value
    w.unmount()
    expect(clearSpy).toHaveBeenCalledWith(id)
  })
})
